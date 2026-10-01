"""切块模板测试:general / section / qa / one。

section:按章节块独立切块、不跨章节、小章节保留;
qa:问答对成对成块;one:整篇一个切块(超长回退 general)。

无需 pytest，可直接运行::

    uv run python tests/test_chunk_templates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.chunker.text_chunker import chunk_blocks
from app.rag.models.blocks import ContentBlock, BlockType


def _block(content: str, title: str | None = None, index: int = 0) -> ContentBlock:
    return ContentBlock(block_type=BlockType.TEXT, content=content,
                        section_title=title, source_index=index)


def test_section_template_keeps_sections_intact():
    """section 模板:不跨章节,小章节保留为独立切片。"""

    def scenario() -> None:
        blocks = [
            _block("短章节内容。", title="第一节", index=0),
            _block("第二章的正文内容比较长。" * 20, title="第二节", index=1),
        ]
        chunks = chunk_blocks(blocks, document_id=1, knowledge_base_id=1,
                             target_size=200, overlap=20, min_size=50, template="section")
        assert chunks, "应产出切片"
        assert any("短章节内容" in c.content for c in chunks), "小章节应保留,不得因 min_size 被丢弃"
        for c in chunks:
            in_first = "短章节内容" in c.content
            in_second = "第二章" in c.content
            assert not (in_first and in_second), f"切片不得跨章节: {c.content[:40]!r}"

    scenario()


def test_qa_template_pairs():
    """qa 模板:问答对成对成块。"""

    def scenario() -> None:
        text = "Q: 猫是什么?\nA: 猫是动物。\nQ: 狗是什么?\nA: 狗是动物。"
        chunks = chunk_blocks([_block(text)], document_id=1, knowledge_base_id=1, template="qa")
        assert len(chunks) == 2, f"应产出 2 个问答块,实际 {len(chunks)}"
        assert "猫是什么" in chunks[0].content and "猫是动物" in chunks[0].content
        assert "狗是什么" in chunks[1].content and "狗是动物" in chunks[1].content

    scenario()


def test_one_template_single_chunk():
    """one 模板:整篇一个切块。"""

    def scenario() -> None:
        blocks = [
            _block("第一部分内容。", index=0),
            _block("第二部分内容。", index=1),
            _block("第三部分内容。", index=2),
        ]
        chunks = chunk_blocks(blocks, document_id=1, knowledge_base_id=1, template="one")
        assert len(chunks) == 1, f"应整篇一个切片,实际 {len(chunks)}"
        for marker in ("第一部分", "第二部分", "第三部分"):
            assert marker in chunks[0].content

    scenario()


def test_one_template_falls_back_when_oversized():
    """one 模板:超出嵌入安全上限时回退 general,不产出巨型切片。"""

    def scenario() -> None:
        blocks = [_block("长" * 20000, index=0)]
        chunks = chunk_blocks(blocks, document_id=1, knowledge_base_id=1,
                              target_size=600, min_size=50, template="one")
        assert len(chunks) > 1, "超长文档应回退 general 切块"

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
