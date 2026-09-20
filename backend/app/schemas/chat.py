from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    knowledge_base_id: int | None = None
    message: str
    stream: bool = True
