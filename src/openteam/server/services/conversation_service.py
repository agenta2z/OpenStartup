"""ConversationService — renders conversation prompts and manages LLM interactions.

Responsibilities:
1. Render initial.jinja2 with session history + user input
2. Call LLM via configurable backend (ai-gateway, direct API, or mock)
3. Parse <Response> tags from LLM output
4. Return the assistant's response content

Does NOT manage session persistence — that's SessionStore's job.
The route handler orchestrates: append user msg → call service → append response.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class _SimplePromptRenderer:
    """Minimal PromptRenderer conforming to ConversationalInferencer's protocol.

    Uses Jinja2 directly, avoiding JinjaPromptRenderer's YAML config loading
    which depends on a newer merge_mappings signature.
    """

    def __init__(self, templates_dir: Path) -> None:
        from jinja2 import Environment, FileSystemLoader

        self._templates_dir = templates_dir
        self._template_path = "conversation/main/initial.jinja2"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=False,
        )
        self._variable_manager = None

    def render(self, variables: dict) -> str:
        template = self._env.get_template(self._template_path)
        return template.render(**variables)

    def render_string(self, template_str: str, context: dict) -> str:
        template = self._env.from_string(template_str)
        return template.render(**context)

    @property
    def template_source(self) -> str:
        source = self._env.loader.get_source(self._env, self._template_path)
        return source[0]

    @property
    def template_config(self) -> dict:
        return {}

    @property
    def template_variables(self) -> dict:
        """Load .variables.yaml from the template directory."""
        template_dir = self._templates_dir / "conversation" / "main"
        variables_file = template_dir / ".variables.yaml"
        if variables_file.is_file():
            import yaml

            try:
                data = yaml.safe_load(variables_file.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

    @property
    def variable_manager(self):
        return self._variable_manager

    def find_sop_file(self) -> Path | None:
        template_dir = self._templates_dir / "conversation" / "main"
        variables_dir = template_dir / "_variables" / "workflow"
        if not variables_dir.is_dir():
            return None
        for ext in (".jinja2", ".j2", ".md", ".yaml", ".yml"):
            candidate = variables_dir / f"sop{ext}"
            if candidate.is_file():
                return candidate
        return None


def _build_prompt_renderer(templates_dir: Path) -> _SimplePromptRenderer:
    """Build a PromptRenderer for the ConversationalInferencer."""
    return _SimplePromptRenderer(templates_dir)


class ConversationService:
    """Renders conversation prompts and manages LLM interactions."""

    def __init__(
        self,
        templates_dir: Path,
        llm_backend: str = "mock",
        working_dir: str | None = None,
        cache_dir: str | None = None,
    ) -> None:
        self._templates_dir = templates_dir
        self._llm_backend = llm_backend
        self._working_dir = working_dir or str(Path.home())
        self._cache_dir = cache_dir
        self._inferencer = None
        self._template_manager = self._build_template_manager()
        if llm_backend == "rovodev":
            self._inferencer = self._build_rovodev_inferencer()

    def _build_template_manager(self):
        """Create TemplateManager for conversation prompt rendering.

        Uses the same TemplateManager pattern as create_role/executor.py:
        - Root: prompt_templates/
        - active_template_type: "main"
        - predefined_variables: True (loads .variables.yaml for {{ employee }})

        Falls back to raw Jinja2 rendering if TemplateManager is not available.
        """
        try:
            from rich_python_utils.string_utils.formatting.template_manager import (
                TemplateManager,
            )

            return TemplateManager(
                templates=str(self._templates_dir),
                active_template_type="main",
                predefined_variables=True,
            )
        except ImportError:
            logger.warning(
                "rich_python_utils not available — using fallback Jinja2 rendering"
            )
            return None

    def render_prompt(self, session: dict, user_message: str) -> str:
        """Render the conversation prompt with session history + current turn.

        Builds the template feed:
        - conversation_history: list of {role, content} from session.messages
        - current_turn: {role: "manager", content: user_message}
        - employee: auto-injected from .variables.yaml (via TemplateManager)
        """
        messages = session.get("messages", [])

        # Build conversation_history from existing messages
        conversation_history = []
        for msg in messages:
            role = msg.get("role", "manager")
            # Map OpenStartup roles to prompt template roles
            prompt_role = "manager" if role in ("manager", "user") else "assistant"
            conversation_history.append(
                {
                    "role": prompt_role,
                    "content": msg.get("content", ""),
                }
            )

        current_turn = {"role": "manager", "content": user_message}

        if self._template_manager is not None:
            return self._template_manager(
                "initial",
                active_template_root_space="conversation",
                conversation_history=conversation_history,
                current_turn=current_turn,
                # Workflow variables not passed — template guards with {% if defined %}
            )

        # Fallback: raw Jinja2 rendering
        return self._render_fallback(conversation_history, current_turn)

    def _build_rovodev_inferencer(self):
        """Create a ConversationalInferencer wrapping RovoDevCliInferencer.

        Architecture:
            ConversationalInferencer (prompt rendering, history, agentic loop)
                └── base_inferencer: RovoDevCliInferencer (LLM streaming via acli)

        The ConversationalInferencer handles:
        - Prompt rendering via the template manager (initial.jinja2)
        - Conversation history management (_messages)
        - Agentic loop with tool execution and conversation tools
        - Streaming via base_inferencer.ainfer_streaming()
        """
        try:
            from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev import (
                RovoDevCliInferencer,
            )
            from agent_foundation.common.inferencers.agentic_inferencers.conversational.conversational_inferencer import (
                ConversationalInferencer,
            )

            # 1. Create the base inferencer (RovoDev CLI) with streaming cache
            cache_folder = self._cache_dir

            base = RovoDevCliInferencer(
                working_dir=self._working_dir,
                idle_timeout_seconds=600,
                tool_use_idle_timeout_seconds=600,
                cache_folder=cache_folder,
            )
            logger.info(
                "RovoDevCliInferencer initialized (working_dir=%s, acli=%s, cache=%s)",
                self._working_dir,
                base.acli_path,
                cache_folder,
            )

            # 2. Build prompt renderer (JinjaPromptRenderer conforms to PromptRenderer protocol)
            from agent_foundation.common.inferencers.agentic_inferencers.conversational.prompt_rendering import (
                JinjaPromptRenderer,
            )

            prompt_renderer = JinjaPromptRenderer(
                template_dir=str(self._templates_dir),
                template_path="conversation/main/initial.jinja2",
            )

            # 3. Wrap in ConversationalInferencer
            conv_inferencer = ConversationalInferencer(
                base_inferencer=base,
                prompt_renderer=prompt_renderer,
                max_iterations=5,
                compression_threshold=8000,
            )
            logger.info("ConversationalInferencer wrapping RovoDevCliInferencer")

            return conv_inferencer

        except ImportError as e:
            logger.error("Failed to import inferencer: %s", e)
            logger.error(
                "Ensure AgentFoundation/src and RichPythonUtils/src are on PYTHONPATH"
            )
            raise
        except Exception as e:
            logger.error("Failed to create inferencer: %s", e)
            raise

    async def astream_response(self, session: dict, user_message: str):
        """Stream response tokens for the user's message.

        Yields individual text chunks. For mock backend, simulates streaming
        by yielding word-by-word. For rovodev backend, streams real LLM output
        line-by-line from ``acli rovodev run``.

        The caller is responsible for persisting messages — this method
        only renders the prompt, calls the LLM, and yields chunks.
        """
        if self._llm_backend == "mock":
            rendered_prompt = self.render_prompt(session, user_message)
            raw_response = self._mock_response(user_message)
            parsed = self._parse_response(raw_response)
            # Simulate streaming: yield word-by-word with tiny delays
            words = parsed.split(" ")
            for i, word in enumerate(words):
                chunk = word if i == 0 else " " + word
                yield chunk
                await asyncio.sleep(0.03)  # 30ms per word — feels natural

        elif self._llm_backend == "rovodev":
            if self._inferencer is None:
                raise RuntimeError("ConversationalInferencer not initialized")

            # Sync conversation history from session into the inferencer
            messages = session.get("messages", [])
            conv_messages = []
            for msg in messages:
                role = msg.get("role", "manager")
                prompt_role = "user" if role in ("manager", "user") else "assistant"
                conv_messages.append(
                    {"role": prompt_role, "content": msg.get("content", "")}
                )
            self._inferencer.set_messages(conv_messages)

            # Stream via the base_inferencer's ainfer_streaming
            # The ConversationalInferencer renders the prompt with full
            # conversation history, then calls base_inferencer.ainfer_streaming()
            rendered = self._inferencer._render_prompt(user_message)
            self._inferencer.base_inferencer.system_prompt = ""

            full_response = ""
            async for chunk in self._inferencer.base_inferencer.ainfer_streaming(
                rendered
            ):
                if chunk:  # Skip empty chunks
                    full_response += chunk
                    yield chunk

            # Add the user + assistant messages to the inferencer's history
            # so future turns include them in the rendered prompt
            self._inferencer.add_message("user", user_message)
            self._inferencer.add_message("assistant", full_response)

        else:
            # Fallback for other backends
            rendered_prompt = self.render_prompt(session, user_message)
            raw_response = await self._call_llm(rendered_prompt)
            yield self._parse_response(raw_response)

    async def get_response(self, session: dict, user_message: str) -> str:
        """Get an AI response for the user's message.

        1. Render prompt with session history
        2. Call LLM backend
        3. Parse <Response> tags from output
        4. Return cleaned response text
        """
        rendered_prompt = self.render_prompt(session, user_message)

        if self._llm_backend == "mock":
            raw_response = self._mock_response(user_message)
        else:
            raw_response = await self._call_llm(rendered_prompt)

        return self._parse_response(raw_response)

    def _mock_response(self, user_message: str) -> str:
        """Generate a mock response for testing without an LLM."""
        return (
            f"<Response>\n"
            f'I received your message: "{user_message}"\n\n'
            f"As the Orchestrator, I can help you with team management, "
            f"project oversight, task coordination, and more. "
            f"This is currently running in mock mode — connect an LLM backend "
            f"to enable full AI conversations.\n"
            f"</Response>"
        )

    async def _call_llm(self, rendered_prompt: str) -> str:
        """Call the configured LLM backend.

        Supports:
        - "mock": returns canned response (default, no deps)
        - "ai-gateway": calls Atlassian AI Gateway (future)
        - "anthropic": direct Anthropic API (future)
        - "openai": direct OpenAI API (future)

        Future: plug in via llm_gateway.py or agent_foundation inferencers.
        """
        raise NotImplementedError(
            f"LLM backend '{self._llm_backend}' not yet implemented"
        )

    @staticmethod
    def _parse_response(raw_output: str) -> str:
        """Extract content from <Response>...</Response> tags.

        Uses the LAST match (not first), matching rankevolve's extract_delimited()
        behavior — handles cases where the LLM outputs multiple attempts.
        Falls back to full output if no tags found (graceful degradation).
        """
        matches = re.findall(r"<Response>(.*?)</Response>", raw_output, re.DOTALL)
        if matches:
            return matches[-1].strip()  # Last match — final attempt
        # No tags — return full output (may happen with some LLM backends)
        return raw_output.strip()

    def _render_fallback(self, conversation_history: list, current_turn: dict) -> str:
        """Fallback rendering when TemplateManager is not available.

        Uses raw Jinja2 to render the conversation template directly.
        """
        from jinja2 import Environment, FileSystemLoader

        template_dir = self._templates_dir / "conversation" / "main"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            undefined=__import__("jinja2").Undefined,  # silent undefined
        )
        template = env.get_template("initial.jinja2")
        return template.render(
            conversation_history=conversation_history,
            current_turn=current_turn,
        )
