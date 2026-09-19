from dataclasses import dataclass, field


@dataclass
class RAGConfig:
    chunk_size: int = 600
    chunk_overlap: int = 80
    candidate_top_k: int = 8
    final_top_k: int = 5
    similarity_threshold: float = 0.60
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
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
