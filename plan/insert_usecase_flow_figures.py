# -*- coding: utf-8 -*-
"""在 3.4.1/3.4.2 用例描述后插入活动流程图（先插 PNG，再用 Word 替换为 SVG）。"""

from pathlib import Path
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_插入用例流程图前.docx"
IMAGES = ROOT / "chapters" / "images"

FIGURES = [
    (
        "该用例由管理员发起",
        IMAGES / "图3-2-管理员上传文档并入库流程.png",
        IMAGES / "图3-2-管理员上传文档并入库流程.svg",
        "图3-2 管理员上传文档并入库流程",
    ),
    (
        "该用例由匿名师生发起",
        IMAGES / "图3-3-匿名用户提问并获得带引用回答流程.png",
        IMAGES / "图3-3-匿名用户提问并获得带引用回答流程.svg",
        "图3-3 匿名用户提问并获得带引用回答流程",
    ),
]


def find_paragraph(doc, prefix):
    for paragraph in doc.paragraphs:
        if paragraph.text.strip().startswith(prefix):
            return paragraph
    raise ValueError(f"未找到段落: {prefix}")


def insert_paragraph_after(paragraph):
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    return Paragraph(new_p, paragraph._parent)


def add_figure(anchor, png_path, caption):
    image_p = insert_paragraph_after(anchor)
    image_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = image_p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = image_p.add_run()
    run.add_picture(str(png_path), width=Cm(14))

    caption_p = insert_paragraph_after(image_p)
    caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = caption_p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(18)
    run = caption_p.add_run(caption)
    run.font.name = "Times New Roman"
    run.font.size = Pt(10.5)
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), "宋体")
    r_fonts.set(qn("w:ascii"), "Times New Roman")
    r_fonts.set(qn("w:hAnsi"), "Times New Roman")
    return caption_p


def replace_png_with_svg():
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)

        def replace(index, svg):
            shape = doc.InlineShapes.Item(index)
            width, height = shape.Width, shape.Height
            target = shape.Range.Duplicate
            target.Collapse(1)
            new_shape = doc.InlineShapes.AddPicture(str(svg), False, True, target)
            new_shape.Width = width
            new_shape.Height = height
            shape.Delete()

        # 文档顺序：图3-1、图3-2、图3-3、图4-1……先替换后面的图3-3
        replace(3, FIGURES[1][2])
        replace(2, FIGURES[0][2])
        doc.Save()
        doc.Close(False)
    finally:
        word.Quit()


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    doc = Document(DOCX)
    for prefix, png, _, caption in FIGURES:
        anchor = find_paragraph(doc, prefix)
        add_figure(anchor, png, caption)
    doc.save(DOCX)
    replace_png_with_svg()
    print("已插入图3-2、图3-3并替换为 SVG")


if __name__ == "__main__":
    main()
