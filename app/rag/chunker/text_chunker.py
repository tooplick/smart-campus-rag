from __future__ import annotations

from app.rag.models.blocks import ContentBlock, DocumentChunkData


def _estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ~ 2 chars for Chinese, 4 chars for English."""
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    other = len(text) - cjk
    return cjk + other // 4 + 1


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences by Chinese/English punctuation."""
    import re
    parts = re.split(r"(?<=[。！？.!?\n])", text)
    return [p for p in parts if p.strip()]


def chunk_blocks(
    blocks: list[ContentBlock],
    *,
    document_id: int,
    knowledge_base_id: int,
    target_size: int = 600,
    overlap: int = 80,
    min_size: int = 50,
) -> list[DocumentChunkData]:
    """Chunk content blocks into document chunks with overlap."""
    chunks: list[DocumentChunkData] = []
    carryover = ""

    for block in blocks:
        if block.block_type.value != "text" or not block.content:
            continue

        text = block.content
        if carryover:
            text = carryover + "\n\n" + text
            carryover = ""

        sentences = _split_sentences(text)
        current_parts: list[str] = []
        current_tokens = 0

        for sent in sentences:
            sent_tokens = _estimate_tokens(sent)
            if current_tokens + sent_tokens > target_size and current_tokens >= min_size:
                chunk_text = "".join(current_parts).strip()
                if chunk_text:
                    chunks.append(DocumentChunkData(
                        document_id=document_id,
                        knowledge_base_id=knowledge_base_id,
                        chunk_index=len(chunks),
                        content=chunk_text,
                        page_number=block.page_number,
                        section_title=block.section_title,
                        token_count=current_tokens,
                    ))
                    # Build carryover from end for overlap
                    overlap_parts: list[str] = []
                    overlap_tokens = 0
                    for p in reversed(current_parts):
                        t = _estimate_tokens(p)
                        if overlap_tokens + t > overlap:
                            break
                        overlap_parts.insert(0, p)
                        overlap_tokens += t
                    carryover = "".join(overlap_parts).strip() if overlap_parts else ""
                    current_parts = []
                    current_tokens = 0

            current_parts.append(sent)
            current_tokens += sent_tokens

        # Remaining text becomes carryover for next block
        remaining = "".join(current_parts).strip()
        if remaining:
            carryover = (carryover + "\n\n" + remaining).strip() if carryover else remaining

    # Flush final carryover
    if carryover and _estimate_tokens(carryover) >= min_size:
        chunks.append(DocumentChunkData(
            document_id=document_id,
            knowledge_base_id=knowledge_base_id,
            chunk_index=len(chunks),
            content=carryover,
            token_count=_estimate_tokens(carryover),
        ))

    return chunks
