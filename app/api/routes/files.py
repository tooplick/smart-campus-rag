from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.models.document import Document
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/files", tags=["files"])


def _file_response(doc: Document, disposition: str) -> FileResponse | None:
    """定位原始文件;缺失返回 None(由端点转 404)。"""
    path = Path(doc.storage_path)
    if not path.is_file():
        return None
    return FileResponse(
        path,
        media_type=doc.mime_type,
        filename=doc.filename,
        content_disposition_type=disposition,
    )


@router.get("/{doc_id}")
async def download_file(doc_id: int, db: AsyncSession = Depends(get_db)):
    """公开下载原始文档文件（匿名可访问，供聊天参考来源下载）。"""
    doc = await db.get(Document, doc_id)
    if not doc:
        return error_response("文件不存在", status_code=404, code="FILE_NOT_FOUND")
    resp = _file_response(doc, "attachment")
    if resp is None:
        return error_response("文件不存在或已被删除", status_code=404, code="FILE_NOT_FOUND")
    return resp


@router.get("/{doc_id}/view")
async def view_file(doc_id: int, db: AsyncSession = Depends(get_db)):
    """公开内联预览原始文档（匿名可访问,图片/文本类直接展示文件本体）。"""
    doc = await db.get(Document, doc_id)
    if not doc:
        return error_response("文件不存在", status_code=404, code="FILE_NOT_FOUND")
    resp = _file_response(doc, "inline")
    if resp is None:
        return error_response("文件不存在或已被删除", status_code=404, code="FILE_NOT_FOUND")
    return resp
