"""
Qdrant vector store + text-embedding-3-large embeddings via Vercel AI Gateway.

On first call, build_vector_store() embeds all chunks and upserts them into
an in-memory Qdrant collection (no separate server needed for the prototype).
Subsequent calls reuse the cached client via @lru_cache.

Uses qdrant-client >= 1.7 API (collection_exists, upsert, query_points).
"""
from __future__ import annotations

import os
from functools import lru_cache

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .knowledge_base import build_knowledge_base
from .types import Chunk

COLLECTION = "repomind"
# Provider-prefixed model ID: all embedding calls route through Vercel AI
# Gateway (see rag/agent.py::_client() for the auth pattern this mirrors).
AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
EMBED_MODEL = "openai/text-embedding-3-large"
EMBED_DIM = 3072  # text-embedding-3-large native output dimension


def _gateway_client() -> OpenAI:
    """
    Client pointed at Vercel AI Gateway. Duplicated (not imported) from
    rag/agent.py::_client() to avoid a circular import — agent.py already
    imports vector_search from this module.
    """
    api_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv("VERCEL_OIDC_TOKEN") or ""
    return OpenAI(api_key=api_key, base_url=AI_GATEWAY_BASE_URL)


def _embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Batch-embed texts; returns list of float vectors in input order."""
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


@lru_cache(maxsize=1)
def build_vector_store() -> QdrantClient:
    """
    Build (or reuse) the in-memory Qdrant collection.
    Returns the QdrantClient so callers can run queries against it.
    """
    oai = _gateway_client()
    qclient = QdrantClient(":memory:")

    # Qdrant in-memory always starts empty; create collection unconditionally.
    qclient.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )

    chunks: tuple[Chunk, ...] = build_knowledge_base()
    texts = [chunk.text for chunk in chunks]

    vectors = _embed_texts(oai, texts)

    points = [
        PointStruct(
            id=idx,
            vector=vec,
            payload={
                "chunk_id": chunk.id,
                "chunk_type": chunk.type,
                "text": chunk.text,
                "metadata": {
                    k: v
                    for k, v in chunk.metadata.items()
                    if isinstance(v, (str, int, float, bool, list)) and k != "metadata"
                },
            },
        )
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    qclient.upsert(collection_name=COLLECTION, points=points)

    return qclient


def vector_search(query: str, top_k: int = 8) -> list[Chunk]:
    """
    Embed *query* with text-embedding-3-large and return the top-k most
    similar chunks from the Qdrant in-memory collection.
    """
    oai = _gateway_client()
    qclient = build_vector_store()

    query_vec = _embed_texts(oai, [query])[0]

    # qdrant-client >= 1.7 uses query_points; fall back to search for older builds
    try:
        hits = qclient.query_points(
            collection_name=COLLECTION,
            query=query_vec,
            limit=top_k,
            with_payload=True,
        ).points
    except AttributeError:
        hits = qclient.search(
            collection_name=COLLECTION,
            query_vector=query_vec,
            limit=top_k,
            with_payload=True,
        )

    chunks_by_id = {c.id: c for c in build_knowledge_base()}
    results: list[Chunk] = []
    for hit in hits:
        cid = hit.payload.get("chunk_id", "") if hit.payload else ""  # type: ignore[union-attr]
        if cid in chunks_by_id:
            results.append(chunks_by_id[cid])
    return results
