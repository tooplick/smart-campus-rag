from pydantic import BaseModel


class RagConfigUpdate(BaseModel):
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    candidate_top_k: int | None = None
    final_top_k: int | None = None
    similarity_threshold: float | None = None


class ModelConfigUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    enabled: bool | None = None
