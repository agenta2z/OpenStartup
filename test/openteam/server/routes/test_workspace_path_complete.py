"""Tests for GET /api/workspace/path-complete (Commit 6).

Mounts the workspace router on a fresh FastAPI app (mirroring the
test_attach_route.py pattern) with a stub ConversationService that only exposes
``_working_dir`` — the attribute the route reads to determine the allowed root.
This exercises the real route + the shared
``agent_foundation.common.workspace.path_completion.complete_path`` helper
without the full server bootstrap.

Also asserts the route is registered on the production app at the expected
mount point.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openteam.server.routes.workspace_routes import router as workspace_router


class _StubConvSvc:
    """Minimal stand-in for ConversationService exposing the working dir."""

    def __init__(self, working_dir: str) -> None:
        self._working_dir = working_dir


@pytest.fixture
def workspace_root(tmp_path):
    """Build a small tree under an allowed session root.

    Layout::

        root/
          alpha/        (dir)
            nested/     (dir)
          beta/         (dir)
          notes.txt     (file)
          .hidden       (file, should never surface)
    """
    root = tmp_path / "root"
    (root / "alpha" / "nested").mkdir(parents=True)
    (root / "beta").mkdir()
    (root / "notes.txt").write_text("hi", encoding="utf-8")
    (root / ".hidden").write_text("secret", encoding="utf-8")
    return root


@pytest.fixture
def client(workspace_root):
    app = FastAPI()
    app.state.conversation_service = _StubConvSvc(str(workspace_root))
    app.include_router(workspace_router, prefix="/api/workspace")
    return TestClient(app)


class TestBasicSuggestions:
    def test_basic_dir_suggestions(self, client, workspace_root):
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(workspace_root)},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        names = {s["name"] for s in body["suggestions"]}
        # dirs_only defaults to True → only directories, with trailing slash.
        assert "alpha/" in names
        assert "beta/" in names
        assert "notes.txt" not in names  # file excluded when dirs_only
        assert all(s["is_dir"] for s in body["suggestions"])
        # Dotfiles are always hidden.
        assert not any(s["name"].startswith(".") for s in body["suggestions"])
        assert body["prefix"] == str(workspace_root)

    def test_dirs_only_false_returns_files(self, client, workspace_root):
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(workspace_root), "dirs_only": "false"},
        )
        assert r.status_code == 200, r.text
        names = {s["name"] for s in r.json()["suggestions"]}
        assert "notes.txt" in names
        assert "alpha/" in names
        # Hidden dotfile still excluded.
        assert ".hidden" not in names

    def test_partial_fragment_filters(self, client, workspace_root):
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(workspace_root), "partial": "al"},
        )
        assert r.status_code == 200, r.text
        names = {s["name"] for s in r.json()["suggestions"]}
        assert names == {"alpha/"}


class TestContainment:
    def test_parent_traversal_rejected(self, client, workspace_root):
        # partial climbing out of the prefix → 403 from the helper.
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(workspace_root), "partial": "../"},
        )
        assert r.status_code == 403, r.text

    def test_sibling_prefix_attack_rejected(self, tmp_path):
        """prefix=/tmp/root2 must NOT be accepted for allowed root /tmp/root.

        This is the bug the resolve().relative_to() containment fixes — a
        string startswith check would let "root2" pass as it starts with the
        "root" prefix string.
        """
        root = tmp_path / "root"
        root.mkdir()
        sibling = tmp_path / "root2"
        sibling.mkdir()

        app = FastAPI()
        app.state.conversation_service = _StubConvSvc(str(root))
        app.include_router(workspace_router, prefix="/api/workspace")
        client = TestClient(app)

        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(sibling)},
        )
        assert r.status_code == 403, r.text
        assert "session root" in r.text.lower()

    def test_out_of_session_root_prefix_rejected(self, client, tmp_path):
        # An entirely unrelated absolute path outside the allowed root → 403.
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(outside)},
        )
        assert r.status_code == 403, r.text

    def test_subdir_prefix_within_root_allowed(self, client, workspace_root):
        # A nested directory under the allowed root is a valid prefix.
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(workspace_root / "alpha")},
        )
        assert r.status_code == 200, r.text
        names = {s["name"] for s in r.json()["suggestions"]}
        assert "nested/" in names


class TestMissingPrefix:
    def test_missing_prefix_dir_returns_404(self, client, workspace_root):
        # Prefix is under the allowed root (passes containment) but does not
        # exist on disk → 404, matching the existing AF route convention.
        r = client.get(
            "/api/workspace/path-complete",
            params={"prefix": str(workspace_root / "does_not_exist")},
        )
        assert r.status_code == 404, r.text

    def test_missing_prefix_query_returns_422(self, client):
        # prefix is a required query param → FastAPI validation 422.
        r = client.get("/api/workspace/path-complete")
        assert r.status_code == 422


class TestRouteMounted:
    def test_route_mounted_on_production_app(self):
        from openteam.server.main import app

        paths = {route.path for route in app.routes}
        assert "/api/workspace/path-complete" in paths
