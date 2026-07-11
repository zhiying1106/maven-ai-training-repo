from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ChunkType = Literal["commit", "pr", "ticket", "chat", "email", "doc"]
QueryType = Literal["why", "what-breaks", "external", "general"]


@dataclass(frozen=True)
class Chunk:
    id: str
    type: ChunkType
    text: str
    metadata: dict[str, object] = field(default_factory=dict)
