"""
RepoMind LangGraph agent.

State machine  (matches the architecture diagram in Project_Documentations.md)
─────────────────────────────────────────────────────────────────────────────
  START
    └─► router          ← classify intent
          ├─► retrieve  ← "why" / "general" → Qdrant hybrid search (vector + BM25)
          ├─► graph_traverse  ← "what-breaks" → knowledge-graph BFS
          └─► tavily_search   ← "external"   → live Tavily web search
   retrieve / graph_traverse / tavily_search
          └─► synthesize      ← LLM answer + source citations
                └─► confidence_check
                      ├─► flag_low (low evidence → explicit "no rationale found")
                      └─► END
─────────────────────────────────────────────────────────────────────────────

Uses the openai SDK directly (no langchain_openai) to avoid version conflicts,
pointed at Vercel AI Gateway (https://ai-gateway.vercel.sh/v1) rather than
OpenAI's API directly — see _client() below. LangSmith tracing is enabled
automatically when LANGCHAIN_API_KEY and LANGCHAIN_TRACING_V2=true are
present in the environment.
"""
from __future__ import annotations

import os
import re
from typing import Any

from openai import OpenAI
from langgraph.graph import END, StateGraph

from .embeddings import vector_search
from .knowledge_base import build_knowledge_base
from .knowledge_graph import find_file_dependents, traverse
from .memory import (
    append_to_session,
    get_session_history,
    lookup_answer_cache,
    store_answer_cache,
)
from .retrieval import search as bm25_search
from .types import AgentState, Chunk, QueryType

# ── Constants ────────────────────────────────────────────────────────────────

# All LLM/embedding calls go through Vercel AI Gateway rather than OpenAI's API
# directly, so model IDs are provider-prefixed ("openai/<model>").
AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_ROUTER_MODEL = "openai/gpt-4o-mini"
SOURCE_RE = re.compile(
    r"(?:PR#\d+|[A-Z]+-\d+|commit:[a-z0-9]+|RFC-\d+|PROP-\d+|chat:[\w-]+|email:[\w-]+)"
)


# ── OpenAI client helpers ────────────────────────────────────────────────────

def _client() -> OpenAI:
    """
    Client pointed at Vercel AI Gateway's OpenAI-compatible endpoint.

    Auth follows Vercel's own recommended fallback chain: an AI Gateway API
    key (works anywhere — local dev, CI, this eval harness) takes precedence
    over a Vercel OIDC token (auto-injected as VERCEL_OIDC_TOKEN when this
    runs as a Vercel Function in production, no secret to manage there).
    """
    api_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_OIDC_TOKEN")
    if not api_key:
        raise RuntimeError(
            "AI_GATEWAY_API_KEY is not configured (and no VERCEL_OIDC_TOKEN "
            "was found). Add an AI Gateway API key locally and to Vercel "
            "project environment variables."
        )
    return OpenAI(api_key=api_key, base_url=AI_GATEWAY_BASE_URL)


def _model() -> str:
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def _router_model() -> str:
    return (
        os.getenv("OPENAI_ROUTER_MODEL")
        or os.getenv("OPENAI_MODEL")
        or DEFAULT_ROUTER_MODEL
    )


