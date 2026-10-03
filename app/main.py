import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, knowledge, documents, chat, conversations, admin, health, files, model_profiles
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


def _load_rag_config() -> RAGConfig:
    """从 app-config.yaml 装载 RAG 参数(缺项回退 RAGConfig 默认)。"""
    from app.core.app_config import get_app_config

    config = RAGConfig()
    try:
        for key, value in get_app_config().get_rag().items():
            setattr(config, key, value)
    except Exception:
        logger.warning("Failed to load RAG config from app-config.yaml, using defaults")
    return config


def _load_model_config(prefix: str) -> dict | None:
    """从 app-config.yaml 取启用配置;未启用返回 None。"""
    from app.core.app_config import get_app_config

    try:
        return get_app_config().get_active_profile(prefix)
    except Exception:
        logger.warning(f"Failed to load {prefix} model config from app-config.yaml")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_pipeline, document_worker, worker_task

    try:
        rag_config = _load_rag_config()
        embedding_cfg = _load_model_config("embedding")
        llm_cfg = _load_model_config("llm")
        if not embedding_cfg or not embedding_cfg["base_url"] or not embedding_cfg["model"]:
            raise RuntimeError("app-config.yaml 缺少可用的 embedding 启用配置")
        if not llm_cfg or not llm_cfg["base_url"] or not llm_cfg["model"]:
            raise RuntimeError("app-config.yaml 缺少可用的 llm 启用配置")

        embedding = OpenAICompatibleEmbedding(
            base_url=embedding_cfg["base_url"],
            api_key=embedding_cfg["api_key"],
            model=embedding_cfg["model"],
            batch_size=rag_config.embedding_batch_size,
            max_retries=rag_config.embedding_max_retries,
            timeout=rag_config.request_timeout,
        )
        llm = OpenAICompatibleLLM(
            base_url=llm_cfg["base_url"],
            api_key=llm_cfg["api_key"],
            model=llm_cfg["model"],
            max_retries=rag_config.llm_max_retries,
            timeout=rag_config.request_timeout,
        )

        qdrant = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        retriever = QdrantRetriever(qdrant, "campus_rag_chunks_v1")
        app.state.retriever = retriever  # 供文档删除等路由清理向量

        # 重排模型可选:启用且配置完整时接入(对齐 RAGFlow 两级排序)
        rerank_profile = _load_model_config("rerank")
        rerank_provider = None
        if rerank_profile and rerank_profile["base_url"] and rerank_profile["model"]:
            rerank_provider = OpenAICompatibleRerank(
                base_url=rerank_profile["base_url"],
                api_key=rerank_profile["api_key"],
                model=rerank_profile["model"],
            )

        app.state.rag_config = rag_config  # 与管线/worker 共享实例,rag-config 保存即热更新
        rag_pipeline = RAGPipeline(embedding, llm, retriever, rag_config, rerank=rerank_provider)

        vision_profile = _load_model_config("vision")
        vision_cfg = None
        if vision_profile and vision_profile["base_url"] and vision_profile["model"]:
            vision_cfg = {
                "base_url": vision_profile["base_url"],
                "api_key": vision_profile["api_key"],
                "model": vision_profile["model"],
            }
        document_worker = DocumentWorker(embedding, retriever, rag_config, llm=llm, vision_config=vision_cfg)
        worker_task = asyncio.create_task(document_worker.run())

        # 供热替换定位实例(model_swap 优先取 app.state,其次回退本模块全局)
        app.state.rag_pipeline = rag_pipeline
        app.state.document_worker = document_worker

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
app.include_router(model_profiles.router)
app.include_router(health.router)
app.include_router(files.router)
