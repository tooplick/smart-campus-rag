# -*- coding: utf-8 -*-
"""删除表3-1后段落中的跨章节套话，只保留表格本身的说明。"""

from pathlib import Path
import shutil

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_套话精简前.docx"

NEW_TEXT = "表中前两行界定谁在什么条件下发起用例，中间两行给出正常路径与异常路径，末行给出可验收的结果状态。"


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    doc = Document(DOCX)
    target = None
    for paragraph in doc.paragraphs:
        if "表中前两行界定" in paragraph.text:
            target = paragraph
            break
    if target is None:
        raise RuntimeError("未找到表3-1后的说明段落")

    runs = target.runs
    if not runs:
        raise RuntimeError("目标段落没有 run")
    runs[0].text = NEW_TEXT
    for run in runs[1:]:
        run._element.getparent().remove(run._element)

    doc.save(DOCX)
    print("已删减套话")
    print(target.text)


if __name__ == "__main__":
    main()
