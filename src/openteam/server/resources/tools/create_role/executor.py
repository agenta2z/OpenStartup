"""Pipeline wiring for the create_role tool.

Builds a ``BreakdownThenAggregateInferencer`` that uses RovoChatInferencer
for all three stages (breakdown, workers, aggregation).

All three phases use **generic** prompt templates from ``prompt_templates/``,
with domain-specific context injected via ``_variables/`` (predefined variables)
or kwargs overrides:

- **Breakdown**: ``task_breakdown/main/initial.jinja2`` — generic decomposition.
  ``task_preamble`` auto-resolved from ``_variables/task_preamble/default.jinja2``
  (create-role-specific context).
- **Worker**: ``deep_research/main/initial.jinja2`` — generic deep research.
  ``task_preamble`` auto-resolved with role-specific source guidance.
- **Aggregation**: ``plan/main/initial.jinja2`` — generic structured document.
  ``task_instructions`` overridden via kwargs with role-specific synthesis
  sections (``ROLE_SYNTHESIS_INSTRUCTIONS``).

A single ``TemplateManager`` is rooted at ``prompt_templates/`` with
``active_template_root_space`` switching between phases.

Usage::

    from openteam.server.resources.tools.create_role import build_create_role_inferencer

    inferencer = build_create_role_inferencer(
        cloud_id="my-cloud-id",
        uct_token="my-uct-token",
    )
    result = inferencer.infer("Senior Backend Engineer focused on microservices")
    # Or async:
    # result = await inferencer.ainfer("Senior Backend Engineer ...")
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, List, Optional

from attr import attrib, attrs

from agent_foundation.common.inferencers.agentic_inferencers.external.rovochat.rovochat_inferencer import (
    RovoChatInferencer,
)
from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.breakdown_then_aggregate_inferencer import (
    BreakdownThenAggregateInferencer,
)
from agent_foundation.common.inferencers.inferencer_base import InferencerBase
from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev.rovodev_cli_inferencer import (
    RovoDevCliInferencer,
)
from agent_foundation.common.response_parsers import extract_delimited
from rich_python_utils.string_utils.formatting.template_manager import TemplateManager

_logger = logging.getLogger(__name__)

# Root of all prompt templates.
# Layout:
#   prompt_templates/.variables.yaml                     (employee persona)
#   prompt_templates/task_breakdown/main/initial.jinja2   (generic breakdown)
#   prompt_templates/deep_research/main/initial.jinja2    (generic deep research)
#   prompt_templates/plan/main/initial.jinja2             (generic structured document)
_PROMPT_TEMPLATES_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "prompt_templates"
)


# ---------------------------------------------------------------------------
# Role synthesis instructions (kwargs override for plan/initial.jinja2)
# ---------------------------------------------------------------------------

ROLE_SYNTHESIS_INSTRUCTIONS = """\
Synthesize ALL research findings into a comprehensive, internally consistent \
Role Responsibility Document in Markdown. The document must:

1. **Synthesize** — merge insights from multiple facets, resolving \
contradictions and eliminating redundancy.
2. **Ground in evidence** — every claim should trace to at least one \
research finding.
3. **Distinguish AI-specific aspects** — note where the role's AI nature \
changes expectations vs. a human equivalent.

### Required Sections

## 1. Role Overview
Brief description of the role, its purpose, and where it fits in the \
organization. Include the role's primary value proposition and how it \
contributes to team goals.

## 2. Core Responsibilities
Day-to-day activities and primary duties, organized by priority. For each \
responsibility, indicate expected time allocation and autonomy level.

## 3. Required Skills & Competencies
Technical skills, soft skills, and domain expertise needed. Distinguish \
**required** vs **nice-to-have**. Include proficiency levels where applicable.

## 4. Collaboration & Communication
Key stakeholders, cross-functional interactions, reporting structure, and \
communication patterns. Specify which roles this position collaborates \
with and how.

## 5. Success Metrics & KPIs
Measurable outcomes that define success in this role, with suggested \
targets and measurement cadence.

