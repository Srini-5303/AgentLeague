from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class LoreChunk(BaseModel):
    source: str          # filename / doc id
    title: str
    text: str
    score: float = 0.0
    gm_only: bool = False


class KnowledgeStore(ABC):
    """Retrieval over the Eldervale world bible. GM-only chunks are returned only
    when include_secrets=True (the GM/narrator path); never to player-facing or
    character-agent paths."""

    @abstractmethod
    async def search(
        self, query: str, *, top_k: int = 3, include_secrets: bool = False
    ) -> list[LoreChunk]:
        ...