def _chat(
    client: OpenAI,
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1200,
    temperature: float | None = None,
) -> str:
    """Single-turn chat completion via openai SDK.

    Uses ``max_completion_tokens`` (not the legacy ``max_tokens``): GPT-5.x
    models — including the default openai/gpt-5.4-mini — reject ``max_tokens``
    with a 400 "Unsupported parameter". ``max_completion_tokens`` is accepted
    by both the GPT-5 family and gpt-4o models.

    ``temperature`` is left at the API default (None) unless the caller needs
    reproducibility — e.g. node_router passes 0, since an eval run showed the
    router non-deterministically reclassifying the same question between
    runs (see Task 6.3 in Project_Documentations.md).
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


# ── Misc helpers ─────────────────────────────────────────────────────────────

def _extract_sources(text: str) -> list[str]:
    return list(dict.fromkeys(SOURCE_RE.findall(text)))


def _format_history(history: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in history[-10:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {item.get('content', '')}")
    return "\n\n".join(lines)


def _chunks_to_context(chunks: list[Chunk]) -> str:
    return "\n\n".join(
        f"===== [{c.id}] ({c.type}) =====\n{c.text}" for c in chunks
    )


# ── LangGraph nodes ──────────────────────────────────────────────────────────

def node_router(state: AgentState) -> AgentState:
    """Classify the user's intent into one of four query types."""
    client = _client()
    raw = _chat(
        client,
        model=_router_model(),
        system="""Classify the engineering question into exactly one category:
- "why" for reasons or rationale behind a past technical decision made by THIS team
- "what-breaks" for impact, dependencies, callers, or tests affected by changing THIS team's code
- "general" for historical summaries, timelines, broad change-history, or "has anyone raised concerns/objections/pushback about X" questions about THIS team's own decisions or work
- "external" ONLY for questions asking for general/public best-practice knowledge that has no connection to this team's own history, artifacts, or decisions

Critical rule: a question about this team's own systems, services, thresholds, PRs, incidents, or past choices is internal ("why" / "what-breaks" / "general") even when it is phrased in a generic-sounding way, e.g. "was X validated against real data" or "did anyone raise concerns about Y". Only use "external" when the question could be asked of any company and has no specific tie to this team's own artifacts.

Examples:
Q: "Did anyone raise concerns about added latency when the payment service moved to Redis?"
A: general
Q: "Was the 5-attempts-per-15-minutes login rate limit validated against real traffic data before it shipped?"
A: general
Q: "What's the current best practice for rate limiting in FastAPI?"
A: external
Q: "What's a good way to unit-test circuit breaker behavior in a Python microservice?"
A: external

Respond with only the category word.""",
        user=state["message"],
        # AI Gateway enforces a minimum max_output_tokens of 16 (rejects lower
        # with a 400), unlike calling OpenAI directly which accepted 10.
        max_tokens=16,
        temperature=0,
    )
    category = raw.strip().lower()
    qt: QueryType = category if category in {"why", "what-breaks", "external", "general"} else "general"  # type: ignore[assignment]
    state["query_type"] = qt
    return state


def retrieval_mode() -> str:
    """
    'hybrid' (default) or 'dense' — set REPOMIND_RETRIEVAL_MODE=dense to force
    dense-vector-only retrieval. This exists solely to produce the "baseline
    (dense vector only)" column in the Task 6.2 eval comparison table; the
    deployed app should always run with the default hybrid mode.
    """
    mode = (os.getenv("REPOMIND_RETRIEVAL_MODE") or "hybrid").strip().lower()
    return mode if mode in {"hybrid", "dense"} else "hybrid"


