"""Built-in inferencer backend factories.

Importing this module registers ``mock``, ``rovodev``, ``claude_cli`` and the
native backends (``native_claude_sdk``, ``native_claude_cli``,
``native_devmate``, ``native_codex``, ``native_metamate``) on the module-level
:func:`get_registry` singleton.

Each non-mock factory builds a backend-specific ``base`` inferencer (step
1) then delegates to :func:`_wrap_in_conversational` for steps 2-11
(TemplateManagerPromptRenderer, tool registry + filter, dispatcher,
ConversationalInferencer wrap, ``tool_dispatcher`` attach). This is the
only place that knows how to assemble OpenStartup's conversation-tool
stack — adding a new backend just means writing a base-builder.
"""

from __future__ import annotations

import functools
import importlib.util
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openteam.server.backends.registry import (
    BackendBuildContext,
    BackendDescriptor,
    BackendFactory,
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
        "1",
        "true",
        "yes",
        "on",
    }


def _restore_sop_state(
    conv_inferencer: Any, ctx: BackendBuildContext, openteam_sops_dir: Path
) -> None:
    """Rehydrate persisted ``sop_state`` + ``suspended_sops`` onto a fresh CI.

    Reads ``session["sop_state"]``/``["suspended_sops"]`` (persisted at turn exit
    by ConversationService) and rebuilds each ``SOPState`` via ``from_dict``,
    reattaching the non-serializable ``.sop`` graph through
    ``build_sop_state(extra_sop_dirs=...)`` (which is extra-dirs-aware — unlike
    the CI's own ``_reload_sop_definition``, so OpenTeam's own SOPs reload too).
    AgentFoundation built-in SOPs (e.g. ``model_optimization``) are found via
    ``load_all_sops`` regardless of ``extra_sop_dirs``.
    """
    from agent_foundation.common.workflow.sop_state import SOPState
    from agent_foundation.resources.tools.sop.executor import build_sop_state

    sess = ctx.session_store.get_session(ctx.session_id) or {}
    sop_dict = sess.get("sop_state")
    suspended = sess.get("suspended_sops") or []

    def _rehydrate(d: dict) -> Any:
        st = SOPState.from_dict(d)
        if getattr(st, "sop", None) is None and getattr(st, "sop_name", ""):
            fresh, _err = build_sop_state(
                st.sop_name,
                yolo=getattr(st, "yolo_mode", False),
                extra_sop_dirs=[openteam_sops_dir],
            )
            if fresh is not None:
                st.sop = fresh.sop
                # Fix D (hardening): the derived phase-maps are persisted verbatim
                # and NOT refreshed by from_dict, so a session created under an
                # older SOP graph would otherwise run the NEW graph with STALE
                # maps. Recompute them from the freshly-loaded graph; keep runtime
                # progress (completed_phases / phase_executed_tools) untouched.
                # This is the load-bearing reattach site for OpenTeam — its resume
                # path uses reattach_sop=False, bypassing the CI's own reload.
                st.phase_required_tools = fresh.sop.phase_required_tools
                st.tool_phase_map = fresh.sop.tool_to_phase_map
        return st

    if sop_dict:
        conv_inferencer.sop_state = _rehydrate(sop_dict)
        logger.info(
            "Restored sop_state for session %s (sop=%s, phase=%s)",
            ctx.session_id,
            getattr(conv_inferencer.sop_state, "sop_name", "?"),
            getattr(conv_inferencer.sop_state, "current_phase", "?"),
        )
    if suspended:
        conv_inferencer.suspended_sops = [_rehydrate(d) for d in suspended if d]


@dataclass
class _ConversationWiring:
    """Host wiring shared by every conversational backend (classic and native):
    prompt renderer, tool registry (+ whitelist), dispatcher, SOP dirs."""

    prompt_renderer: Any
    tool_registry: dict
    all_tools: dict
    dispatcher: Any
    openteam_sops_dir: Path
    session_id: str
    session_root: str


