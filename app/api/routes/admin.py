import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.qa_record import QaRecord
from app.models.qa_source import QaSource
from app.models.system_config import SystemConfig
from app.schemas.admin import RagConfigUpdate, ModelConfigUpdate
from app.utils.response import success_response, error_response, paginated_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def get_dashboard(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    kb_count = (await db.execute(select(func.count(KnowledgeBase.id)))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    chunk_count = (await db.execute(select(func.count(DocumentChunk.id)))).scalar() or 0
    qa_count = (await db.execute(select(func.count(QaRecord.id)))).scalar() or 0

    status_query = select(Document.status, func.count(Document.id)).group_by(Document.status)
    status_result = await db.execute(status_query)
    document_status = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for row in status_result.all():
        if row[0] in document_status:
            document_status[row[0]] = row[1]

    kb_dist_query = (
        select(KnowledgeBase.id, KnowledgeBase.name, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
        .group_by(KnowledgeBase.id, KnowledgeBase.name)
    )
    kb_dist_result = await db.execute(kb_dist_query)
    knowledge_base_distribution = [
        {"id": row[0], "name": row[1], "document_count": row[2]}
        for row in kb_dist_result.all()
    ]

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    qa_trend_query = (
        select(
            func.date(QaRecord.created_at).label("date"),
            func.count(QaRecord.id).label("count"),
        )
        .where(QaRecord.created_at >= seven_days_ago)
        .group_by(func.date(QaRecord.created_at))
        .order_by(func.date(QaRecord.created_at))
    )
    qa_trend_result = await db.execute(qa_trend_query)
    qa_trend = [{"date": str(row[0]), "count": row[1]} for row in qa_trend_result.all()]

    return success_response(data={
        "statistics": {
            "knowledge_base_count": kb_count,
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "qa_count": qa_count,
        },
        "qa_trend": qa_trend,
        "document_status": document_status,
        "knowledge_base_distribution": knowledge_base_distribution,
    })


@router.get("/rag-config")
async def get_rag_config(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    defaults = {
        "chunk_size": 600, "chunk_overlap": 80,
        "candidate_top_k": 8, "final_top_k": 5,
        "similarity_threshold": 0.60, "temperature": 0.2, "max_tokens": 2048,
    }
    stmt = select(SystemConfig).where(
        SystemConfig.config_key.in_([
            "rag.chunk_size", "rag.chunk_overlap", "rag.candidate_top_k",
            "rag.final_top_k", "rag.similarity_threshold", "rag.temperature", "rag.max_tokens",
        ])
    )
    result = await db.execute(stmt)
    for row in result.scalars().all():
        key = row.config_key.replace("rag.", "")
        if key in defaults:
            if row.value_type == "int":
                defaults[key] = int(row.config_value)
            elif row.value_type == "float":
                defaults[key] = float(row.config_value)
    return success_response(data=defaults)


@router.put("/rag-config")
async def update_rag_config(
    req: RagConfigUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if req.chunk_size is not None and req.chunk_size <= 0:
        return error_response("chunk_size 必须大于0", status_code=422, code="INVALID_CHUNK_SIZE")
    if req.chunk_overlap is not None and req.chunk_overlap < 0:
        return error_response("chunk_overlap 不能为负数", status_code=422, code="INVALID_CHUNK_OVERLAP")
    if req.chunk_size is not None and req.chunk_overlap is not None and req.chunk_overlap >= req.chunk_size:
        return error_response("chunk_overlap 必须小于 chunk_size", status_code=422, code="INVALID_OVERLAP")
    if req.candidate_top_k is not None and req.final_top_k is not None:
        if req.candidate_top_k < req.final_top_k:
            return error_response("candidate_top_k >= final_top_k", status_code=422, code="INVALID_TOP_K")
    if req.final_top_k is not None and req.final_top_k <= 0:
        return error_response("final_top_k 必须大于0", status_code=422, code="INVALID_FINAL_TOP_K")
    if req.similarity_threshold is not None and not (0 <= req.similarity_threshold <= 1):
        return error_response("similarity_threshold 必须在 0~1 之间", status_code=422, code="INVALID_THRESHOLD")

    for key, value in req.model_dump(exclude_unset=True).items():
        config_key = f"rag.{key}"
        value_type = "float" if isinstance(value, float) else "int"
        existing = (await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == config_key)
        )).scalar_one_or_none()
        if existing:
            existing.config_value = str(value)
            existing.value_type = value_type
        else:
            db.add(SystemConfig(config_key=config_key, config_value=str(value), value_type=value_type))
    await db.commit()
    return await get_rag_config(admin=admin, db=db)


@router.get("/models")
async def list_models(admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = {}
    for prefix in ["llm", "embedding", "vision"]:
        stmt = select(SystemConfig).where(SystemConfig.config_key.in_([
            f"model.{prefix}.base_url", f"model.{prefix}.api_key",
            f"model.{prefix}.model", f"model.{prefix}.enabled",
        ]))
        rows = (await db.execute(stmt)).scalars().all()
        config = {}
        api_key_configured = False
        for row in rows:
            short_key = row.config_key.split(".")[-1]
            if short_key == "api_key":
                api_key_configured = bool(row.config_value)
            else:
                config[short_key] = row.config_value
        result[prefix] = {
            "base_url": config.get("base_url", ""),
            "model": config.get("model", ""),
            "enabled": config.get("enabled", "true") == "true",
            "api_key_configured": api_key_configured,
        }
    return success_response(data=result)


@router.get("/models/{model_type}")
async def get_model(model_type: str, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    if model_type not in ("llm", "embedding", "vision"):
        return error_response("无效的模型类型", status_code=400, code="INVALID_MODEL_TYPE")
    stmt = select(SystemConfig).where(SystemConfig.config_key.in_([
        f"model.{model_type}.base_url", f"model.{model_type}.api_key",
        f"model.{model_type}.model", f"model.{model_type}.enabled",
    ]))
    rows = (await db.execute(stmt)).scalars().all()
    config = {}
    api_key_configured = False
    for row in rows:
        short_key = row.config_key.split(".")[-1]
        if short_key == "api_key":
            api_key_configured = bool(row.config_value)
        else:
            config[short_key] = row.config_value
    return success_response(data={
        "type": model_type, "base_url": config.get("base_url", ""),
        "model": config.get("model", ""), "enabled": config.get("enabled", "true") == "true",
        "api_key_configured": api_key_configured,
    })


@router.put("/models/{model_type}")
async def update_model(model_type: str, req: ModelConfigUpdate, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    if model_type not in ("llm", "embedding", "vision"):
        return error_response("无效的模型类型", status_code=400, code="INVALID_MODEL_TYPE")
    update_fields = {}
    if req.base_url is not None:
        update_fields[f"model.{model_type}.base_url"] = (req.base_url, "string")
    if req.api_key is not None and req.api_key.strip():
        update_fields[f"model.{model_type}.api_key"] = (req.api_key, "secret")
    if req.model is not None:
        update_fields[f"model.{model_type}.model"] = (req.model, "string")
    if req.enabled is not None:
        update_fields[f"model.{model_type}.enabled"] = (str(req.enabled).lower(), "string")
    for config_key, (value, vtype) in update_fields.items():
        existing = (await db.execute(select(SystemConfig).where(SystemConfig.config_key == config_key))).scalar_one_or_none()
        if existing:
            existing.config_value = value
            if vtype == "secret":
                existing.is_secret = True
        else:
            db.add(SystemConfig(config_key=config_key, config_value=value, is_secret=(vtype == "secret")))
    await db.commit()
    return await get_model(model_type=model_type, admin=admin, db=db)


@router.post("/models/{model_type}/test")
async def test_model(model_type: str, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    if model_type not in ("llm", "embedding", "vision"):
        return error_response("无效的模型类型", status_code=400, code="INVALID_MODEL_TYPE")
    stmt = select(SystemConfig).where(SystemConfig.config_key.in_([
        f"model.{model_type}.base_url", f"model.{model_type}.api_key", f"model.{model_type}.model",
    ]))
    rows = (await db.execute(stmt)).scalars().all()
    config = {row.config_key.split(".")[-1]: row.config_value for row in rows}
    base_url = config.get("base_url", "")
    api_key = config.get("api_key", "")
    model_name = config.get("model", "")
    if not base_url or not api_key or not model_name:
        return error_response("模型配置不完整", status_code=400, code="INCOMPLETE_MODEL_CONFIG")
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            if model_type == "embedding":
                resp = await client.post(f"{base_url}/embeddings",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"input": "test", "model": model_name})
                resp.raise_for_status()
                data = resp.json()
                latency = int((time.monotonic() - start) * 1000)
                dimension = len(data.get("data", [{}])[0].get("embedding", []))
                return success_response(data={"status": "ok", "model": model_name, "latency_ms": latency, "dimension": dimension}, message="连接成功")
            else:
                resp = await client.post(f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5})
                resp.raise_for_status()
                latency = int((time.monotonic() - start) * 1000)
                return success_response(data={"status": "ok", "model": model_name, "latency_ms": latency, "dimension": None}, message="连接成功")
    except Exception as e:
        logger.exception(f"Model test failed for {model_type}")
        return success_response(data={"status": "error", "model": model_name, "latency_ms": 0, "dimension": None}, message=f"连接失败: {str(e)[:100]}")


@router.get("/qa-logs")
async def list_qa_logs(page: int = 1, page_size: int = 20, sort_by: str = "created_at", sort_order: str = "desc", admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    total = (await db.execute(select(func.count(QaRecord.id)))).scalar() or 0
    sort_column = getattr(QaRecord, sort_by, QaRecord.created_at)
    stmt = select(QaRecord).order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(stmt)).scalars().all()
    items = [{
        "id": r.id, "conversation_id": r.conversation_id, "question": r.question,
        "answer": r.answer[:200] if r.answer else "", "knowledge_base_id": r.knowledge_base_id,
        "model_name": r.model_name, "status": r.status, "latency_ms": r.latency_ms,
        "total_tokens": r.total_tokens, "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records]
    return paginated_response(items, page, page_size, total)


@router.get("/qa-logs/{qa_id}")
async def get_qa_log_detail(qa_id: int, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    record = await db.get(QaRecord, qa_id)
    if not record:
        return error_response("QA 记录不存在", status_code=404, code="QA_NOT_FOUND")
    stmt = (
        select(QaSource, DocumentChunk, Document)
        .outerjoin(DocumentChunk, DocumentChunk.id == QaSource.chunk_id)
        .outerjoin(Document, Document.id == DocumentChunk.document_id)
        .where(QaSource.qa_record_id == qa_id)
        .order_by(QaSource.source_order)
    )
    rows = (await db.execute(stmt)).all()
    sources_data = []
    for source, chunk, doc in rows:
        sources_data.append({
            "chunk_id": source.chunk_id,
            "document_id": chunk.document_id if chunk else None,
            "filename": doc.filename if doc else None,
            "page_number": chunk.page_number if chunk else None,
            "section_title": chunk.section_title if chunk else None,
            "content": chunk.content[:200] if chunk and chunk.content else None,
            "similarity_score": round(source.similarity_score, 4),
            "source_order": source.source_order,
        })
    return success_response(data={
        "id": record.id, "conversation_id": record.conversation_id, "turn_index": record.turn_index,
        "question": record.question, "answer": record.answer,
        "knowledge_base_id": record.knowledge_base_id, "model_name": record.model_name,
        "status": record.status, "error_message": record.error_message,
        "rag": {"candidate_top_k": record.candidate_top_k, "final_top_k": record.final_top_k, "similarity_threshold": record.similarity_threshold},
        "retrieval": {"count": record.retrieval_count, "latency_ms": record.retrieval_latency_ms},
        "llm": {"latency_ms": record.llm_latency_ms},
        "latency": {"total_ms": record.latency_ms},
        "tokens": {"prompt": record.prompt_tokens, "completion": record.completion_tokens, "total": record.total_tokens},
        "sources": sources_data,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    })
