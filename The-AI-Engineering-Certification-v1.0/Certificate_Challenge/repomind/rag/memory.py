"""
Two-layer memory for RepoMind.

Layer 1 – Session chat memory (in-process dict, keyed by session_id).
           Stores the last WINDOW_SIZE messages per session so the
           stateless API can reconstruct multi-turn context server-side,
           rather than relying solely on the client to replay history.
           Caveat: this dict lives in one function instance's process
           memory. On Vercel, a Python Function's container is not
           guaranteed to stay warm between requests, so this layer can
           silently reset mid-conversation. The client also resends the
           last 10 messages as `history` on every request (see
           ChatInterface.tsx), which is what actually keeps a conversation
           coherent across a cold start — this layer is a same-container
           optimisation on top of that, not a durability guarantee.

Layer 2 – Persistent answer cache (JSON file on disk).
           Survives across server restarts (same machine/container only).
           Stores a lightweight map of
               question → {answer_summary, sources, timestamp}
           so the same (or very similar) question is answered without
           re-running retrieval + generation. Written to
           data/answer_cache.json locally, or a Vercel-writable temp path
           in production (see _default_answer_cache_file).

           This is NOT the structural knowledge graph described in the
           architecture doc — that graph (nodes = chunk IDs, edges =
           cross-references + file co-change) lives in
           rag/knowledge_graph.py and is intentionally not persisted here
           or anywhere else. It's a pure, deterministic function of the
           static files in data/*.json, rebuilt in-process via @lru_cache
           on first use each cold start. Since the source of truth (the
           data files) doesn't change at runtime, re-deriving the graph is
           cheap and always consistent — persisting a second copy of it
           would only add a cache-invalidation liability with no benefit.

Both layers are initialised lazily on first access.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

WINDOW_SIZE = 20          # messages kept per session


def _default_answer_cache_file() -> Path:
    """
    Where to persist the answer cache.

    On Vercel the function filesystem is read-only except for the system temp
    dir (/tmp), so a write to data/answer_cache.json raises OSError and would
    500 the request. Default to a writable temp path there; allow an explicit
    override via REPOMIND_ANSWER_CACHE_FILE. Locally this still lands next to
    the data files.
    """
    override = os.getenv("REPOMIND_ANSWER_CACHE_FILE")
    if override:
        return Path(override)
    # VERCEL is set in the Vercel runtime; fall back to /tmp there.
    if os.getenv("VERCEL"):
        return Path(tempfile.gettempdir()) / "repomind_answer_cache.json"
    return Path(__file__).resolve().parent.parent / "data" / "answer_cache.json"


ANSWER_CACHE_FILE = _default_answer_cache_file()
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7   # 7 days before a cached answer expires


# ── Layer 1: in-process session memory ──────────────────────────────────────

_sessions: dict[str, list[dict[str, str]]] = {}


def get_session_history(session_id: str) -> list[dict[str, str]]:
    """Return the stored chat history for *session_id* (may be empty list)."""
    return list(_sessions.get(session_id, []))


def append_to_session(session_id: str, role: str, content: str) -> None:
    """Append a message to the session window, trimming to WINDOW_SIZE."""
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append({"role": role, "content": content})
    # Keep only the last WINDOW_SIZE messages
    if len(_sessions[session_id]) > WINDOW_SIZE:
        _sessions[session_id] = _sessions[session_id][-WINDOW_SIZE:]


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


# ── Layer 2: persistent answer cache ─────────────────────────────────────────

def _load_cache() -> dict[str, Any]:
    if ANSWER_CACHE_FILE.exists():
        try:
            with ANSWER_CACHE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(data: dict[str, Any]) -> None:
    # Best-effort: the answer cache is an optimisation, never a correctness
    # requirement. A read-only filesystem (or any other write failure) must not
    # break the request that produced the answer.
    try:
        ANSWER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with ANSWER_CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def _question_key(question: str) -> str:
    """Stable hash key for a question string."""
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]


def lookup_answer_cache(question: str) -> dict[str, Any] | None:
    """
    Return the cached entry for *question* if present and not expired,
    else None.
    """
    data = _load_cache()
    key = _question_key(question)
    entry = data.get(key)
    if not entry:
        return None
    age = time.time() - entry.get("timestamp", 0)
    if age > CACHE_TTL_SECONDS:
        # Expired — remove and return None
        data.pop(key, None)
        _save_cache(data)
        return None
    return entry


def store_answer_cache(question: str, answer: str, sources: list[str]) -> None:
    """Cache a question → answer mapping in the persistent answer cache."""
    data = _load_cache()
    key = _question_key(question)
    data[key] = {
        "question": question,
        "answer_summary": answer[:500],   # truncate for storage efficiency
        "sources": sources,
        "timestamp": time.time(),
    }
    _save_cache(data)


def list_answer_cache_entries() -> list[dict[str, Any]]:
    """Return all non-expired cached entries (for debugging / inspection)."""
    data = _load_cache()
    now = time.time()
    return [
        entry
        for entry in data.values()
        if isinstance(entry, dict) and (now - entry.get("timestamp", 0)) <= CACHE_TTL_SECONDS
    ]
