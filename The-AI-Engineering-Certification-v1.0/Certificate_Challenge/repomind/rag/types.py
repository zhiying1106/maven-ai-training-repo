from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

ChunkType = Literal["commit", "pr", "ticket", "chat", "email", "doc"]
QueryType = Literal["why", "what-breaks", "external", "general"]


@dataclass(frozen=True)
class Chunk:
    id: str
    type: ChunkType
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ── LangGraph state ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """
    State object threaded through the LangGraph state machine.

    Must be a TypedDict (not a bare ``dict`` subclass): LangGraph derives its
    state channels from the annotations here, and a schema with no annotations
    compiles to a graph with zero channels that raises InvalidUpdateError
    ("Must write to at least one of []") on the very first invoke.

    Keys
    ----
    message       : current user question
    history       : list of {role, content} dicts (last N turns)
    query_type    : classified intent (why / what-breaks / external / general)
    chunks        : retrieved Chunk objects
    graph_nodes   : extra nodes from knowledge-graph traversal
    tavily_results: raw Tavily search results
    answer        : final synthesized answer text
    sources       : list of cited source IDs
    confidence    : "high" | "low" | "external"
    session_id    : opaque string used for server-side session memory
    """

    message: str
    history: list[dict[str, Any]]
    query_type: QueryType
    chunks: list[Chunk]
    graph_nodes: list[Chunk]
    tavily_results: list[dict[str, Any]]
    answer: str
    sources: list[str]
    confidence: str
    session_id: str
