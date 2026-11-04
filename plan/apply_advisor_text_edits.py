# -*- coding: utf-8 -*-
"""按导师意见删除跨章节回溯式表述，并为表4-1、表4-2、表6-2补充逐表说明。"""

from pathlib import Path
import shutil

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Pt


ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "毕业设计论文_唐星星_最终定稿.docx"
BACKUP = ROOT / "毕业设计论文_唐星星_最终定稿_备份_导师意见文字修改前.docx"

# (匹配前缀, 需删除的片段, 删除后替换为)
REMOVALS = [
    ("横切模块有两个", "，回应了3.2.1中保存即生效的需求", ""),
    ("管理端围绕知识的组织与入库划分为五个模块", "，对应3.2.1的身份认证需求", ""),
    ("聊天端围绕知识的消费划分为三个模块", "，满足3.2.2中匿名归属、误删可防的要求", ""),
    ("数据库设计遵循三条约定", "，与3.2.2和3.3的安全性需求一致", ""),
    ("第一步把问题交给嵌入模型", "两路并行的理由2.3已述；", ""),
    ("第三步按向量权重", "，回退机制保证了3.3所要求的响应稳定性", ""),
    ("处理按阶段推进", "，对应3.3中进度逐段提交的要求", ""),
    ("切块阶段读取所属知识库", "，对应3.2.1的自动回退要求", ""),
    ("重新处理在上述链路上", "，对应3.2.1中保持两侧对应的验收条件", ""),
    ("本章完成了从需求到设计的转化", "上述设计逐项回应了第3章的需求，", "上述设计构成了系统实现的基础，"),
    ("表6-2覆盖了登录", "登录、文档处理、问答和来源查看均有第5章截图作为界面证据。", ""),
]

# (匹配前缀, 整段新文字)
REWRITES = [
    (
        "分层的直接收益是变更隔离",
        "分层的直接收益是变更隔离：替换模型服务或调整检索环节只影响对应的服务装配与运行期配置，"
        "接口层的校验与鉴权保持不变。",
    ),
    (
        "聊天端的测试重点是匿名会话",
        "聊天端的测试重点是匿名会话、流式回答、来源引用、原文预览和无证据拒答，"
        "脚本对检索、流式事件、邻块扩展与文件预览逻辑进行补充验证。",
    ),
    (
        "演示按照",
        "演示按照实际使用顺序进行：管理员先登录并完成首次改密，再上传文档并观察入库进度；"
        "随后进入聊天端提交问题，查看回答中的来源标记，并打开原始文件核对。"
        "各页面均配有截图与说明，便于对照操作过程检查系统输出。",
    ),
]

# (插在哪个段落之前, 新段落文字)
INSERTS = [
    (
        "围绕表4-1补充两点关系",
        "表4-1列出七张主要数据表。admin 表保存唯一管理员的用户名、口令散列、强制改密标志与最近登录时间；"
        "knowledge_bases 表保存知识库名称、启用状态与切块模板；documents 表保存上传文件的存储路径、"
        "文件哈希、处理状态、进度与重试次数；document_chunks 表保存切片正文与位置信息，主键同时作为向量点标识；"
        "conversations 表按匿名客户端标识归属会话，并以删除标志支持软删除；qa_records 表记录每次问答的检索参数、"
        "耗时分项与 token 统计；qa_sources 表保存回答命中的来源切片、相似度与排序。",
    ),
    (
        "第一步把问题交给嵌入模型",
        "表4-2列出检索与切块环节的默认参数。candidate_top_k 控制向量路与关键词路各自取回的候选数量；"
        "vector_weight 控制融合时向量得分的权重，其余权重归关键词路；similarity_threshold 是融合之后的统一过滤下限；"
        "final_top_k 控制截断后进入邻块扩展的候选数；chunk_size 与 chunk_overlap 控制通用模板的切片目标长度与相邻块重叠；"
        "auto_keywords 与 auto_questions 控制入库增强生成的关键词与候选问题数量，置 0 即关闭。",
    ),
    (
        "表6-2覆盖了登录",
        "表6-2的九条用例按功能分组。TC-01 至 TC-03 覆盖管理员登录改密、知识库创建与文档格式校验；"
        "TC-04 与 TC-05 覆盖文档入库进度、重新处理与删除；TC-06 覆盖模型配置切换与检索参数保存；"
        "TC-07 至 TC-09 覆盖匿名会话、流式回答、来源预览与无证据拒答。",
    ),
]


def find_paragraph(doc, prefix):
    for paragraph in doc.paragraphs:
        if paragraph.text.strip().startswith(prefix):
            return paragraph
    raise ValueError(f"未找到段落: {prefix}")


def set_text(paragraph, text):
    runs = paragraph.runs
    if not runs:
        raise ValueError(f"段落没有 run: {paragraph.text[:30]}")
    runs[0].text = text
    for run in runs[1:]:
        run._element.getparent().remove(run._element)


def set_body_format(paragraph):
    paragraph.alignment = None
    pf = paragraph.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(24)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(24)


def add_body_paragraph_before(reference, text):
    paragraph = reference.insert_paragraph_before()
    paragraph.style = reference.style
    set_body_format(paragraph)
    run = paragraph.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), "宋体")
    r_fonts.set(qn("w:ascii"), "Times New Roman")
    r_fonts.set(qn("w:hAnsi"), "Times New Roman")
    return paragraph


def main():
    if not BACKUP.exists():
        shutil.copy2(DOCX, BACKUP)

    doc = Document(DOCX)

    for prefix, old, new in REMOVALS:
        paragraph = find_paragraph(doc, prefix)
        text = paragraph.text
        if old not in text:
            raise ValueError(f"未找到待删除片段: {prefix} -> {old}")
        set_text(paragraph, text.replace(old, new, 1))

    for prefix, new_text in REWRITES:
        paragraph = find_paragraph(doc, prefix)
        set_text(paragraph, new_text)

    for prefix, text in INSERTS:
        reference = find_paragraph(doc, prefix)
        add_body_paragraph_before(reference, text)

    doc.save(DOCX)
    print(f"已删除回溯式片段 {len(REMOVALS)} 处，重写 {len(REWRITES)} 段，插入表格说明 {len(INSERTS)} 段")


if __name__ == "__main__":
    main()
