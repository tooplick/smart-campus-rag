# -*- coding: utf-8 -*-
"""删除封面后的重复分页符，修复页脚页码域，并按实际分页更新静态目录页码。"""

from pathlib import Path
import re
import shutil

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "毕业设计论文_导师修改版_摘要扩充.docx"
BACKUP = ROOT / "毕业设计论文_导师修改版_摘要扩充_备份_页码修复前.docx"
OUTPUT = ROOT / "毕业设计论文_唐星星_最终定稿.docx"


def fix_layout():
    """删除多余分页符，并把页脚的三个页码占位改成单个 PAGE 域。"""
    if not BACKUP.exists():
        shutil.copy2(SOURCE, BACKUP)
    shutil.copy2(SOURCE, OUTPUT)

    doc = Document(OUTPUT)
    removed = 0
    for paragraph in list(doc.paragraphs):
        xml = paragraph._p.xml
        if 'w:lastRenderedPageBreak' in xml and 'w:type="page"' in xml:
            paragraph._p.getparent().remove(paragraph._p)
            removed += 1
    if removed != 1:
        raise RuntimeError(f"预期删除 1 个重复分页段，实际删除 {removed} 个")

    footer = doc.sections[0].footer
    paragraph = footer.paragraphs[0]
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)

    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), " PAGE ")
    field.set(qn("w:dirty"), "true")
    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), "宋体")
    fonts.set(qn("w:hAnsi"), "宋体")
    fonts.set(qn("w:eastAsia"), "宋体")
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "21")
    r_pr.append(fonts)
    r_pr.append(size)
    run.append(r_pr)
    text = OxmlElement("w:t")
    text.text = "2"
    run.append(text)
    field.append(run)
    paragraph._p.append(field)

    doc.save(OUTPUT)
    print(f"已删除重复分页段 {removed} 个，页脚已改为单个 PAGE 域")


def read_heading_pages():
    """用 Word 重新分页，返回 {标题文本: 页码}。"""
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(OUTPUT), ReadOnly=True, AddToRecentFiles=False)
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


def update_toc_pages(page_map):
    doc = Document(OUTPUT)
    updated = 0
    for paragraph in doc.paragraphs:
        if not paragraph.style.name.lower().startswith("toc"):
            continue
        text = paragraph.text
        if "\t" not in text:
            raise RuntimeError(f"目录条目缺少制表符: {text!r}")
        heading, _ = text.rsplit("\t", 1)
        key = heading.replace("　", "").strip()
        if key not in page_map:
            raise RuntimeError(f"目录条目未找到对应标题: {key}")
        page = str(page_map[key])

        last = paragraph.runs[-1]
        if not last.text.strip().isdigit():
            raise RuntimeError(f"目录页码不在最后一个 run 中: {text!r}")
        last.text = page
        updated += 1
    doc.save(OUTPUT)
    print(f"目录条目已更新: {updated} 条")


def main():
    fix_layout()
    page_map, total = read_heading_pages()
    print(f"Word 实际页数: {total}，标题数: {len(page_map)}")
    update_toc_pages(page_map)

    check_map, total_after = read_heading_pages()
    if check_map != page_map:
        raise RuntimeError("更新目录后分页发生变化，请重新运行")
    print(f"复核通过: 页数 {total_after}，标题页码未变")
    print(f"完成: {OUTPUT}")


if __name__ == "__main__":
    main()
