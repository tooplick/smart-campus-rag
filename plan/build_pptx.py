# -*- coding: utf-8 -*-
"""生成毕设答辩 PPT(15 页, 16:9, 蓝白简洁学术风)。
- 依赖:python-pptx(uv 环境已含, 零新增)、Pillow(读取配图尺寸)
- 用法:uv run python plan/build_pptx.py
- 输出:c:\\Users\\id654\\Desktop\\毕设答辩PPT_唐星星.pptx
- 配色沿用 plan/draw_architecture.py 色板;中文字体写法参考 build_docx.py
  (python-pptx 的 font.name 只设 a:latin,东亚字体需手写 a:ea)
- 内容口径与 chapters/*.md 一致:性能实测数据论文中为 [待补:实测],PPT 不编造。
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from PIL import Image

OUT = r'c:\Users\id654\Desktop\毕设答辩PPT_唐星星.pptx'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_ARCH = os.path.join(BASE, 'chapters', 'images', '图4-1-总体架构图.png')
IMG_COMP = os.path.join(BASE, 'chapters', 'images', '图4-2-组件交互图.png')

# ---------- 主题 ----------
BLUE = RGBColor(0x5B, 0x82, 0xB6)      # 主色
DARK = RGBColor(0x2C, 0x3E, 0x50)      # 标题深色
INK = RGBColor(0x33, 0x33, 0x33)       # 正文
GRAY = RGBColor(0x88, 0x88, 0x88)      # 辅助
LIGHT = RGBColor(0xEE, 0xF3, 0xF9)     # 卡片底
LIGHT2 = RGBColor(0xF5, 0xF7, 0xFA)    # 次级底
GREEN = RGBColor(0x6F, 0xAE, 0x7F)
ORANGE = RGBColor(0xE0, 0xA4, 0x58)
PURPLE = RGBColor(0x8B, 0x7B, 0xC4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD8, 0xE2, 0xEF)

F_TITLE = '黑体'      # 东亚字体:标题
F_BODY = '宋体'       # 东亚字体:正文
F_WEST = 'Times New Roman'

SW, SH = 13.333, 7.5          # 幻灯片尺寸(英寸)
M = 0.55                       # 左右页边距
CW = SW - 2 * M                # 内容宽度 12.233
TOP = 1.45                     # 内容区顶部
BOTTOM = 6.95                  # 内容区底部
FOOT_Y = 7.02

TITLE_TXT = '基于 RAG 的智能校园知识库系统的设计与实现 · 毕业设计答辩'


# ---------- 字体 ----------
def set_run(run, size=16, bold=False, color=INK, east=F_BODY, ascii_font=F_WEST):
    """设置 run 字体:latin 用 font.name,东亚字体手写 a:ea。"""
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = ascii_font          # 写入 a:latin
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        # a:ea 必须排在 a:latin 之后,先设 font.name 再追加即可满足序列
        ea = parse_xml('<a:ea %s typeface="%s"/>' % (nsdecls('a'), east))
        rPr.append(ea)
    else:
        ea.set('typeface', east)


# ---------- 基础构件 ----------
def add_box(slide, l, t, w, h):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    return tb


def add_para(tf, runs, size=16, align=PP_ALIGN.LEFT, first=False,
             space_before=0, space_after=6, line=1.18, east=F_BODY,
             mar_l=None, hang=None, bold=False, color=None):
    """runs: str 或 [(text, kwargs), ...];kwargs 透传 set_run。"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.line_spacing = line
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    if mar_l is not None:
        pPr = p._p.get_or_add_pPr()
        pPr.set('marL', str(int(Inches(mar_l))))
        if hang is not None:
            pPr.set('indent', str(-int(Inches(hang))))
    if isinstance(runs, str):
        runs = [(runs, {})]
    for text, kw in runs:
        r = p.add_run()
        r.text = text
        kw2 = dict(size=size, east=east, bold=bold)
        if color is not None:
            kw2['color'] = color
        kw2.update(kw)
        set_run(r, **kw2)
    return p


