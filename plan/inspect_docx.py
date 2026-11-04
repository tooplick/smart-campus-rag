# -*- coding: utf-8 -*-
"""临时排查脚本:导出 docx 段落索引/样式/文本,便于定点修改。"""
import sys
from docx import Document
from docx.oxml.ns import qn

DOC = r'd:\Github\smart-campus-rag\毕业设计论文_唐星星.docx'

doc = Document(DOC)
start_kw = sys.argv[1] if len(sys.argv) > 1 else '3.4 用例分析'
end_kw = sys.argv[2] if len(sys.argv) > 2 else '3.5 本章小结'

idx_start = idx_end = None
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if idx_start is None and t.startswith(start_kw):
        idx_start = i
    elif idx_start is not None and t.startswith(end_kw):
        idx_end = i
        break

print('总段落数:', len(doc.paragraphs), '| 表格数:', len(doc.tables), '| 图片数:', len(doc.inline_shapes))
print('定位:', idx_start, '->', idx_end)
print('-' * 70)
for i in range(max(0, (idx_start or 0) - 2), min(len(doc.paragraphs), (idx_end or 0) + 2)):
    p = doc.paragraphs[i]
    has_img = bool(p._p.findall('.//' + qn('a:blip')))
    outline = p._p.find(qn('w:pPr') + '/' + qn('w:outlineLvl'))
    mark = []
    if has_img:
        mark.append('IMG')
    if outline is not None:
        mark.append('outline=' + outline.get(qn('w:val')))
    txt = p.text.replace('\n', ' ')[:70]
    print(f'[{i:3d}] {p.style.name:14s} {" ".join(mark):12s} {txt}')
