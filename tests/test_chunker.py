"""切块器分句规则测试。

句边界 = 句末标点之后,或换行后紧跟列表/编号标记;
其余单个换行是排版软换行(PDF 硬换行),不得在词中间截断句子。
单句超过 target_size 时硬切,防止巨型切片。

无需 pytest，可直接运行::

    uv run python tests/test_chunker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.chunker.text_chunker import _split_sentences, chunk_blocks
from app.rag.models.blocks import ContentBlock, BlockType


def test_soft_newline_does_not_split_sentence():
    """排版换行(非列表行)不作句边界:'句子级重\n叠分块' 必须保持在同一句内。"""

    def scenario() -> None:
        text = (
            "• RAG 核心：模块化 Provider 抽象（可插拔替换）；句子级重\n"
            "叠分块、相似度阈值 + Top-K 双阶段过滤、上下文来源标注"
        )
        parts = _split_sentences(text)
        assert len(parts) == 1, f"软换行不应产生句边界,实际 {parts!r}"
        assert "句子级重\n叠分块" in "".join(parts), f"换行处被拆开: {parts!r}"

    scenario()


def test_list_lines_still_split():
    """列表/编号行开头的换行仍是句边界。"""

    def scenario() -> None:
        text = "正文内容结束。\n• 条目一\n• 条目二\n1. 编号项"
        parts = _split_sentences(text)
        assert len(parts) == 4, f"列表行应各自成句,实际 {parts!r}"
        assert parts[0].strip() == "正文内容结束。"
        assert parts[3].strip() == "1. 编号项", f"编号行应整体成句,实际 {parts!r}"

    scenario()


def test_oversized_sentence_hard_splits():
    """无标点超长句按 target_size 硬切,不产出巨型切片。"""

    def scenario() -> None:
        target = 200
        text = "长" * 1000
        blocks = [ContentBlock(block_type=BlockType.TEXT, content=text, source_index=0)]
        chunks = chunk_blocks(
            blocks, document_id=1, knowledge_base_id=1,
            target_size=target, overlap=20, min_size=10,
        )
        assert chunks, "超长句应产出切片"
        for c in chunks:
            assert len(c.content) <= target + 20, f"切片过长: {len(c.content)}"

    scenario()


def test_final_chunk_keeps_page_and_section():
    """收尾切片(含 carryover 收尾/QA 配对/整篇)必须携带页码与章节,来源卡片不得丢页。"""

    def scenario() -> None:
        blocks = [
            ContentBlock(block_type=BlockType.TEXT, content="第一页正文。" * 30,
                         page_number=1, section_title="第一章", source_index=0),
            ContentBlock(block_type=BlockType.TEXT, content="第二页正文。" * 30,
                         page_number=2, section_title="第二章", source_index=1),
        ]
        chunks = chunk_blocks(blocks, document_id=1, knowledge_base_id=1,
                              target_size=120, overlap=20, min_size=20)
        assert chunks, "应产出切片"
        for c in chunks:
            assert c.page_number is not None, f"切片丢了页码: {c.content[:20]!r}"
            assert c.section_title is not None, f"切片丢了章节: {c.content[:20]!r}"

        qa_blocks = [ContentBlock(block_type=BlockType.TEXT,
                                  content="Q: 猫是什么?\nA: 猫是动物。", page_number=3, source_index=0)]
        qa_chunks = chunk_blocks(qa_blocks, document_id=1, knowledge_base_id=1, template="qa")
        assert qa_chunks and qa_chunks[0].page_number == 3, f"QA 块应带页码,实际 {qa_chunks}"

        one_chunks = chunk_blocks(blocks[:1], document_id=1, knowledge_base_id=1, template="one")
        assert one_chunks and one_chunks[0].page_number == 1, f"整篇块应带页码,实际 {one_chunks}"

    scenario()


def test_chunk_attribution_from_chunk_start():
    """切片的页码/章节归属取其内容起点,而非块尾。"""

    def scenario() -> None:
        blocks = [
            # 甲块 120 token(不触发切分),乙块 300 token → 首个切片跨块,起点在甲块
            ContentBlock(block_type=BlockType.TEXT, content="第一章的正文甲甲甲。" * 12,
                         page_number=1, section_title="第一章", source_index=0),
            ContentBlock(block_type=BlockType.TEXT, content="第二章的正文乙乙乙。" * 30,
                         page_number=2, section_title="第二章", source_index=1),
        ]
        chunks = chunk_blocks(blocks, document_id=1, knowledge_base_id=1,
                              target_size=200, overlap=10, min_size=20)
        first = chunks[0]
        assert "甲甲甲" in first.content, f"首块应以甲块开头: {first.content[:30]!r}"
        assert first.section_title == "第一章" and first.page_number == 1,             f"归属应取内容起点,实际 {first.section_title}/{first.page_number}"

    scenario()


def test_no_duplicate_across_block_boundary():
    """跨块累积必须清零状态:块尾小余量不得在下一块开头重复。"""

    def scenario() -> None:
        blocks = [
            ContentBlock(block_type=BlockType.TEXT, content="小甲块内容独特。",
                         page_number=1, section_title="甲", source_index=0),
            ContentBlock(block_type=BlockType.TEXT, content="乙块的句子很丰富。" * 30,
                         page_number=2, section_title="乙", source_index=1),
        ]
        chunks = chunk_blocks(blocks, document_id=1, knowledge_base_id=1,
                              target_size=200, overlap=10, min_size=20)
        joined = "".join(c.content for c in chunks)
        assert joined.count("小甲块内容独特") == 1, f"甲块内容被重复: {joined.count('小甲块内容独特')} 次"

    scenario()


def main() -> int:
    tests = [
        obj
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            failed += 1
            print(f"FAIL {test.__name__}: {type(e).__name__}: {e}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