def rect(slide, l, t, w, h, fill=None, line_color=None, line_w=1.0,
         shape=MSO_SHAPE.RECTANGLE, adj=None):
    shp = slide.shapes.add_shape(shape, Inches(l), Inches(t), Inches(w), Inches(h))
    if adj is not None:
        try:
            shp.adjustments[0] = adj
        except (IndexError, ValueError):
            pass
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line_color is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line_color
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    shp.text_frame.word_wrap = True
    return shp


def add_title(slide, text, page=None):
    """内容页标题:蓝色竖条 + 标题 + 分隔线 + 页脚。"""
    rect(slide, M, 0.46, 0.13, 0.52, fill=BLUE)
    tb = add_box(slide, M + 0.25, 0.38, CW - 0.25, 0.7)
    add_para(tb.text_frame, text, size=26, bold=True, color=DARK,
             first=True, east=F_TITLE, space_after=0)
    rect(slide, M, 1.2, CW, 0.022, fill=LINE)
    if page is not None:
        ft = add_box(slide, M, FOOT_Y, 9.5, 0.3)
        add_para(ft.text_frame, TITLE_TXT, size=9, color=GRAY, first=True,
                 space_after=0, east=F_BODY)
        pg = add_box(slide, SW - M - 1.2, FOOT_Y, 1.2, 0.3)
        add_para(pg.text_frame, '%02d / 15' % page, size=9, color=GRAY,
                 align=PP_ALIGN.RIGHT, first=True, space_after=0)


def col_header(slide, l, t, w, text, fill=BLUE, size=15, h=0.44):
    shp = rect(slide, l, t, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.25)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    add_para(tf, text, size=size, bold=True, color=WHITE, first=True,
             align=PP_ALIGN.CENTER, space_after=0, east=F_TITLE)
    return shp


def add_bullets(slide, items, l, t, w, h, size=15, gap=9, line=1.2):
    """items: (level, text) 或 (level, text, color);level0 方块,level1 短横。"""
    tb = add_box(slide, l, t, w, h)
    tf = tb.text_frame
    for i, it in enumerate(items):
        lvl, text = it[0], it[1]
        color = it[2] if len(it) > 2 else None
        marker = '▪  ' if lvl == 0 else '–  '
        m_color = BLUE if lvl == 0 else GRAY
        body_size = size if lvl == 0 else size - 2
        add_para(tf, [
            (marker, dict(color=m_color, size=body_size)),
            (text, dict(color=color or (INK if lvl == 0 else RGBColor(0x55, 0x55, 0x55)),
                        size=body_size, east=F_BODY)),
        ], first=(i == 0), space_after=gap, line=line,
            mar_l=0.26 if lvl == 0 else 0.5, hang=0.26 if lvl == 0 else 0.24)
    return tb


def add_card(slide, l, t, w, h, title, lines, accent=BLUE, fill=LIGHT,
             title_size=16, body_size=13.5, numbered=None):
    shp = rect(slide, l, t, w, h, fill=fill, line_color=accent, line_w=1.2,
               shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.06)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.16)
    tf.margin_top = Inches(0.14)
    tf.margin_bottom = Inches(0.1)
    head = ('%s  %s' % (numbered, title)) if numbered else title
    add_para(tf, head, size=title_size, bold=True, color=accent, first=True,
             space_after=6, east=F_TITLE, line=1.1)
    for ln in lines:
        add_para(tf, [('▪ ', dict(color=accent, size=body_size)),
                      (ln, dict(color=INK, size=body_size))],
                 space_after=4, line=1.15, mar_l=0.0, hang=None, size=body_size)
    return shp


def note_bar(slide, text, t, h=0.56, fill=LIGHT2, color=DARK, size=14, l=M, w=CW):
    shp = rect(slide, l, t, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.3)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.18)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    add_para(tf, text, size=size, color=color, first=True, align=PP_ALIGN.CENTER,
             space_after=0, line=1.1, east=F_BODY)
    return shp