def node_retrieve(state: AgentState) -> AgentState:
    """
    Hybrid retrieval (default): dense vector search (Qdrant /
    text-embedding-3-large) fused with BM25 keyword search via Reciprocal
    Rank Fusion. Set REPOMIND_RETRIEVAL_MODE=dense to bypass BM25 fusion and
    run dense-vector-only retrieval instead (see retrieval_mode() above).
    """
    message: str = state["message"]
    kb = build_knowledge_base()

    # Dense (vector) retrieval
    try:
        dense = vector_search(message, top_k=8)
    except Exception:
        dense = []

    if retrieval_mode() == "dense":
        state["chunks"] = dense[:8]
        return state

    # Sparse / BM25 retrieval
    sparse = bm25_search(message, kb, top_k=8)

    # Reciprocal Rank Fusion (k=60)
    k = 60
    scores: dict[str, float] = {}
    id_to_chunk: dict[str, Chunk] = {}

    for rank, chunk in enumerate(dense, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        id_to_chunk[chunk.id] = chunk
    for rank, chunk in enumerate(sparse, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        id_to_chunk[chunk.id] = chunk

    fused = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)[:8]
    state["chunks"] = [id_to_chunk[cid] for cid in fused]
    return state


def node_graph_traverse(state: AgentState) -> AgentState:
    """
    Knowledge-graph traversal for 'what-breaks' questions.
    Seeds from BM25, expands via structural dependency edges (BFS).
    """
    message: str = state["message"]
    kb = build_knowledge_base()

    seeds = bm25_search(message, kb, top_k=5)

    # Also seed from filenames mentioned in the question
    file_re = re.compile(r"[\w/]+\.py\b")
    for fname in file_re.findall(message):
        for chunk in find_file_dependents(fname):
            if chunk not in seeds:
                seeds.append(chunk)

    extras = traverse(seeds, max_hops=2, max_nodes=8)

    seen: set[str] = set()
    merged: list[Chunk] = []
    for c in seeds + extras:
        if c.id not in seen:
            seen.add(c.id)
            merged.append(c)

    state["chunks"] = merged[:10]
    state["graph_nodes"] = extras
    return state


def node_tavily_search(state: AgentState) -> AgentState:
    """
    Live Tavily web search for external / general-knowledge questions.
    Gracefully falls back if TAVILY_API_KEY is absent.
    """
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    if not tavily_key:
        state["tavily_results"] = []
        state["chunks"] = []
        return state

    try:
        from tavily import TavilyClient  # type: ignore[import]
        tc = TavilyClient(api_key=tavily_key)
        results = tc.search(query=state["message"], max_results=5)
        state["tavily_results"] = results.get("results", [])
    except Exception:
        state["tavily_results"] = []

    state["chunks"] = []
    return state


def node_synthesize(state: AgentState) -> AgentState:
    """
    Synthesize a grounded answer from retrieved context + conversation history.
    """
    message: str = state["message"]
    query_type: str = state.get("query_type", "general")
    history: list[dict[str, Any]] = state.get("history", [])
    chunks: list[Chunk] = state.get("chunks", [])
    tavily_results: list[dict] = state.get("tavily_results", [])
    session_id: str = state.get("session_id", "")

    # Merge server-side session history (survives across page reloads)
    if session_id:
        server_history = get_session_history(session_id)
        history = server_history + history  # server is older, client is newer

    history_text = _format_history(history)
    client = _client()

    # ── External path (Tavily) ─────────────────────────────────────────────
    if query_type == "external":
        if tavily_results:
            search_context = "\n\n".join(
                f"[{i+1}] {r.get('title', '')}\nURL: {r.get('url', '')}\n{r.get('content', '')}"
                for i, r in enumerate(tavily_results)
            )
            system = (
                "You are RepoMind, an engineering knowledge agent.\n"
                "Answer the question using the web search results provided. "
                "Prefix your answer with [EXTERNAL]. "
                "Cite the source URL(s) inline where relevant. "
                "If the topic is time-sensitive, note that the answer should be "
                "verified against current official documentation."
            )
            user = (
                f"{history_text}\n\nWeb search results:\n{search_context}\n\nUser: {message}"
            ).strip()
        else:
            system = (
                "You are RepoMind, an engineering knowledge agent.\n"
                "This question requires general or external knowledge. "
                "Answer clearly and prefix your reply with [EXTERNAL]. "
                "If the topic is time-sensitive, say the answer should be verified "
                "against current official documentation."
            )
            user = f"{history_text}\n\nUser: {message}".strip()

        answer: str = _chat(client, model=_model(), system=system, user=user, max_tokens=900)
        state["answer"] = answer
        state["sources"] = []
        state["confidence"] = "external"

        if session_id:
            append_to_session(session_id, "user", message)
            append_to_session(session_id, "assistant", answer)
        return state

    # ── Internal RAG / graph path ──────────────────────────────────────────
    if not chunks:
        state["answer"] = (
            "No rationale found in source artifacts. "
            "The internal data (commits, PRs, tickets, docs, chat, and email) "
            "does not contain evidence relevant to this question."
        )
        state["sources"] = []
        state["confidence"] = "low"
        if session_id:
            append_to_session(session_id, "user", message)
            append_to_session(session_id, "assistant", state["answer"])
        return state

    context_blocks = _chunks_to_context(chunks)
    graph_note = ""
    if query_type == "what-breaks" and state.get("graph_nodes"):
        graph_note = (
            "\n\nNote: context below includes chunks discovered via structural "
            "dependency-graph traversal in addition to direct retrieval."
        )

    system = (
        "You are RepoMind, an engineering knowledge agent for the Northwind Analytics demo team.\n"
        "Answer questions about codebase history, architectural decisions, and technical rationale "
        "by synthesising evidence from commits, pull requests, tickets, chat threads, emails, "
        "and internal documents.\n\n"
        "Rules:\n"
        "1. Cite source IDs inline exactly as written — e.g. PR#245, PAY-102, "
        "commit:a1b2c3d, chat:th-pay-1, email:email-pay-1, RFC-004, PROP-001.\n"
        "2. If the retrieved context does not contain enough evidence, say "
        '"No rationale found in source artifacts" and explain what was checked.\n'
        "3. For 'what breaks if I change X' questions, list specific files, services, "
        "callers, and tests mentioned in the source artifacts.\n"
        "4. Keep answers concise and engineer-focused.\n"
        "5. For multi-hop questions, walk the chain of artifacts explicitly."
    )
    user = (
        f"{history_text}\n\n"
        f"Retrieved context:{graph_note}\n{context_blocks}\n\n"
        f"User: {message}"
    ).strip()

    answer = _chat(client, model=_model(), system=system, user=user, max_tokens=1200)
    sources = _extract_sources(answer)

    state["answer"] = answer
    state["sources"] = sources

    if session_id:
        append_to_session(session_id, "user", message)
        append_to_session(session_id, "assistant", answer)
    if sources:
        store_answer_cache(message, answer, sources)

    return state


def node_confidence_check(state: AgentState) -> AgentState:
    """Heuristic confidence gate — no LLM call."""
    if state.get("confidence") == "external":
        return state

    answer: str = state.get("answer", "")
    sources: list[str] = state.get("sources", [])
    lower = answer.lower()

    low = (
        "no rationale found" in lower
        or "not found in source" in lower
        or "no evidence" in lower
        or not sources
    )

    if low:
        state["confidence"] = "low"
        if "no rationale found" not in lower and "no evidence" not in lower:
            state["answer"] = "No rationale found in source artifacts. " + answer
    else:
        state["confidence"] = "high"

    return state


# ── Conditional routing ───────────────────────────────────────────────────────

def _route_after_router(state: AgentState) -> str:
    qt = state.get("query_type", "general")
    if qt == "external":
        return "tavily_search"
    if qt == "what-breaks":
        return "graph_traverse"
    return "retrieve"


# ── LangGraph construction ────────────────────────────────────────────────────

def _build_graph() -> Any:
    g: StateGraph = StateGraph(AgentState)  # type: ignore[arg-type]

    g.add_node("router", node_router)
    g.add_node("retrieve", node_retrieve)
    g.add_node("graph_traverse", node_graph_traverse)
    g.add_node("tavily_search", node_tavily_search)
    g.add_node("synthesize", node_synthesize)
    g.add_node("confidence_check", node_confidence_check)

    g.set_entry_point("router")
    g.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "retrieve": "retrieve",
            "graph_traverse": "graph_traverse",
            "tavily_search": "tavily_search",
        },
    )
    g.add_edge("retrieve", "synthesize")
    g.add_edge("graph_traverse", "synthesize")
    g.add_edge("tavily_search", "synthesize")
    g.add_edge("synthesize", "confidence_check")
    g.add_edge("confidence_check", END)

    return g.compile()


