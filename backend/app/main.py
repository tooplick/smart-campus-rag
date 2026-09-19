import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, knowledge, documents, chat
from app.core.config import get_settings
from app.rag.config import RAGConfig
from app.rag.embedding.openai_compatible import OpenAICompatibleEmbedding
from app.rag.llm.openai_compatible import OpenAICompatibleLLM
from app.rag.retriever.qdrant import QdrantRetriever
from app.rag.pipeline import RAGPipeline
from app.services.worker_service import DocumentWorker

from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)
settings = get_settings()

rag_pipeline: RAGPipeline | None = None
document_worker: DocumentWorker | None = None
worker_task: asyncio.Task | None = None


async def _load_rag_config() -> RAGConfig:
    """Load RAG config from database, falling back to defaults."""
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
                    "rag.similarity_threshold", "rag.temperature",
                    "rag.max_tokens",
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
    """Load model config (base_url, api_key, model) from system_configs."""
    from app.core.database import async_session
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    keys = [f"model.{prefix}.base_url", f"model.{prefix}.api_key", f"model.{prefix}.model"]
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
        # Load config
        rag_config = await _load_rag_config()

        # Load model configs
        embedding_cfg = await _load_model_config("embedding")
        llm_cfg = await _load_model_config("llm")

        # Create providers
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

        # Qdrant client
        qdrant = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        retriever = QdrantRetriever(qdrant, "campus_rag_chunks_v1")

        # Pipeline
        rag_pipeline = RAGPipeline(embedding, llm, retriever, rag_config)

        # Worker
        document_worker = DocumentWorker(embedding, retriever, rag_config)
        worker_task = asyncio.create_task(document_worker.run())

        logger.info("RAG pipeline and worker started")
    except Exception:
        logger.exception("Failed to start RAG pipeline")

    yield

    # Shutdown
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "smart-campus-rag"}