def add_table(slide, rows, l, t, w, h, col_w=None, size=12.5, header_size=13):
    n_rows, n_cols = len(rows), len(rows[0])
    tbl_shape = slide.shapes.add_table(n_rows, n_cols, Inches(l), Inches(t),
                                       Inches(w), Inches(h))
    table = tbl_shape.table
    if col_w:
        for j, cw in enumerate(col_w):
            table.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        table.rows[i].height = Inches(h / n_rows)
        for j, txt in enumerate(row):
            cell = table.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = BLUE if i == 0 else (
                WHITE if i % 2 == 1 else LIGHT2)
            tf = cell.text_frame
            tf.word_wrap = True
            add_para(tf, txt, size=header_size if i == 0 else size,
                     bold=(i == 0), color=WHITE if i == 0 else INK,
                     first=True, align=PP_ALIGN.LEFT, space_after=0,
                     line=1.05, east=F_TITLE if i == 0 else F_BODY)
    return table


def add_picture_fit(slide, path, l, t, max_w, max_h):
    """按比例缩放并居中放置图片。"""
    iw, ih = Image.open(path).size
    ratio = iw / ih
    w, h = max_w, max_w / ratio
    if h > max_h:
        h, w = max_h, max_h * ratio
    left = l + (max_w - w) / 2
    top = t + (max_h - h) / 2
    return slide.shapes.add_picture(path, Inches(left), Inches(top),
                                    Inches(w), Inches(h))


def add_flow(slide, steps, t, box_w, box_h, gap, l=None, fill=LIGHT,
             accent=BLUE, size=12.5):
    """一行圆角流程框 + 箭头。"""
    x = M if l is None else l
    for i, s in enumerate(steps):
        shp = rect(slide, x, t, box_w, box_h, fill=fill, line_color=accent,
                   line_w=1.0, shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.12)
        tf = shp.text_frame
        tf.margin_left = tf.margin_right = Inches(0.04)
        tf.margin_top = tf.margin_bottom = Inches(0.03)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        add_para(tf, s, size=size, color=DARK, first=True, align=PP_ALIGN.CENTER,
                 space_after=0, line=1.05, east=F_BODY)
        x += box_w
        if i < len(steps) - 1:
            ar = add_box(slide, x, t, gap, box_h)
            ar.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            add_para(ar.text_frame, '→', size=size + 3, color=BLUE, first=True,
                     align=PP_ALIGN.CENTER, space_after=0)
            x += gap


# ---------- 各页 ----------
def slide_cover(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, SW, 0.16, fill=BLUE)
    rect(s, 0, SH - 0.16, SW, 0.16, fill=BLUE)
    tb = add_box(s, 1.0, 1.9, SW - 2.0, 1.9)
    add_para(tb.text_frame, '基于 RAG 的智能校园知识库系统', size=40, bold=True,
             color=DARK, first=True, align=PP_ALIGN.CENTER, space_after=10,
             east=F_TITLE, line=1.1)
    add_para(tb.text_frame, '的设计与实现', size=40, bold=True, color=DARK,
             align=PP_ALIGN.CENTER, space_after=0, east=F_TITLE, line=1.1)
    sub = add_box(s, 1.0, 3.85, SW - 2.0, 0.6)
    add_para(sub.text_frame, '毕 业 设 计 答 辩', size=22, color=BLUE, first=True,
             align=PP_ALIGN.CENTER, space_after=0, east=F_TITLE)
    rect(s, SW / 2 - 1.2, 4.6, 2.4, 0.03, fill=BLUE)
    info = add_box(s, 1.0, 4.95, SW - 2.0, 1.7)
    for i, line in enumerate([
        '答辩人：唐星星        学号：024324925',
        '指导教师：瞿梦菊',
        '人工智能学院 · 软件技术专业',
    ]):
        add_para(info.text_frame, line, size=17, color=INK, first=(i == 0),
                 align=PP_ALIGN.CENTER, space_after=10, east=F_BODY)


