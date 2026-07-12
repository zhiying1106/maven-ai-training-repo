"""
Structural knowledge graph for "what-breaks-if" traversal.

The graph is a directed adjacency structure built once from the chunk corpus.
Nodes are chunk IDs; edges represent:
  - explicit cross-reference IDs found in chunk text (linkedIds)
  - file-level co-change relationships (two commits/PRs touching the same file)

traverse() starts from the matched chunks and expands 1-2 hops of the graph,
returning additional dependency context.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from functools import lru_cache

from .knowledge_base import build_knowledge_base
from .types import Chunk

# IDs that look like file paths or function names in "what-breaks" questions
FILE_RE = re.compile(r"[\w/]+\.py\b")


@lru_cache(maxsize=1)
def build_knowledge_graph() -> dict[str, list[str]]:
    """
    Return adjacency list: node_id → [neighbour_id, ...].

    Two kinds of edges:
    1. Explicit cross-reference  — linkedIds embedded in chunk metadata
    2. File co-change            — two chunks share at least one filename in
                                   their `files` metadata list
    """
    chunks = build_knowledge_base()
    graph: dict[str, list[str]] = defaultdict(list)

    # Edge type 1 – explicit cross-references
    for chunk in chunks:
        for linked_id in chunk.metadata.get("linkedIds", []):
            if isinstance(linked_id, str) and linked_id != chunk.id:
                graph[chunk.id].append(linked_id)

    # Edge type 2 – file co-change
    file_to_chunks: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        for f in chunk.metadata.get("files", []):
            if isinstance(f, str):
                file_to_chunks[f].append(chunk.id)

    for cid_list in file_to_chunks.values():
        for i, a in enumerate(cid_list):
            for b in cid_list[i + 1 :]:
                if b not in graph[a]:
                    graph[a].append(b)
                if a not in graph[b]:
                    graph[b].append(a)

    return dict(graph)


def traverse(seed_chunks: list[Chunk], max_hops: int = 2, max_nodes: int = 10) -> list[Chunk]:
    """
    BFS from seed_chunks through the knowledge graph up to max_hops.
    Returns additional chunks (not already in seed) sorted by hop distance.
    """
    graph = build_knowledge_graph()
    chunks_by_id = {c.id: c for c in build_knowledge_base()}

    visited: set[str] = {c.id for c in seed_chunks}
    queue: deque[tuple[str, int]] = deque((c.id, 0) for c in seed_chunks)
    extra: list[Chunk] = []

    while queue and len(extra) < max_nodes:
        node_id, hop = queue.popleft()
        if hop >= max_hops:
            continue
        for neighbour in graph.get(node_id, []):
            if neighbour not in visited:
                visited.add(neighbour)
                chunk = chunks_by_id.get(neighbour)
                if chunk:
                    extra.append(chunk)
                    queue.append((neighbour, hop + 1))

    return extra[:max_nodes]


def find_file_dependents(filename: str) -> list[Chunk]:
    """
    Return every chunk that references *filename* directly (for 'what-breaks').
    """
    chunks = build_knowledge_base()
    results: list[Chunk] = []
    lower = filename.lower()
    for chunk in chunks:
        files: list[str] = chunk.metadata.get("files", [])  # type: ignore[assignment]
        if any(lower in f.lower() for f in files if isinstance(f, str)):
            results.append(chunk)
        elif lower in chunk.text.lower():
            results.append(chunk)
    return results
