import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Request, APIRouter, Depends
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
from app.core.app_config import MODEL_TYPES, AppConfigError, AppConfigStore, get_app_config
from app.rag.config import RAGConfig
from app.schemas.admin import RagConfigUpdate, ModelConfigUpdate, ModelTestRequest
from app.services.model_swap import OPTIONAL_TYPES, apply_model_change
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
    store: AppConfigStore = Depends(get_app_config),
):
    try:
        return success_response(data=store.get_rag())
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.put("/rag-config")
async def update_rag_config(
    req: RagConfigUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
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
    if req.vector_weight is not None and not (0 <= req.vector_weight <= 1):
        return error_response("vector_weight 必须在 0~1 之间", status_code=422, code="INVALID_VECTOR_WEIGHT")
    if req.auto_keywords is not None and not (0 <= req.auto_keywords <= 20):
        return error_response("auto_keywords 必须在 0~20 之间", status_code=422, code="INVALID_AUTO_KEYWORDS")
    if req.auto_questions is not None and not (0 <= req.auto_questions <= 10):
        return error_response("auto_questions 必须在 0~10 之间", status_code=422, code="INVALID_AUTO_QUESTIONS")
    if req.temperature is not None and not (0 <= req.temperature <= 2):
        return error_response("temperature 必须在 0~2 之间", status_code=422, code="INVALID_TEMPERATURE")
    if req.max_tokens is not None and not (64 <= req.max_tokens <= 8192):
        return error_response("max_tokens 必须在 64~8192 之间", status_code=422, code="INVALID_MAX_TOKENS")

    # exclude_none:显式 null(如 {"chunk_size": null})不得绕过上面的范围校验污染运行中配置
    updates = req.model_dump(exclude_unset=True, exclude_none=True)

    try:
        saved = store.save_rag(updates)
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")

    # 落盘成功后再热更新:避免落盘失败时运行中配置已改、文件未改的分歧窗口
    live: RAGConfig | None = getattr(request.app.state, "rag_config", None)
    if live is not None:
        for key, value in updates.items():
            setattr(live, key, value)
    return success_response(data=saved)


def _model_view(store: AppConfigStore, model_type: str) -> dict:
    """旧端点响应形状:当前启用配置 + api_key_configured(与历史兼容)。

    停用时回退展示已存的 default 配置字段(旧界面仍能看到原配置),
    enabled=False 表明未启用;完全无配置时字段为空。
    """
    active = store.get_active_profile(model_type)
    view = active
    if view is None:
        default = store.list_profiles(model_type)["profiles"].get("default")
        if default:
            view = {k: str(default.get(k, "")) for k in ("base_url", "api_key", "model")}
    return {
        "type": model_type,
        "base_url": view["base_url"] if view else "",
        "model": view["model"] if view else "",
        "enabled": active is not None,
        "api_key_configured": bool(view and view["api_key"]),
    }


@router.get("/models")
async def list_models(admin: Admin = Depends(get_current_admin), store: AppConfigStore = Depends(get_app_config)):
    """兼容端点(已废弃,前端设置页上线后下线):返回各类型当前启用配置。"""
    try:
        return success_response(data={t: _model_view(store, t) for t in MODEL_TYPES})
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.get("/models/{model_type}")
async def get_model(model_type: str, admin: Admin = Depends(get_current_admin), store: AppConfigStore = Depends(get_app_config)):
    """兼容端点(已废弃)。"""
    if model_type not in MODEL_TYPES:
        return error_response("无效的模型类型", status_code=400, code="INVALID_MODEL_TYPE")
    try:
        return success_response(data=_model_view(store, model_type))
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.put("/models/{model_type}")
async def update_model(
    model_type: str,
    req: ModelConfigUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    """兼容端点(已废弃):写入该类型的启用配置(无配置时建 default),等价于写配置文件。"""
    if model_type not in MODEL_TYPES:
        return error_response("无效的模型类型", status_code=400, code="INVALID_MODEL_TYPE")
    if req.enabled is False and model_type not in OPTIONAL_TYPES:
        return error_response(f"{model_type} 不支持停用", status_code=422, code="CANNOT_DISABLE")
    try:
        active = store.get_active_profile(model_type)
        fields = {k: v for k, v in {
            "base_url": req.base_url, "api_key": req.api_key, "model": req.model,
        }.items() if v not in (None, "")}
        re_enable = req.enabled is not False
        if active is None:
            # 停用后再写入:复用既存 default(而非重复 add 触发「配置名已存在」),并按需重新启用
            if "default" in store.list_profiles(model_type)["profiles"]:
                if fields:
                    store.update_profile(model_type, "default", fields)
            else:
                store.add_profile(model_type, "default", {
                    "base_url": req.base_url or "", "api_key": req.api_key or "", "model": req.model or "",
                })
            store.set_active(model_type, "default" if re_enable else None)
        else:
            if fields:
                store.update_profile(model_type, active["name"], fields)
            if not re_enable:
                store.set_active(model_type, None)
        apply_model_change(request.app, model_type, store)
        return success_response(data=_model_view(store, model_type))
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.post("/models/{model_type}/test")
async def test_model(
    model_type: str,
    req: ModelTestRequest | None = None,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    """连通性测试:POST body 可选 {name} 测指定配置,缺省测启用配置。"""
    if model_type not in MODEL_TYPES:
        return error_response("无效的模型类型", status_code=400, code="INVALID_MODEL_TYPE")
    try:
        profile = store.get_profile(model_type, req.name) if req and req.name else store.get_active_profile(model_type)
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")
    if not profile or not profile["base_url"] or not profile["model"]:
        return error_response("模型配置不完整", status_code=400, code="INCOMPLETE_MODEL_CONFIG")
    base_url = profile["base_url"].rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    api_key = profile["api_key"]
    model_name = profile["model"]
    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=30) as client:
            if model_type == "rerank":
                resp = await client.post(f"{base_url}/rerank",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "query": "测试", "documents": ["测试文档一", "测试文档二"], "top_n": 2})
                resp.raise_for_status()
                latency = int((time.monotonic() - start) * 1000)
                return success_response(data={"status": "ok", "model": model_name, "latency_ms": latency, "dimension": None}, message="连接成功")
            elif model_type == "embedding":
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