def slide_toc(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '汇报提纲', page=2)
    items = [
        ('01', '选题背景与研究目标', '为什么做、要做什么'),
        ('02', '系统需求分析', '管理端 + 聊天端功能与用例'),
        ('03', '系统设计', '总体架构、数据设计、核心流程'),
        ('04', '关键技术与实现', 'RAG 管线、流式问答、难点解决'),
        ('05', '系统测试', '脚本测试 + 黑盒演示双线验证'),
        ('06', '总结与展望', '目标达成、不足与后续方向'),
    ]
    for i, (num, title, desc) in enumerate(items):
        col, row = i % 2, i // 2
        l = M + col * (CW / 2 + 0.15)
        t = TOP + 0.35 + row * 1.65
        w = CW / 2 - 0.15
        circ = rect(s, l, t, 0.62, 0.62, fill=BLUE, shape=MSO_SHAPE.OVAL)
        circ.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        add_para(circ.text_frame, num, size=17, bold=True, color=WHITE,
                 first=True, align=PP_ALIGN.CENTER, space_after=0, east=F_TITLE)
        tb = add_box(s, l + 0.82, t - 0.03, w - 0.85, 1.3)
        add_para(tb.text_frame, title, size=19, bold=True, color=DARK, first=True,
                 space_after=4, east=F_TITLE)
        add_para(tb.text_frame, desc, size=13, color=GRAY, space_after=0)


def slide_background(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '一、选题背景与意义', page=3)
    add_bullets(s, [
        (0, '校园资料现状：制度、手册、通知等分散在 PDF / Word / Excel 等多格式文件中，师生查找费时费力'),
        (0, '大模型直接问答的三大问题：'),
        (1, '幻觉——生成内容可能与事实不符'),
        (1, '知识过时——训练数据有截止日期'),
        (1, '来源不可追溯——无法核对答案依据'),
        (0, 'RAG（检索增强生成）：先检索证据再生成，回答有据可查、可点击回查原文'),
        (0, '工程条件成熟：Qdrant、bge-m3、FastAPI、Vue 3 等开源组件可直接组合落地'),
    ], M, TOP, CW, 3.1, size=15.5, gap=8)
    gaps = [
        ('格式单一', '多数系统仅支持 PDF/Word，忽略网页、表格、图片等常见资料'),
        ('不给出处', '答案无引用，无法核对，师生不敢直接采信'),
        ('强制注册', '提问前必须注册登录，校园轻量问答门槛高'),
    ]
    w = (CW - 0.4) / 3
    for i, (t_, d) in enumerate(gaps):
        add_card(s, M + i * (w + 0.2), 4.85, w, 1.9, t_, [d],
                 accent=[ORANGE, PURPLE, GREEN][i], fill=LIGHT2,
                 title_size=16, body_size=13)


def slide_goals(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '一、研究目标与建设内容', page=4)
    goals = [
        ('目标一', '带出处引用的自然语言问答', [
            '回答逐段流式输出，附来源编号',
            '引用可点击预览原文片段',
            '检索不到证据时明确拒答',
        ], BLUE),
        ('目标二', '多格式文档全流程入库', [
            '支持 10 种格式，单文件 ≤ 50MB',
            '4 种切块模板按知识库配置',
            '解析→切块→增强→向量化全自动',
        ], GREEN),
        ('目标三', '可完整运行演示的系统', [
            '管理端 + 聊天端双端闭环',
            '配置落盘、热切换，无需重启',
            '容器化依赖，单机即可跑通',
        ], ORANGE),
    ]
    w = (CW - 0.5) / 3
    for i, (tag, title, lines, color) in enumerate(goals):
        l = M + i * (w + 0.25)
        add_card(s, l, TOP + 0.15, w, 3.6, title, lines, accent=color,
                 fill=LIGHT2, title_size=17, body_size=14, numbered=None)
        tag_box = rect(s, l, TOP + 0.15, 1.3, 0.5, fill=color,
                       shape=MSO_SHAPE.ROUNDED_RECTANGLE, adj=0.3)
        tag_box.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        add_para(tag_box.text_frame, tag, size=13.5, bold=True, color=WHITE,
                 first=True, align=PP_ALIGN.CENTER, space_after=0, east=F_TITLE)
    note_bar(s, '定位：工程实现目标 —— 链路完整、可运行、可演示、可回查；不宣称检索方法层面的创新',
             5.6, h=0.62, size=14.5)


