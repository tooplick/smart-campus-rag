# -*- coding: utf-8 -*-
"""把最终定稿中的图3-1替换为黑白 SVG 矢量图。"""

from pathlib import Path
import shutil

import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_图3-1改矢量前.docx"
SVG = ROOT / "chapters" / "images" / "图3-1-系统用例图.svg"


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)
        shape = doc.InlineShapes.Item(1)
        width, height = shape.Width, shape.Height
        target = shape.Range.Duplicate
        target.Collapse(1)
        new_shape = doc.InlineShapes.AddPicture(str(SVG), False, True, target)
        new_shape.Width = width
        new_shape.Height = height
        shape.Delete()
        doc.Save()
        doc.Close(False)
        print(f"图3-1 已替换为 SVG，尺寸 {width:.1f} x {height:.1f} pt")
    finally:
        word.Quit()


if __name__ == "__main__":
    main()
