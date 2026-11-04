# -*- coding: utf-8 -*-
import re, os
from docx import Document
from docx.oxml.ns import qn

p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '毕业设计论文_唐星星.docx')
doc = Document(p)
texts = [para.text for para in doc.paragraphs]
full = '\n'.join(texts)

print('== 关键内容 ==')
print('封面校名:', any('苏州高博职业学院' in t for t in texts[:10]))
print('摘要/Abstract/关键词:', '中 文 摘 要' in full, 'Abstract' in full,
      any(t.startswith('关键词：') for t in texts))
toc = any('TOC \\o' in (it.text or '') for it in doc.element.body.iter(qn('w:instrText')))
print('目录域:', toc)

chs = [t for t in texts if re.fullmatch(r'第\d章 .*', t)]
print('章标题(%d/6):' % len(chs), chs)
for name in ('结论与展望', '致 谢', '参 考 文 献'):
    print(f'  {name}:', name in texts)

print()
print('== 标题与大纲 ==')
h = [pa for pa in doc.paragraphs if re.match(r'^Heading \d$', pa.style.name)]
print('Heading 样式段落数:', len(h))
print('可用标题样式:', [s.name for s in doc.styles if s.name.startswith('Heading')])
ol = [pa.text for pa in doc.paragraphs
      if pa._p.find(qn('w:pPr')) is not None
      and pa._p.find(qn('w:pPr')).find(qn('w:outlineLvl')) is not None]
print('带大纲级别段落数:', len(ol))

print()
print('== 标点 ==')
bad = [t for t in texts if re.search(r'[一-鿿][,;:?!]', t)
       and not re.match(r'^\s*(raise|#|\w+\s*=|\w+\()', t)]
print('正文残留半角标点(排除代码行):', len(bad))
for t in bad[:3]:
    print('  例:', t[:60])

sample = next(pa for pa in doc.paragraphs
              if pa.style.name not in ('Heading 1', 'Heading 2', 'Heading 3')
              and re.match(r'^(检索环节|入库流程|高校在)', pa.text or ''))
pf = sample.paragraph_format
print()
print('正文抽样:', sample.text[:20])
print('  行距pt:', pf.line_spacing.pt, '| 首缩pt:', pf.first_line_indent.pt,
      '| 字号pt:', sample.runs[0].font.size.pt)
print('文件大小 KB:', round(os.path.getsize(p) / 1024, 1))