def slide_requirements(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '二、系统需求分析', page=5)
    cw2 = (CW - 0.4) / 2
    col_header(s, M, TOP, cw2, '管理端（JWT 鉴权 · 单管理员）')
    add_bullets(s, [
        (0, '认证：登录、首次登录强制改密、退出'),
        (0, '知识库管理：增删改查、切块模板配置'),
        (0, '文档管理：上传校验、入库进度、重新处理'),
        (0, '模型配置：Embedding / LLM / Rerank 多套 profile 与连通性测试'),
        (0, '日志回查：问答记录、延迟分项、检索参数'),
    ], M, TOP + 0.6, cw2, 3.3, size=14.5, gap=9)
    col_header(s, M + cw2 + 0.4, TOP, cw2, '聊天端（X-Client-ID 匿名会话）', fill=GREEN)
    add_bullets(s, [
        (0, '会话建立：匿名 client_id，首条消息自动建会话'),
        (0, '提问回答：SSE 流式输出，可多轮追问'),
        (0, '引用核对：来源列表 + 点击预览原文'),
        (0, '会话管理：列表、改名、软删除'),
        (0, '提问前校验：知识库存在、启用且有已完成文档'),
    ], M + cw2 + 0.4, TOP + 0.6, cw2, 3.3, size=14.5, gap=9)
    note_bar(s, '非功能需求：性能（分段进度、流式首字）· 安全（强散列口令、软/硬删除语义）· 易用（聊天免注册）· 可维护（配置落盘热更新）',
             5.85, h=0.62, size=14)


def slide_arch(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '三、系统总体设计 — 四层架构', page=6)
    tip = add_box(s, M, 1.32, CW, 0.35)
    add_para(tip.text_frame,
             '接口层 → 服务层 → RAG 管线层 → 外部资源层；横切模块：app_config（配置落盘）· model_swap（Provider 热替换）',
             size=14, color=GRAY, first=True, space_after=0)
    add_picture_fit(s, IMG_ARCH, M, 1.75, CW, 5.15)


def slide_components(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '三、系统设计 — 组件交互', page=7)
    tip = add_box(s, M, 1.32, CW, 0.35)
    add_para(tip.text_frame,
             '单向依赖，层次清晰；同一条 RAG 管线同时服务管理端与聊天端，避免两套检索逻辑',
             size=14, color=GRAY, first=True, space_after=0)
    add_picture_fit(s, IMG_COMP, M, 1.75, CW, 5.15)


def slide_data(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '三、系统设计 — 数据存储', page=8)
    cw2 = (CW - 0.4) / 2
    col_header(s, M, TOP, cw2, 'PostgreSQL（业务数据 · 7 张主要表）')
    add_bullets(s, [
        (0, 'admin / knowledge_bases / documents / document_chunks'),
        (0, 'conversations / qa_records / qa_sources'),
        (0, '三级归属级联删除：知识库 → 文档 → 切片；会话为软删除（is_deleted）'),
        (0, 'document_chunks.metadata 为 JSON 列，保存切块与增强信息'),
        (0, '问答链路留痕：qa_records 记录延迟分项、检索参数、token 统计'),
    ], M, TOP + 0.6, cw2, 3.4, size=14.5, gap=9)
    col_header(s, M + cw2 + 0.4, TOP, cw2, 'Qdrant（向量存储 · 单集合）', fill=PURPLE)
    add_bullets(s, [
        (0, '集合 campus_rag_chunks_v1：1024 维 · COSINE 相似度'),
        (0, '嵌入模型 bge-m3（OpenAI 兼容协议，本地服务）'),
        (0, 'Chunk ID = Qdrant Point ID：切片不可变'),
        (0, '重新处理生成新 id、写入新点，旧点一并清理，无空窗'),
        (0, '增强内容（关键词/候选问题）只拼入嵌入文本，原文保持纯净'),
    ], M + cw2 + 0.4, TOP + 0.6, cw2, 3.4, size=14.5, gap=9)
    note_bar(s, '设计要点：切片主键与向量点 ID 统一，检索命中即可精确回查原文并构造引用',
             5.95, h=0.6, size=14)


