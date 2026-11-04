# -*- coding: utf-8 -*-
"""将最终版 Word 中的目录域替换为静态目录文本,保留页码且不触发更新弹窗。"""
from pathlib import Path
import re
import shutil
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '毕业设计论文_最终版.docx'
OUTPUT = ROOT / '毕业设计论文_最终版_含目录.docx'
shutil.copy2(SOURCE, OUTPUT)

# Word 常量: wdGoToBookmark=-1, wdCollapseStart=1, wdCollapseEnd=0
word = win32com.client.DispatchEx('Word.Application')
word.Visible = False
word.DisplayAlerts = 0
word.Options.UpdateLinksAtOpen = False
try:
    doc = word.Documents.Open(str(OUTPUT), ReadOnly=False, AddToRecentFiles=False)
    # 当前目录域已在另存时转换为空段,其后紧接第1章标题。
    paragraphs = doc.Paragraphs
    toc_title = None
    first_chapter = None
    for i in range(1, paragraphs.Count + 1):
        text = paragraphs.Item(i).Range.Text.replace('\r', '').replace('\x07', '').strip()
        if text == '目  录':
            toc_title = i
        elif toc_title is not None and text == '第1章 绪论':
            first_chapter = i
            break
    if toc_title is None or first_chapter is None:
        raise RuntimeError(f'无法定位目录: toc={toc_title}, first_chapter={first_chapter}')

    # 用当前文档中 Heading 1-3 的文本和页码生成目录。Word 本地化后
    # 的样式名可能是“标题 11”“标题 21”“标题 31”,因此不能只判断英文样式名。
    entries = []
    for i in range(first_chapter, paragraphs.Count + 1):
        p = paragraphs.Item(i)
        style = p.Style.NameLocal
        text = p.Range.Text.replace('\r', '').replace('\x07', '').strip()
        match = re.search(r'(?:Heading|标题)\s*([123])(?:[123])?$', style)
        if match:
            level = int(match.group(1))
            if text:
                page = p.Range.Information(3)  # wdActiveEndAdjustedPageNumber
                entries.append((level, text, int(page)))

    if not entries:
        raise RuntimeError('未识别到正文标题,未写入目录')

    def write_static_entries():
        """将目录条目写入目录标题后的区域,用右对齐制表位放置页码。"""
        current = doc.Paragraphs
        start = current.Item(toc_title + 1).Range.Start
        end = current.Item(first_chapter + 1).Range.Start
        doc.Range(start, end).Text = ''
        insert = doc.Range(start, start)
        for level, text, page in entries:
            insert.InsertAfter(('　' * (level - 1)) + text + '\t' + str(page) + '\r')
            insert.Collapse(0)
        current = doc.Paragraphs
        for offset in range(len(entries)):
            p = current.Item(toc_title + 1 + offset)
            p.Style = 'Normal'
            p.Range.Font.NameFarEast = '宋体'
            p.Range.Font.Name = 'Times New Roman'
            p.Range.Font.Size = 12
            p.ParagraphFormat.LeftIndent = 0
            p.ParagraphFormat.FirstLineIndent = 0
            p.ParagraphFormat.LineSpacingRule = 4
            p.ParagraphFormat.LineSpacing = word.PointsToLines(24)
            p.ParagraphFormat.TabStops.ClearAll()
            p.ParagraphFormat.TabStops.Add(
                word.CentimetersToPoints(14.8), 2, 1
            )  # 右对齐 + 点引导线

    write_static_entries()

    # 插入目录可能使正文分页,重新读取正文标题页码并更新目录中的页码。
    current = doc.Paragraphs
    for i in range(first_chapter + len(entries), current.Count + 1):
        p = current.Item(i)
        style = p.Style.NameLocal
        text = p.Range.Text.replace('\r', '').replace('\x07', '').strip()
        match = re.search(r'(?:Heading|标题)\s*([123])(?:[123])?$', style)
        if match and text:
            for entry in entries:
                if entry[1] == text:
                    entries[entries.index(entry)] = (entry[0], entry[1], int(p.Range.Information(3)))
                    break
    write_static_entries()

    # 再清理可能残留的域，并关闭自动更新。
    for story in doc.StoryRanges:
        current = story
        while current is not None:
            while current.Fields.Count > 0:
                current.Fields.Item(1).Unlink()
            current = current.NextStoryRange
    doc.Save()
    doc.Close(False)
    print(f'已生成: {OUTPUT}')
    print(f'目录条目: {len(entries)}')
finally:
    word.Quit()
