"""Health and config endpoints."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    mode = getattr(request.app.state, "mode", "mock")
    svc = getattr(request.app.state, "data_service", None)
    has_real_sessions = svc is not None and hasattr(svc, "create_session")
    return {
        "status": "ok",
        "mode": mode,
        "real_sessions": has_real_sessions,
        "version": "0.1.0",
    }


@router.get("/config")
async def get_config(request: Request):
    mode = getattr(request.app.state, "mode", "mock")
    svc = getattr(request.app.state, "data_service", None)
    has_real_sessions = svc is not None and hasattr(svc, "create_session")
    return {
        "data": {
            "mode": mode,
            "real_sessions": has_real_sessions,
            "features": [
                "teams", "projects", "tasks", "employees",
                "conversations", "sprints", "intelligence",
            ],
        }
    }
