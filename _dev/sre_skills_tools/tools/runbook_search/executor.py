"""runbook_search tool executor — vendor-neutral docs backend dispatcher.

Returns dict directly. Currently supported:
  - confluence       (Confluence Cloud REST API v1, CQL queries) — full
  - atlassian_docs   — stub (intended to call Rovo Dev's atlassian_docs_search MCP)
  - notion           — stub
  - mkdocs           — stub

Environment:
    CONFLUENCE_URL: Required for confluence provider.
    CONFLUENCE_USER + CONFLUENCE_TOKEN: Basic-auth credentials for Confluence.
    DOCS_BACKEND: Override provider auto-detect.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse, parse_qs

import aiohttp

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)
_DEFAULT_LIMIT = 10
_VALID_ACTIONS = {"search", "get", "list_by_label", "recent"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(data: Any, metadata: dict | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "metadata": metadata or {}, "warnings": warnings or []}


def _err(message: str, *, provider: str | None = None, action: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": message, "data": None, "metadata": {}, "warnings": []}
    if provider:
        out["metadata"]["provider"] = provider
    if action:
        out["metadata"]["action"] = action
    return out


def _resolve_provider(arguments: dict[str, Any], endpoint: str) -> str:
    if (p := arguments.get("provider")):
        return str(p).lower()
    if (p := os.environ.get("DOCS_BACKEND")):
        return p.lower()
    e = endpoint.lower()
    if "atlassian.net/wiki" in e or "/rest/api/content" in e:
        return "confluence"
    if "notion.so" in e or "api.notion.com" in e:
        return "notion"
    return "atlassian_docs"  # default — vendor-neutral, expects MCP wiring


def _resolve_endpoint(arguments: dict[str, Any]) -> str:
    return (
        arguments.get("endpoint")
        or os.environ.get("CONFLUENCE_URL")
        or os.environ.get("DOCS_URL")
        or ""
    )


def _strip_html(s: str, max_len: int = 200) -> str:
    """Quick HTML-tag strip for snippet generation. Not a security boundary."""
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] + ("…" if len(s) > max_len else "")


# ---------------------------------------------------------------------------
# ConfluenceProvider — full implementation
# ---------------------------------------------------------------------------


class ConfluenceProvider:
    """Confluence Cloud REST API v1 (CQL search + content fetch)."""

    name = "confluence"

    def __init__(self, endpoint: str, headers: dict[str, str], session_kwargs: dict):
        self.endpoint = endpoint.rstrip("/")
        self.headers = headers
        self.session_kwargs = session_kwargs

    async def _request(self, session: aiohttp.ClientSession, path: str, params: dict | None = None) -> dict:
        url = f"{self.endpoint}{path}"
        try:
            async with session.get(url, params=params, headers=self.headers) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    return _err(
                        f"Confluence HTTP {resp.status}: {text[:500]}",
                        provider=self.name,
                    )
                try:
                    return {"_raw": json.loads(text)}
                except json.JSONDecodeError:
                    return _err(
                        f"Confluence returned non-JSON: {text[:200]}",
                        provider=self.name,
                    )
        except aiohttp.ClientError as exc:
            return _err(f"Confluence transport error: {exc}", provider=self.name)

    @staticmethod
    def _build_cql(arguments: dict[str, Any]) -> str:
        """Compose a CQL expression from --query, --space, --label."""
        parts: list[str] = []
        if (q := arguments.get("query")):
            # Escape double quotes for CQL safety
            esc = q.replace('"', '\\"')
            parts.append(f'(text ~ "{esc}" OR title ~ "{esc}")')
        if (sp := arguments.get("space")):
            parts.append(f'space = "{sp}"')
        if (lbl := arguments.get("label")):
            parts.append(f'label = "{lbl}"')
        # Always exclude archived
        parts.append("type in (page, blogpost)")
        return " AND ".join(parts) if parts else "type in (page, blogpost)"

    @staticmethod
    def _normalize_search_result(raw: dict, base_url: str, include_body: bool) -> list[dict]:
        out: list[dict] = []
        for entry in raw.get("results", []):
            content = entry.get("content") or entry
            page_id = content.get("id", "")
            title = content.get("title", entry.get("title", ""))
            space_key = (content.get("space") or {}).get("key")
            labels_raw = ((content.get("metadata") or {}).get("labels") or {}).get("results", [])
            labels = [l.get("name") for l in labels_raw if l.get("name")]
            url = f"{base_url}/wiki{content.get('_links', {}).get('webui', '/spaces/' + (space_key or '_') + '/pages/' + page_id)}"
            snippet = _strip_html(entry.get("excerpt") or entry.get("title", ""))
            last_updated = (content.get("version") or entry.get("lastModified") or {}).get("when")
            row = {
                "id": page_id,
                "title": title,
                "url": url,
                "space": space_key,
                "labels": labels,
                "snippet": snippet,
                "last_updated": last_updated,
            }
            if include_body and content.get("body", {}).get("storage", {}).get("value"):
                row["body"] = _strip_html(content["body"]["storage"]["value"], max_len=10_000)
            out.append(row)
        return out

    async def search(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        if not arguments.get("query") and not arguments.get("label"):
            return _err(
                "Either --query or --label is required for search",
                provider=self.name,
                action="search",
            )
        cql = self._build_cql(arguments)
        limit = max(1, min(int(arguments.get("limit") or _DEFAULT_LIMIT), 250))
        params: dict[str, Any] = {
            "cql": cql,
            "limit": str(limit),
            "expand": "content.metadata.labels,content.version,content.space,content._links",
        }
        if arguments.get("include_body"):
            params["expand"] += ",content.body.storage"
        raw = await self._request(session, "/rest/api/content/search", params)
        if not raw.get("ok", True) and "_raw" not in raw:
            return raw
        rows = self._normalize_search_result(raw["_raw"], self.endpoint, bool(arguments.get("include_body")))
        warnings: list[str] = []
        total = raw["_raw"].get("totalSize") or raw["_raw"].get("size", len(rows))
        if total > limit:
            warnings.append(f"Truncated: total={total} returned={limit}; pass --limit to widen")
        return _ok(
            {"results": rows},
            metadata={
                "provider": self.name,
                "action": "search",
                "cql": cql,
                "total_count": total,
                "returned_count": len(rows),
            },
            warnings=warnings,
        )

    async def get(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        doc_id = arguments.get("id")
        if not doc_id:
            return _err("--id is required for get", provider=self.name, action="get")
        # Allow URL → id extraction
        if doc_id.startswith("http"):
            doc_id = self._extract_id_from_url(doc_id)
            if not doc_id:
                return _err(
                    "Cannot extract page ID from URL — pass numeric id instead",
                    provider=self.name,
                    action="get",
                )
        params = {"expand": "metadata.labels,version,space,body.storage"}
        raw = await self._request(session, f"/rest/api/content/{doc_id}", params)
        if not raw.get("ok", True) and "_raw" not in raw:
            return raw
        rows = self._normalize_search_result(
            {"results": [raw["_raw"]]},
            self.endpoint,
            bool(arguments.get("include_body")),
        )
        return _ok(
            {"results": rows},
            metadata={"provider": self.name, "action": "get", "id": doc_id},
        )

    @staticmethod
    def _extract_id_from_url(url: str) -> str | None:
        # /wiki/spaces/SPACE/pages/12345/Title or /wiki/display?pageId=12345
        m = re.search(r"/pages/(\d+)", url)
        if m:
            return m.group(1)
        qs = parse_qs(urlparse(url).query)
        return (qs.get("pageId") or [None])[0]

    async def list_by_label(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        if not arguments.get("label"):
            return _err("--label is required for list_by_label", provider=self.name, action="list_by_label")
        # Reuse search with label filter
        return await self.search(session, arguments)

    async def recent(self, session: aiohttp.ClientSession, arguments: dict) -> dict:
        # CQL ordering by lastmodified desc
        cql_parts: list[str] = ["type in (page, blogpost)"]
        if (sp := arguments.get("space")):
            cql_parts.append(f'space = "{sp}"')
        cql = " AND ".join(cql_parts) + " ORDER BY lastmodified DESC"
        limit = max(1, min(int(arguments.get("limit") or _DEFAULT_LIMIT), 250))
        params = {
            "cql": cql,
            "limit": str(limit),
            "expand": "content.metadata.labels,content.version,content.space,content._links",
        }
        raw = await self._request(session, "/rest/api/content/search", params)
        if not raw.get("ok", True) and "_raw" not in raw:
            return raw
        rows = self._normalize_search_result(raw["_raw"], self.endpoint, False)
        return _ok(
            {"results": rows},
            metadata={
                "provider": self.name,
                "action": "recent",
                "cql": cql,
                "returned_count": len(rows),
            },
        )


# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------


class _StubProvider:
    name = "stub"

    def __init__(self, endpoint: str, *_, **__):
        self.endpoint = endpoint

    async def _unsupported(self, *_, **__) -> dict:
        return _err(
            f"Provider {self.name!r} is declared but not yet implemented in this version. "
            f"For atlassian_docs, the implementation is the Rovo Dev MCP shim — see ARCHITECTURE.md.",
            provider=self.name,
        )

    search = get = list_by_label = recent = _unsupported


class AtlassianDocsProvider(_StubProvider):
    name = "atlassian_docs"


class NotionProvider(_StubProvider):
    name = "notion"


class MkDocsProvider(_StubProvider):
    name = "mkdocs"


# ---------------------------------------------------------------------------
# Auth + headers
# ---------------------------------------------------------------------------


def _get_auth_kwargs() -> dict:
    if (u := os.environ.get("CONFLUENCE_USER")) and (t := os.environ.get("CONFLUENCE_TOKEN")):
        return {"auth": aiohttp.BasicAuth(u, t)}
    return {}


def _get_headers() -> dict[str, str]:
    return {"Accept": "application/json"}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


_PROVIDERS = {
    "confluence": ConfluenceProvider,
    "atlassian_docs": AtlassianDocsProvider,
    "notion": NotionProvider,
    "mkdocs": MkDocsProvider,
}


async def execute(
    arguments: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Entry point for the runbook_search tool executor."""
    action = arguments.get("action")
    if not action:
        return _err("action parameter is required")
    if action not in _VALID_ACTIONS:
        return _err(f"Unknown action: {action!r}. Valid: {sorted(_VALID_ACTIONS)}")

    endpoint = _resolve_endpoint(arguments)
    provider_name = _resolve_provider(arguments, endpoint)

    # atlassian_docs is the default but doesn't need an endpoint URL (uses MCP).
    # All others need an endpoint.
    if provider_name != "atlassian_docs" and not endpoint:
        return _err(
            f"Provider {provider_name!r} requires --endpoint or CONFLUENCE_URL/DOCS_URL env var.",
            action=action,
        )

    provider_cls = _PROVIDERS.get(provider_name)
    if not provider_cls:
        return _err(f"Unknown provider: {provider_name!r}. Valid: {sorted(_PROVIDERS)}", action=action)

    if arguments.get("dry_run"):
        return _ok(
            {
                "action": action,
                "provider": provider_name,
                "endpoint": endpoint,
                "arguments": {
                    k: v for k, v in arguments.items()
                    if k not in ("action", "dry_run", "endpoint")
                },
            },
            metadata={"action": action, "provider": provider_name, "dry_run": True},
        )

    headers = _get_headers()
    session_kwargs = {"timeout": _REQUEST_TIMEOUT, **_get_auth_kwargs()}
    provider = provider_cls(endpoint, headers, session_kwargs)
    handler = getattr(provider, action, None)
    if handler is None:
        return _err(f"Action {action!r} not implemented on {provider_name!r}", action=action)

    async with aiohttp.ClientSession(**session_kwargs) as session:
        try:
            return await handler(session, arguments)
        except Exception as exc:
            logger.exception("runbook_search.execute crashed in %s.%s", provider_name, action)
            return _err(f"Unexpected error: {exc!r}", provider=provider_name, action=action)
