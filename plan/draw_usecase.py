# -*- coding: utf-8 -*-
"""绘制 图3-1 系统用例图 → chapters/images/图3-1-系统用例图.png

UML 用例图约定:参与者用小人,用例用椭圆,系统边界用矩形,
关联用实线,«include»/«extend» 用带箭头的虚线并标注构造型。
版式:管理侧与聊天侧各占一列,包含/扩展关系放在同列相邻两行,避免连线穿越其他用例。
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, FancyArrowPatch

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
# 文字转路径，保证 SVG 在 Word 中不依赖本机字体
plt.rcParams['svg.fonttype'] = 'path'

# 按最终印刷宽度出图:正文版心约 15cm,figsize 取 5.9in(≈15cm),字号即为实际磅值
fig, ax = plt.subplots(figsize=(5.9, 4.45), dpi=320)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

LINE = '#000000'
TEXT = '#000000'
REL = '#000000'
REL_TXT = '#000000'

# ── 系统边界 ──
bx, by, bw, bh = 21, 4, 58, 92
ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle='round,pad=0,rounding_size=1.8',
                            fc='white', ec='#000000', lw=1.4, zorder=1))
ax.text(bx + bw / 2, by + bh - 4.4, '智能校园知识库系统', ha='center', va='center',
        fontsize=11.5, fontweight='bold', color='#000000', zorder=3)


def actor(x, y, label, s=1.0):
    """UML 参与者小人:头、躯干、双臂、双腿 + 标签。"""
    ax.add_patch(Ellipse((x, y + 6.2 * s), 3.0 * s, 3.6 * s, fc='white', ec=TEXT, lw=1.4, zorder=4))
    ax.plot([x, x], [y + 4.4 * s, y - 1.6 * s], color=TEXT, lw=1.4, zorder=4)
    ax.plot([x - 3.0 * s, x + 3.0 * s], [y + 2.2 * s, y + 2.2 * s], color=TEXT, lw=1.4, zorder=4)
    ax.plot([x, x - 2.6 * s], [y - 1.6 * s, y - 6.4 * s], color=TEXT, lw=1.4, zorder=4)
    ax.plot([x, x + 2.6 * s], [y - 1.6 * s, y - 6.4 * s], color=TEXT, lw=1.4, zorder=4)
    ax.text(x, y - 9.8 * s, label, ha='center', va='center', fontsize=10.5,
            fontweight='bold', color=TEXT, zorder=5)


def uc(cx, cy, text, core=False, sub=False, w=25.0, h=8.6):
    """用例椭圆:核心用例加粗描边与文字,扩展用例用虚线边框。"""
    lw = 1.9 if core else 1.2
    ls = '--' if sub else 'solid'
    ax.add_patch(Ellipse((cx, cy), w, h, fc='white', ec='#000000', lw=lw,
                         linestyle=ls, zorder=3))
    ax.text(cx, cy, text, ha='center', va='center',
            fontsize=8.6 if core else 9.2, color='#000000',
            fontweight='bold' if core else 'normal', linespacing=1.4, zorder=4)


def assoc(x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color=LINE, lw=1.0, solid_capstyle='round', zorder=2)


def rel(x1, y1, x2, y2, label, lx, ly):
    """«include» / «extend»:带箭头的虚线。"""
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=12,
                                 lw=1.2, color=REL, linestyle=(0, (5, 3)), zorder=2))
    ax.text(lx, ly, label, ha='center', va='center', fontsize=8.2, color=REL_TXT, zorder=6)


AX, CX = 34.0, 66.0     # 管理侧 / 聊天侧用例圆心横坐标
W, H = 25.0, 8.6
R = (84, 70, 56, 42, 28)   # 行高:两侧主用例共用

# ── 管理侧用例 ──
uc(AX, R[0], '登录与首次改密', w=W, h=H)
uc(AX, R[1], '知识库管理', w=W, h=H)
uc(AX, R[2], '文档管理', w=W, h=H)
uc(AX, R[3], '文档上传与入库', core=True, w=W, h=H)     # 由「文档管理」包含
uc(AX, R[4], '模型配置与连通测试', w=W, h=H)
uc(AX, 14, '问答日志查看', w=W, h=H)

# ── 聊天侧用例 ──
uc(CX, R[0], '匿名会话建立', w=W, h=H)
uc(CX, R[1], '提问并获得带引用回答', core=True, w=W, h=H)
uc(CX, R[2], '无证据拒答', sub=True, w=W, h=H)          # 扩展「提问并获得带引用回答」
uc(CX, R[3], '引用核对与原文预览', w=W, h=H)
uc(CX, R[4], '会话管理', w=W, h=H)

# ── 参与者 ──
actor(9.0, 56, '管理员', s=1.0)
actor(92.0, 70, '匿名师生', s=1.0)

# ── 关联关系:参与者与用例(包含/扩展目标不单独关联) ──
for y in (R[0], R[1], R[2], R[4], 14):
    assoc(12.2, 56, AX - W / 2 - 0.6, y)
for y in (R[0], R[1], R[3], R[4]):
    assoc(88.8, 70, CX + W / 2 + 0.6, y)

# ── 包含与扩展:同列相邻两行,连线不穿越其他用例 ──
rel(AX, R[2] - H / 2 - 0.5, AX, R[3] + H / 2 + 0.5, '«include»', AX + 7.4, (R[2] + R[3]) / 2)
rel(CX, R[2] + H / 2 + 0.5, CX, R[1] - H / 2 - 0.5, '«extend»', CX + 7.4, (R[1] + R[2]) / 2)

plt.tight_layout(pad=0.3)
base = r'd:\Github\smart-campus-rag\chapters\images\图3-1-系统用例图'
os.makedirs(os.path.dirname(base), exist_ok=True)
plt.savefig(base + '.png', bbox_inches='tight', facecolor='white')
plt.savefig(base + '.svg', bbox_inches='tight', facecolor='white')
print('已生成:', base + '.png')
print('已生成:', base + '.svg')
