from __future__ import annotations

import math
import re
from collections import Counter

from .types import Chunk

TOKEN_RE = re.compile(r"[^a-z0-9_#.:/-]+")
EXPLICIT_ID_RE = re.compile(r"(?:PR#\d+|[A-Z]+-\d+|commit:[a-z0-9]+|RFC-\d+|PROP-\d+)")

WHY_TERMS = {"why", "reason", "decided", "rationale", "chose", "choice", "decision", "because"}
BREAKS_TERMS = {"breaks", "break", "change", "impact", "depend", "affect", "caller", "downstream"}
CONCERN_TERMS = {"concern", "raised", "complaint", "worry", "pushback", "disagree", "objection"}


def _tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.sub(" ", text.lower()).split() if len(token) > 1]


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _idf_map(query_terms: list[str], chunks: tuple[Chunk, ...]) -> dict[str, float]:
    idf: dict[str, float] = {}
    tokenized_chunks = [set(_tokenize(chunk.text)) for chunk in chunks]
    for term in query_terms:
        df = sum(1 for tokens in tokenized_chunks if term in tokens)
        idf[term] = math.log((len(chunks) + 1) / (df + 0.5))
    return idf


def _bm25(
    query_terms: list[str],
    chunk_tokens: list[str],
    idf: dict[str, float],
    avg_doc_len: float,
) -> float:
    k1 = 1.5
    b = 0.75
    doc_len = len(chunk_tokens) or 1
    counts = Counter(chunk_tokens)
    score = 0.0

    for term in query_terms:
        tf = counts[term]
        if tf == 0:
            continue
        score += idf.get(term, 1.0) * (
            (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len)))
        )

    return score


def search(query: str, chunks: tuple[Chunk, ...], top_k: int = 7) -> list[Chunk]:
    if not chunks:
        return []

    lower_query = query.lower()
    query_terms = _tokenize(query)
    explicit_ids = EXPLICIT_ID_RE.findall(query)
    chunk_tokens_by_id = {chunk.id: _tokenize(chunk.text) for chunk in chunks}
    avg_doc_len = sum(len(tokens) for tokens in chunk_tokens_by_id.values()) / len(chunks)
    idf = _idf_map(query_terms, chunks)

    scored: list[tuple[Chunk, float]] = []
    for chunk in chunks:
        score = _bm25(query_terms, chunk_tokens_by_id[chunk.id], idf, avg_doc_len)
        linked_ids = chunk.metadata.get("linkedIds", [])

        for source_id in explicit_ids:
            if chunk.id == source_id or source_id in chunk.text or source_id in linked_ids:
                score += 8

        if _has_any(lower_query, WHY_TERMS) and chunk.type in {"pr", "doc", "ticket"}:
            score *= 1.4
        if _has_any(lower_query, BREAKS_TERMS) and chunk.type in {"pr", "commit"}:
            score *= 1.3
        if _has_any(lower_query, CONCERN_TERMS) and chunk.type in {"chat", "pr"}:
            score *= 1.5
        if any(term in lower_query for term in ("summarize", "summary", "changed")) and chunk.type in {
            "commit",
            "pr",
        }:
            score *= 1.2
        if any(term in lower_query for term in ("business case", "proposal", "original")) and chunk.type == "doc":
            score *= 1.6

        scored.append((chunk, score))

    top = [chunk for chunk, score in sorted(scored, key=lambda item: item[1], reverse=True)[:top_k] if score > 0]

    retrieved_ids = {chunk.id for chunk in top}
    extras: list[Chunk] = []
    chunks_by_id = {chunk.id: chunk for chunk in chunks}

    for chunk in top:
        if len(extras) >= 2:
            break
        for linked_id in chunk.metadata.get("linkedIds", []):
            if not isinstance(linked_id, str) or linked_id in retrieved_ids:
                continue
            linked = chunks_by_id.get(linked_id)
            if linked:
                extras.append(linked)
                retrieved_ids.add(linked_id)
                if len(extras) >= 2:
                    break

    return top + extras
