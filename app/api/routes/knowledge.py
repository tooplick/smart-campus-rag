from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.utils.response import success_response, error_response, paginated_response

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge"])


async def _enrich_kb(db: AsyncSession, kb: KnowledgeBase) -> dict:
    doc_count_stmt = select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
    doc_count = (await db.execute(doc_count_stmt)).scalar() or 0

    chunk_sum_stmt = select(func.coalesce(func.sum(Document.chunk_count), 0)).where(
        Document.knowledge_base_id == kb.id
    )
    chunk_sum = (await db.execute(chunk_sum_stmt)).scalar() or 0

    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "icon": kb.icon,
        "is_enabled": kb.is_enabled,
        "document_count": doc_count,
        "chunk_count": chunk_sum,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
    }


@router.get("")
async def list_knowledge_bases(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    count_stmt = select(func.count(KnowledgeBase.id))
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    kbs = result.scalars().all()

    items = []
    for kb in kbs:
        items.append(await _enrich_kb(db, kb))

    return paginated_response(items, page, page_size, total)


@router.post("")
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(name=req.name, description=req.description, icon=req.icon)
    db.add(kb)
    await db.flush()
    await db.commit()

    return success_response(
        data=await _enrich_kb(db, kb),
        message="知识库创建成功",
        status_code=201,
    )


@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return error_response("知识库不存在", status_code=404, code="KB_NOT_FOUND")

    return success_response(data=await _enrich_kb(db, kb))


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: int,
    req: KnowledgeBaseUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return error_response("知识库不存在", status_code=404, code="KB_NOT_FOUND")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kb, key, value)

    await db.commit()
    return success_response(data=await _enrich_kb(db, kb))


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return error_response("知识库不存在", status_code=404, code="KB_NOT_FOUND")

    await db.delete(kb)
    await db.commit()
    return success_response(message="知识库已删除")
