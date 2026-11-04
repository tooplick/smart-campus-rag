# -*- coding: utf-8 -*-
"""扩充论文中文摘要并同步英文摘要。"""

from pathlib import Path
import shutil

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "毕业设计论文_导师修改版_第五章扩充格式优化.docx"
BACKUP = ROOT / "毕业设计论文_导师修改版_第五章扩充格式优化_备份_摘要修改前.docx"
OUTPUT = ROOT / "毕业设计论文_导师修改版_摘要扩充.docx"

ZH_ABSTRACT = (
    "高校的规章制度、办事指南与课程资料通常以 PDF、Word、Excel、PPT、网页和图片等多种格式分散存放，"
    "师生查找信息时往往需要反复检索或翻阅原文，普通关键词搜索也难以理解口语化提问。"
    "通用大语言模型虽然具备自然语言交互能力，却存在知识过时、事实幻觉和无法溯源等问题。"
    "针对上述问题，本设计实现了一个基于检索增强生成的智能校园知识库系统。"
    "管理员上传文档后，系统按文件类型完成解析，依据知识库模板切块，可选地进行关键词与候选问题增强，"
    "再将切片向量化并写入 Qdrant 向量数据库。"
    "用户以自然语言提问时，系统同时执行向量检索与关键词检索，对两路结果加权融合并按相似度阈值过滤，"
    "在启用重排时对候选重新排序，随后扩展相邻切片以补充上下文，由大语言模型依据检索证据生成回答。"
    "回答通过服务器推送事件流式返回，并附带来源引用，用户可以预览原始文件核对出处；"
    "当检索不到足够证据时，系统拒绝作答。"
    "系统后端采用 FastAPI、异步 SQLAlchemy 与 PostgreSQL，前端采用 Vue 3、TypeScript 与 Vite，"
    "包含管理端和聊天端，能够完成文档入库、匿名问答、来源查看与问答日志管理等功能，"
    "为校园信息查询提供了一种可更新、可核验的实现方案。"
)

ZH_KEYWORDS = "关键词：检索增强生成；知识库问答；混合检索；向量检索；校园信息化"

EN_ABSTRACT = (
    "Campus rules, service guides and course materials are stored in a variety of formats such as PDF, Word, "
    "Excel, PowerPoint, web pages and images, and they are scattered across different platforms. "
    "Teachers and students often have to search repeatedly or read the original documents, and ordinary keyword "
    "search can hardly handle colloquial questions. Although general large language models support natural "
    "language interaction, they suffer from outdated knowledge, factual hallucination and a lack of traceability. "
    "To address these problems, this graduation project designs and implements an intelligent campus knowledge "
    "base system based on retrieval-augmented generation. After an administrator uploads a document, the system "
    "parses it according to its file type, splits it into chunks with the knowledge base template, optionally "
    "enriches the chunks with keywords and candidate questions, and writes the chunk vectors into the Qdrant "
    "vector database. When a user asks a question in natural language, the system performs vector retrieval and "
    "keyword retrieval at the same time, fuses the two result lists with weights, filters candidates by a "
    "similarity threshold, optionally reranks them, and expands adjacent chunks to supply context. A large "
    "language model then generates an answer from the retrieved evidence. The answer is pushed to the front end "
    "through server-sent events and carries citations, so that users can preview the original files and check "
    "the sources. When no sufficient evidence is found, the system refuses to answer. The backend uses FastAPI, "
    "asynchronous SQLAlchemy and PostgreSQL, and the frontend uses Vue 3, TypeScript and Vite. The system "
    "consists of an administrative side and a chat side, and supports document ingestion, anonymous question "
    "answering, source viewing and question-answer log management, providing an updatable and verifiable "
    "approach to campus information retrieval."
)

EN_KEYWORDS = (
    "Retrieval-Augmented Generation; knowledge base question answering; hybrid retrieval; "
    "vector retrieval; campus informatization"
)


def find_paragraph(document, prefix):
    for paragraph in document.paragraphs:
        if paragraph.text.strip().startswith(prefix):
            return paragraph
    raise ValueError(f"未找到段落: {prefix}")


def replace_single_run(paragraph, text):
    """保留首个 run 的字符格式，替换整段文字。"""
    runs = paragraph.runs
    if not runs:
        raise ValueError(f"段落没有 run: {paragraph.text[:30]}")
    runs[0].text = text
    for run in runs[1:]:
        run._element.getparent().remove(run._element)


def replace_keywords(paragraph, text):
    """关键词段落保留加粗的“Keywords: ”前缀，只替换其后内容。"""
    runs = paragraph.runs
    if len(runs) < 2:
        replace_single_run(paragraph, text)
        return
    runs[1].text = text
    for run in runs[2:]:
        run._element.getparent().remove(run._element)


def main():
    if not BACKUP.exists():
        shutil.copy2(SOURCE, BACKUP)
    shutil.copy2(SOURCE, OUTPUT)

    doc = Document(OUTPUT)
    replace_single_run(find_paragraph(doc, "高校"), ZH_ABSTRACT)
    replace_single_run(find_paragraph(doc, "关键词："), ZH_KEYWORDS)
    replace_single_run(find_paragraph(doc, "Campus rules"), EN_ABSTRACT)
    replace_keywords(find_paragraph(doc, "Keywords:"), EN_KEYWORDS)

    doc.save(OUTPUT)
    print(f"已备份: {BACKUP.name}")
    print(f"已生成: {OUTPUT.name}")


if __name__ == "__main__":
    main()
