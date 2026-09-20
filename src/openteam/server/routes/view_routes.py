"""File viewer and directory browser endpoints for the FileViewer drawer.

Security: Only serves files/directories that resolve to within the server's
runtime directory OR the configured working directory.  Uses pathlib.resolve()
to prevent path traversal attacks.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

router = APIRouter()

_MAX_BROWSE_DEPTH = 5
_MAX_BROWSE_ENTRIES = 500


def _allowed_bases(request: Request) -> list[Path]:
    """Collect allowed root directories for file serving.

    Mirrors RankEvolve's dual-base pattern: runtime dir (task outputs,
    session artifacts) + working dir (generated docs in project trees).
    """
    bases: list[Path] = []

    data_service = getattr(request.app.state, "data_service", None)
    if data_service is not None:
        session_store = getattr(data_service, "_session_store", None)
        if session_store is not None:
            runtime_root = getattr(session_store, "runtime_root", None)
            if runtime_root:
                bases.append(Path(runtime_root).resolve())

    conv_svc = getattr(request.app.state, "conversation_service", None)
    if conv_svc is not None:
        working_dir = getattr(conv_svc, "_working_dir", None)
        if working_dir:
            bases.append(Path(working_dir).resolve())

    return bases


def _check_access(path: Path, bases: list[Path], label: str = "file") -> None:
    """Raise 403 if *path* is not under any allowed base."""
    if bases:
        if not any(path.is_relative_to(b) for b in bases):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied — {label} is outside allowed directories",
            )
    else:
        if "_runtime" not in str(path):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied — only runtime {label}s can be viewed",
            )


@router.get("/view/{file_path:path}")
async def view_file(request: Request, file_path: str):
    """Serve file content by absolute path.

    Security model:
    - Path must be absolute
    - Path must resolve to within runtime dir or working dir
    - Serves .html/.htm as HTML, everything else as plain text
    """
    if not file_path.startswith("/") and not (
        len(file_path) >= 2 and file_path[1] == ":"
    ):
        file_path = "/" + file_path

    path = Path(file_path).resolve()

    if not Path(file_path).is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {file_path}")

    _check_access(path, _allowed_bases(request), "file")

    if path.suffix in (".html", ".htm"):
        return FileResponse(str(path), media_type="text/html")

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")

    return PlainTextResponse(content)


def _build_tree(directory: Path, depth: int = 0, counter: list | None = None):
    """Recursively build a directory tree structure.

    Returns a sorted list of entries (directories first, then files).
    """
    if counter is None:
        counter = [0]
    if depth >= _MAX_BROWSE_DEPTH:
        return []

    entries = []
    try:
        children = sorted(
            directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
        )
    except PermissionError:
        return []

    for child in children:
        if child.name.startswith("."):
            continue
        counter[0] += 1
        if counter[0] > _MAX_BROWSE_ENTRIES:
            break

        if child.is_symlink():
            continue
        elif child.is_dir():
            entries.append(
                {
                    "name": child.name,
                    "type": "directory",
                    "children": _build_tree(child, depth + 1, counter),
                }
            )
        elif child.is_file():
            entries.append(
                {
                    "name": child.name,
                    "type": "file",
                    "path": str(child),
                    "size": child.stat().st_size,
                }
            )
    return entries


@router.get("/browse/{dir_path:path}")
async def browse_directory(request: Request, dir_path: str):
    """Return recursive directory listing as JSON for folder browser UI."""
    if not dir_path.startswith("/") and not (len(dir_path) >= 2 and dir_path[1] == ":"):
        dir_path = "/" + dir_path

    path = Path(dir_path).resolve()

    if not Path(dir_path).is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {dir_path}")

    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {dir_path}")

    _check_access(path, _allowed_bases(request), "directory")

    entries = _build_tree(path)
    return JSONResponse({"path": str(path), "entries": entries})
