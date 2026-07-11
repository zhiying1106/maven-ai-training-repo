from __future__ import annotations

import os
import re
from typing import Any

from openai import OpenAI

from .knowledge_base import build_knowledge_base
from .retrieval import search
from .types import QueryType

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_ROUTER_MODEL = "gpt-5.4-mini"
SOURCE_RE = re.compile(
    r"(?:PR#\d+|[A-Z]+-\d+|commit:[a-z0-9]+|RFC-\d+|PROP-\d+|chat:[\w-]+|email:[\w-]+)"
)


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-..."):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Add it locally and to Vercel project environment variables."
        )
    return OpenAI(api_key=api_key)


def _model() -> str:
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def _router_model() -> str:
    return os.getenv("OPENAI_ROUTER_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_ROUTER_MODEL


def _generate_text(
    client: OpenAI,
    *,
    model: str,
    instructions: str,
    input_text: str,
    max_output_tokens: int,
) -> str:
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=input_text,
        max_output_tokens=max_output_tokens,
    )
    return response.output_text or ""


def _classify_question(client: OpenAI, question: str) -> QueryType:
    content = _generate_text(
        client,
        model=_router_model(),
        instructions="""Classify the engineering question into exactly one category:
- "why" for reasons or rationale behind past technical decisions
- "what-breaks" for impact, dependencies, callers, or tests affected by code changes
- "external" for general best-practice questions requiring public knowledge
- "general" for historical summaries, timelines, and broad change-history questions

Respond with only the category word.""",
        input_text=question,
        max_output_tokens=20,
    )
    category = content.strip().lower()
    if category in {"why", "what-breaks", "external", "general"}:
        return category  # type: ignore[return-value]
    return "general"


def _extract_sources(text: str) -> list[str]:
    return list(dict.fromkeys(SOURCE_RE.findall(text)))


def _format_history(history: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in history[-6:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        content = str(item.get("content", ""))
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def run_agent(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    history = history or []
    client = _client()
    query_type = _classify_question(client, message)

    if query_type == "external":
        answer = _generate_text(
            client,
            model=_model(),
            instructions="""You are RepoMind, an engineering knowledge agent.
This question requires general or external knowledge rather than the internal repository corpus.
Answer clearly and start with [EXTERNAL]. If the topic is time-sensitive, say that the answer should be verified against current official documentation.""",
            input_text=f"{_format_history(history)}\n\nUser: {message}".strip(),
            max_output_tokens=900,
        )
        return {
            "answer": answer,
            "sources": [],
            "confidence": "external",
            "queryType": query_type,
        }

    chunks = search(message, build_knowledge_base(), 8)
    if not chunks:
        return {
            "answer": "No rationale found in source artifacts. The internal data (commits, PRs, tickets, docs, chat, and email) does not contain evidence relevant to this question.",
            "sources": [],
            "confidence": "low",
            "queryType": query_type,
        }

    context_blocks = "\n\n".join(f"===== [{chunk.id}] ({chunk.type}) =====\n{chunk.text}" for chunk in chunks)
    answer = _generate_text(
        client,
        model=_model(),
        instructions="""You are RepoMind, an engineering knowledge agent for the Northwind Analytics demo team.
Answer questions about codebase history, architectural decisions, and technical rationale by synthesizing evidence from commits, pull requests, tickets, chat threads, emails, and internal documents.

Rules:
1. Cite source IDs inline exactly as written, such as PR#245, PAY-102, commit:a1b2c3d, chat:th-pay-1, email:email-pay-1, RFC-004, or PROP-001.
2. If the retrieved context does not contain enough evidence, say "No rationale found in source artifacts" and explain what was checked.
3. For "what breaks if I change X" questions, list specific files, services, callers, and tests mentioned in the source artifacts.
4. Keep answers concise and engineer-focused.
5. For multi-hop questions, explicitly walk the chain of artifacts so the user can see the reasoning trail.""",
        input_text=f"""{_format_history(history)}

Retrieved context:
{context_blocks}

User: {message}""".strip(),
        max_output_tokens=1100,
    )

    sources = _extract_sources(answer)
    lower_answer = answer.lower()
    low_confidence = (
        "no rationale found" in lower_answer
        or "not found in source" in lower_answer
        or "no evidence" in lower_answer
        or not sources
    )

    return {
        "answer": answer,
        "sources": sources,
        "confidence": "low" if low_confidence else "high",
        "queryType": query_type,
    }
