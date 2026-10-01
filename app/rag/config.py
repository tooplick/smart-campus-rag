from dataclasses import dataclass


@dataclass
class RAGConfig:
    chunk_size: int = 600
    chunk_overlap: int = 80
    candidate_top_k: int = 8
    final_top_k: int = 5
    similarity_threshold: float = 0.60
    vector_weight: float = 0.7  # 混合检索向量权重(0~1),其余归关键词路
    auto_keywords: int = 5  # 入库增强:每切片关键词数,0=关闭
    auto_questions: int = 2  # 入库增强:每切片候选问题数,0=关闭
    temperature: float = 0.2
    max_tokens: int = 2048
    embedding_batch_size: int = 32
    embedding_max_retries: int = 3
    llm_max_retries: int = 3
    request_timeout: float = 60.0

    def to_dict(self) -> dict:
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "candidate_top_k": self.candidate_top_k,
            "final_top_k": self.final_top_k,
            "similarity_threshold": self.similarity_threshold,
            "vector_weight": self.vector_weight,
            "auto_keywords": self.auto_keywords,
            "auto_questions": self.auto_questions,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
