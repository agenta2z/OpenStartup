"""Built-in inferencer backend factories.

Importing this module registers ``mock``, ``rovodev``, and ``claude_cli``
on the module-level :func:`get_registry` singleton.

Each non-mock factory builds a backend-specific ``base`` inferencer (step
1) then delegates to :func:`_wrap_in_conversational` for steps 2-11
(TemplateManagerPromptRenderer, tool registry + filter, dispatcher,
ConversationalInferencer wrap, ``_tool_dispatcher`` attach). This is the
only place that knows how to assemble OpenStartup's conversation-tool
stack — adding a new backend just means writing a base-builder.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from openteam.server.backends.registry import (
    BackendBuildContext,
    BackendDescriptor,
    get_registry,
)

logger = logging.getLogger(__name__)

_rovodev_model_warning_logged = False


def _filter_tools_by_config(tool_registry: dict, prompt_renderer: object) -> dict:
    """Filter tool_registry based on .initial.config.yaml whitelist.

    Reads ``tools.enabled_action_tools`` from the template's config YAML.
    If the list is defined and non-empty, only tools whose name appears in
    the whitelist (or whose aliases include a whitelisted name) are kept.

    If the config key is absent, empty, or the config cannot be loaded,
    all tools are returned unchanged (safe default).
    """
    try:
        config = getattr(prompt_renderer, "template_config", None) or {}
        tools_config = config.get("tools", {})
        if not isinstance(tools_config, dict):
            return tool_registry
        enabled_list = tools_config.get("enabled_action_tools")
        if not enabled_list or not isinstance(enabled_list, list):
            return tool_registry
        enabled_set = set(enabled_list)
        filtered = {}
        for name, tool_def in tool_registry.items():
            aliases = set(getattr(tool_def, "aliases", []))
            if name in enabled_set or aliases & enabled_set:
                filtered[name] = tool_def
        logger.info(
            "Tool filtering applied: %d/%d tools enabled (whitelist: %s)",
            len(filtered),
            len(tool_registry),
            enabled_list,
        )
        return filtered
    except Exception as e:
        logger.warning(
            "Failed to apply tool filtering from config: %s — returning all tools",
            e,
        )
        return tool_registry


def _debug_mode_enabled() -> bool:
    """True when the operator opted into verbose inferencer debug logging.

    Gated by the ``OPENTEAM_DEBUG_MODE`` env var (truthy: 1/true/yes/on).
    When set, the CI's ``enable_debug_mode()`` is called after construction,
    which cascades ``debug_mode=True`` to the backend leaf via
    ``InferencerBase._propagate_cascading_attributes``.
    """
    import os
    return os.environ.get("OPENTEAM_DEBUG_MODE", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _wrap_in_conversational(base: Any, ctx: BackendBuildContext) -> Any:
    """Wrap a base inferencer in OpenStartup's ConversationalInferencer stack.

    Steps (verified against the prior monolithic ``_build_rovodev_inferencer``):
      (a) TemplateManagerPromptRenderer backed by TemplateManager (conversation/main/initial.jinja2)
      (b) load_all_tools(extra_dirs=[ctx.templates_dir.parent / "tools"])
      (c) _filter_tools_by_config (whitelist from .initial.config.yaml)
      (d) build_integration_executor()
      (e) build dispatcher session_context from ctx.working_dir + ctx.session_store
      (f) construct ToolDispatcher
      (g) define tool_executor closure that injects tool_phase_map
      (h) build the ConversationalInferencer wrapper FROM the AgentFoundation
          framework YAML (resources/configs/conversational/default.yaml) via
          ``_ci_host.build_ci_from_config``, injecting the pre-built backend
          ``base`` plus the runtime wiring (prompt_renderer, tool_registry,
          tool_executor, extra_sop_dirs). The YAML owns the CI-wrapper policy
          (max_iterations, soft_max_iterations, compression_threshold,
          _debug_mode); the factory owns everything runtime/backend-specific.
      (i) attach _tool_dispatcher for per-turn interactive injection
      (j) return conv_inferencer

    Why inject the base instead of letting the YAML build it: the backend
    ``base`` carries runtime-only state the YAML leaf cannot express —
    per-session ``cache_folder``, ``target_path`` (claude_cli also mkdir's it),
    and backend-specific model handling (rovodev selects via config_override,
    not model_name). Building it in the factory keeps that behavior verbatim;
    the YAML only governs the wrapper config.
    """
    import agent_foundation
    from agent_foundation.resources.tools import _ci_host
    from agent_foundation.common.inferencers.agentic_inferencers.conversational.template_manager_renderer import (
        TemplateManagerPromptRenderer,
    )
    from rich_python_utils.string_utils.formatting.template_manager.template_manager import (
        TemplateManager,
    )
    from agent_foundation.resources.tools.registry import load_all_tools
    from openteam.server.integrations.dispatch import build_integration_executor
    from openteam.server.services.tool_dispatcher import ToolDispatcher

    # (a) Prompt renderer
    #
    # The conversational template lives in AgentFoundation (canonical):
    #     agent_foundation/resources/prompt_templates/conversation/main/initial.jinja2
    # OpenStartup's own ``prompt_templates/`` contains tool-specific templates
    # (task_breakdown/, plan/, implementation/, deep_research/) but does NOT
    # ship a ``conversation/`` subdir. If we pointed TemplateManager only at
    # OpenStartup's dir, the renderer would silently resolve to "" and the
    # backend would hang on an empty prompt (regression observed in production
    # session server_20260615_194631_8e0863a8 / turn_002).
    #
    # ``TemplateManager.templates`` accepts a list of roots; earlier roots are
    # consulted first. We pass AgentFoundation first (canonical templates),
    # then OpenStartup (overrides / app-specific additions).
    # ``prompt_templates`` is an implicit namespace package, so ``__file__``
    # is None on Python 3.13. ``__path__`` (a _NamespacePath) is the
    # canonical way to recover the directory list — element [0] is the
    # primary AF location.
    from agent_foundation.resources import prompt_templates as _af_prompt_templates

    _af_templates_dir = Path(list(_af_prompt_templates.__path__)[0])
    prompt_renderer = TemplateManagerPromptRenderer(
        template_manager=TemplateManager(
            templates=[str(_af_templates_dir), str(ctx.templates_dir)],
            active_template_root_space="conversation",
            active_template_type="main",
        ),
        template_key="initial",
    )

    # (b) + (c) Tool registry, with whitelist
    openteam_tools_dir = ctx.templates_dir.parent / "tools"
    tool_registry = load_all_tools(extra_dirs=[openteam_tools_dir])
    tool_registry = _filter_tools_by_config(tool_registry, prompt_renderer)

    # (d) Integration executor (Slack/TWG fallback path)
    integration_executor = build_integration_executor()

    # (e) + (f) Dispatcher
    _sid = getattr(ctx, "session_id", "") or ""
    _session_root = ""
    if (
        _sid
        and ctx.session_store is not None
        and hasattr(ctx.session_store, "get_session_dir")
    ):
        try:
            _session_root = str(ctx.session_store.get_session_dir(_sid))
        except Exception:
            pass
    openteam_sops_dir = ctx.templates_dir.parent / "sops"
    session_context = {
        "session_id": _sid,
        "session_root": _session_root,
        "working_dir": ctx.working_dir,
        "server_dir": (
            str(ctx.session_store.server_dir)
            if ctx.session_store is not None
            and hasattr(ctx.session_store, "server_dir")
            else ""
        ),
        "extra_sop_dirs": [openteam_sops_dir],
        "extra_tool_dirs": [openteam_tools_dir],
        "cloud_id": "",
        "uct_token": None,
        "email": None,
    }
    dispatcher = ToolDispatcher(
        tool_registry=tool_registry,
        integration_executor=integration_executor,
        session_context=session_context,
        interactive=None,  # Injected per-turn by run_conversation_turn
    )

    # (g) Forward-decl + tool_executor closure with tool_phase_map injection
    conv_inferencer = None  # bound below; safe — tools only run during run_agentic_loop

    async def tool_executor(tool_name, arguments):
        result = await dispatcher(tool_name, arguments)
        if hasattr(result, "context_updates") and conv_inferencer is not None:
            tool_phase_map = conv_inferencer.prior_context.get("tool_phase_map", {})
            tool_phase = tool_phase_map.get(tool_name)
            if tool_phase and "current_phase" not in result.context_updates:
                result.context_updates["current_phase"] = tool_phase
                result.context_updates["phase_status"] = "completed"
        return result

    # (h) ConversationalInferencer — built from the AgentFoundation framework
    # YAML so max_iterations / soft_max_iterations / compression_threshold /
    # _debug_mode are config-governed (single source of truth) rather than
    # hand-coded here. The pre-built backend `base` is injected (see docstring);
    # extra_sop_dirs is passed so the /sop command + the Available-SOPs prompt
    # list discover the same OpenTeam SOPs the dispatcher's session_context does.
    ci_config_path = (
        Path(agent_foundation.__file__).parent
        / "resources" / "configs" / "conversational" / "default.yaml"
    )
    # SOP discovery filters for the Orchestrator's "Available SOPs" prompt
    # section. Semantics match iptables / AWS IAM / k8s NetworkPolicy:
    #   * allowed_sops (whitelist) — if non-empty, ONLY these names pass.
    #   * disallowed_sops (denylist) — then filters the survivors.
    # Both empty = framework default (every discovered SOP visible).
    # Hidden SOPs remain loadable via /sop <name> explicitly — this is
    # purely a cosmetic filter on the LLM's discovery prompt. May also be
    # set in the YAML at
    # AgentFoundation/.../resources/configs/conversational/default.yaml;
    # explicit values here override the YAML defaults.
    allowed_sops: list[str] = []
    disallowed_sops: list[str] = []

    conv_inferencer = _ci_host.build_ci_from_config(
        ci_config_path,
        base_inferencer=base,
        prompt_renderer=prompt_renderer,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        extra_sop_dirs=[openteam_sops_dir],
        allowed_sops=allowed_sops or None,
        disallowed_sops=disallowed_sops or None,
    )
    # (i) Attach dispatcher for per-turn interactive injection
    conv_inferencer._tool_dispatcher = dispatcher

    # (i.5) Operator opt-in: enable verbose debug logging on the CI and cascade
    # it to the backend leaf. enable_debug_mode() is the reliable trigger for the
    # CI — its __attrs_post_init__ does not chain super(), so a constructor
    # debug_mode=True would NOT cascade; the override propagates to
    # base_inferencer via InferencerBase._propagate_cascading_attributes.
    if _debug_mode_enabled():
        conv_inferencer.enable_debug_mode()
        logger.info(
            "Debug mode enabled on ConversationalInferencer; cascaded to %s",
            type(base).__name__,
        )

    logger.info(
        "ConversationalInferencer wrapping %s (tools: %d registered)",
        type(base).__name__,
        len(tool_registry),
    )
    # (j)
    return conv_inferencer


# ── Factory: rovodev ────────────────────────────────────────────────────


def _rovodev_factory(ctx: BackendBuildContext) -> Any:
    """Build a ConversationalInferencer wrapping RovoDevCliInferencer.

    Note: ``RovoDevCliInferencer`` has no ``model_name`` attribute — model
    selection happens via the ``config_override`` JSON string. We log once
    at INFO if the operator passed a model so they know it had no effect.
    """
    global _rovodev_model_warning_logged
    if ctx.model_name and not _rovodev_model_warning_logged:
        logger.info(
            "rovodev backend ignores model_name=%r (RovoDevCliInferencer "
            "selects model via config_override JSON; per-session UI override "
            "is a no-op for this backend)",
            ctx.model_name,
        )
        _rovodev_model_warning_logged = True

    from agent_foundation.common.inferencers.agentic_inferencers.external.rovodev import (
        RovoDevCliInferencer,
    )

    base = RovoDevCliInferencer(
        target_path=ctx.working_dir,
        idle_timeout_seconds=600,
        tool_use_idle_timeout_seconds=600,
        cache_folder=ctx.cache_dir,
        enable_legacy=True,
    )
    logger.info(
        "RovoDevCliInferencer initialized (target_path=%s, acli=%s, cache=%s)",
        ctx.working_dir,
        base.acli_path,
        ctx.cache_dir,
    )
    return _wrap_in_conversational(base, ctx)


def _rovodev_status_message() -> str:
    found = shutil.which("acli")
    if found:
        return f"acli found at {found}"
    return "acli binary not found on PATH — install Atlassian CLI to enable rovodev"


# ── Factory: claude_cli ─────────────────────────────────────────────────


def _claude_cli_factory(ctx: BackendBuildContext) -> Any:
    """Build a ConversationalInferencer wrapping ClaudeCodeCliInferencer.

    The two kwargs that match the class default (idle_timeout_seconds,
    permission_mode) are intentionally explicit so the factory's behavior
    is self-documenting and survives any future default change upstream
    in AgentFoundation.
    """
    from agent_foundation.common.inferencers.agentic_inferencers.external.claude_code.claude_code_cli_inferencer import (
        ClaudeCodeCliInferencer,
    )

    # claude.exe requires its target_path (--cwd) to exist; create on first
    # use so a fresh install with default OPENTEAM_WORKING_DIR=~/MyProjects
    # works without manual setup.
    target = Path(ctx.working_dir)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("Could not ensure target_path %s exists: %s", target, e)

    base = ClaudeCodeCliInferencer(
        target_path=str(target),
        model_name=ctx.model_name or "opus[1m]",
        idle_timeout_seconds=1800,
        permission_mode="bypassPermissions",
        cache_folder=ctx.cache_dir,
    )
    logger.info(
        "ClaudeCodeCliInferencer initialized (target_path=%s, model=%s, cache=%s)",
        ctx.working_dir,
        base.model_name,
        ctx.cache_dir,
    )
    return _wrap_in_conversational(base, ctx)


def _claude_cli_status_message() -> str:
    found = shutil.which("claude")
    if found:
        return f"claude found at {found}"
    return (
        "claude binary not found on PATH — install Claude Code "
        "(https://claude.com/claude-code) to enable claude_cli"
    )


# ── Factory: mock (guard) ───────────────────────────────────────────────


def _mock_guard_factory(ctx: BackendBuildContext) -> Any:
    """Should never be invoked — mock is service-handled in ConversationService."""
    raise RuntimeError(
        "mock is service-handled — never call mock factory through the registry. "
        "ConversationService._get_session_inferencer short-circuits before reaching here."
    )


# ── Registration ────────────────────────────────────────────────────────

_registry = get_registry()

_registry.register(
    "mock",
    _mock_guard_factory,
    BackendDescriptor(
        name="mock",
        display_name="Mock",
        description="Canned responses, no external dependencies — for UI testing.",
        default_model=None,
        is_available=lambda: True,
        status_message=lambda: "Always available",
    ),
)

_registry.register(
    "rovodev",
    _rovodev_factory,
    BackendDescriptor(
        name="rovodev",
        display_name="Rovo Dev (acli)",
        description="Atlassian Rovo Dev CLI via acli binary.",
        default_model=None,  # selected via config_override JSON
        is_available=lambda: shutil.which("acli") is not None,
        status_message=_rovodev_status_message,
    ),
)

_registry.register(
    "claude_cli",
    _claude_cli_factory,
    BackendDescriptor(
        name="claude_cli",
        display_name="Claude Code (CLI)",
        description="Anthropic Claude Code CLI via the `claude` binary.",
        default_model="opus[1m]",
        is_available=lambda: shutil.which("claude") is not None,
        status_message=_claude_cli_status_message,
    ),
)
