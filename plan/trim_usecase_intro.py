# -*- coding: utf-8 -*-
"""删除 3.4 节开头对 UML 用例图符号约定的解释，只保留系统自身的用例说明。"""

from pathlib import Path
import shutil

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_用例说明精简前.docx"

NEW_TEXT = (
    "系统有管理员与匿名师生两类参与者，前者负责知识的组织与入库，后者负责知识的消费，"
    "二者的目标不同，所涉及的用例也不相同。图3-1给出系统的整体用例视图，"
    "管理端与聊天端的用例分列呈现。"
)


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    doc = Document(DOCX)
    target = None
    for paragraph in doc.paragraphs:
        if "按统一建模语言的用例图约定" in paragraph.text:
            target = paragraph
            break
    if target is None:
        raise RuntimeError("未找到包含 UML 符号解释的段落")

    runs = target.runs
    if not runs:
        raise RuntimeError("目标段落没有 run")
    runs[0].text = NEW_TEXT
    for run in runs[1:]:
        run._element.getparent().remove(run._element)

    doc.save(DOCX)
    print("已替换 3.4 节开头段落")
    print(target.text)


if __name__ == "__main__":
    main()