def _build_conversation_wiring(ctx: BackendBuildContext) -> _ConversationWiring:
    """Steps (a)-(f) of :func:`_wrap_in_conversational` (see its docstring)."""
    # ``prompt_templates`` is an implicit namespace package, so ``__file__``
    # is None on Python 3.13. ``__path__`` (a _NamespacePath) is the
    # canonical way to recover the directory list — element [0] is the
    # primary AF location.
    from agent_foundation.common.inferencers.agentic_inferencers.conversational.template_manager_renderer import (
        TemplateManagerPromptRenderer,
    )
    from agent_foundation.resources import prompt_templates as _af_prompt_templates
    from agent_foundation.resources.tools.registry import load_all_tools
    from openteam.server.integrations.dispatch import build_integration_executor
    from openteam.server.services.tool_dispatcher import ToolDispatcher
    from rich_python_utils.string_utils.formatting.template_manager.template_manager import (
        TemplateManager,
    )

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
    all_tools = load_all_tools(extra_dirs=[openteam_tools_dir])
    tool_registry = _filter_tools_by_config(all_tools, prompt_renderer)

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
        session_store=ctx.session_store,  # sidecars, task_ref, reuse matcher
    )
    return _ConversationWiring(
        prompt_renderer=prompt_renderer,
        tool_registry=tool_registry,
        all_tools=all_tools,
        dispatcher=dispatcher,
        openteam_sops_dir=openteam_sops_dir,
        session_id=_sid,
        session_root=_session_root,
    )


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
      (i) attach the dispatcher (``tool_dispatcher``) for per-turn interactive
          injection
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

    # (a)-(f) Prompt renderer, tool registry + whitelist, dispatcher.
    wiring = _build_conversation_wiring(ctx)
    prompt_renderer = wiring.prompt_renderer
    tool_registry = wiring.tool_registry
    dispatcher = wiring.dispatcher
    openteam_sops_dir = wiring.openteam_sops_dir
    _sid = wiring.session_id

    # (g) The dispatcher IS the tool executor — pass it DIRECTLY, do not wrap it.
    # `ToolDispatcher` implements `ToolExecutorCallable` (async `__call__`) AND the
    # `HubAwareToolExecutor` / `DashboardAwareToolExecutor` capability Protocols
    # (`create_experiment_hub` / `open_dashboard`). The CI's `__attrs_post_init__`
    # builds the `DashboardCoordinator` with `tool_dispatcher or tool_executor`,
    # before the dispatcher is attached in (i) (whose `tool_dispatcher` setter
    # re-points the coordinator at it). A bare passthrough closure is NOT
    # Hub-aware, so a coordinator holding one would log "executor is not
    # dashboard-aware" from `maybe_open` and never open the Experiment Hub. (The
    # old wrapper existed only for a `current_phase` writer removed in Fix 4b —
    # the SOP framework's `check_phase_completion` is the sole authoritative
    # writer — so the wrapper had become pure passthrough dead code.)
    conv_inferencer = None  # bound below (assigned from build_ci_from_config)

    # (h) ConversationalInferencer — built from the AgentFoundation framework
    # YAML so max_iterations / soft_max_iterations / compression_threshold /
    # _debug_mode are config-governed (single source of truth) rather than
    # hand-coded here. The pre-built backend `base` is injected (see docstring);
    # extra_sop_dirs is passed so the /sop command + the Available-SOPs prompt
    # list discover the same OpenTeam SOPs the dispatcher's session_context does.
    ci_config_path = (
        Path(agent_foundation.__file__).parent
        / "resources"
        / "configs"
        / "conversational"
        / "default.yaml"
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
        tool_executor=dispatcher,
        extra_sop_dirs=[openteam_sops_dir],
        allowed_sops=allowed_sops or None,
        disallowed_sops=disallowed_sops or None,
    )
    # (i) Attach dispatcher for per-turn interactive injection
    conv_inferencer.tool_dispatcher = dispatcher
    # (i.1) Back-ref so the dispatcher can read the LIVE sop_state at dispatch
    # time (for SOP-scoped task keying). Same object the per-turn injection
    # updates; the dispatcher + CI are always rebuilt together on eviction.
    dispatcher._inferencer = conv_inferencer

    # (i.2) Restore persisted SOP state (Piece F) onto the freshly-built CI so a
    # mid-SOP session survives restart/eviction. We rehydrate OpenStartup-side
    # via build_sop_state(extra_sop_dirs=...) — NOT the CI's _reload_sop_definition,
    # which is not extra-dirs-aware and would fail to find OpenTeam's own SOPs.
    #
    # NOTE (load-bearing): this is a deliberate parallel path to the CI's dormant
    # RunStateStore "conversation"-blob mechanism. That path's _serialize_pause_state
    # never fires in normal turns (self._paused is never set), so the agentic
    # loop's _rehydrate_from_resumed_store is a no-op and will NOT clobber the
    # sop_state we set here. Activating that path instead would require AF changes
    # (a session-stable RunContext node + the extra-dirs reload fix); we avoid
    # those per the zero-AF-change constraint.
    if _sid and ctx.session_store is not None:
        try:
            _restore_sop_state(conv_inferencer, ctx, openteam_sops_dir)
        except Exception:
            logger.warning(
                "SOP-state restore failed for session %s", _sid, exc_info=True
            )

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

