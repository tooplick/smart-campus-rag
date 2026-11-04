# -*- coding: utf-8 -*-
"""把 3.4 用例分析改为「用例图 + 文字描述 + 核心用例表格」。

原稿用加粗行当小标题、逐条罗列「用例名称/参与者/前置条件…」,不符合论文撰写要求。
本脚本在 docx 上定点替换 3.4 节正文(不动其他章节),新增 图3-1 与 表3-1。
格式复用 build_docx.py 的正文/图题/表题函数,保证与全文一致。
"""
import os
import shutil
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_docx import _borders, add_runs, fmt_para, set_font, to_fullwidth  # noqa: E402

DOC = r'd:\Github\smart-campus-rag\毕业设计论文_唐星星.docx'
FIG = r'd:\Github\smart-campus-rag\chapters\images\图3-1-系统用例图.png'
BAK = DOC + '.bak'

P1 = ('系统有管理员与匿名师生两类参与者,前者负责知识的组织与入库,后者负责知识的消费,'
      '二者的目标不同,所涉及的用例也不相同。图3-1按统一建模语言的用例图约定给出系统的整体用例视图:'
      '矩形表示系统边界,椭圆表示用例,小人表示参与者,实线表示参与者与用例之间的关联,'
      '带箭头的虚线表示用例之间的包含与扩展关系。')

P3 = ('从图中可以看出,管理员一侧有登录与首次改密、知识库管理、文档管理、模型配置与连通测试、'
      '问答日志查看五个用例,覆盖身份凭证、知识组织与运行维护三个方面,其中文档管理通过包含关系'
      '复用文档上传与入库,后者承担格式与大小校验、解析、切块、可选增强与向量化等步骤,'
      '是管理员侧最重的一条路径。匿名师生一侧有匿名会话建立、提问并获得带引用回答、'
      '引用核对与原文预览、会话管理四个用例,覆盖从进入会话页到回查出处的完整闭环,'
      '无证据拒答作为提问用例的扩展分支出现,只在检索不到达到阈值的证据时触发,'
      '正常回答与拒答由此构成互斥的两条出口。两类参与者之间没有继承或包含关系:'
      '管理员以令牌访问管理端,师生以匿名标识直接进入会话页,两条链路在用例层面互不交叠,'
      '仅原文件的预览接口对两端同时开放。')

P4 = ('图中以橙色标出的两个用例是系统的主干,分别对应知识的入库与消费两端,其余用例围绕它们展开。'
      '为避免把用例描述拆成条目式的字段罗列,这两个用例的参与者、前置条件、基本事件流、'
      '扩展事件流与后置条件统一整理为表3-1。')

P5 = ('表中前两行界定谁在什么条件下发起用例,中间两行给出正常路径与异常路径,'
      '末行给出可验收的结果状态,分别与3.2节的功能需求和3.3节的质量要求对应。'
      '用例一的基本事件流是4.5节入库流程设计的依据,用例二的基本事件流则对应4.4节的检索流程设计,'
      '两者的环节划分与参数取舍将在第4章展开。')

TABLE = [
    ['项目', '用例一:文档上传与入库', '用例二:匿名提问并获得\n带引用回答'],
    ['参与者', '管理员', '匿名师生'],
    ['前置条件',
     '管理员已登录并完成首次改密,目标知识库已创建并指定切块模板,数据库与向量库已初始化',
     '至少存在一个启用且含有已完成文档的知识库,嵌入与生成服务配置可用,用户已取得匿名客户端标识'],
    ['基本事件流',
     '管理员选定知识库上传一份不超过 50MB 的文档,系统校验格式与大小后受理,保存原文件并把记录置为待处理;'
     '后台线程领取任务,依次完成解析、按模板切块、可选增强与向量化,进度按阶段写回,处理完毕状态转为已完成',
     '用户输入问题并发送,系统校验知识库可用后受理,问题经向量化、双路检索、加权融合、阈值过滤、'
     '可选重排与邻块扩展后拼装为带来源编号的上下文,由大语言模型生成回答并逐段推送'],
    ['扩展事件流',
     '格式或大小不通过时在写盘之前拒绝,不建立文档记录;处理失败累计三次后置为失败并保留错误信息,'
     '管理员可发起重新处理,系统清理旧切片与旧向量点后重建',
     '过滤后没有任何候选达到阈值时不调用生成模型,直接返回注明未找到依据的拒答内容'],
    ['后置条件',
     '切片与向量均已写入且一一对应;执行过重新处理时库中只保留重建后的结果',
     '该次问答及命中来源写入问答记录,回答带有可点击核对的出处引用,'
     '首条消息对应的会话自动建立并归属当前匿名标识'],
]
COL_W = (2.3, 6.2, 6.2)   # cm,合计 14.7,与正文版心一致


