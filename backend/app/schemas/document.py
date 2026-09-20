from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    knowledge_base_id: int
    filename: str
    file_type: str
    mime_type: str
    file_size: int
    page_count: int
    image_count: int
    chunk_count: int
    status: str
    progress: int
    error_message: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    status: str


class DocumentStatusResponse(BaseModel):
    id: int
    status: str
    progress: int
    error_message: str | None
