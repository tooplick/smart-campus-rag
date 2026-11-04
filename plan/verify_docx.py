# -*- coding: utf-8 -*-
import re
from docx import Document
from docx.oxml.ns import qn

p = r'c:\Users\id654\Desktop\毕业设计论文_唐星星.docx'
doc = Document(p)

texts = [para.text for para in doc.paragraphs]
full = '\n'.join(texts)

print('== 关键内容 ==')
print('封面校名:', any('苏州高博职业学院' in t for t in texts[:10]))
print('摘要在:', '中 文 摘 要' in full, '| Abstract 在:', re.search(r'^Abstract$', full, re.M) is not None)
print('关键词行:', [t[:30] for t in texts if t.startswith('关键词')][:1])
toc = any('TOC \\o' in (it.text or '') for it in doc.element.body.iter(qn('w:instrText')))
print('目录域:', toc)
print('章标题:', [t for t in texts if re.match(r'^第\d章', t)])
print('结论/致谢/参考文献:', '结论与展望' in texts, '致 谢' in texts, '参 考 文 献' in texts)

print()
print('== 标点与格式 ==')
bad = [t for t in texts if re.search(r'[一-鿿][,;:?!]', t)]
print('中文旁残留半角标点段数:', len(bad))
for t in bad[:3]:
    print('  例:', t[:60])

h1 = [para for para in doc.paragraphs if para.style.name == 'Heading 1']
print('Heading1 数量:', len(h1), '->', [h.text for h in h1])

body_like = [para for para in doc.paragraphs
             if para.style.name not in ('Heading 1', 'Heading 2', 'Heading 3')
             and re.match(r'^[一-鿿]', para.text or '')]
sample = body_like[len(body_like) // 2] if body_like else None
if sample:
    pf = sample.paragraph_format
    print('正文抽样:', sample.text[:30], '...')
    print('  行距:', pf.line_spacing, '规则:', pf.line_spacing_rule,
          '| 首缩:', pf.first_line_indent)
    r = sample.runs[0]
    print('  字体:', r.font.name, r.font.size)

import os
print()
print('文件大小 KB:', round(os.path.getsize(p) / 1024, 1))
