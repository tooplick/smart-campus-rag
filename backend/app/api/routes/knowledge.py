from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services.knowledge_service import KnowledgeService
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge"])


@router.get("")
async def list_knowledge_bases(db: AsyncSession = Depends(get_db)):
    service = KnowledgeService(db)
    items = await service.list_all()
    for item in items:
        item["created_at"] = item["created_at"].isoformat()
        item["updated_at"] = item["updated_at"].isoformat()
    return success_response(items)


@router.post("")
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    kb = await service.create(name=req.name, description=req.description, icon=req.icon)
    return success_response({
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "icon": kb.icon,
        "is_enabled": kb.is_enabled,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    })


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: int, db: AsyncSession = Depends(get_db)):
    service = KnowledgeService(db)
    kb = await service.get_by_id(kb_id)
    if not kb:
        return error_response("Knowledge base not found", status_code=404)
    return success_response({
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "icon": kb.icon,
        "is_enabled": kb.is_enabled,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    })


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: int,
    req: KnowledgeBaseUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    kb = await service.update(kb_id, **req.model_dump(exclude_unset=True))
    if not kb:
        return error_response("Knowledge base not found", status_code=404)
    return success_response({
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "icon": kb.icon,
        "is_enabled": kb.is_enabled,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    })


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = KnowledgeService(db)
    deleted = await service.delete(kb_id)
    if not deleted:
        return error_response("Knowledge base not found", status_code=404)
    return success_response(message="Knowledge base deleted")
