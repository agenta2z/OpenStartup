"""Drive create_role with Metamate/Devmate inferencer overrides.

Why this file exists
====================
The canonical ``create_role_bta.yaml`` topology pins:

    _params:
      default_research_inferencer: RovoChat
      default_aggregation_inferencer: RovoDevCLI

This driver runs the SAME topology with those two ``_params`` flipped to
``Metamate`` / ``Devmate`` via the ``overrides`` dict that
``_run_topology()`` already accepts (see
``src/openteam/server/resources/tools/task/executor.py:471``). The YAML on
disk is untouched.

Two overrides modes
-------------------
The ``MODE`` constant picks which leaves get swapped:

* ``MODE = "devmate_only"`` (default, runnable on this Linux devvm)
  - research (breakdown + workers): ``Devmate``  (DevmateCliInferencer)
  - aggregator                    : ``Devmate``  (DevmateCliInferencer)
  Devmate is fully self-contained — needs only the ``devmate`` binary on
  PATH (already at ``/usr/local/bin/devmate`` here). Both Templated and
  CLI-write capable, so it satisfies the YAML's ``template_variables`` /
  ``output_path`` requirements.

* ``MODE = "metamate_and_devmate"`` (matches the user's literal ask)
  - research (breakdown + workers): ``Metamate`` (MetamateSDKInferencer)
  - aggregator                    : ``Devmate``  (DevmateCliInferencer)
  Requires the buck-only ``msl.metamate.cli.metamate_graphql`` module to
  be importable — see "Runtime gotcha for Metamate" below.

Runtime gotcha for Metamate
---------------------------
``MetamateSDKInferencer`` is the closest API match to ``RovoChatInferencer``
(both extend ``StreamingInferencerBase``), but it has two known gaps that
this driver does NOT paper over:

1. ``MetamateSDKInferencer`` does NOT extend ``TemplatedInferencerBase``,
   so the YAML's per-leaf ``template_variables: {...}`` kwarg is silently
   dropped by ``_filter_attrs_keys`` (rich_python_utils logs a WARNING).
   The breakdown/worker prompts will therefore lack the create_role task
   preamble — VERIFICATION.md observation O-6 ("input is raw, not
   templated") will fire. Future fix: multi-inherit Templated on
   MetamateSDKInferencer (mirror RovoChatInferencer's pattern).

2. ``msl.metamate.cli.metamate_graphql`` is a Buck-only thrift binding,
   not pip-installable. In a pure-venv run it imports at call time and
   raises ``RuntimeError: MetaMate upstream client not available``. To
   exercise Metamate end-to-end the run must be wrapped in a Buck binary
   that declares ``//msl/metamate/cli:metamate_graphql`` as a dep — see
   AgentFoundation/.../metamate/BUCK ``query_metamate`` target for the
   shape.

Run from the repo root
----------------------
    source /home/zgchen/openteam-venv/bin/activate
    cd /data/users/zgchen/fbsource/fbcode/_tony_dev/CoreProjects/OpenStartup
    export PYTHONPATH=src:../AgentFoundation/src:../RichPythonUtils/src
    python -m test.openteam.resources.tools.create_role.test_create_role_metamate_devmate \
        --mode devmate_only --max-facets 2 "hire a machine learning engineer (MLE)"

Or via the sibling bash wrapper:
    ./test/openteam/resources/tools/create_role/test_create_role_metamate_devmate.sh \
        "hire a machine learning engineer (MLE)"
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


# Devmate's CLI must be launched from inside a real Sapling/Git repo;
# it looks for `.sl`/`.git` markers via "Failed to find repo root" otherwise.
# The per-task workspace under `_runtime/tasks/<task_id>/` has none, so the
# `workspace.root` fallback inside `effective_cwd` fails. Pin `target_path`
# to the fbsource checkout on this devvm. Set DEVMATE_REPO_PATH to override.
import os as _os
_DEVMATE_REPO_PATH = _os.environ.get("DEVMATE_REPO_PATH", "/data/users/zgchen/fbsource")


# Metamate worker stages need the deep-research EXECUTOR agent. Two-agent
# distinction (verified 2026-05-26):
#
# * ``SPACES_DEEP_RESEARCH_AGENT`` (upper-case) — UI gatekeeper. Routes
#   user requests by asking them to click a "Deep Research" / "think
#   longer" button. Replies non-interactively are stubs like "If you
#   click Deep Research, I'll return ...". NOT what we want for an
#   automated pipeline — auto_continue can't break out because the
#   wording doesn't match the framework's continuation phrases.
#
# * ``metamate_mdr`` (lower-case!) — the actual MDR (Metamate Deep
#   Research) executor agent. Used by production callers like
#   ``fbcode/mrs/tools/vocal_digest/vocal_query.py:24`` and the
#   ``deep_evaluator``. Bypasses the UI gatekeeper and runs the
#   research synchronously, streaming the result back via the same
#   ``engine_start_v2`` → ``get_conversation_for_stream`` polling path
#   that ``MetamateSDKInferencer`` already uses.
#
# Bug in the existing enum: ``MetamateAgent.METAMATE_MDR = "METAMATE_MDR"``
# at ``agent_foundation/.../external/metamate/common.py:146`` uses
# upper-case, but the canonical enum value (per
# ``dataswarm-pipelines/upm_data/types/enum/metamate_engine_agent_name.py:2712``)
# is lower-case ``"metamate_mdr"``. We hard-code the correct value here.
_METAMATE_MDR_AGENT = "metamate_mdr"


_MODES = {
    "devmate_only": {
        "_params.default_research_inferencer": "Devmate",
        "_params.default_aggregation_inferencer": "Devmate",
        # Per-leaf target_path overrides — Devmate needs a real Sapling
        # repo as its operating dir. After the 3-path consolidation
        # (target_path on InferencerBase), the YAML's `_target_path`
        # cascade also reaches every leaf, but explicit per-slot
        # overrides remain clearer for documenting intent.
        "breakdown_inferencer.target_path": _DEVMATE_REPO_PATH,
        "worker_factory.target_path": _DEVMATE_REPO_PATH,
        "aggregator_inferencer.target_path": _DEVMATE_REPO_PATH,
    },
    "metamate_and_devmate": {
        "_params.default_research_inferencer": "Metamate",
        "_params.default_aggregation_inferencer": "Devmate",
        # Only Devmate aggregator needs target_path pinned to a Sapling
        # repo; Metamate runs server-side and ignores target_path.
        "aggregator_inferencer.target_path": _DEVMATE_REPO_PATH,
        # SLOT_DEFAULTS["aggregator_inferencer"] = AGGREGATION_DEFAULTS
        # already sets template_master_version="aggregation" automatically
        # (verified via TemplateState debug 2026-05-26: the field WAS
        # populated correctly). No explicit override needed once the
        # DevmateCli.ainfer bypass bug is fixed.
        # Devmate's default freeform config arms it with shell + codesearch
        # tools and an "implement code" disposition. For an aggregator
        # stage we want pure synthesis: read upstream `(See file: ...)`
        # refs, write the final doc to ``{{ output_path }}`` in the
        # workspace. Shell tools enable Devmate to wander into codesearch
        # mode ("let me look for existing ml-engineer SKILL.md") and
        # then create files in fbsource via its create_commit hook (the
        # ``--no-create-commit`` flag does NOT suppress this — Devmate
        # still produces commits as its end-of-session artifact). Disabling
        # shell prunes that path entirely.
        "aggregator_inferencer.enable_shell": False,
        # Workers need the MDR executor (see comment above). Breakdown
        # keeps DEFAULT (no agent_name override) — it produces clean JSON
        # decomposition in one shot; MDR is overkill for that stage.
        # ``mode="AGENT"`` is the GraphQL ``XFBMetamateMode`` value that
        # routes the request to the agent named in ``agent_name`` instead
        # of letting the server pick (``AUTO``). With AUTO + a deep-research
        # agent_name, the server still routes through the chat gatekeeper
        # ("click Deep Research"). With AGENT + agent_name="metamate_mdr"
        # the request is dispatched directly to the MDR worker.
        # XFBMetamateMode valid values: {AGENT, AUTO, COMMAND, RAG_ENGINE}.
        # (Source: nest/libs/eps/graphql/schema.graphql:7499-7504.)
        "worker_factory.agent_name": _METAMATE_MDR_AGENT,
        "worker_factory.mode": "AGENT",
    },
    "rovochat_and_devmate": {
        # Useful regression contrast: only swap the aggregator.
        "_params.default_aggregation_inferencer": "Devmate",
        "aggregator_inferencer.target_path": _DEVMATE_REPO_PATH,
    },
    "metamate_and_claudecodecli": {
        # Metamate research + ClaudeCodeCli aggregator. ClaudeCodeCli already
        # has has_local_access=True (line 87) and ainfer routes through
        # _ainfer_single (line 656), so no inferencer-side bug fixes needed —
        # this is a clean drop-in. ``ClaudeCodeCLI`` alias was already
        # registered at registered_targets.py:28-32.
        "_params.default_research_inferencer": "Metamate",
        "_params.default_aggregation_inferencer": "ClaudeCodeCLI",
        # ClaudeCodeCli uses ``target_path`` as the subprocess cwd
        # (canonical name across all inferencers). Unlike Devmate,
        # ClaudeCodeCli does NOT require a Sapling/git repo — it just
        # cd's there and runs ``claude -p``. We still point it at
        # fbsource so ``claude`` has its usual workspace context.
        "aggregator_inferencer.target_path": _DEVMATE_REPO_PATH,
        # Workers — same Metamate MDR routing as metamate_and_devmate.
        "worker_factory.agent_name": _METAMATE_MDR_AGENT,
        "worker_factory.mode": "AGENT",
    },
    "metamate_and_claudecodesdk": {
        "_params.default_research_inferencer": "Metamate",
        # Metamate research + ClaudeCodeSdk aggregator. Requires three
        # framework fixes (applied 2026-05-27, mirror MetamateSDK + DevmateCli
        # patterns):
        #   1. ``class ClaudeCodeSdkInferencer(StreamingInferencerBase,
        #      TemplatedInferencerBase)`` — adds template rendering capability
        #      (SDK was streaming-only, dropped all template_* kwargs).
        #   2. ``has_local_access: bool = attrib(default=True)`` — SDK uses
        #      Read/Write/Bash tools, has local access by definition.
        #   3. ``register_alias("ClaudeCodeSDK", ...)`` in registered_targets.py.
        # Plus runtime: SDK's ``permission_mode`` defaults to None (interactive
        # prompt) — must override to ``bypassPermissions`` for headless use.
        "_params.default_aggregation_inferencer": "ClaudeCodeSDK",
        # ClaudeCodeSdk uses ``target_path`` (formerly ``root_folder``,
        # consolidated to the canonical name).
        "aggregator_inferencer.target_path": _DEVMATE_REPO_PATH,
        "aggregator_inferencer.permission_mode": "bypassPermissions",
        # SDK clears ANTHROPIC_API_KEY by default (prefers Claude Max
        # subscription). On a devvm without ~/.claude/ subscription auth,
        # this may fail — set to False to keep API-key auth path if the
        # ``claude`` CLI on this devvm is API-key-backed.
        "aggregator_inferencer.prefer_subscription": False,
        # ``effort`` defaults to "max" on ClaudeCodeSdkInferencer (line 114),
        # but the version of ``claude-agent-sdk`` installed on this devvm
        # doesn't accept it on ``ClaudeAgentOptions`` — passing it fires
        # ``TypeError: ClaudeAgentOptions.__init__() got an unexpected
        # keyword argument 'effort'``. Setting to None skips the flag.
        # If/when the SDK is upgraded, remove this override.
        "aggregator_inferencer.effort": None,
        "worker_factory.agent_name": _METAMATE_MDR_AGENT,
        "worker_factory.mode": "AGENT",
    },
}


def _build_session_context(workspace_dir: Path) -> dict:
    """Mirror what `openteam.server.resources.tools.create_role.executor.execute`
    constructs for `session_context`, but driven from the CLI test rather
    than from the WebSocket dispatcher.
    """
    return {
        "session_root": str(workspace_dir),
        "task_id": f"create_role_metamate_devmate_{os.getpid()}",
    }


def _resolve_repo_root() -> Path:
    """Locate ``OpenStartup/`` for ``_runtime/`` placement.

    Priority:
      1. ``OPENTEAM_REPO_ROOT`` env override (set by the bash wrapper or
         in Buck runs where ``__file__`` is in a .par bundle and parent
         traversal is meaningless).
      2. Walk up from this file looking for ``pyproject.toml`` (works
         when run via plain ``python -m`` from the source tree).
      3. Hardcoded devvm default — a last-resort guess so Buck runs from
         arbitrary cwds still have a sensible workspace location.
    """
    env = os.environ.get("OPENTEAM_REPO_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for cur in [here, *here.parents]:
        if (cur / "pyproject.toml").is_file() and (cur / "src" / "openteam").is_dir():
            return cur
    return Path("/data/users/zgchen/fbsource/fbcode/_tony_dev/CoreProjects/OpenStartup")


def _resolve_yaml_path() -> Path:
    """Locate ``create_role_bta.yaml`` regardless of Buck vs venv.

    Both paths resolve the file via the ``openteam.server.resources.tools.
    create_role`` package's own ``__file__``, which Buck materializes
    into the .par bundle (declared as a resource glob in
    ``OpenStartup/src/BUCK``). The venv path resolves to the source
    file directly.
    """
    from openteam.server.resources.tools import create_role as create_role_pkg
    return Path(create_role_pkg.__file__).resolve().parent / "create_role_bta.yaml"


async def _run(role_description: str, max_facets: int, mode: str) -> None:
    # ``ensure_siblings_on_path`` is a no-op (returns []) in Buck builds
    # because the sibling repos aren't on the devvm-style disk layout
    # inside the .par bundle. In venv mode it's load-bearing.
    from openteam.bootstrap import ensure_siblings_on_path
    ensure_siblings_on_path()

    # Trigger alias registration BEFORE _run_topology imports it itself.
    # (It does the same, but importing here lets us early-fail on alias
    # registration regressions with a clear traceback.)
    import agent_foundation.common.configs.registered_targets  # noqa: F401

    from openteam.server.resources.tools.task.executor import _run_topology

    overrides = dict(_MODES[mode])
    print(f"[driver] mode={mode}, overrides={overrides}", flush=True)

    repo_root = _resolve_repo_root()
    print(f"[driver] repo_root={repo_root}", flush=True)
    runtime = repo_root / "_runtime"
    runtime.mkdir(parents=True, exist_ok=True)

    from openteam.server.resources.tools._shared.workspace_allocator import (
        allocate_tool_workspace,
    )
    tasks_base = runtime / "tasks"
    tasks_base.mkdir(parents=True, exist_ok=True)
    workspace = allocate_tool_workspace("create_role", base_dir=tasks_base)
    print(f"[driver] workspace={workspace}", flush=True)

    sc = {
        "session_root": str(runtime),
        "task_id": Path(workspace).name,
        "working_dir": str(workspace),
    }

    overrides["max_breakdown"] = max_facets

    yaml_path = _resolve_yaml_path()
    print(f"[driver] yaml_path={yaml_path}", flush=True)

    result = await _run_topology(
        source=("file", yaml_path),
        request=role_description,
        overrides=overrides,
        session_context=sc,
    )

    print(f"[driver] result.result.head={str(result.result)[:200]!r}", flush=True)
    print(f"[driver] result.context_updates={result.context_updates}", flush=True)
    deliverable = Path(workspace) / "outputs" / "final_deliverables" / "role_document.md"
    if deliverable.is_file():
        size = deliverable.stat().st_size
        head = deliverable.read_text(encoding="utf-8")[:500]
        print(
            f"[driver] role_document.md: {size} bytes at {deliverable}\n"
            f"--- head ---\n{head}\n--- end head ---",
            flush=True,
        )
    else:
        print(f"[driver] MISSING expected deliverable: {deliverable}", flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("role_description")
    parser.add_argument("--max-facets", type=int, default=2)
    parser.add_argument(
        "--mode",
        choices=list(_MODES.keys()),
        default="devmate_only",
        help="Which inferencer-pair to substitute for the baseline RovoChat/RovoDevCLI.",
    )
    args = parser.parse_args(argv)

    asyncio.run(
        _run(args.role_description, args.max_facets, args.mode)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