## 6. Tools & Technologies
Platforms, frameworks, and tools the role works with daily. Distinguish \
core tools from secondary ones.

## 7. Standard Operating Procedures
2-3 key SOPs with trigger conditions and step-by-step procedures. Focus \
on high-impact, repeatable workflows.

## 8. Guardrails & Autonomy
Autonomy levels, escalation thresholds, approval requirements, and safety \
boundaries. Specify what the role can do independently vs. what requires \
human approval.

## 9. Challenges & Mitigation Strategies
Common obstacles and recommended approaches to handle them. Include both \
technical and organizational challenges.

## 10. Growth Path & Career Development
Progression opportunities, skill development areas, and mentorship \
expectations.

## 11. Onboarding Plan
First 30/60/90 day milestones for ramping up in this role.

### Quality Requirements

- **Internal consistency** — sections must not contradict each other.
- **No concatenation** — synthesize and deduplicate; do NOT simply paste \
research results.
- **Professional tone** — the document should be usable for hiring, \
onboarding, or team planning.
- **Actionable specificity** — avoid vague statements; every item should \
be concrete enough to act on.
"""


# ---------------------------------------------------------------------------
# Breakdown response parser
# ---------------------------------------------------------------------------


def parse_breakdown_response(raw_output: str) -> List[str]:
    """Parse the JSON decomposition from the breakdown inferencer's output.

    The breakdown template produces a ``<Response>`` block containing a
    JSON object with a ``subtasks`` array (unified format matching
    ``task_breakdown``).  Each subtask has a ``description`` and ``todos``
    list.  This parser extracts a self-contained research query string
    for each subtask by combining them.

    Falls back to ``parse_numbered_list`` if JSON extraction fails.
    """
    from agent_foundation.common.inferencers.agentic_inferencers.flow_inferencers.breakdown_then_aggregate_inferencer import (
        parse_numbered_list,
    )

    # 1. Extract <Response> content
    response_text = extract_delimited(str(raw_output))

    # 2. Try to extract JSON from ```json ... ``` code fence
    json_match = re.search(
        r"```json[^\n{]*(\{[\s\S]*\})\s*```", response_text
    )
    if not json_match:
        # No code fence — maybe the whole response is JSON?
        json_match = re.search(
            r"\{[\s\S]*\"subtasks\"[\s\S]*\}", response_text
        )
        if json_match:
            json_str = json_match.group(0)
        else:
            _logger.warning(
                "No JSON found in breakdown response, falling back to numbered list"
            )
            return parse_numbered_list(response_text)
    else:
        json_str = json_match.group(1)

    # 3. Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        _logger.warning("JSON parse failed (%s), falling back to numbered list", e)
        return parse_numbered_list(response_text)

    # 4. Extract subtasks → sub-query strings for workers
    subtasks = data.get("subtasks") or []
    if not subtasks:
        _logger.warning("No subtasks in JSON, falling back to numbered list")
        return parse_numbered_list(response_text)

    queries = []
    for subtask in subtasks:
        desc = subtask.get("description", "")
        todos = subtask.get("todos") or []
        # Build a self-contained research query for the worker
        if todos:
            details = "\n".join(f"- {t}" for t in todos)
            query = f"{desc}\n\nSpecific areas to investigate:\n{details}"
        else:
            query = desc
        if query.strip():
            queries.append(query.strip())

    if not queries:
        _logger.warning("Empty subtask descriptions, falling back to numbered list")
        return parse_numbered_list(response_text)

    _logger.info("Parsed %d research subtasks from breakdown response", len(queries))
    return queries


def _build_template_manager(
    templates_dir: Optional[str] = None,
) -> TemplateManager:
    """Create a ``TemplateManager`` rooted at the ``prompt_templates/`` directory.

    The single TemplateManager serves all phases via
    ``active_template_root_space`` switching:

    - ``task_breakdown`` — generic task decomposition
    - ``deep_research`` — generic deep research
    - ``plan`` — generic structured document creation

    The root ``.variables.yaml`` defines the OpenStartup employee persona,
    auto-injected into ``{{ employee }}`` across all templates.
    """
    root = templates_dir or str(_PROMPT_TEMPLATES_ROOT)
    return TemplateManager(
        templates=root,
        active_template_type="main",
        predefined_variables=True,
    )


# ---------------------------------------------------------------------------
# PromptWrapperInferencer — thin adapter using TemplateManager
# ---------------------------------------------------------------------------


@attrs(slots=False)
class PromptWrapperInferencer(InferencerBase):
    """Wraps an inferencer with a TemplateManager-rendered prompt.

    Needed because ``RovoChatInferencer`` treats its input as the raw user
    message — there is no separate system prompt mechanism.  This wrapper
    renders a Jinja2 template (via ``TemplateManager``) with the incoming
    ``inference_input`` bound to ``{{ input }}``, then delegates the
    rendered prompt to the underlying inferencer.

    When ``output_path`` is set and the underlying inferencer does NOT have
    local file access (``has_local_access is False``), the wrapper:
    - Omits ``output_path`` from the template feed (the template's
      ``{% if output_path %}`` block is skipped so the agent includes
      full content in ``<Response>`` tags instead of writing to a file).
    - After receiving the response, extracts ``<Response>`` content and
      writes it to ``output_path``.
    """

    inferencer: InferencerBase = attrib(default=None)
    template_manager: TemplateManager = attrib(default=None)
    template_key: str = attrib(default="")
    template_root_space: Optional[str] = attrib(default=None)
    output_path: Optional[str] = attrib(default=None)

    def _build_feed(self, inference_input: str) -> dict:
        """Build the template feed dict, conditionally including output_path.

        Uses ``resolve_output_path()`` to get the workspace-resolved absolute
        path.  Only includes it in the feed when the underlying inferencer
        has local file access (so the agent can write to disk).
        """
        feed: dict = {"input": inference_input}
        resolved = self.resolve_output_path()
        if resolved and os.path.isabs(resolved) and getattr(
            self.inferencer, "has_local_access", False
        ):
            feed["output_path"] = resolved
        return feed

    def _save_response_if_needed(self, response: str) -> str:
        """If output_path resolves to an absolute path and inferencer lacks
        local access, extract ``<Response>`` content, write it, and return
        the cleaned text (without tags).

        Uses ``resolve_output_path()`` for workspace-aware path resolution.
        Skips writing if the resolved path is relative (no workspace set) to
        avoid writing to the current working directory.
        """
        resolved = self.resolve_output_path()
        if not resolved or not os.path.isabs(resolved):
            return response
        if getattr(self.inferencer, "has_local_access", False):
            # Local-access inferencer writes the file itself; return as-is
            return response
        # Non-local inferencer: extract <Response> content and save to file
        cleaned = extract_delimited(str(response))
        os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(cleaned)
        # Return cleaned text so downstream nodes receive tag-free content
        return cleaned

    def _infer(self, inference_input, inference_config=None, **kwargs):
        feed = self._build_feed(inference_input)
        rendered = self.template_manager(
            self.template_key,
            active_template_root_space=self.template_root_space,
            **feed,
        )
        result = self.inferencer.infer(
            rendered, inference_config=inference_config, **kwargs
        )
        return self._save_response_if_needed(result)

    async def _ainfer(self, inference_input, inference_config=None, **kwargs):
        feed = self._build_feed(inference_input)
        rendered = self.template_manager(
            self.template_key,
            active_template_root_space=self.template_root_space,
            **feed,
        )
        result = await self.inferencer.ainfer(
            rendered, inference_config=inference_config, **kwargs
        )
        return self._save_response_if_needed(result)


# ---------------------------------------------------------------------------
# RovoChat factory
# ---------------------------------------------------------------------------


def _make_rovochat(
    cloud_id: str = "",
    uct_token: Optional[str] = None,
    email: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
    agent_named_id: Optional[str] = None,
    cache_folder: Optional[str] = None,
) -> RovoChatInferencer:
    """Create a fresh ``RovoChatInferencer``.

    Called once per worker to ensure conversation isolation (each worker
    gets its own RovoChat conversation).

    Supports two auth modes:
    - UCT: pass ``uct_token``
    - Basic Auth: pass ``email`` + ``api_token`` (gateway auto-detected
      for ``.atlassian.net`` URLs; ``cloud_id`` is optional in this mode)
    """
    kwargs: dict[str, Any] = dict(
        cloud_id=cloud_id or "",
        base_url=base_url or "",
        agent_named_id=agent_named_id or "",
        auto_continue=True,
        max_continuations=5,
        auto_resume=False,
    )
    if cache_folder:
        kwargs["cache_folder"] = cache_folder
    if uct_token:
        kwargs["uct_token"] = uct_token
    elif email and api_token:
        kwargs["email"] = email
        kwargs["api_token"] = api_token
    return RovoChatInferencer(**kwargs)


# ---------------------------------------------------------------------------
# Main factory
# ---------------------------------------------------------------------------


def build_create_role_inferencer(
    cloud_id: str = "",
    uct_token: Optional[str] = None,
    email: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
    agent_named_id: Optional[str] = None,
    max_facets: int = 8,
    checkpoint_dir: Optional[str] = None,
    templates_dir: Optional[str] = None,
    aggregator_type: str = "rovochat",
    aggregator_working_dir: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> BreakdownThenAggregateInferencer:
    """Build a ``BreakdownThenAggregateInferencer`` wired for role creation.

    The pipeline uses three generic templates with domain-specific context:

    1. **Breakdown** — ``task_breakdown/main/initial.jinja2`` decomposes the
       role description into research subtasks. ``task_preamble`` auto-resolved
       with create-role-specific dimensions.
    2. **Workers** — ``deep_research/main/initial.jinja2`` researches one
       facet each (parallel). ``task_preamble`` auto-resolved with
       role-specific source guidance.
    3. **Aggregator** — ``plan/main/initial.jinja2`` synthesizes all research
       into a role responsibility document. ``task_instructions`` overridden
       via kwargs with ``ROLE_SYNTHESIS_INSTRUCTIONS``.

    A single ``TemplateManager`` is rooted at ``prompt_templates/`` with
    ``active_template_root_space`` switching between phases.

    Args:
        cloud_id: Atlassian Cloud ID. Required for UCT auth; optional for
            Basic Auth gateway mode.
        uct_token: UCT authentication token.
        email: Email for Basic Auth (alternative to UCT).
        api_token: API token for Basic Auth (alternative to UCT).
        base_url: RovoChat API base URL override.
        agent_named_id: Route to a specific Rovo agent.
        max_facets: Maximum number of research sub-queries (caps breakdown).
        checkpoint_dir: Directory for saving intermediate results (enables
            resuming failed runs).
        templates_dir: Override path to the ``prompt_templates/`` root
            directory.  Defaults to the built-in templates.

    Returns:
        A configured ``BreakdownThenAggregateInferencer`` ready to call
        ``infer(role_description)`` or ``await ainfer(role_description)``.
    """
    tm = _build_template_manager(templates_dir)

    # Build runtime directories from workspace_root
    import os as _os
    streaming_cache_dir: Optional[str] = None
    if workspace_root:
        streaming_cache_dir = _os.path.join(workspace_root, "_runtime", "inferencer_cache")
        _os.makedirs(streaming_cache_dir, exist_ok=True)
        _os.makedirs(_os.path.join(workspace_root, "_runtime", "tmp_output_files"), exist_ok=True)

    # Common kwargs for _make_rovochat
    rovo_kwargs: dict[str, Any] = dict(
        cloud_id=cloud_id,
        uct_token=uct_token,
        email=email,
        api_token=api_token,
        base_url=base_url,
        agent_named_id=agent_named_id,
    )
    if streaming_cache_dir:
        rovo_kwargs["cache_folder"] = streaming_cache_dir

    # 1. Breakdown inferencer — uses generic task_breakdown template
    #    task_preamble auto-resolved from _variables/task_preamble/default.jinja2
    breakdown_inf = PromptWrapperInferencer(
        inferencer=_make_rovochat(**rovo_kwargs),
        template_manager=tm,
        template_key="initial",
        template_root_space="task_breakdown",
    )

    # 2. Worker factory — uses generic deep_research template
    #    task_preamble auto-resolved from _variables/task_preamble/default.jinja2
    #    Creates a fresh RovoChat per sub-query for conversation isolation
    def worker_factory(sub_query: str, index: int) -> PromptWrapperInferencer:
        _logger.info("Creating worker %d for sub-query: %.80s...", index, sub_query)
        # output_path is relative — BTA assigns child workspace in
        # _build_diamond_graph, then resolve_output_path() resolves to
        # workspace_root/children/worker_N/outputs/facet_N.md
        return PromptWrapperInferencer(
            inferencer=_make_rovochat(**rovo_kwargs),
            template_manager=tm,
            template_key="initial",
            template_root_space="deep_research",
            output_path=f"facet_{index}.md",
        )

    # 3. Aggregator inferencer (no wrapper — prompt injected via builder)
    if aggregator_type == "rovodev":
        rovodev_kwargs = dict(
            working_dir=aggregator_working_dir or ".",
            yolo=True,
        )
        if streaming_cache_dir:
            rovodev_kwargs["cache_folder"] = streaming_cache_dir
        aggregator_inf = RovoDevCliInferencer(**rovodev_kwargs)
    else:
        aggregator_inf = _make_rovochat(**rovo_kwargs)

    # 4. Aggregator prompt builder — uses generic plan template
    #    with task_instructions overridden by ROLE_SYNTHESIS_INSTRUCTIONS
    #    BTA calls: prompt_builder(worker_results, original_query=original_query)
    #    - worker_results is a tuple (collected from *worker_results in the
    #      aggregator node closure)
    #    - original_query is a keyword arg (from _original_query=inference_input)
    def agg_prompt_builder(
        worker_results: tuple,
        *,
        original_query: str = "",
        worker_output_paths: list = None,
    ) -> str:
        agg_has_local = getattr(aggregator_inf, "has_local_access", False)
        parts = []
        for idx, res in enumerate(worker_results):
            cleaned = extract_delimited(str(res))
            facet_path = (
                worker_output_paths[idx]
                if worker_output_paths and idx < len(worker_output_paths)
                else None
            )
            if facet_path and agg_has_local:
                # Local-access aggregator: pass file paths only.
                # The aggregator can read the full research from disk.
                # worker_output_paths is the single source of truth —
                # same paths workers write to (captured by BTA's closure).
                parts.append(
                    f"### Research Facet {idx + 1}\n"
                    f"Read the full research report from: `{facet_path}`"
                )
            else:
                # Non-local aggregator or no workspace: include full text inline.
                parts.append(f"### Research Facet {idx + 1}\n{cleaned}")
        joined = "\n\n".join(parts)
        agg_input = (
            f"**Original Role Request:** {original_query}\n\n"
            f"**Research Findings ({len(worker_results)} facets):**\n{joined}"
        )
        return tm(
            "initial",
            active_template_root_space="plan",
            input=agg_input,
            task_instructions=ROLE_SYNTHESIS_INSTRUCTIONS,
        )

    # 5. Wire the BTA pipeline
    #    CRITICAL: max_concurrency MUST be None when using an aggregator.
    #    See BTA source lines 99-138 for the deadlock warning.
    return BreakdownThenAggregateInferencer(
        breakdown_inferencer=breakdown_inf,
        breakdown_parser=parse_breakdown_response,
        worker_factory=worker_factory,
        aggregator_inferencer=aggregator_inf,
        aggregator_prompt_builder=agg_prompt_builder,
        max_breakdown=max_facets,
        max_concurrency=None,
        workspace_root=workspace_root,
    )
