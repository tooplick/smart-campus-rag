# -*- coding: utf-8 -*-
"""在无外部域的论文中生成 Word 目录,更新后转为静态内容并另存。"""
from pathlib import Path
import shutil
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '毕业设计论文_最终版.docx'
OUTPUT = ROOT / '毕业设计论文_最终版_含目录.docx'
shutil.copy2(SOURCE, OUTPUT)

word = win32com.client.DispatchEx('Word.Application')
word.Visible = False
word.DisplayAlerts = 0
word.Options.UpdateLinksAtOpen = False
try:
    doc = word.Documents.Open(str(OUTPUT), ReadOnly=False, AddToRecentFiles=False)
    paragraphs = doc.Paragraphs
    toc_idx = first_idx = None
    for i in range(1, paragraphs.Count + 1):
        text = paragraphs.Item(i).Range.Text.replace('\r', '').replace('\x07', '').strip()
        if text == '目  录':
            toc_idx = i
        elif toc_idx is not None and text == '第1章 绪论':
            first_idx = i
            break
    if toc_idx is None or first_idx is None:
        raise RuntimeError(f'无法定位目录和第1章: {toc_idx}, {first_idx}')

    # 删除目录标题后原有的空段,在标题末尾插入真正的目录对象。
    empty_range = doc.Paragraphs.Item(toc_idx + 1).Range
    empty_range.Delete()
    insert = doc.Paragraphs.Item(toc_idx).Range.Duplicate
    insert.Collapse(0)
    toc = doc.TablesOfContents.Add(
        insert, True, 1, 3, True, '', True, True, '', False, False
    )
    toc.Update()

    # 将目录域转换为普通文本,保留刚刚生成的目录结果,避免打开时执行任何域更新。
    toc.Range.Fields.Unlink()
    for story in doc.StoryRanges:
        current = story
        while current is not None:
            while current.Fields.Count > 0:
                current.Fields.Item(1).Unlink()
            current = current.NextStoryRange

    doc.Save()
    doc.Close(False)
    print(f'已生成: {OUTPUT}')
finally:
    word.Quit()
