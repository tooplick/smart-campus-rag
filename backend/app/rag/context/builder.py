from __future__ import annotations

from app.rag.models.blocks import RetrievalResult


def build_context(results: list[RetrievalResult], max_context_tokens: int = 4000) -> str:
    """Build retrieval context sorted by document/chunk order."""
    if not results:
        return ""

    # Sort by document_id then chunk_index for coherent reading
    sorted_results = sorted(results, key=lambda r: (r.document_id, r.chunk_index))

    parts: list[str] = []
    total_tokens = 0

    for i, r in enumerate(sorted_results, 1):
        page_str = f"第 {r.page_number} 页" if r.page_number else ""
        section_str = r.section_title or ""

        part = f"[来源 {i}]\n"
        if page_str:
            part += f"页码：{page_str}\n"
        if section_str:
            part += f"章节：{section_str}\n"
        part += f"\n内容：\n{r.content}\n"

        est_tokens = len(part) // 2
        if total_tokens + est_tokens > max_context_tokens:
            break
        parts.append(part)
        total_tokens += est_tokens

    return "\n---\n".join(parts)