# The chat leaf's claude processes take slots of their own pool: background
# runs' leaves share the default pool and hold a slot for each process's whole
# lifetime, so in that pool a chat reply would queue behind them.
_CHAT_CLI_CONCURRENCY_POOL = "openstartup_chat"
_CHAT_CLI_CONCURRENCY_CAP = 2


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
        concurrency_pool=_CHAT_CLI_CONCURRENCY_POOL,
        concurrency_pool_cap=_CHAT_CLI_CONCURRENCY_CAP,
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


# ── Factories: native (the vendor agent owns the conversation) ─────────


@dataclass(frozen=True)
class _NativeBackend:
    """An OpenStartup backend over AgentFoundation's native orchestrator."""

    name: str
    kind: str  # AgentFoundation configs/conversational_native/backend/<kind>.yaml
    display_name: str
    description: str
    binary: str | None  # vendor CLI on PATH (None: a remote service)
    modules: tuple[str, ...]  # Python packages the backend needs at runtime
    default_model: str | None = None
    # Further runtime requirement: returns what is missing, or None.
    missing_requirement: Callable[[], str | None] | None = None
    # How to get what is missing, appended to the "Unavailable" message.
    remedy: str | None = None


_SERVER_TARGET = "//_tony_dev/CoreProjects/OpenStartup/src:server"
_NATIVE_METAMATE_MODULE = (
    "agent_foundation.common.inferencers.agentic_inferencers."
    "conversational_native.session.metamate"
)


