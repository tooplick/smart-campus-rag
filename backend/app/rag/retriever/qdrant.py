from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.rag.models.blocks import RetrievalResult

logger = logging.getLogger(__name__)


class QdrantRetriever:
    def __init__(self, client: AsyncQdrantClient, collection_name: str):
        self.client = client
        self.collection = collection_name

    async def search(
        self,
        query_vector: list[float],
        *,
        knowledge_base_id: int | None = None,
        limit: int = 8,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        query_filter = None
        if knowledge_base_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="knowledge_base_id",
                        match=MatchValue(value=knowledge_base_id),
                    )
                ]
            )

        results = await self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [
            RetrievalResult(
                chunk_id=point.id,
                document_id=point.payload.get("document_id", 0),
                knowledge_base_id=point.payload.get("knowledge_base_id", 0),
                score=point.score,
                content=point.payload.get("content", ""),
                content_type=point.payload.get("content_type", "text"),
                page_number=point.payload.get("page_number"),
                section_title=point.payload.get("section_title"),
                chunk_index=point.payload.get("chunk_index", 0),
            )
            for point in results
        ]