def slide_retrieval(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '三、系统设计 — 混合检索核心流程', page=9)
    cw2 = (CW - 0.4) / 2
    add_bullets(s, [
        (0, '① 问题向量化：bge-m3 输出 1024 维向量'),
        (0, '② 双路检索：向量检索 + 关键词检索（jieba 分词 + bigram，ILIKE）'),
        (0, '③ 加权融合：vector_weight = 0.7，单路命中保持原分'),
        (0, '④ 阈值过滤：similarity_threshold = 0.60（融合后统一过滤，保留关键词独有命中）'),
    ], M, TOP + 0.1, cw2, 3.4, size=14.5, gap=13)
    add_bullets(s, [
        (0, '⑤ 可选重排：交叉编码精排，失败自动回退融合序'),
        (0, '⑥ 截断：final_top_k = 5 进入生成'),
        (0, '⑦ 邻块扩展：同文档前后各取 1 块，补跨切片断文'),
        (0, '⑧ 生成：[来源 N] 上下文（≤ 4000 token）→ LLM 逐段生成；无证据则拒答'),
    ], M + cw2 + 0.4, TOP + 0.1, cw2, 3.4, size=14.5, gap=13)
    note_bar(s, 'candidate_top_k = 8 · vector_weight = 0.7 · threshold = 0.60 · final_top_k = 5 · 上下文 ≤ 4000 token（参数可在设置页热更新）',
             5.55, h=0.6, size=14)
    note_bar(s, '为什么混合：语义表述靠向量，文号/编号等精确关键词靠检索 —— 单路均有盲区，融合后互补',
             6.3, h=0.6, size=14, fill=LIGHT)


def slide_ingest(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '三、系统设计 — 文档入库链路', page=10)
    add_flow(s, ['上传\n10 种格式 ≤50MB', '解析\n按扩展名分派', '模板切块\n4 种模板',
                 'LLM 增强\n关键词/问题', '原文入库\nchunks 表',
                 '向量化\nQdrant upsert'],
             t=TOP + 0.1, box_w=1.72, box_h=1.05, gap=0.42, size=12)
    add_bullets(s, [
        (0, '切块模板：general 句级流式 / section 章节独立 / qa 问答对 / one 整篇'),
        (0, '默认 600 字/块、重叠 80；one 超嵌入上限自动回退 general'),
        (0, '增强失败降级纯正文，不阻塞入库'),
        (0, 'Worker 轮询领取（FOR UPDATE SKIP LOCKED，5 秒间隔），最多重试 3 次'),
        (0, '阶段进度 10 → 30 → 40 → 60 → 80 → 100 即刻提交，前端实时可见'),
    ], M, 3.1, CW, 3.0, size=15, gap=10)
    note_bar(s, '重新处理 = 重建切片：新切片新 id，旧切片与旧向量点一并清理，保证数据一致',
             6.25, h=0.6, size=14)


