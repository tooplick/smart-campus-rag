import logging
from fastapi import APIRouter
from app.utils.response import success_response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "smart-campus-rag"}


@router.get("/api/ready")
async def readiness_check():
    services = {}
    # PostgreSQL
    try:
        from app.core.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        services["postgresql"] = {"status": "ok"}
    except Exception:
        services["postgresql"] = {"status": "unavailable"}
    # Qdrant
    try:
        from app.core.config import get_settings
        from qdrant_client import AsyncQdrantClient
        settings = get_settings()
        client = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        await client.get_collections()
        services["qdrant"] = {"status": "ok"}
    except Exception:
        services["qdrant"] = {"status": "unavailable"}
    # LLM
    try:
        from app.main import rag_pipeline
        services["llm"] = {"status": "ok"} if rag_pipeline and rag_pipeline.llm else {"status": "unavailable"}
    except Exception:
        services["llm"] = {"status": "unavailable"}
    # Embedding
    try:
        from app.main import rag_pipeline
        services["embedding"] = {"status": "ok"} if rag_pipeline and rag_pipeline.embedding else {"status": "unavailable"}
    except Exception:
        services["embedding"] = {"status": "unavailable"}

    statuses = [s["status"] for s in services.values()]
    overall = "ok" if all(s == "ok" for s in statuses) else "degraded" if any(s == "unavailable" for s in statuses) else "ok"
    return success_response(data={"status": overall, "services": services}, message="ready")
