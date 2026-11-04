# -*- coding: utf-8 -*-
"""把预览 PDF 指定页渲染为 PNG,供肉眼核对排版。"""
import sys
import pymupdf

PDF = r'd:\Github\smart-campus-rag\plan\_preview.pdf'
doc = pymupdf.open(PDF)
print('总页数:', doc.page_count)

# 定位含 3.4 用例分析的页
target = []
for i, page in enumerate(doc):
    txt = page.get_text()
    if '3.4 用例分析' in txt or '系统用例图' in txt or '核心用例描述' in txt:
        target.append(i)

pages = [int(x) for x in sys.argv[1:]] or target
for i in pages:
    page = doc[i]
    pix = page.get_pixmap(dpi=140)
    out = rf'd:\Github\smart-campus-rag\plan\_page{i + 1}.png'
    pix.save(out)
    print(f'第 {i + 1} 页 → {out}')
