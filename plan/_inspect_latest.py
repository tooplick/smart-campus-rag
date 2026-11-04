# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn
f='毕业设计论文_导师修改版_第五章扩充格式优化.docx'
d=Document(f)
print('paras', len(d.paragraphs), 'tables', len(d.tables))
for i,p in enumerate(d.paragraphs):
    t=p.text.strip()
    has_img = bool(p._p.findall('.//'+qn('a:blip')))
    if not t and not has_img: continue
    style = p.style.name
    pf = p.paragraph_format
    info = f'[{i}] <{style}> ind={pf.first_line_indent} ls={pf.line_spacing} align={p.alignment}'
    if has_img: info += ' [IMG]'
    print(info, t[:120])
