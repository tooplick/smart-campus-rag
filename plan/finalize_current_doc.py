# -*- coding: utf-8 -*-
"""将当前重建的论文更新目录、转为静态内容并另存为无弹窗版本。"""
from pathlib import Path
import shutil
import win32com.client

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / '毕业设计论文_唐星星.docx'
output = ROOT / '毕业设计论文_导师修改版_最终.docx'
if output.exists():
    output.unlink()
shutil.copy2(source, output)

word = win32com.client.DispatchEx('Word.Application')
word.Visible = False
word.DisplayAlerts = 0
word.Options.UpdateLinksAtOpen = False
try:
    doc = word.Documents.Open(str(output), ReadOnly=False, AddToRecentFiles=False)
    # 更新目录和页码后,解除所有域,保留域当前显示结果。
    for story in doc.StoryRanges:
        current = story
        while current is not None:
            if current.Fields.Count:
                current.Fields.Update()
            current = current.NextStoryRange
    for story in doc.StoryRanges:
        current = story
        while current is not None:
            while current.Fields.Count:
                current.Fields.Item(1).Unlink()
            current = current.NextStoryRange
    doc.Save()
    print('已生成:', output)
    print('页数:', doc.ComputeStatistics(2), '段落:', doc.Paragraphs.Count)
    doc.Close(False)
finally:
    word.Quit()
