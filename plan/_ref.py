# -*- coding: utf-8 -*-
import sys, io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
from docx import Document
d=Document('8-毕业设计（论文）吴羿泽 范文.docx')
paras=d.paragraphs
# print first 60 non-empty
n=0
for i,p in enumerate(paras):
    t=p.text.strip()
    if not t: continue
    print(f'[{i}] <{p.style.name}> {t[:180]}')
    n+=1
    if n>55: break
print('TOTAL paras', len(paras))
