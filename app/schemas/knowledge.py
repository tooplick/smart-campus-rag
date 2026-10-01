from pydantic import BaseModel
from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None
    chunk_template: str | None = None  # general/section/qa/one,默认 general


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    is_enabled: bool | None = None
    chunk_template: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    icon: str | None
    is_enabled: bool
    chunk_template: str = "general"
    document_count: int = 0
    chunk_count: int = 0
    created_at: str
    updated_at: str | None = None

    class Config:
        from_attributes = True
