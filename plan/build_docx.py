# -*- coding: utf-8 -*-
"""把 chapters/*.md 按苏州高博职业学院格式范本生成 Word 文档。
- 基底:用户已填好的封面 docx(1-毕业设计（论文）封面_唐星星.docx)
- 正文:小四宋体固定24磅、首行缩进2字符;标题黑体(章三号居中/节四号/小节小四)
- 摘要:五号楷体固定18磅;Abstract: Times New Roman;参考文献:五号楷体固定18磅
- 表格:五号宋体、Table Grid;代码:9pt Courier New(中文宋体9)
- 半角标点在中文语境自动转全角(代码块内不转)
"""
import re
import os
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVER = os.path.join(BASE, '毕业设计论文_唐星星.docx')
OUT = os.path.join(BASE, '毕业设计论文_唐星星.docx')

CHAPTERS = ['00_摘要', '01_绪论', '02_相关技术与理论', '03_系统需求分析',
            '04_系统设计', '05_系统实现', '06_系统测试', '07_结论与展望',
            '08_致谢', '09_参考文献']


def is_cjk(c):
    return bool(c) and ('\u4e00' <= c <= '\u9fff' or c in '、。；：？！《》【】（）“”‘’…—·')


def to_fullwidth(t):
    out = []
    n = len(t)
    for i, ch in enumerate(t):
        prev = t[i - 1] if i > 0 else ''
        nxt = t[i + 1] if i + 1 < n else ''
        if ch in ',;?!' and (is_cjk(prev) or is_cjk(nxt)):
            ch = {',': '，', ';': '；', '?': '？', '!': '！'}[ch]
        elif ch == ':' and (is_cjk(prev) or prev in '）)'):
            ch = '：'
        elif ch == '(' and is_cjk(nxt):
            ch = '（'
        elif ch == ')' and is_cjk(prev):
            ch = '）'
        out.append(ch)
    return ''.join(out)


def set_font(run, east='宋体', size=12, bold=False, ascii_font=None):
    ascii_font = ascii_font or east
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:eastAsia'), east)
    rFonts.set(qn('w:ascii'), ascii_font)
    rFonts.set(qn('w:hAnsi'), ascii_font)


def fmt_para(p, spacing=24, indent_chars=None, size=12, align=None,
             before=0, after=0, rule=WD_LINE_SPACING.EXACTLY):
    pf = p.paragraph_format
    pf.line_spacing_rule = rule
    pf.line_spacing = Pt(spacing)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if indent_chars:
        pf.first_line_indent = Pt(size * indent_chars)
    if align is not None:
        p.alignment = align
    return p


def add_runs(p, text, east='宋体', size=12, ascii_font='Times New Roman', bold=False):
    """正文行内解析:`code` 用 Courier,其余按中英文字体。"""
    for part in re.split(r'(`[^`]+`)', text):
        if not part:
            continue
        if part.startswith('`') and part.endswith('`') and len(part) > 2:
            r = p.add_run(part[1:-1])
            set_font(r, east='宋体', size=size, ascii_font='Consolas', bold=bold)
        else:
            r = p.add_run(part)
            set_font(r, east=east, size=size, ascii_font=ascii_font, bold=bold)


def body(doc, text, size=12, east='宋体', spacing=24, align=None, before=0, after=0):
    p = doc.add_paragraph()
    fmt_para(p, spacing=spacing, indent_chars=2 if align is None else None,
             size=size, align=align, before=before, after=after)
    add_runs(p, to_fullwidth(text), east=east, size=size)
    return p


def ensure_heading_styles(doc):
    """封面文档仅含 Normal/Footer/Header,需创建 Heading 1-3 供目录域抓取。"""
    from docx.enum.style import WD_STYLE_TYPE
    names = [s.name for s in doc.styles]
    for lvl in (1, 2, 3):
        name = f'Heading {lvl}'
        if name in names:
            continue
        st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles['Normal']
        pPr = st.element.get_or_add_pPr()
        outline = OxmlElement('w:outlineLvl')
        outline.set(qn('w:val'), str(lvl - 1))
        pPr.append(outline)
        qf = OxmlElement('w:qFormat')
        st.element.append(qf)


def set_outline(p, level):
    """给段落写入大纲级别,TOC \\u 按大纲级别抓取(样式的双保险)。"""
    pPr = p._p.get_or_add_pPr()
    outline = OxmlElement('w:outlineLvl')
    outline.set(qn('w:val'), str(level - 1))
    pPr.append(outline)


