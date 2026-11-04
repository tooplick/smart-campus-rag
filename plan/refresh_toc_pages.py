# -*- coding: utf-8 -*-
"""按 Word 实际分页刷新静态目录页码（不重建文档）。"""

from pathlib import Path
import re

from docx import Document
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"


def read_heading_pages():
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=True, AddToRecentFiles=False)
        doc.Repaginate()
        pages = {}
        for i in range(1, doc.Paragraphs.Count + 1):
            paragraph = doc.Paragraphs.Item(i)
            style = paragraph.Style.NameLocal
            match = re.search(r"(?:Heading|标题)\s*([123])(?:[123])?$", style)
            if not match:
                continue
            text = paragraph.Range.Text.replace("\r", "").replace("\x07", "").strip()
            if text:
                pages[text] = int(paragraph.Range.Information(3))
        total = int(doc.Content.Information(4))
        doc.Close(False)
        return pages, total
    finally:
        word.Quit()


def update_toc(page_map):
    doc = Document(DOCX)
    updated = 0
    for paragraph in doc.paragraphs:
        if not paragraph.style.name.lower().startswith("toc"):
            continue
        text = paragraph.text
        if "\t" not in text:
            continue
        heading, _ = text.rsplit("\t", 1)
        key = heading.replace("　", "").strip()
        if key not in page_map:
            raise RuntimeError(f"目录条目未找到标题: {key}")
        last = paragraph.runs[-1]
        if not last.text.strip().isdigit():
            raise RuntimeError(f"目录页码不在最后一个 run: {text!r}")
        last.text = str(page_map[key])
        updated += 1
    doc.save(DOCX)
    return updated


def main():
    page_map, total = read_heading_pages()
    updated = update_toc(page_map)
    check_map, total_after = read_heading_pages()
    bad = [(k, v, check_map.get(k)) for k, v in page_map.items() if check_map.get(k) != v]
    print(f"页数: {total_after}，目录条目: {updated}，页码不一致: {len(bad)}")
    for item in bad[:5]:
        print("  ", item)


if __name__ == "__main__":
    main()