def slide_tech(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '四、关键技术实现', page=11)
    cw2 = (CW - 0.4) / 2
    add_bullets(s, [
        (0, 'SSE 流式问答：5 类事件 start / token / sources / done / error，逐段推送即时渲染'),
        (0, '双鉴权：管理端 JWT（Bearer 拦截器）；聊天端 X-Client-ID 匿名会话，无需注册'),
        (0, '并发入库：SKIP LOCKED 领取任务，阶段进度即刻提交，避免 0→100 跳变'),
        (0, '配置热替换：app-config.yaml 落盘，切换 active 时热替换运行中 Provider'),
    ], M, TOP + 0.1, cw2, 4.6, size=14.5, gap=14)
    add_bullets(s, [
        (0, '可信回答：融合后阈值过滤 + 引用回查文档名/原文；检索不到证据明确拒答'),
        (0, 'Provider 归一：base_url 不带 /v1，调用前统一补齐，四类模型一致处理'),
        (0, '前端流式渲染：markdown-it 实时解析，引用卡片 CitationCard 可点开原文预览'),
        (0, '路由守卫纯函数 guard.ts + vitest 覆盖；错误归一化统一提示'),
    ], M + cw2 + 0.4, TOP + 0.1, cw2, 4.6, size=14.5, gap=14)
    note_bar(s, '双端共用同一条 RAG 管线：检索、重排、生成逻辑只有一份，保证行为一致、易于维护',
             6.2, h=0.6, size=14)


def slide_ui(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '四、系统实现 — 功能模块', page=12)
    cw2 = (CW - 0.4) / 2
    col_header(s, M, TOP, cw2, '管理端 5 大模块')
    add_bullets(s, [
        (0, '登录认证：bcrypt 口令、首次登录强制改密'),
        (0, '知识库：CRUD + 4 种切块模板'),
        (0, '文档：多格式上传、进度条、重新处理'),
        (0, '模型配置：多 profile 增删改、启用切换、连通性测试'),
        (0, '问答日志：检索参数与延迟分项回查'),
    ], M, TOP + 0.6, cw2, 3.4, size=14.5, gap=9)
    col_header(s, M + cw2 + 0.4, TOP, cw2, '聊天端 3 大模块', fill=GREEN)
    add_bullets(s, [
        (0, '对话主界面：流式回答、Markdown 渲染、追问多轮'),
        (0, '来源与引用：来源列表 + 原文预览弹层（回查文档）'),
        (0, '会话侧栏：历史会话、改名、软删除'),
        (0, '统一壳层：TopNav + 侧栏，管理页二级导航'),
        (0, '免注册开箱即问：打开页面即可提问'),
    ], M + cw2 + 0.4, TOP + 0.6, cw2, 3.4, size=14.5, gap=9)
    note_bar(s, '运行环境：Windows 11 + Docker（PostgreSQL / Qdrant）· 后端 8001 · 前端 5173 · 嵌入服务 8080 · Qdrant 6333 · PG 5432',
             5.95, h=0.6, size=13.5)


def slide_problems(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '四、关键问题与解决', page=13)
    rows = [
        ['遇到的问题', '原因分析', '解决方案'],
        ['入库进度瞬间 0 → 100 跳变',
         '进度更新与切片写入在同一事务，提交前前端读不到中间值',
         '各阶段进度独立即刻提交（10/30/40/60/80/100）'],
        ['修改模型配置需重启服务',
         'Provider 对象随进程启动时构建，配置只在启动时读取',
         '配置落盘 app-config.yaml，切换 active 时热替换运行中 Provider'],
        ['one（整篇）模板切片超过嵌入上限',
         '单块 token 数超过嵌入服务 --ubatch-size 上限',
         '自动回退 general 模板 + 调整批上限，保证入库不中断'],
        ['后端 8000 端口被系统进程占用',
         '开发环境端口硬编码，冲突后无法启动',
         '端口配置化（改用 8001），代码不写死端口'],
    ]
    add_table(s, rows, M, TOP + 0.1, CW, 4.9,
              col_w=[3.4, 4.4, 4.43], size=13, header_size=14.5)
    note_bar(s, '共同思路：把“环境差异与运行时变化”收敛进配置与提交粒度，而不是散落在代码里',
             6.5, h=0.5, size=13.5)