def body_before(anchor, text):
    p = anchor.insert_paragraph_before()
    fmt_para(p, spacing=24, indent_chars=2, size=12)
    add_runs(p, to_fullwidth(text), east='宋体', size=12)
    return p


def caption_before(anchor, text):
    p = anchor.insert_paragraph_before()
    fmt_para(p, spacing=18, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=3)
    r = p.add_run(to_fullwidth(text))
    set_font(r, east='宋体', size=10.5)
    return p


def image_before(anchor, path, width_cm=15.0):
    p = anchor.insert_paragraph_before()
    fmt_para(p, spacing=18, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
             before=6, after=0, rule=WD_LINE_SPACING.SINGLE)
    # 行距必须是单倍:写成固定值(如 18 磅)会把内联图片裁成一条线
    spacing = p._p.get_or_add_pPr().find(qn('w:spacing'))
    if spacing is not None:
        for attr in ('w:line', 'w:lineRule'):
            if spacing.get(qn(attr)) is not None:
                del spacing.attrib[qn(attr)]
    p.add_run().add_picture(path, width=Cm(width_cm))
    return p


def table_before(doc, anchor, rows, col_w):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    try:
        table.style = 'Table Grid'
    except KeyError:
        _borders(table)
    table.autofit = False
    for j, w in enumerate(col_w):
        table.columns[j].width = Cm(w)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            cell = table.cell(i, j)
            cell.width = Cm(col_w[j])
            p = cell.paragraphs[0]
            fmt_para(p, spacing=14, rule=WD_LINE_SPACING.SINGLE, size=10.5,
                     align=WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT)
            r = p.add_run(to_fullwidth(txt))
            set_font(r, east='宋体', size=10.5, bold=(i == 0))
        trPr = table.rows[i]._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))       # 行不跨页断开
        if i == 0:
            trPr.append(OxmlElement('w:tblHeader'))   # 跨页重复表头
    anchor._p.addprevious(table._tbl)
    return table


def main():
    if not os.path.exists(BAK):
        shutil.copy2(DOC, BAK)
        print('已备份:', BAK)

    doc = Document(DOC)
    if any(p.text.strip().startswith('图3-1 系统用例图') for p in doc.paragraphs):
        raise SystemExit('文档中已存在「图3-1 系统用例图」,补丁已应用过;请先从 .bak 备份还原再重跑')
    i_start = i_end = None
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if t == '3.4 用例分析':
            i_start = i
        elif i_start is not None and t == '3.5 本章小结':
            i_end = i
            break
    if i_start is None or i_end is None:
        raise SystemExit('未定位到 3.4 / 3.5 标题')
    print(f'待替换段落: [{i_start + 1}, {i_end - 1}],共 {i_end - i_start - 1} 段')

    anchor = doc.paragraphs[i_end]
    for p in doc.paragraphs[i_start + 1:i_end]:
        p._p.getparent().remove(p._p)

    body_before(anchor, P1)
    image_before(anchor, FIG)
    caption_before(anchor, '图3-1 系统用例图')
    body_before(anchor, P3)
    body_before(anchor, P4)
    caption_before(anchor, '表3-1 核心用例描述')
    table_before(doc, anchor, TABLE, COL_W)
    body_before(anchor, P5)

    doc.save(DOC)
    chk = Document(DOC)
    print('已保存:', DOC)
    print('段落数:', len(chk.paragraphs), '| 表格数:', len(chk.tables),
          '| 图片数:', len(chk.inline_shapes))


if __name__ == '__main__':
    main()
