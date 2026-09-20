# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-strict

"""REST routes backing the Experiment Hub frontend (``useHubApiClient``).

Mounted at ``/api/sessions/{session_id}/hubs/{hub_id}``; ``hub_id`` is the hub's
``multi_task_id``. This router exposes EXACTLY the REST endpoints the React
``useHubApiClient`` hook calls — no more, no less (the hook's three long-running
actions — implement-hypothesis / resume-implement / run-combos — travel over the
manager WebSocket as ``hub_command`` frames, NOT REST, so they are intentionally
absent here; see the module-level note in the parent task / report).

Each handler is a thin transport adapter:

  1. Resolve ``session_store`` from ``app.state.data_service.session_store``
     (503 if absent — e.g. mock mode without real sessions).
  2. Resolve ``session_dir`` / ``hub_dir`` from the store.
  3. Call the matching transport-agnostic ``agent_foundation.experiment_hub``
     service (or, for the submission run, drive a ``HubController`` out-of-turn
     via the run supervisor) and translate its plain exceptions to ``HTTPException``:
     ``KeyError`` → 404, ``ValueError`` → 400, ``NotImplementedError`` → 501,
     ``RuntimeError`` → 503.

All business logic stays in the AF services / ``HubController``; this layer only
parses requests and injects dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from agent_foundation.experiment_hub import setup_store, submissions_service
from fastapi import APIRouter, HTTPException, Request
from openteam.server.services.hub_factory import (
    build_hub_controller,
    make_hub_event_emitter,
)

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter()


# ── Dependency resolution helpers ───────────────────────────────────────────


def _session_store(request: Request) -> Any:
    """Resolve the SessionStore off ``app.state.data_service`` or 503.

    Real-sessions mode hangs the store on ``data_service.session_store``; mock
    mode (``MockDataService``) has none — hub routes require persistence."""
    svc = getattr(request.app.state, "data_service", None)
    store = getattr(svc, "session_store", None)
    if store is None:
        raise HTTPException(503, "Session store not available (mock mode?)")
    return store


def _session_dir(store: Any, session_id: str) -> Path:
    """Resolve ``<session_dir>`` for a session id (ensure-created by the store)."""
    return Path(store.get_session_dir(session_id))


def _hub_dir(store: Any, session_id: str, hub_id: str) -> Path:
    """Resolve ``<session_dir>/hubs/<hub_id>`` (the dashboard sidecar dir).

    The AF submission/baseline services key off ``session_dir`` + the
    ``multi_task_id`` (== ``hub_id``); the per-hub ``hub_dir`` is resolved here
    for the dashboard subtab sidecar and any per-hub state the controller
    initialized."""
    return Path(store.get_session_hubs_dir(session_id)) / hub_id


def _persist_wc(store: Any, session_id: str, wc: Any) -> None:
    """Persist a controller-mutated ``WorkflowContext`` back to the session."""
    try:
        store.update_workflow_context(session_id, wc.to_dict())
    except Exception as exc:  # noqa: BLE001 — persist failure must not 500 the action
        logger.warning("[hub] workflow_context persist failed: %s", exc)


# ── Submission CRUD ─────────────────────────────────────────────────────────


@router.get("/submissions")
async def list_submissions(
    request: Request,
    session_id: str,
    hub_id: str,
    baseline_id: str | None = None,
) -> dict[str, Any]:
    """``GET .../submissions`` — the hub's submissions, verdicts overlaid.

    Backs ``useHubApiClient.refetchHubSubmissions`` (and ``setBaseline``'s
    follow-up refetch)."""
    store = _session_store(request)
    try:
        data = await submissions_service.list_submissions(
            _session_dir(store, session_id), hub_id, baseline_id=baseline_id
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"data": data}


@router.post("/submissions")
async def add_submission(
    request: Request, session_id: str, hub_id: str
) -> dict[str, Any]:
    """``POST .../submissions`` — append a submission (``addSubmission``)."""
    store = _session_store(request)
    body = await _json_body(request)
    try:
        entry = await submissions_service.add_submission(
            _session_dir(store, session_id), session_id, hub_id, body
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"data": entry}


@router.post("/submissions/{submission_id}")
async def update_submission(
    request: Request, session_id: str, hub_id: str, submission_id: str
) -> dict[str, Any]:
    """``POST .../submissions/{id}`` — patch mutable fields (``updateSubmission``).

    The FE uses POST (not PATCH) for this mutation; AF's allow-list filters the
    body down to safe mutable fields."""
    store = _session_store(request)
    patch = await _json_body(request)
    try:
        entry = await submissions_service.update_submission(
            _session_dir(store, session_id), session_id, hub_id, submission_id, patch
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"data": entry}


# ── Baseline ────────────────────────────────────────────────────────────────


@router.post("/baseline")
async def set_baseline(
    request: Request, session_id: str, hub_id: str
) -> dict[str, Any]:
    """``POST .../baseline`` — set/clear the active baseline (``setBaseline``).

    FE body: ``{submission_id, ...}``. AF expects ``{baseline_submission_id,
    selected_by?}``; we map ``submission_id`` → ``baseline_submission_id`` so the
    persisted choice matches the resolver's key, and forward any ``selected_by``.
    A ``null``/absent id clears the override (resolver falls back to
    ``isBaseline`` rows)."""
    store = _session_store(request)
    body = await _json_body(request)
    payload: dict[str, Any] = {
        # FE sends ``submission_id``; AF's set_baseline keys on
        # ``baseline_submission_id``. Honor an explicit AF-shaped key if present.
        "baseline_submission_id": body.get("baseline_submission_id")
        if "baseline_submission_id" in body
        else body.get("submission_id"),
    }
    if body.get("selected_by"):
        payload["selected_by"] = body["selected_by"]
    try:
        choice = await submissions_service.set_baseline(
            _session_dir(store, session_id), session_id, hub_id, payload
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"data": choice}


# ── Single-run lifecycle (out-of-turn HubController + run supervisor) ─────────


@router.post("/submissions/{submission_id}/run")
async def run_submission(
    request: Request, session_id: str, hub_id: str, submission_id: str
) -> dict[str, Any]:
    """``POST .../submissions/{id}/run`` — launch the submission's runner.

    Backs ``useHubApiClient.runSubmission(submissionId, opts)``. This is a
    LONG-RUNNING action: we build a ``HubController`` out-of-turn (events flow to
    every open tab via ``ConnectionRegistry.emit``), spawn
    ``run_submission_script`` on the ``HubRunSupervisor`` keyed by the returned
    queue task id, and return ``{run_id, status:"started"}`` immediately — the
    FastAPI worker is never blocked on the run.

    The runner needs the resolved script/launch paths + flags; the FE's
    Monitor-view ``opts`` carry them (camelCase). We do NOT call
    ``submissions_service.run_submission`` here because its agent-server enqueue
    path (``_enqueue_agent_message``) is an unwired ``NotImplementedError``
    (TODO(port) in that module — the AF file-queue service has no AF home yet);
    the in-process ``HubController.run_submission_script`` is the wired path.
    """
    store = _session_store(request)
    opts = await _json_body(request)

    script_path = str(opts.get("scriptPath") or "").strip()
    launch_path = str(opts.get("launchPath") or "").strip()
    if not script_path or not launch_path:
        raise HTTPException(400, "scriptPath and launchPath are required")
    enable_flags = opts.get("enableFlags") or []
    if not isinstance(enable_flags, list):
        enable_flags = []
    experiment_name = str(opts.get("experimentName") or f"combo_{submission_id}")
    submission_label = str(opts.get("submissionLabel") or f"Submission {submission_id}")
    setup_id = str(opts.get("setupId") or "")
    app_layer_version = str(opts.get("appLayerVersion") or "").strip()
    build_command = str(opts.get("buildCommand") or "").strip()

    # Wrap the controller's RankEvolve-shaped events into the generic
    # dashboard_* protocol (routed by hub_id) so submission_state/token/setup
    # updates land in the hub bus — NOT raw connection_registry.emit (which the
    # FE would not route to the hub).
    emit_event = make_hub_event_emitter(
        request.app.state.connection_registry, {"hub_id": hub_id}
    )
    built = build_hub_controller(
        session_store=store,
        session_id=session_id,
        session_context={"working_dir": opts.get("workflowTargetPath", "")},
        emit_event=emit_event,
        stream_sink=None,
    )
    if built is None:
        raise HTTPException(503, "Experiment Hub backend unavailable")
    controller, wc = built

    # ``run_submission_script`` enqueues + starts the run; it returns the queue
    # task id and (via the controller's own queue runner) drives the subprocess.
    # Spawn the START on the supervisor so the request returns immediately; the
    # task id doubles as the run_id the FE later cancels.
    run_id = f"subrun-{uuid.uuid4().hex[:8]}"
    try:
        await request.app.state.hub_run_supervisor.spawn(
            session_id,
            run_id,
            controller.run_submission_script(
                multi_task_id=hub_id,
                submission_id=submission_id,
                setup_id=setup_id,
                script_path=script_path,
                launch_path=launch_path,
                enable_flags=enable_flags,
                experiment_name=experiment_name,
                submission_label=submission_label,
                app_layer_version=app_layer_version,
                build_command=build_command,
            ),
        )
    except Exception as exc:  # noqa: BLE001 — translate spawn-time failures
        logger.error("[hub] run_submission spawn failed: %s", exc, exc_info=True)
        raise HTTPException(503, f"Failed to start run: {exc}") from exc
    # The controller mutates the task queue on its wc; persist immediately so a
    # restart can reconcile the in-flight run.
    _persist_wc(store, session_id, wc)
    return {
        "data": {"run_id": run_id, "submission_id": submission_id, "status": "started"}
    }


@router.post("/submissions/{submission_id}/cancel")
async def cancel_submission_run(
    request: Request, session_id: str, hub_id: str, submission_id: str
) -> dict[str, Any]:
    """``POST .../submissions/{id}/cancel`` — cancel a running submission.

    Backs ``useHubApiClient.cancelSubmissionRun``. The run was spawned on the
    ``HubRunSupervisor``; cancelling it cooperatively cancels the controller's
    ``asyncio.Task`` (which terminates the SubmissionRunner subprocess and emits
    the ``cancelled`` ``submission_state``). The FE may send the ``run_id`` it
    got from ``run``; if absent we cancel by the submission's own run id (best
    effort) and report.

    **G21 — MAST cancel** (post-audit): Phase 1 (local in-process cancel) fires
    via ``hub_run_supervisor`` as before. Phase 2 (remote FBLearner/MAST cancel)
    now also fires when the submission row has a ``mastJob``: we call
    ``submissions_service._cancel_mast_job_best_effort`` in a fire-and-forget
    ``asyncio.create_task`` (matches the AF ``cancel_submission_run`` pattern
    at :940-944). We don't invoke AF's full ``cancel_submission_run`` because
    it requires ``queue_root_path`` for phase 1 — OpenTeam runs the cancel via
    the in-process ``HubRunSupervisor`` instead, so we only need the phase-2
    remote-cancel branch here.
    """
    opts = await _json_body(request)
    run_id = str(opts.get("run_id") or opts.get("runId") or "").strip()
    if not run_id:
        # The FE typically threads the run_id from the run response; fall back to
        # the submission's recorded runTaskId so a reload can still cancel.
        run_id = str(opts.get("runTaskId") or submission_id)
    cancelled = await request.app.state.hub_run_supervisor.cancel(session_id, run_id)

    # G21 phase 2 — best-effort remote MAST job cancel. Non-fatal: phase 1
    # already terminated the local subprocess and the user sees 'cancelled' on
    # the run row; MAST cancel is a resource-cleanup nicety. Never blocks the
    # response.
    mast_job_cancel_scheduled = False
    try:
        store = _session_store(request)
        session_dir = _session_dir(store, session_id)
        submissions = submissions_service.load_hub_submissions(session_dir, hub_id)
        target = None
        for entry in submissions or []:
            if (
                entry.get("id") == submission_id
                or entry.get("submission_id") == submission_id
            ):
                target = entry
                break
        mast_job = (target or {}).get("mastJob")
        mast_job = str(mast_job).strip() if mast_job else ""
        if mast_job:
            # Fire-and-forget — same pattern as submissions_service:940-944.
            # The AF helper handles the meta CLI shell-out + retries; a failure
            # only leaves the remote job running (visible in FBLearner UI), not
            # a stuck local state.
            asyncio.create_task(
                submissions_service._cancel_mast_job_best_effort(mast_job)
            )
            mast_job_cancel_scheduled = True
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — remote cancel is best-effort
        logger.warning(
            "[hub] MAST cancel best-effort failed for %s/%s: %s",
            hub_id,
            submission_id,
            exc,
        )

    return {
        "data": {
            "submission_id": submission_id,
            "run_id": run_id,
            "cancelled": cancelled,
            "mast_job_cancel_scheduled": mast_job_cancel_scheduled,
        }
    }


# ── Setup + script versions (hub-scoped; FE addresses them per-submission) ───


@router.post("/submissions/{submission_id}/setup")
async def setup_submission(
    request: Request, session_id: str, hub_id: str, submission_id: str
) -> dict[str, Any]:
    """``POST .../submissions/{id}/setup`` — create/replace the hub's run setup.

    Backs ``useHubApiClient.setupSubmission``. CONTRACT NOTE (flagged): the FE
    addresses setup per ``submission_id``, but in the AF/RankEvolve model setup
    is a PER-HUB unit (one ``submit_v<n>.py`` + ``launch.json`` per hub,
    keyed by ``multi_task_id``). We therefore drive
    ``setup_store.post_submission_setup`` keyed by ``hub_id`` and ignore the
    path ``submission_id`` (the submission row binds to the resulting setup at
    run time via ``setupId``). The submitted body is forwarded verbatim
    (``setupName``, ``mode``, generate/import fields, ``dryRun``).

    ``queue_root_path=None``: the generate-mode PTI enqueue uses the agent-server
    file queue, which has no AF home yet (TODO(port)); ``mode="import"`` (direct
    upload + validate, no queue) works today, as does ``dry_run`` validation.
    """
    store = _session_store(request)
    body = await _json_body(request)
    dry_run = bool(body.get("dryRun") or body.get("dry_run"))
    try:
        result = await setup_store.post_submission_setup(
            _session_dir(store, session_id),
            session_id,
            hub_id,
            body,
            queue_root_path=None,
            dry_run=dry_run,
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except NotImplementedError as e:
        # generate-mode requires the unwired agent queue; import/dry_run do not.
        raise HTTPException(
            501, f"Setup generate-mode not yet wired (use import mode): {e}"
        ) from e
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    return {"data": result}


@router.post("/submissions/{submission_id}/script")
async def save_script_version(
    request: Request, session_id: str, hub_id: str, submission_id: str
) -> dict[str, Any]:
    """``POST .../submissions/{id}/script`` — save a user-edited script version.

    Backs ``useHubApiClient.saveScriptVersion(submissionId, script)``. CONTRACT
    NOTES (flagged):
      * Like setup, script versions are PER-HUB in AF
        (``save_setup_script_version`` keyed by ``multi_task_id``); the path
        ``submission_id`` is not used for keying.
      * The FE sends ``{content: "<script string>"}`` (its helper wraps a bare
        string as ``{content}``); AF expects ``{scriptContent, launchContent?}``.
        We map ``content`` → ``scriptContent`` and pass through an optional
        ``launchContent`` so small drawer edits reuse the prior ``launch.json``.
    """
    store = _session_store(request)
    body = await _json_body(request)
    payload: dict[str, Any] = {
        # FE saveScriptVersion wraps a bare string as {content}; AF wants
        # scriptContent. Honor an explicit AF-shaped key if the caller sent one.
        "scriptContent": body.get("scriptContent")
        if "scriptContent" in body
        else body.get("content"),
    }
    if body.get("launchContent") is not None:
        payload["launchContent"] = body["launchContent"]
    try:
        result = await setup_store.save_setup_script_version(
            _session_dir(store, session_id), session_id, hub_id, payload
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"data": result}


# ── Local helpers ────────────────────────────────────────────────────────────


async def _json_body(request: Request) -> dict[str, Any]:
    """Parse a JSON object request body, tolerating an empty body.

    The FE always POSTs an object (``postJson`` sends ``JSON.stringify(data)``),
    but some calls pass ``{}``; an empty/whitespace body decodes to ``{}`` so
    handlers can use ``.get(...)`` uniformly. A non-object body is a 400."""
    raw = await request.body()
    if not raw or not raw.strip():
        return {}
    import json

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(400, f"Invalid JSON body: {e}") from e
    if not isinstance(data, dict):
        raise HTTPException(400, "Request body must be a JSON object")
    return data