def slide_test(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '五、系统测试', page=14)
    cw2 = (CW - 0.4) / 2
    col_header(s, M, TOP, cw2, '双线验证方法')
    add_bullets(s, [
        (0, '脚本线：20 个独立测试脚本 · 84 断言全部 PASS（httpx.MockTransport，不发真实请求）'),
        (0, '功能线：黑盒演示覆盖正常与异常路径'),
        (0, '17 条功能用例 TC-01 ~ TC-17，映射管理端 5 组 + 聊天端 4 组需求'),
        (0, '脚本↔用例对应：切块模板↔TC-03、配置落盘↔TC-11、热替换↔TC-10、重处理↔TC-08'),
    ], M, TOP + 0.6, cw2, 3.5, size=14, gap=11)
    col_header(s, M + cw2 + 0.4, TOP, cw2, '端到端演示闭环', fill=GREEN)
    add_bullets(s, [
        (0, '建知识库 → 上传文档 → 观察分段进度 → 重新处理'),
        (0, '匿名提问 → 流式回答 → 点击引用预览原文'),
        (0, '追问与拒答：无证据问题明确拒答，不编造'),
        (0, '会话管理（改名/删除）→ 问答日志回查 → 模型连通性测试'),
    ], M + cw2 + 0.4, TOP + 0.6, cw2, 3.5, size=14, gap=11)
    note_bar(s, '实测基准（2026-10-05）：单路首字 TTFT 均值 2.03s · 端到端 2.32s · 并发 5/5 成功 · 检索 562ms / 生成 1692ms · 小文档入库 4.3~6.5s',
             6.15, h=0.6, size=13.5, fill=RGBColor(0xE9, 0xF4, 0xEC), color=RGBColor(0x2F, 0x6B, 0x45))


def slide_summary(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, '六、总结与展望', page=15)
    w = (CW - 0.5) / 3
    add_card(s, M, TOP, w, 3.3, '目标达成', [
        '带出处引用问答 + 无证据拒答',
        '10 格式 / 4 模板全流程入库',
        '双端闭环、可运行、可演示',
    ], accent=BLUE, fill=LIGHT2, title_size=17, body_size=14)
    add_card(s, M + w + 0.25, TOP, w, 3.3, '现存不足', [
        '大规模语料与长期运行验证不足',
        '检索质量缺少标注集与基线对比',
        '单管理员 + 匿名模型，权限较简单',
    ], accent=ORANGE, fill=LIGHT2, title_size=17, body_size=14)
    add_card(s, M + 2 * (w + 0.25), TOP, w, 3.3, '后续方向', [
        '补充检索质量对比实验',
        '多角色权限体系',
        '知识库运营：审核、命中统计、反馈回流',
    ], accent=GREEN, fill=LIGHT2, title_size=17, body_size=14)
    ref = add_box(s, M, 5.15, CW, 1.6)
    add_para(ref.text_frame, '主要参考文献', size=14, bold=True, color=DARK,
             first=True, space_after=6, east=F_TITLE)
    for t_ in [
        '[2] LEWIS P, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[C]//NeurIPS 2020.',
        '[1] GAO Y, et al. Retrieval-augmented generation for large language models: a survey[EB/OL]. arXiv:2312.10997, 2024.',
        '[6] KARPUKHIN V, et al. Dense passage retrieval for open-domain question answering[C]//EMNLP 2020.',
        '[5] REIMERS N, GUREVYCH I. Sentence-BERT: sentence embeddings using siamese BERT-networks[C]//EMNLP 2019.',
    ]:
        add_para(ref.text_frame, t_, size=11.5, color=GRAY, space_after=3,
                 line=1.1, east=F_BODY)
    end = add_box(s, M, 6.55, CW, 0.45)
    add_para(end.text_frame, '恳请各位老师批评指正，谢谢！', size=17, bold=True,
             color=BLUE, first=True, align=PP_ALIGN.CENTER, space_after=0,
             east=F_TITLE)


SLIDES = [slide_cover, slide_toc, slide_background, slide_goals, slide_requirements,
          slide_arch, slide_components, slide_data, slide_retrieval, slide_ingest,
          slide_tech, slide_ui, slide_problems, slide_test, slide_summary]


def main():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    for fn in SLIDES:
        fn(prs)
    prs.save(OUT)
    print('已生成: %s（%d 页）' % (OUT, len(prs.slides._sldIdLst)))


if __name__ == '__main__':
    main()
