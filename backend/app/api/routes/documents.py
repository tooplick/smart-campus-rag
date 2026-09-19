from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.services.document_service import DocumentService
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents(
    knowledge_base_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    docs = await service.list_by_knowledge_base(knowledge_base_id)
    return success_response([{
        "id": d.id,
        "knowledge_base_id": d.knowledge_base_id,
        "filename": d.filename,
        "file_type": d.file_type,
        "mime_type": d.mime_type,
        "file_size": d.file_size,
        "page_count": d.page_count,
        "image_count": d.image_count,
        "chunk_count": d.chunk_count,
        "status": d.status,
        "progress": d.progress,
        "error_message": d.error_message,
        "processed_at": d.processed_at.isoformat() if d.processed_at else None,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    } for d in docs])


@router.post("/upload")
async def upload_document(
    knowledge_base_id: int = Form(...),
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    try:
        doc = await service.upload(file, knowledge_base_id)
    except ValueError as e:
        return error_response(str(e), status_code=400)

    return success_response({
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "message": "Document uploaded successfully. Processing will begin shortly.",
    })


@router.get("/{doc_id}")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    service = DocumentService(db)
    doc = await service.get_by_id(doc_id)
    if not doc:
        return error_response("Document not found", status_code=404)
    return success_response({
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
        "updated_at": doc.updated_at.isoformat(),
    })


@router.get("/{doc_id}/status")
async def get_document_status(doc_id: int, db: AsyncSession = Depends(get_db)):
    service = DocumentService(db)
    doc = await service.get_by_id(doc_id)
    if not doc:
        return error_response("Document not found", status_code=404)
    return success_response({
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
    deleted = await service.delete(doc_id)
    if not deleted:
        return error_response("Document not found", status_code=404)
    return success_response(message="Document deleted")


@router.post("/{doc_id}/reprocess")
async def reprocess_document(
    doc_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    doc = await service.get_by_id(doc_id)
    if not doc:
        return error_response("Document not found", status_code=404)
    await service.update_status(doc_id, "pending", progress=0)
    return success_response(message="Document queued for reprocessing")
