# -*- coding: utf-8 -*-
"""绘制核心用例的活动流程图：图3-2 文档上传入库、图3-3 匿名提问回答。

黑白矢量，主流程竖向排列，异常分支放右侧，避免连线穿越主流程。
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch, FancyArrowPatch, Polygon

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "path"

MAIN_X = 36
MAIN_W = 54
SIDE_X = 80
SIDE_W = 30


def box(cx, cy, text, w=MAIN_W, h=7.0, fs=10.2):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.25,rounding_size=1.2",
                                fc="white", ec="black", lw=1.1, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color="black", linespacing=1.35, zorder=3)


def diamond(cx, cy, text, w=42, h=11.5, fs=10.0):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                          (cx, cy - h / 2), (cx - w / 2, cy)],
                         closed=True, fc="white", ec="black", lw=1.1, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            color="black", zorder=3)


def oval(cx, cy, text, w=14, h=5.5, fs=10.0):
    ax.add_patch(Ellipse((cx, cy), w, h, fc="white", ec="black", lw=1.1, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color="black", zorder=3)


def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None, dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, lw=1.2, color="black",
                                 linestyle="--" if dashed else "solid", zorder=1))
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2,
                ly if ly is not None else (y1 + y2) / 2,
                label, ha="center", va="center", fontsize=9.0, color="black",
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none"), zorder=4)


def save(name):
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "chapters", "images", name)
    plt.tight_layout(pad=0.2)
    plt.savefig(base + ".png", bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.savefig(base + ".svg", bbox_inches="tight", pad_inches=0.04, facecolor="white")
    print("已生成:", base)


# ── 图3-2 管理员上传文档并入库 ──
fig, ax = plt.subplots(figsize=(5.9, 6.8), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(-10, 102)
ax.axis("off")

oval(MAIN_X, 96, "开始")
box(MAIN_X, 85, "管理员选择知识库并上传文件")
diamond(MAIN_X, 72, "格式与大小通过?")
box(SIDE_X, 72, "返回错误提示", w=SIDE_W, h=7, fs=9.2)
box(MAIN_X, 59, "保存原文件，建立待处理记录")
box(MAIN_X, 49, "后台任务领取文档")
box(MAIN_X, 39, "解析、切块、可选增强、向量化")
box(MAIN_X, 29, "写入切片与向量，更新进度")
diamond(MAIN_X, 16, "处理成功?")
box(SIDE_X, 16, "记录失败，允许重新处理", w=SIDE_W, h=7, fs=9.0)
box(MAIN_X, 3, "文档状态置为已完成")
oval(MAIN_X, -7, "结束")

arrow(MAIN_X, 93.2, MAIN_X, 88.5)
arrow(MAIN_X, 81.5, MAIN_X, 77.8)
arrow(MAIN_X, 66.2, MAIN_X, 62.5, "是", MAIN_X + 2.6, 64.5)
arrow(MAIN_X + 21, 72, SIDE_X - SIDE_W / 2, 72, "否", 60, 74.2, dashed=True)
arrow(MAIN_X, 55.5, MAIN_X, 52.5)
arrow(MAIN_X, 45.5, MAIN_X, 42.5)
arrow(MAIN_X, 35.5, MAIN_X, 32.5)
arrow(MAIN_X, 25.5, MAIN_X, 21.8)
arrow(MAIN_X, 10.2, MAIN_X, 6.5, "是", MAIN_X + 2.6, 8.6)
arrow(MAIN_X + 21, 16, SIDE_X - SIDE_W / 2, 16, "否", 60, 18.2, dashed=True)
arrow(MAIN_X, -0.5, MAIN_X, -4.2)

save("图3-2-管理员上传文档并入库流程")

# ── 图3-3 匿名用户提问并获得带引用回答 ──
fig, ax = plt.subplots(figsize=(5.9, 6.4), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(-8, 102)
ax.axis("off")

oval(MAIN_X, 96, "开始")
box(MAIN_X, 85, "用户输入问题并提交")
diamond(MAIN_X, 72, "知识库可用?")
box(SIDE_X, 72, "返回错误提示", w=SIDE_W, h=7, fs=9.2)
box(MAIN_X, 59, "问题向量化，执行双路检索")
box(MAIN_X, 49, "融合、阈值过滤、可选重排、邻块扩展")
diamond(MAIN_X, 35, "有候选达到阈值?")
box(SIDE_X, 35, "返回拒答", w=SIDE_W, h=7, fs=9.2)
box(MAIN_X, 21, "拼装上下文，调用生成模型")
box(MAIN_X, 10, "流式返回回答与来源引用")
oval(MAIN_X, -2, "结束")

arrow(MAIN_X, 93.2, MAIN_X, 88.5)
arrow(MAIN_X, 81.5, MAIN_X, 77.8)
arrow(MAIN_X, 66.2, MAIN_X, 62.5, "是", MAIN_X + 2.6, 64.5)
arrow(MAIN_X + 21, 72, SIDE_X - SIDE_W / 2, 72, "否", 60, 74.2, dashed=True)
arrow(MAIN_X, 55.5, MAIN_X, 52.5)
arrow(MAIN_X, 45.5, MAIN_X, 40.8)
arrow(MAIN_X, 29.2, MAIN_X, 24.5, "是", MAIN_X + 2.6, 26.8)
arrow(MAIN_X + 21, 35, SIDE_X - SIDE_W / 2, 35, "否", 60, 37.2, dashed=True)
arrow(MAIN_X, 17.5, MAIN_X, 13.5)
arrow(MAIN_X, 6.5, MAIN_X, 0.8)

save("图3-3-匿名用户提问并获得带引用回答流程")
