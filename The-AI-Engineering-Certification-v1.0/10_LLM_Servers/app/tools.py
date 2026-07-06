"""Toolbelt assembly for agents.

Collects third-party tools and local tools (like RAG) into a single list that
graphs can bind to their language models.
"""
from __future__ import annotations

from typing import List

from app.rag import retrieve_information


def get_tool_belt() -> List:
    """Return the lightweight tool set used by the notebook evaluation."""
    return [retrieve_information]


