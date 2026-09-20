from pydantic import BaseModel


class ConversationCreate(BaseModel):
    knowledge_base_id: int | None = None
    title: str = "新对话"


class ConversationUpdate(BaseModel):
    title: str | None = None
