"""Native session records stored in OpenStartup's per-session state.

A native backend keeps a small durable record per conversation (vendor session
id, fingerprints, delivery cursors — never transcripts or rendered prompts).
OpenStartup stores it as ``session["native_session"]`` through the
SessionStore, so it survives server restarts, inferencer eviction and the
session's own checkpoints/rewinds.
"""

from __future__ import annotations

import threading
import weakref
from contextlib import AbstractContextManager
from typing import Any, Optional

from agent_foundation.common.inferencers.agentic_inferencers.conversational_native.session.record import (
    CallbackRecordStore,
    StaleRecordError,
)

SESSION_KEY = "native_session"
# The session dir's subdirectory for a native backend's private files (session
# instructions, CLI settings/MCP config, spilled tool results), owned by its
# live vendor session — so a checkpoint restore keeps it.
NATIVE_SESSION_DIR = "native"

_STORE_LOCKS: weakref.WeakKeyDictionary[Any, threading.Lock] = (
    weakref.WeakKeyDictionary()
)
_STORE_LOCKS_GUARD = threading.Lock()


def _record_lock(session_store: Any, session_id: str) -> AbstractContextManager[Any]:
    """The lock a record write holds: the session's own lock when the store
    has one (``SessionStore.session_lock``, held by every writer of the
    session's state), else one lock per store object. An inferencer rebuilt
    after an eviction gets a new adapter while the old one may still save, so
    the compare-and-swap needs a lock all adapters share."""
    session_lock = getattr(session_store, "session_lock", None)
    if callable(session_lock):
        return session_lock(session_id)
    with _STORE_LOCKS_GUARD:
        lock = _STORE_LOCKS.get(session_store)
        if lock is None:
            lock = _STORE_LOCKS[session_store] = threading.Lock()
        return lock


class SessionStoreRecordAdapter(CallbackRecordStore):
    """``NativeSessionRecordStore`` backed by ``session[SESSION_KEY]``; a save
    is a compare-and-swap on the record's generation and ``saved_at``."""

    def __init__(self, session_store: Any, session_id: str) -> None:
        self._session_store = session_store
        self._session_id = session_id
        super().__init__(
            load_fn=self._load_data,
            save_fn=self._save_data,
            lock=_record_lock(session_store, session_id),
        )

    def _load_data(self, conversation_key: str) -> Optional[dict[str, Any]]:
        session = self._session_store.get_session(self._session_id) or {}
        data = session.get(SESSION_KEY)
        if (
            not isinstance(data, dict)
            or data.get("conversation_key") != conversation_key
        ):
            return None
        return data

    def _save_data(self, conversation_key: str, data: dict[str, Any]) -> None:
        self._session_store.update_session(self._session_id, {SESSION_KEY: data})


def replace_record(
    session_store: Any,
    session_id: str,
    expected: Optional[dict[str, Any]],
    record: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Store ``record`` — derived from the stored record ``expected``, e.g. by
    a rewind made aside — in its place, atomically with every other writer of
    the session. Raises ``StaleRecordError``, writing nothing, when the stored
    record is no longer ``expected``. Returns the updated session."""
    with _record_lock(session_store, session_id):
        session = session_store.get_session(session_id) or {}
        if session.get(SESSION_KEY) != expected:
            raise StaleRecordError(
                f"The native session record of {session_id!r} changed while a "
                "replacement was being prepared; refusing to overwrite it."
            )
        return session_store.update_session(session_id, {SESSION_KEY: record})
