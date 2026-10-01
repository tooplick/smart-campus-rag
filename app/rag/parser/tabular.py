from __future__ import annotations

from app.rag.models.blocks import BlockType, ContentBlock


def rows_to_blocks(
    rows: list[list[str]],
    *,
    section_title: str | None = None,
    source_start: int = 0,
) -> list[ContentBlock]:
    """表格行 → 块:首行作表头注入其后每一行,行内容为「列名: 值」连接。

    行块自包含列语义(配合 section 模板即 RAGFlow Table 式行级切片)。
    """
    if not rows:
        return []
    header = [str(c) if c is not None else "" for c in rows[0]]
    out: list[ContentBlock] = []
    for row in rows[1:]:
        cells = [("" if c is None else str(c)) for c in row]
        if not any(cells):
            continue
        parts = []
        for i, value in enumerate(cells):
            if not value:
                continue
            name = header[i] if i < len(header) and header[i] else f"列{i + 1}"
            parts.append(f"{name}: {value}")
        if not parts:
            continue
        out.append(ContentBlock(
            block_type=BlockType.TABLE,
            content=" | ".join(parts),
            section_title=section_title,
            source_index=source_start + len(out),
        ))
    return out