_GRAPH: Any = None


def _get_graph() -> Any:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


# ── Public entry point ───────────────────────────────────────────────────────

def run_agent(
    message: str,
    history: list[dict[str, Any]] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """
    Run the LangGraph agent for a single turn.

    Parameters
    ----------
    message    : the user's question
    history    : list of {role, content} dicts (client-supplied, last N turns)
    session_id : opaque string for server-side session memory; optional

    Returns
    -------
    dict with keys: answer, sources, confidence, queryType
    """
    history = history or []

    # Serve from the persistent answer cache if available
    cached = lookup_answer_cache(message)
    if cached:
        return {
            "answer": cached["answer_summary"],
            "sources": cached["sources"],
            "confidence": "high",
            "queryType": "cached",
            "cached": True,
        }

    initial_state: AgentState = AgentState(
        message=message,
        history=history,
        query_type="general",
        chunks=[],
        graph_nodes=[],
        tavily_results=[],
        answer="",
        sources=[],
        confidence="low",
        session_id=session_id,
    )

    final_state: AgentState = _get_graph().invoke(initial_state)

    return {
        "answer": final_state.get("answer", ""),
        "sources": final_state.get("sources", []),
        "confidence": final_state.get("confidence", "low"),
        "queryType": final_state.get("query_type", "general"),
    }
