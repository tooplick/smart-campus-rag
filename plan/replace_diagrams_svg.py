# -*- coding: utf-8 -*-
"""把最终定稿中的图4-1、图4-2替换为黑白 SVG 矢量图。"""

from pathlib import Path
import shutil

import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_图4改矢量前.docx"
IMAGES = ROOT / "chapters" / "images"

# 从后往前替换，避免删除图片后 InlineShapes 索引变化
REPLACEMENTS = [
    (3, IMAGES / "图4-2-组件交互图.svg", "图4-2"),
    (2, IMAGES / "图4-1-总体架构图.svg", "图4-1"),
]


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)
        for index, svg, name in REPLACEMENTS:
            shape = doc.InlineShapes.Item(index)
            width, height = shape.Width, shape.Height
            target = shape.Range.Duplicate
            target.Collapse(1)
            new_shape = doc.InlineShapes.AddPicture(str(svg), False, True, target)
            new_shape.Width = width
            new_shape.Height = height
            shape.Delete()
            print(f"{name} 已替换，尺寸 {width:.1f} x {height:.1f} pt")
        doc.Save()
        doc.Close(False)
    finally:
        word.Quit()


if __name__ == "__main__":
    main()
