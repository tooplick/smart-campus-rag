from __future__ import annotations

import re

from app.rag.models.blocks import ContentBlock, DocumentChunkData

# one 模板的嵌入安全上限:超出回退 general,防巨型切片超出嵌入模型输入
_ONE_MAX_TOKENS = 8000

# 问答对标记:Q/问/问题 开头开新对,A/答/回答 归入当前对
_QA_START = re.compile(r"^[ \t]*(?:[Qq]|问|问题)[:：]")
_QA_ANS = re.compile(r"^[ \t]*(?:[Aa]|答|回答)[:：]")


def _estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ~ 2 chars for Chinese, 4 chars for English."""
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    other = len(text) - cjk
    return cjk + other // 4 + 1


_SENT_SPLIT = re.compile(
    r"(?<=[。！？!?])"  # 中英文句末标点
    r"|(?<=[.])(?<![0-9][.])"  # 英文句点(排除 "1." 等编号点)
    r"|(?=\n\s*[•\-·*#])"  # 列表符号行前
    r"|(?=\n\s*[（(]?[一二三四五六七八九十]+[、.）)])"  # 中文编号行前
    r"|(?=\n\s*\d+[.、)])"  # 数字编号行前
)


def _split_sentences(text: str) -> list[str]:
    """按句末标点/列表行分句。单个换行是排版软换行(PDF 硬换行),不作句边界。"""
    parts = _SENT_SPLIT.split(text)
    return [p for p in parts if p.strip()]


def _split_oversized(sent: str, target_size: int) -> list[str]:
    """单句超过 target_size 时按字符硬切,防止无标点长句产出巨型切片。"""
    if _estimate_tokens(sent) <= target_size:
        return [sent]
    return [sent[i:i + target_size] for i in range(0, len(sent), target_size)]


def _make_chunk(
    content: str,
    *,
    document_id: int,
    knowledge_base_id: int,
    page_number: int | None = None,
    section_title: str | None = None,
) -> DocumentChunkData:
    return DocumentChunkData(
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        chunk_index=0,  # 由调用方统一重排
        content=content,
        page_number=page_number,
        section_title=section_title,
        token_count=_estimate_tokens(content),
    )


def _chunk_general(
    blocks: list[ContentBlock],
    *,
    document_id: int,
    knowledge_base_id: int,
    target_size: int,
    overlap: int,
    min_size: int,
    cross_block: bool,
) -> list[DocumentChunkData]:
    """句级流式切块。cross_block=True 跨块带重叠(general),False 按章节独立(section)。

    句子按来源标注 (文本, 页码, 章节);切片的页码/章节归属取其**内容起点**
    (而非切分点所在块),保证引用卡片的章节指向切片开头所在章节。
    """
    chunks: list[DocumentChunkData] = []
    # carryover:跨块重叠前缀,带来源归属 (句, 页, 章)
    carryover: list[tuple[str, int | None, str | None]] = []

    for block in blocks:
        if block.block_type.value not in ("text", "table") or not block.content:
            continue

        if cross_block and carryover:
            base = carryover
        else:
            base = []
        carryover = []

        body_sents = [p for s in _split_sentences(block.content) for p in _split_oversized(s, target_size)]
        sentences = base + [(t, block.page_number, block.section_title) for t in body_sents]

        current: list[tuple[str, int | None, str | None]] = []
        current_tokens = 0

        for sent, sent_page, sent_section in sentences:
            sent_tokens = _estimate_tokens(sent)
            if current_tokens + sent_tokens > target_size and current_tokens >= min_size:
                chunk_text = "".join(t for t, _, _ in current).strip()
                if chunk_text:
                    chunks.append(_make_chunk(
                        chunk_text,
                        document_id=document_id,
                        knowledge_base_id=knowledge_base_id,
                        page_number=current[0][1],
                        section_title=current[0][2],
                    ))
                    # 从块尾取重叠前缀(带来源归属)
                    overlap_parts: list[tuple[str, int | None, str | None]] = []
                    overlap_tokens = 0
                    for item in reversed(current):
                        tok = _estimate_tokens(item[0])
                        if overlap_tokens + tok > overlap:
                            break
                        overlap_parts.insert(0, item)
                        overlap_tokens += tok
                    carryover = overlap_parts
                    current = []
                    current_tokens = 0

            current.append((sent, sent_page, sent_section))
            current_tokens += sent_tokens

        if cross_block:
            # 余量连同重叠一起带入下一块(内容连续,归属随句保留)
            if current:
                carryover = carryover + current
        else:
            # 章节模式:余量立即成片(min_size=0 保证小章节保留),不带入下一块
            remaining = "".join(t for t, _, _ in current).strip()
            if remaining and (min_size == 0 or _estimate_tokens(remaining) >= min_size):
                chunks.append(_make_chunk(
                    remaining,
                    document_id=document_id,
                    knowledge_base_id=knowledge_base_id,
                    page_number=current[0][1],
                    section_title=current[0][2],
                ))
            carryover = []

    if cross_block and carryover:
        text = "".join(t for t, _, _ in carryover).strip()
        if text and _estimate_tokens(text) >= min_size:
            chunks.append(_make_chunk(
                text,
                document_id=document_id,
                knowledge_base_id=knowledge_base_id,
                page_number=carryover[0][1],
                section_title=carryover[0][2],
            ))

    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def _chunk_qa(
    blocks: list[ContentBlock],
    *,
    document_id: int,
    knowledge_base_id: int,
) -> list[DocumentChunkData]:
    """问答对模板:Q 行开新对,A 行与续行归入当前对;无问答标记回退 general。"""
    has_marker = any(_QA_START.search(b.content or "") for b in blocks)
    if not has_marker:
        return _chunk_general(
            blocks, document_id=document_id, knowledge_base_id=knowledge_base_id,
            target_size=600, overlap=80, min_size=50, cross_block=True,
        )

    chunks: list[DocumentChunkData] = []
    cur_lines: list[str] = []
    cur_title: str | None = None
    cur_page: int | None = None

    def flush() -> None:
        nonlocal cur_lines
        content = "".join(cur_lines).strip()
        if content:
            chunks.append(_make_chunk(
                content,
                document_id=document_id,
                knowledge_base_id=knowledge_base_id,
                page_number=cur_page,
                section_title=cur_title,
            ))
        cur_lines = []

    for block in blocks:
        if block.block_type.value not in ("text", "table") or not block.content:
            continue
        for line in block.content.splitlines(keepends=True):
            if _QA_START.match(line):
                flush()
                cur_title = block.section_title
                cur_page = block.page_number
            cur_lines.append(line)
    flush()

    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def _chunk_one(
    blocks: list[ContentBlock],
    *,
    document_id: int,
    knowledge_base_id: int,
    target_size: int,
    overlap: int,
    min_size: int,
) -> list[DocumentChunkData]:
    """整篇模板:全部内容一个切片;超出嵌入安全上限回退 general。"""
    full = "\n\n".join(
        b.content.strip()
        for b in blocks
        if b.block_type.value in ("text", "table") and b.content and b.content.strip()
    )
    if not full:
        return []
    if _estimate_tokens(full) > _ONE_MAX_TOKENS:
        return _chunk_general(
            blocks, document_id=document_id, knowledge_base_id=knowledge_base_id,
            target_size=target_size, overlap=overlap, min_size=min_size, cross_block=True,
        )
    first = next((b for b in blocks if b.content), None)
    return [_make_chunk(
        full,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        page_number=first.page_number if first else None,
    )]


def chunk_blocks(
    blocks: list[ContentBlock],
    *,
    document_id: int,
    knowledge_base_id: int,
    target_size: int = 600,
    overlap: int = 80,
    min_size: int = 50,
    template: str = "general",
) -> list[DocumentChunkData]:
    """按模板切块:general(句级流式)/section(章节独立)/qa(问答对)/one(整篇)。"""
    if template == "qa":
        return _chunk_qa(blocks, document_id=document_id, knowledge_base_id=knowledge_base_id)
    if template == "one":
        return _chunk_one(
            blocks, document_id=document_id, knowledge_base_id=knowledge_base_id,
            target_size=target_size, overlap=overlap, min_size=min_size,
        )
    if template == "section":
        return _chunk_general(
            blocks, document_id=document_id, knowledge_base_id=knowledge_base_id,
            target_size=target_size, overlap=overlap, min_size=0, cross_block=False,
        )
    return _chunk_general(
        blocks, document_id=document_id, knowledge_base_id=knowledge_base_id,
        target_size=target_size, overlap=overlap, min_size=min_size, cross_block=True,
    )
