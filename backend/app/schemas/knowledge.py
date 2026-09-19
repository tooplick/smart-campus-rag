from pydantic import BaseModel
from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    is_enabled: bool | None = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    icon: str | None
    is_enabled: bool
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
