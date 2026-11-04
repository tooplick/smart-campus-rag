# -*- coding: utf-8 -*-
"""把第5章的 7 张界面截图替换为高清版本(保持原显示尺寸与位置)。"""

from pathlib import Path
import shutil

import win32com.client


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_替换高清截图前.docx"
HD_DIR = ROOT / "thesis_shots" / "enhanced"

# 文档内联图形顺序:[1..5] 为矢量图(图3-1/3-2/3-3/4-1/4-2),[6..12] 为第5章 7 张截图
# 截图按文档顺序对应 图5-1 → 图5-7
HD_FILES = [
    "图5-1-登录失败提示.png",
    "图5-2-首次改密页面.png",
    "图5-3-文档列表页面.png",
    "图5-4-文档入库进度页面.png",
    "图5-5-聊天端问答页面.png",
    "图5-6-问答来源列表.png",
    "图5-7-引用文件预览页面.png",
]


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)
        print("已备份:", BACKUP.name)

    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)

        # 逐个替换:先在旧图前插入新图再删除旧图,净索引零位移,可按顺序进行
        for offset, filename in enumerate(HD_FILES):
            index = 6 + offset  # 6..12
            path = HD_DIR / filename
            shape = doc.InlineShapes.Item(index)
            width, height = shape.Width, shape.Height
            target = shape.Range.Duplicate
            target.Collapse(1)  # wdCollapseStart
            new_shape = doc.InlineShapes.AddPicture(str(path), False, True, target)
            new_shape.Width = width
            new_shape.Height = height
            shape.Delete()
            print(f"已替换 [{index}] → {filename} ({width:.0f}x{height:.0f}pt)")

        doc.Save()
        doc.Close(False)
        print("保存完成")
    finally:
        word.Quit()


if __name__ == "__main__":
    main()
