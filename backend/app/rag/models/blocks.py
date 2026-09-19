from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    MIXED = "mixed"


@dataclass
class ContentBlock:
    block_type: BlockType
    content: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    source_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunkData:
    document_id: int
    knowledge_base_id: int
    chunk_index: int
    content: str
    content_type: str = "text"
    page_number: int | None = None
    section_title: str | None = None
    start_char: int | None = None
    end_char: int | None = None
    token_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunk_id: int
    document_id: int
    knowledge_base_id: int
    score: float
    content: str
    content_type: str
    page_number: int | None = None
    section_title: str | None = None
    chunk_index: int = 0


@dataclass
class Citation:
    chunk_id: int
    document_id: int
    filename: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    content: str = ""
    score: float = 0.0


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class RagAnswer:
    answer: str
    retrievals: list[RetrievalResult] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    model_name: str = ""
    usage: Usage | None = None
    latency_ms: int = 0
