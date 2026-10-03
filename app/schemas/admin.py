from pydantic import BaseModel


class RagConfigUpdate(BaseModel):
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    candidate_top_k: int | None = None
    final_top_k: int | None = None
    similarity_threshold: float | None = None
    vector_weight: float | None = None
    auto_keywords: int | None = None
    auto_questions: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    # 可选运行参数(与 RAG_DEFAULTS 对齐,设置页「可选参数」区)
    embedding_batch_size: int | None = None
    embedding_max_retries: int | None = None
    llm_max_retries: int | None = None
    request_timeout: float | None = None


class ModelTestRequest(BaseModel):
    name: str | None = None  # 指定配置名;缺省测当前启用配置