def heading(doc, text, level):
    """level1 黑体三号居中(章);2 黑体四号;3 黑体小四加粗。"""
    style = f'Heading {level}'
    # 先查样式是否存在再建段,避免 add_paragraph 内部赋样式失败留下孤儿空段
    style_names = {s.name for s in doc.styles}
    if style in style_names:
        p = doc.add_paragraph(style=style)
    else:
        p = doc.add_paragraph()
    size = {1: 16, 2: 14, 3: 12}[level]
    align = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    before = {1: 0, 2: 12, 3: 6}[level]
    after = {1: 12, 2: 6, 3: 3}[level]
    fmt_para(p, spacing=max(24, size + 6), size=size, align=align, before=before, after=after)
    if level == 1:
        p.paragraph_format.page_break_before = True
    set_outline(p, level)
    r = p.add_run(to_fullwidth(text))
    set_font(r, east='黑体', size=size, ascii_font='Times New Roman', bold=(level == 3))
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    fmt_para(p, spacing=18, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=3)
    r = p.add_run(to_fullwidth(text))
    set_font(r, east='宋体', size=10.5)
    return p


def code_line(doc, text):
    p = doc.add_paragraph()
    fmt_para(p, spacing=14, rule=WD_LINE_SPACING.SINGLE, size=9)
    p.paragraph_format.left_indent = Cm(0.5)
    r = p.add_run(text)
    set_font(r, east='宋体', size=9, ascii_font='Courier New')
    return p


def add_table(doc, rows):
    ncols = max(len(r) for r in rows)
    # 注意:必须只创建一次表。style 赋值失败时不得重建(否则会留下一张空表)
    table = doc.add_table(rows=len(rows), cols=ncols)
    try:
        table.style = 'Table Grid'
    except KeyError:
        _borders(table)  # 封面文档无 Table Grid 样式,改为手写边框
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = table.cell(i, j)
            txt = row[j] if j < len(row) else ''
            p = cell.paragraphs[0]
            fmt_para(p, spacing=14, rule=WD_LINE_SPACING.SINGLE, size=10.5,
                     align=WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT)
            r = p.add_run(to_fullwidth(txt))
            set_font(r, east='宋体', size=10.5, bold=(i == 0))
    sp = doc.add_paragraph()
    fmt_para(sp, spacing=6, rule=WD_LINE_SPACING.SINGLE, size=6)
    return table


def _borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:color'), '000000')
        borders.append(el)
    tblPr.append(borders)


def page_number_footer(doc):
    for sec in doc.sections:
        sec.different_first_page_header_footer = True
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        set_font(r, east='宋体', size=10.5)
        f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
        it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = 'PAGE'
        f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end')
        r._r.append(f1); r._r.append(it); r._r.append(f2)


def add_toc(doc):
    p_title = doc.add_paragraph()
    p_title.paragraph_format.page_break_before = True
    fmt_para(p_title, spacing=24, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12)
    r = p_title.add_run('目  录')
    set_font(r, east='黑体', size=16, ascii_font='Times New Roman')

    # 标准 TOC 域:每个域元素独立成 run,Word 才能识别并更新
    p = doc.add_paragraph()
    fmt_para(p, spacing=24, size=12)

    r1 = p.add_run()
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    fld_begin.set(qn('w:dirty'), 'true')  # 打开时提示/自动更新
    r1._r.append(fld_begin)

    r2 = p.add_run()
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = r' TOC \o "1-3" \h \z \u '
    r2._r.append(instr)

    r3 = p.add_run()
    fld_sep = OxmlElement('w:fldChar')
    fld_sep.set(qn('w:fldCharType'), 'separate')
    r3._r.append(fld_sep)

    # 目录域由 Word 打开时自动更新,不在正文中写入操作提示。

    r5 = p.add_run()
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    r5._r.append(fld_end)


def enable_update_fields(doc):
    """settings.xml 写入 updateFields,Word 打开文档时自动更新目录等域。"""
    try:
        settings = doc.settings.element
    except Exception:
        return
    for el in settings.findall(qn('w:updateFields')):
        settings.remove(el)
    upd = OxmlElement('w:updateFields')
    upd.set(qn('w:val'), 'true')
    settings.append(upd)


def special_title(doc, text, page_break=True):
    p = doc.add_paragraph()
    fmt_para(p, spacing=24, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12)
    if page_break:
        p.paragraph_format.page_break_before = True
    r = p.add_run(text)
    set_font(r, east='黑体', size=16, ascii_font='Times New Roman')
    return p


def render_abstract(doc, raw):
    lines = [l for l in raw.split('\n') if l.strip() and not l.strip().startswith('<!--')]
    zh_body, zh_kw, en_body, en_kw = '', '', '', ''
    mode = 'zh'
    for l in lines:
        s = l.strip()
        if s.startswith('# 中'):
            mode = 'zh'; continue
        if s.startswith('# Abstract'):
            mode = 'en'; continue
        if s.startswith('关键词'):
            zh_kw = s; continue
        if s.lower().startswith('keywords'):
            en_kw = s; continue
        if mode == 'zh' and not zh_body:
            zh_body = s
        elif mode == 'en' and not en_body:
            en_body = s

    special_title(doc, '中 文 摘 要')
    p = body(doc, zh_body, size=10.5, east='楷体', spacing=18)
    p2 = doc.add_paragraph()
    fmt_para(p2, spacing=18, size=10.5, before=12)
    add_runs(p2, to_fullwidth(zh_kw), east='楷体', size=10.5)

    special_title(doc, 'Abstract')
    p3 = doc.add_paragraph()
    fmt_para(p3, spacing=18, size=10.5, indent_chars=2)
    r = p3.add_run(en_body)
    set_font(r, east='Times New Roman', size=10.5, ascii_font='Times New Roman')
    p4 = doc.add_paragraph()
    fmt_para(p4, spacing=18, size=10.5, before=12)
    label, _, rest = en_kw.partition(':')
    r1 = p4.add_run(label + ': ')
    set_font(r1, east='Times New Roman', size=10.5, bold=True)
    r2 = p4.add_run(rest.strip())
    set_font(r2, east='Times New Roman', size=10.5)


