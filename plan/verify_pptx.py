# -*- coding: utf-8 -*-
"""自检 plan/build_pptx.py 的产物(仿 verify_docx.py 模式)。
- 用法:uv run python plan/verify_pptx.py
- 断言:文件存在 / 15 页 / 封面题目 / 每页标题 / 2 张架构图 / 中文东亚字体已写入 / 页码
"""
import os
import sys
from pptx import Presentation
from pptx.oxml.ns import qn

OUT = r'c:\Users\id654\Desktop\毕设答辩PPT_唐星星.pptx'

EXPECTED_TITLES = [
    '',                      # 封面无页标题
    '汇报提纲',
    '一、选题背景与意义',
    '一、研究目标与建设内容',
    '二、系统需求分析',
    '三、系统总体设计 — 四层架构',
    '三、系统设计 — 组件交互',
    '三、系统设计 — 数据存储',
    '三、系统设计 — 混合检索核心流程',
    '三、系统设计 — 文档入库链路',
    '四、关键技术实现',
    '四、系统实现 — 功能模块',
    '四、关键问题与解决',
    '五、系统测试',
    '六、总结与展望',
]

KEYWORDS = ['RAG', '校园知识库', '唐星星', '瞿梦菊']  # 封面必含
BODY_KEYWORDS = ['混合检索', 'Qdrant', 'SSE', 'TC-01']  # 正文必含(跨页汇总)


def slide_text(slide):
    parts = []
    for shp in slide.shapes:
        if shp.has_text_frame:
            parts.append(shp.text_frame.text)
        if getattr(shp, 'has_table', False) and shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    parts.append(cell.text)
    return '\n'.join(parts)


def check(cond, msg, errors):
    if cond:
        print('  [PASS] %s' % msg)
    else:
        print('  [FAIL] %s' % msg)
        errors.append(msg)


def main():
    errors = []
    print('== 自检开始 ==')
    if not os.path.exists(OUT):
        print('[FAIL] 文件不存在: %s(先运行 build_pptx.py)' % OUT)
        sys.exit(1)
    prs = Presentation(OUT)
    texts = [slide_text(s) for s in prs.slides]

    print('-- 结构 --')
    check(len(prs.slides) == 15, '页数 = 15(实际 %d)' % len(prs.slides), errors)
    check(abs(prs.slide_width.inches - 13.333) < 0.01 and
          abs(prs.slide_height.inches - 7.5) < 0.01,
          '画幅 16:9(%.3f x %.3f in)' % (prs.slide_width.inches, prs.slide_height.inches),
          errors)

    print('-- 封面 --')
    for kw in KEYWORDS:
        check(kw in texts[0], '封面含 "%s"' % kw, errors)

    print('-- 每页标题 --')
    for i, expect in enumerate(EXPECTED_TITLES):
        if not expect:
            continue
        check(expect in texts[i], '第 %d 页标题 "%s"' % (i + 1, expect), errors)

    print('-- 内容关键词(跨页汇总) --')
    all_text = '\n'.join(texts)
    for kw in BODY_KEYWORDS:
        check(kw in all_text, '正文含 "%s"' % kw, errors)

    print('-- 配图 --')
    pic_slides = []
    for i, s in enumerate(prs.slides):
        for shp in s.shapes:
            if shp.shape_type == 13:  # PICTURE
                pic_slides.append(i + 1)
                break
    check(pic_slides == [6, 7], '架构图位于第 6、7 页(实际 %s)' % pic_slides, errors)

    print('-- 字体(东亚字体 a:ea) --')
    ea_types, title_ea = set(), set()
    for i, s in enumerate(prs.slides):
        for shp in s.shapes:
            if not shp.has_text_frame:
                continue
            for p in shp.text_frame.paragraphs:
                for r in p.runs:
                    rPr = r._r.find(qn('a:rPr'))
                    if rPr is None:
                        continue
                    ea = rPr.find(qn('a:ea'))
                    if ea is not None:
                        ea_types.add(ea.get('typeface'))
                        if i == 0:
                            title_ea.add(ea.get('typeface'))
    check('宋体' in ea_types, '正文东亚字体含 宋体(实际 %s)' % sorted(ea_types), errors)
    check('黑体' in ea_types, '标题东亚字体含 黑体(实际 %s)' % sorted(ea_types), errors)

    print('-- 页码 --')
    for i in range(1, 15):
        if ('%02d / 15' % (i + 1)) not in texts[i]:
            check(False, '第 %d 页页码' % (i + 1), errors)
            break
    else:
        check(True, '第 2-15 页页码齐全', errors)

    print('== 结果: %s ==' % ('全部通过' if not errors else '%d 项失败' % len(errors)))
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
