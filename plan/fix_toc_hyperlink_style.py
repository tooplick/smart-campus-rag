# -*- coding: utf-8 -*-
"""移除目录文字继承的 Word Hyperlink 字符样式，强制恢复黑色无下划线。"""
from pathlib import Path
from docx import Document
from docx.shared import RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / '毕业设计论文_导师修改版_目录黑色.docx'
temp = ROOT / '毕业设计论文_导师修改版_目录黑色_修复中.docx'

doc = Document(source)
active = False
fixed_runs = 0
for para in doc.paragraphs:
    text = para.text.strip()
    if text == '目  录':
        active = True
        continue
    if active and text == '第1章 绪论':
        break
    if not active or not text:
        continue
    for run in para.runs:
        rpr = run._r.get_or_add_rPr()
        rstyle = rpr.find(qn('w:rStyle'))
        if rstyle is not None:
            rpr.remove(rstyle)
        run.font.color.rgb = RGBColor(0, 0, 0)
        run.font.underline = False
        fixed_runs += 1

doc.save(temp)
temp.replace(source)
print(f'目录字符样式已清理: {fixed_runs} 个文字片段')
print(f'已更新: {source}')
