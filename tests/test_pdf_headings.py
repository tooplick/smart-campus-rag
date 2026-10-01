"""PDF 标题检测测试:行级(跨 span)匹配 + 相对字号启发。

真实简历的标题行常被写入器拆成多个 span('掌握'|'技'|'能'),
检测必须按版面行聚合后匹配;标题字号可能不超过 13pt,需按相对正文字号识别。

无需 pytest，可直接运行::

    uv run python tests/test_pdf_headings.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf as fitz


def _make_pdf(path: Path, heading_size: float, body_size: float, *, split_heading: bool) -> None:
    """构造一页 PDF:标题行 + 若干正文行(含日期行防误报)。split_heading 时标题拆两个 span。"""
    doc = fitz.open()
    page = doc.new_page()
    y = 100.0
    if split_heading:
        # 同一基线、颜色微差 → 同一版面行强制拆成两个 span(复现真实简历的 span 拆分)
        page.insert_text((72, y), "掌握", fontname="china-s", fontsize=heading_size, color=(0, 0, 0))
        page.insert_text((72 + 2 * heading_size, y), "技能", fontname="china-s", fontsize=heading_size, color=(0.01, 0, 0))
    else:
        page.insert_text((72, y), "掌握技能", fontname="china-s", fontsize=heading_size)
    y += 24
    for text in ("熟悉 FastAPI 与 Qdrant 向量检索。", "2024-01 - 2027-01 某某学院", "具备良好的工程能力。"):
        page.insert_text((72, y), text, fontname="china-s", fontsize=body_size)
        y += 18
    doc.save(str(path))
    doc.close()


def test_multi_span_heading_detected():
    """跨 span 标题行(13.4pt/正文 10.4pt)必须识别为章节。"""

    def scenario() -> None:
        from app.rag.parser.pdf import PdfParser

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.pdf"
            _make_pdf(p, heading_size=13.4, body_size=10.4, split_heading=True)
            blocks = asyncio.run(PdfParser().parse(p))
            titles = {b.section_title for b in blocks}
            assert "掌握技能" in titles, f"多 span 标题应识别,实际 titles={titles}"

    scenario()


def test_relative_size_heading_detected():
    """标题字号不超过 13pt(11.5/正文 9.5)时按相对字号识别。"""

    def scenario() -> None:
        from app.rag.parser.pdf import PdfParser

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.pdf"
            _make_pdf(p, heading_size=11.5, body_size=9.5, split_heading=False)
            blocks = asyncio.run(PdfParser().parse(p))
            titles = {b.section_title for b in blocks}
            assert "掌握技能" in titles, f"相对字号标题应识别,实际 titles={titles}"

    scenario()


def test_body_lines_are_not_headings():
    """正文行与日期行不得误判为章节。"""

    def scenario() -> None:
        from app.rag.parser.pdf import PdfParser

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.pdf"
            _make_pdf(p, heading_size=13.4, body_size=10.4, split_heading=False)
            blocks = asyncio.run(PdfParser().parse(p))
            titles = {b.section_title for b in blocks}
            for bad in ("2024-01 - 2027-01 某某学院", "熟悉 FastAPI 与 Qdrant 向量检索。"):
                assert bad not in titles, f"正文不得成章节: {bad!r} in {titles}"

    scenario()


def test_heading_text_kept_in_content():
    """标题文本必须保留在切片正文里(只进 section_title 会丢检索词,如人名标题)。"""

    def scenario() -> None:
        from app.rag.parser.pdf import PdfParser

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.pdf"
            _make_pdf(p, heading_size=13.4, body_size=10.4, split_heading=False)
            blocks = asyncio.run(PdfParser().parse(p))
            joined = "".join(b.content or "" for b in blocks)
            assert "掌握技能" in joined, f"标题文本不得从正文丢失: {joined[:60]!r}"

    scenario()


def test_md_heading_text_kept_in_content():
    """Markdown 的 # 标题同样保留在正文(检索词不丢)。"""

    def scenario() -> None:
        import asyncio as _a

        from app.rag.parser.txt import TxtParser

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.md"
            p.write_text("# 奖学金申请\n\n每年九月开放申请。", encoding="utf-8")
            blocks = _a.run(TxtParser().parse(p))
            joined = "".join(b.content or "" for b in blocks)
            assert "奖学金申请" in joined, f"标题文本不得从正文丢失: {joined!r}"

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
