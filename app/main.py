import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, knowledge, documents, chat, conversations, admin, health, files
from app.core.config import get_settings
from app.rag.config import RAGConfig
from app.rag.embedding.openai_compatible import OpenAICompatibleEmbedding
from app.rag.llm.openai_compatible import OpenAICompatibleLLM
from app.rag.retriever.qdrant import QdrantRetriever
from app.rag.rerank.openai_compatible import OpenAICompatibleRerank
from app.rag.pipeline import RAGPipeline
from app.services.worker_service import DocumentWorker

from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)
settings = get_settings()

rag_pipeline: RAGPipeline | None = None
document_worker: DocumentWorker | None = None
worker_task: asyncio.Task | None = None


async def _load_rag_config() -> RAGConfig:
    from app.core.database import async_session
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    config = RAGConfig()
    try:
        async with async_session() as db:
            stmt = select(SystemConfig).where(
                SystemConfig.config_key.in_([
                    "rag.chunk_size", "rag.chunk_overlap",
                    "rag.candidate_top_k", "rag.final_top_k",
                    "rag.similarity_threshold", "rag.temperature", "rag.max_tokens",
                    "rag.vector_weight",
                ])
            )
            result = await db.execute(stmt)
            for row in result.scalars().all():
                key = row.config_key.replace("rag.", "")
                if row.value_type == "int":
                    setattr(config, key, int(row.config_value))
                elif row.value_type == "float":
                    setattr(config, key, float(row.config_value))
    except Exception:
        logger.warning("Failed to load RAG config from DB, using defaults")
    return config


async def _load_model_config(prefix: str) -> dict:
    from app.core.database import async_session
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    keys = [f"model.{prefix}.base_url", f"model.{prefix}.api_key", f"model.{prefix}.model", f"model.{prefix}.enabled"]
    result_dict = {}
    try:
        async with async_session() as db:
            stmt = select(SystemConfig).where(SystemConfig.config_key.in_(keys))
            result = await db.execute(stmt)
            for row in result.scalars().all():
                short_key = row.config_key.split(".")[-1]
                result_dict[short_key] = row.config_value
    except Exception:
        logger.warning(f"Failed to load {prefix} model config")
    return result_dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_pipeline, document_worker, worker_task

    try:
        rag_config = await _load_rag_config()
        embedding_cfg = await _load_model_config("embedding")
        llm_cfg = await _load_model_config("llm")

        embedding = OpenAICompatibleEmbedding(
            base_url=embedding_cfg.get("base_url", ""),
            api_key=embedding_cfg.get("api_key", ""),
            model=embedding_cfg.get("model", ""),
            batch_size=rag_config.embedding_batch_size,
        )
        llm = OpenAICompatibleLLM(
            base_url=llm_cfg.get("base_url", ""),
            api_key=llm_cfg.get("api_key", ""),
            model=llm_cfg.get("model", ""),
        )

        qdrant = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        retriever = QdrantRetriever(qdrant, "campus_rag_chunks_v1")
        app.state.retriever = retriever  # 供文档删除等路由清理向量

        # 重排模型可选:启用且配置完整时接入(对齐 RAGFlow 两级排序)
        rerank_cfg = await _load_model_config("rerank")
        rerank_provider = None
        if (rerank_cfg.get("enabled") == "true" and rerank_cfg.get("base_url")
                and rerank_cfg.get("api_key") and rerank_cfg.get("model")):
            rerank_provider = OpenAICompatibleRerank(
                base_url=rerank_cfg["base_url"],
                api_key=rerank_cfg["api_key"],
                model=rerank_cfg["model"],
            )

        app.state.rag_config = rag_config  # 与管线/worker 共享实例,rag-config 保存即热更新
        rag_pipeline = RAGPipeline(embedding, llm, retriever, rag_config, rerank=rerank_provider)

        vision_cfg = await _load_model_config("vision")
        if vision_cfg.get("enabled") != "true":
            vision_cfg = None
        document_worker = DocumentWorker(embedding, retriever, rag_config, llm=llm, vision_config=vision_cfg)
        worker_task = asyncio.create_task(document_worker.run())

        logger.info("RAG pipeline and worker started")
    except Exception:
        logger.exception("Failed to start RAG pipeline")

    yield

    if document_worker:
        document_worker.stop()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Smart Campus RAG", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(admin.router)
app.include_router(health.router)
app.include_router(files.router)
