from __future__ import annotations

from typing import Protocol

from app.rag.models.blocks import RetrievalResult


class Retriever(Protocol):
    async def search(
        self,
        query_vector: list[float],
        *,
        knowledge_base_id: int | None = None,
        limit: int = 8,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        ...
