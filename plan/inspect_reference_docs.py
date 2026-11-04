# -*- coding: utf-8 -*-
from pathlib import Path
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
for path in sorted(ROOT.glob('*.docx')):
    if path.name.startswith(('毕业设计论文', '~$')):
        continue
    print(f'=== {path.name} | {path.stat().st_size} bytes ===')
    doc = Document(path)
    print('段落:', len(doc.paragraphs), '表格:', len(doc.tables), '图片:', len(doc.inline_shapes), '节:', len(doc.sections))
    print('--- 段落文本 ---')
    for i, p in enumerate(doc.paragraphs):
        text = p.text.replace('\r', '').replace('\x07', '').strip()
        if text:
            print(f'P{i:03d} [{p.style.name}] {text}')
    print('--- 表格 ---')
    for ti, table in enumerate(doc.tables):
        print(f'TABLE {ti}: {len(table.rows)}x{len(table.columns)}')
        for row in table.rows:
            print(' | '.join(cell.text.replace('\n', ' / ').strip() for cell in row.cells))