def render_references(doc, raw):
    heading(doc, '参 考 文 献', 1)
    for l in raw.split('\n'):
        s = l.strip()
        if not s or s.startswith('#') or s.startswith('>') or s.startswith('<!--'):
            continue
        p = doc.add_paragraph()
        fmt_para(p, spacing=18, size=10.5)
        add_runs(p, to_fullwidth(s), east='楷体', size=10.5, ascii_font='Times New Roman')


def render_chapter(doc, text):
    lines = text.split('\n')
    i = 0
    in_code = False
    code_buf = []
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith('```'):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                for cl in code_buf:
                    code_line(doc, cl)
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        if not s or s.startswith('<!--'):
            i += 1; continue
        if s.startswith('>'):
            i += 1; continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                add_table(doc, rows)
            continue
        if s.startswith('$$'):
            f = s.strip('$').strip()
            p = doc.add_paragraph()
            fmt_para(p, spacing=24, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
            r = p.add_run(f)
            set_font(r, east='宋体', size=12, ascii_font='Cambria Math')
            i += 1; continue
        m_img = re.match(r'^!\[(.*?)\]\((.*?)\)$', s)
        if m_img:
            img_ref = m_img.group(2).replace('/', os.sep)
            img_path = os.path.normpath(os.path.join(BASE, 'chapters', img_ref))
            p = doc.add_paragraph()
            fmt_para(p, spacing=18, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
                     before=6, after=0, rule=WD_LINE_SPACING.SINGLE)
            # 行距必须是单倍:写成固定值(如 18 磅)会把内联图片裁成一条线
            spacing = p._p.get_or_add_pPr().find(qn('w:spacing'))
            if spacing is not None:
                for attr in ('w:line', 'w:lineRule'):
                    if spacing.get(qn(attr)) is not None:
                        del spacing.attrib[qn(attr)]
            run = p.add_run()
            run.add_picture(img_path, width=Cm(15))
            i += 1; continue
        if s.startswith('#### '):
            p = doc.add_paragraph()
            fmt_para(p, spacing=24, size=12, before=6, after=0)
            r = p.add_run(to_fullwidth(s[5:]))
            set_font(r, east='黑体', size=12, ascii_font='Times New Roman', bold=True)
            i += 1; continue
        m = re.match(r'^(#{1,3})\s+(.*)$', s)
        if m:
            heading(doc, m.group(2), len(m.group(1)))
            i += 1; continue
        if re.match(r'^[图表]\d+-\d+', s) and len(s) < 60:
            caption(doc, s)
            i += 1; continue
        body(doc, s)
        i += 1


def keep_cover_only(doc):
    """保留封面页,删除当前文档中旧的摘要、正文、表格和图片。"""
    body = doc.element.body
    paragraphs = doc.paragraphs
    if len(paragraphs) < 21 or '学生毕业设计' not in paragraphs[5].text:
        raise ValueError('未识别到预期封面,为避免误删未执行重建')
    cover_end = paragraphs[20]._p
    child = cover_end.getnext()
    while child is not None and child.tag != qn('w:sectPr'):
        next_child = child.getnext()
        body.remove(child)
        child = next_child


def main():
    try:
        doc = Document(COVER)
    except Exception as e:
        print('封面加载失败,使用空白文档:', e)
        doc = Document()
    ensure_heading_styles(doc)
    keep_cover_only(doc)
    # 封面后分页
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)

    for name in CHAPTERS:
        raw = open(rf'{BASE}\chapters\{name}.md', encoding='utf-8').read()
        print('渲染', name)
        if name == '00_摘要':
            render_abstract(doc, raw)
            add_toc(doc)  # 目录:摘要之后、正文之前
        elif name == '09_参考文献':
            render_references(doc, raw)
        else:
            render_chapter(doc, raw)

    page_number_footer(doc)
    enable_update_fields(doc)
    doc.core_properties.title = '基于RAG的智能校园知识库系统的设计与实现'
    doc.core_properties.author = '唐星星'
    doc.save(OUT)
    d2 = Document(OUT)
    print('已生成:', OUT)
    print('段落数:', len(d2.paragraphs), '| 表格数:', len(d2.tables))


if __name__ == '__main__':
    main()
