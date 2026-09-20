from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.config import RAGConfig
from app.rag.models.blocks import RagAnswer, RetrievalResult, Usage
from app.rag.embedding.openai_compatible import OpenAICompatibleEmbedding
from app.rag.llm.openai_compatible import OpenAICompatibleLLM
from app.rag.retriever.qdrant import QdrantRetriever
from app.rag.context.builder import build_context
from app.rag.prompt.campus_qa import build_messages
from app.rag.citation.source_builder import build_citations

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        embedding: OpenAICompatibleEmbedding,
        llm: OpenAICompatibleLLM,
        retriever: QdrantRetriever,
        config: RAGConfig | None = None,
    ):
        self.embedding = embedding
        self.llm = llm
        self.retriever = retriever
        self.config = config or RAGConfig()

    async def answer(
        self,
        question: str,
        knowledge_base_id: int | None,
        db: AsyncSession,
        *,
        history: list[dict] | None = None,
        stream: bool = False,
    ) -> RagAnswer | tuple[RagAnswer, AsyncIterator[str]]:
        start = time.monotonic()

        # 1. Embed question
        q_vectors = await self.embedding.embed([question])
        q_vector = q_vectors[0]

        # 2. Retrieve
        retrieval_start = time.monotonic()
        results = await self.retriever.search(
            q_vector,
            knowledge_base_id=knowledge_base_id,
            limit=self.config.candidate_top_k,
            score_threshold=self.config.similarity_threshold,
        )
        retrieval_elapsed = int((time.monotonic() - retrieval_start) * 1000)

        # 3. Final top-k
        results = results[: self.config.final_top_k]

        # 4. No evidence -> refuse
        if not results:
            refusal = "知识库中暂未找到足够的相关资料，暂时无法根据现有校园知识库给出可靠答案。"
            elapsed = int((time.monotonic() - start) * 1000)
            return RagAnswer(
                answer=refusal,
                retrievals=[],
                citations=[],
                model_name=self.llm.model,
                latency_ms=elapsed,
                retrieval_latency_ms=retrieval_elapsed,
                candidate_top_k=self.config.candidate_top_k,
                final_top_k=self.config.final_top_k,
                similarity_threshold=self.config.similarity_threshold,
            )

        # 5. Build context
        context = build_context(results, max_context_tokens=4000)

        # 6. Build messages
        messages = build_messages(context, question, history)

        # 7. Call LLM
        if stream:
            rag_answer = RagAnswer(
                answer="",
                retrievals=results,
                citations=[],
                model_name=self.llm.model,
                retrieval_latency_ms=retrieval_elapsed,
                candidate_top_k=self.config.candidate_top_k,
                final_top_k=self.config.final_top_k,
                similarity_threshold=self.config.similarity_threshold,
            )
            llm_start = time.monotonic()
            stream_iter = await self.llm.chat(
                messages,
                stream=True,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            # Return a wrapper that builds the final answer
            async def _stream_with_citations():
                full_answer = []
                async for token in stream_iter:
                    full_answer.append(token)
                    yield token
                rag_answer.answer = "".join(full_answer)
                rag_answer.citations = await build_citations(db, results)
                rag_answer.llm_latency_ms = int((time.monotonic() - llm_start) * 1000)
                rag_answer.latency_ms = int((time.monotonic() - start) * 1000)

            return rag_answer, _stream_with_citations()

        # Non-streaming
        llm_start = time.monotonic()
        resp = await self.llm.chat(
            messages,
            stream=False,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        answer_text = resp["choices"][0]["message"]["content"]
        usage_data = resp.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )
        citations = await build_citations(db, results)
        elapsed = int((time.monotonic() - start) * 1000)

        llm_elapsed = int((time.monotonic() - llm_start) * 1000)

        return RagAnswer(
            answer=answer_text,
            retrievals=results,
            citations=citations,
            model_name=self.llm.model,
            usage=usage,
            latency_ms=elapsed,
            retrieval_latency_ms=retrieval_elapsed,
            llm_latency_ms=llm_elapsed,
            candidate_top_k=self.config.candidate_top_k,
            final_top_k=self.config.final_top_k,
            similarity_threshold=self.config.similarity_threshold,
        )
