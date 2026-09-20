from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.services.document_service import DocumentService
from app.utils.response import success_response, error_response, paginated_response

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents(
    knowledge_base_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    base_query = select(Document)
    count_query = select(func.count(Document.id))

    if knowledge_base_id:
        base_query = base_query.where(Document.knowledge_base_id == knowledge_base_id)
        count_query = count_query.where(Document.knowledge_base_id == knowledge_base_id)

    sort_column = getattr(Document, sort_by, Document.created_at)
    if sort_order == "desc":
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())

    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)
    result = await db.execute(base_query)
    docs = result.scalars().all()

    items = [
        {
            "id": doc.id,
            "knowledge_base_id": doc.knowledge_base_id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "page_count": doc.page_count,
            "image_count": doc.image_count,
            "chunk_count": doc.chunk_count,
            "status": doc.status,
            "progress": doc.progress,
            "error_message": doc.error_message,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }
        for doc in docs
    ]

    return paginated_response(items, page, page_size, total)


@router.post("")
async def upload_document(
    knowledge_base_id: int = Form(...),
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBase, knowledge_base_id)
    if not kb:
        return error_response("知识库不存在", status_code=404, code="KB_NOT_FOUND")

    service = DocumentService(db)
    try:
        doc = await service.upload(file, knowledge_base_id)
    except ValueError as e:
        return error_response(str(e), status_code=400, code="UPLOAD_ERROR")

    return success_response(
        data={"id": doc.id, "filename": doc.filename, "status": doc.status},
        message="文档上传成功",
        status_code=201,
    )


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        return error_response("文档不存在", status_code=404, code="DOC_NOT_FOUND")

    return success_response(data={
        "id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "page_count": doc.page_count,
        "image_count": doc.image_count,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "progress": doc.progress,
        "error_message": doc.error_message,
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    })


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        return error_response("文档不存在", status_code=404, code="DOC_NOT_FOUND")

    return success_response(data={
        "id": doc.id,
        "status": doc.status,
        "progress": doc.progress,
        "error_message": doc.error_message,
    })


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    doc = await service.get_by_id(doc_id)
    if not doc:
        return error_response("文档不存在", status_code=404, code="DOC_NOT_FOUND")

    if doc.status == "processing":
        return error_response("文档正在处理中，请先取消", status_code=409, code="DOC_PROCESSING")

    await service.delete(doc_id)
    return success_response(message="文档已删除")


@router.post("/{doc_id}/reprocess")
async def reprocess_document(
    doc_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    doc = await service.get_by_id(doc_id)
    if not doc:
        return error_response("文档不存在", status_code=404, code="DOC_NOT_FOUND")

    if doc.status == "processing":
        return error_response("文档正在处理中，请先取消后再重新处理", status_code=409, code="DOC_PROCESSING")

    await service.update_status(doc_id, "pending", progress=0)
    return success_response(message="文档已加入重新处理队列")


@router.post("/{doc_id}/cancel")
async def cancel_document(
    doc_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    doc = await service.get_by_id(doc_id)
    if not doc:
        return error_response("文档不存在", status_code=404, code="DOC_NOT_FOUND")

    if doc.status != "processing":
        return error_response("只有处理中的文档可以取消", status_code=409, code="DOC_NOT_PROCESSING")

    await service.update_status(doc_id, "pending", progress=0)
    doc.locked_at = None
    doc.locked_by = None
    await db.commit()
    return success_response(message="文档处理已取消")
