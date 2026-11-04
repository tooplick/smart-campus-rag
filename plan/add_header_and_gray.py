# -*- coding: utf-8 -*-
"""补页眉，并把第5章的界面截图设为灰度显示。"""

from pathlib import Path
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_页眉与灰度前.docx"

HEADER_TEXT = "苏州高博职业学院毕业设计（论文）"


def add_header():
    doc = Document(DOCX)
    section = doc.sections[0]

    header = section.header
    header.is_linked_to_previous = False
    paragraph = header.paragraphs[0]
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)

    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = paragraph.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(12)

    run = paragraph.add_run(HEADER_TEXT)
    run.font.name = "Times New Roman"
    run.font.size = Pt(9)
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), "宋体")
    r_fonts.set(qn("w:ascii"), "Times New Roman")
    r_fonts.set(qn("w:hAnsi"), "Times New Roman")

    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    p_bdr.append(bottom)
    insert_at = len(p_pr)
    for index, child in enumerate(p_pr):
        if child.tag in (qn("w:spacing"), qn("w:ind"), qn("w:jc")):
            insert_at = index
            break
    p_pr.insert(insert_at, p_bdr)

    # 封面使用空白首页页眉
    section.first_page_header.is_linked_to_previous = False

    doc.save(DOCX)
    print("页眉已添加")


def grayscale_screenshots():
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)
        count = 0
        for index in range(6, 13):
            shape = doc.InlineShapes.Item(index)
            shape.PictureFormat.ColorType = 3  # wdPictureColorTypeGrayscale
            count += 1
        doc.Save()
        doc.Close(False)
        print(f"已设为灰度截图: {count} 张")
    finally:
        word.Quit()


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)
    add_header()
    grayscale_screenshots()


if __name__ == "__main__":
    main()