def _module_found(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _native_metamate_backend_missing() -> str | None:
    """AgentFoundation's native Metamate backend has its own Buck target, outside
    the core library: a binary has it only when it depends on that target."""
    if _module_found(_NATIVE_METAMATE_MODULE):
        return None
    return f"AgentFoundation's native Metamate backend (`{_NATIVE_METAMATE_MODULE}`)"


def _devmate_credentials_missing() -> str | None:
    """dm serves AF tools without stalling only in workflow mode, which needs
    explicit CAT credentials."""
    from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.devmate_dm import (
        resolve_cats_file,
    )

    if resolve_cats_file({}):
        return None
    return "Devmate CAT credentials (set DM_CATS_FILE to a dm --cats-file)"


_NATIVE_BACKENDS = (
    _NativeBackend(
        name="native_claude_sdk",
        kind="claude_sdk",
        display_name="Claude Code (native, SDK)",
        description=(
            "Claude Code runs the conversation through the Agent SDK; "
            "AgentFoundation adds SOP context and its tools."
        ),
        binary="claude",
        modules=("claude_agent_sdk",),
        default_model="opus[1m]",
    ),
    _NativeBackend(
        name="native_claude_cli",
        kind="claude_cli",
        display_name="Claude Code (native, CLI)",
        description=(
            "Claude Code CLI runs the conversation; AgentFoundation tools are "
            "served over a local MCP server."
        ),
        binary="claude",
        modules=("mcp", "uvicorn", "starlette"),
        default_model="opus[1m]",
    ),
    _NativeBackend(
        name="native_devmate",
        kind="devmate_dm",
        display_name="Devmate (native)",
        description=(
            "Devmate `dm` runs the conversation; AgentFoundation tools are "
            "served over a local MCP relay."
        ),
        binary="dm",
        modules=("mcp",),
        missing_requirement=_devmate_credentials_missing,
    ),
    _NativeBackend(
        name="native_codex",
        kind="codex_cli",
        display_name="Codex (native)",
        description=(
            "Codex CLI runs the conversation; AgentFoundation tools are served "
            "over a local MCP server."
        ),
        binary="codex",
        modules=("mcp", "uvicorn", "starlette"),
    ),
    _NativeBackend(
        name="native_metamate",
        kind="metamate",
        display_name="Metamate (native, tool-less)",
        description=(
            "Metamate runs the conversation remotely; SOPs are guided and "
            "controlled with slash commands (no AgentFoundation tools)."
        ),
        binary=None,
        modules=("msl.metamate.sdk",),  # Buck-only Metamate SDK
        missing_requirement=_native_metamate_backend_missing,
        remedy=(
            f"run the server from the `{_SERVER_TARGET}` Buck target, which "
            f"carries both: buck2 run @fbcode//mode/dev {_SERVER_TARGET} -- "
            "--real-sessions <dir> --llm-backend native_metamate"
        ),
    ),
)


def _native_missing(backend: _NativeBackend) -> list[str]:
    missing = []
    if backend.binary and not shutil.which(backend.binary):
        missing.append(f"`{backend.binary}` on PATH")
    for module in backend.modules:
        if not _module_found(module):
            missing.append(f"Python package `{module}`")
    if backend.missing_requirement is not None:
        requirement = backend.missing_requirement()
        if requirement:
            missing.append(requirement)
    return missing


def _native_available(backend: _NativeBackend) -> bool:
    return not _native_missing(backend)


def _native_status_message(backend: _NativeBackend) -> str:
    missing = _native_missing(backend)
    if missing:
        message = "Unavailable — missing " + ", ".join(missing)
        return f"{message}; {backend.remedy}" if backend.remedy else message
    if backend.binary is None:
        return "Available"
    return f"{backend.binary} found at {shutil.which(backend.binary)}"


def _native_tool_registry(wiring: _ConversationWiring) -> dict:
    """The host whitelist governs action tools; the conversation widgets SOP
    phases are completed with stay available to the vendor agent."""
    widgets = {
        name: tool
        for name, tool in wiring.all_tools.items()
        if getattr(tool, "tool_type", None) == "Conversation"
    }
    return {**widgets, **wiring.tool_registry}


def _build_native(backend: _NativeBackend, ctx: BackendBuildContext) -> Any:
    """Build a NativeConversationalInferencer for ``backend``.

    Shares the classic wiring — renderer, tool registry + whitelist,
    ``ToolDispatcher`` (+ back-reference) and the persisted-SOP restore — and
    is configured from AgentFoundation's ``conversational_native`` YAML. The
    vendor-session record is kept in the session state
    (``session["native_session"]``) and the live vendor session in the
    service-owned runtime manager, so the conversation survives inferencer
    eviction and server restarts.
    """
    import agent_foundation
    from agent_foundation.resources.tools import _ci_host
    from openteam.server.services.native_session_store import (
        NATIVE_SESSION_DIR,
        SessionStoreRecordAdapter,
    )

    wiring = _build_conversation_wiring(ctx)
    target = Path(ctx.working_dir)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("Could not ensure working dir %s exists: %s", target, e)

    backend_overrides: dict[str, Any] = {"cwd": str(target)}
    if ctx.model_name:
        backend_overrides["model"] = ctx.model_name
    session_kwargs: dict[str, Any] = {}
    sid = wiring.session_id
    if sid:
        session_kwargs["conversation_key"] = sid
        if ctx.session_store is not None:
            session_kwargs["record_store"] = SessionStoreRecordAdapter(
                ctx.session_store, sid
            )
    if wiring.session_root:
        session_kwargs["native_session_dir"] = str(
            Path(wiring.session_root) / NATIVE_SESSION_DIR
        )

    native_config_path = (
        Path(agent_foundation.__file__).parent
        / "resources"
        / "configs"
        / "conversational_native"
        / "default.yaml"
    )
    native = _ci_host.build_native_from_config(
        native_config_path,
        backend=backend.kind,
        backend_overrides=backend_overrides,
        prompt_renderer=wiring.prompt_renderer,
        tool_registry=_native_tool_registry(wiring),
        tool_executor=wiring.dispatcher,
        extra_sop_dirs=[wiring.openteam_sops_dir],
        runtime_manager=ctx.native_runtime,
        # Resume-from-turn re-runs a turn number; the service rewinds the
        # vendor session first (prepare_rewind) and this covers any other
        # repeat. Backends without an exact fork continue with a recap.
        rewind_on_repeat_turn=True,
        on_rewind_unsupported="recap",
        # The dispatcher backgrounds async tools and their completion arrives
        # as an auto-advance turn.
        host_manages_async_results=True,
        **session_kwargs,
    )
    native.tool_dispatcher = wiring.dispatcher
    wiring.dispatcher._inferencer = native

    if sid and ctx.session_store is not None:
        try:
            _restore_sop_state(native, ctx, wiring.openteam_sops_dir)
        except Exception:
            logger.warning(
                "SOP-state restore failed for session %s", sid, exc_info=True
            )
    if _debug_mode_enabled():
        native.enable_debug_mode()

    logger.info(
        "NativeConversationalInferencer built (backend=%s, cwd=%s, model=%s, tools: %d)",
        backend.kind,
        target,
        native.backend.model or "(vendor default)",
        len(native.tool_registry),
    )
    return native


def _native_factory(backend: _NativeBackend) -> BackendFactory:
    return functools.partial(_build_native, backend)


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

for _native_backend in _NATIVE_BACKENDS:
    _registry.register(
        _native_backend.name,
        _native_factory(_native_backend),
        BackendDescriptor(
            name=_native_backend.name,
            display_name=_native_backend.display_name,
            description=_native_backend.description,
            default_model=_native_backend.default_model,
            is_available=functools.partial(_native_available, _native_backend),
            status_message=functools.partial(_native_status_message, _native_backend),
            native=True,
        ),
    )
