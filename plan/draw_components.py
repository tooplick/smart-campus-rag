# -*- coding: utf-8 -*-
"""绘制 图4-2 系统组件与交互关系 → chapters/images/图4-2-组件交互图.png/.svg

黑白矢量版：左右四列布局，放大字号，去掉底部小注与多余留白。
协议全称在正文说明，图中只保留短标签，避免标签压住框体。
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "path"

fig, ax = plt.subplots(figsize=(6.4, 4.1), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(18, 88)
ax.axis("off")

BOX_WHITE = "#FFFFFF"
BOX_LIGHT = "#E6E6E6"
BOX_MID = "#EDEDED"
EDGE = "#000000"
TEXT = "#000000"


def box(x, y, w, h, text, fc, fs=9.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0",
                                fc=fc, ec=EDGE, lw=1.1, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=TEXT, linespacing=1.5, zorder=3)


def edge(x1, y1, x2, y2, label, lx, ly, fs=7.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=11, lw=1.2, color=EDGE, zorder=4))
    if label:
        ax.text(lx, ly, label, ha="center", va="center", fontsize=fs, color=TEXT,
                linespacing=1.2, zorder=5,
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none"))


# ── 用户 ──
box(0, 62, 15, 11, "管理员用户", BOX_LIGHT, fs=9.2)
box(0, 27, 15, 11, "师生用户\n(匿名)", BOX_LIGHT, fs=9.2)

# ── 前端 ──
box(21, 32, 18, 32, "前端(Vue 3)\n\n管理端页面\n聊天端页面\n\nSSE 流式渲染\n引用预览",
    BOX_WHITE, fs=8.8)

# ── 后端 ──
box(47, 20, 21, 62,
    "后端(FastAPI)\n\n接口层\n统一响应·鉴权\n\n服务层\n业务·Worker\n\nRAG 管线\n检索·融合·生成",
    BOX_LIGHT, fs=8.6)

# ── 外部服务 ──
box(82, 77, 17, 9, "PostgreSQL\n业务与切片数据", BOX_MID, fs=8.2)
box(82, 65, 17, 9, "Qdrant\n向量集合(1024 维)", BOX_MID, fs=8.2)
box(82, 53, 17, 9, "LLM 服务\n生成·视觉", BOX_MID, fs=8.4)
box(82, 41, 17, 9, "嵌入服务\nbge-m3(1024 维)", BOX_MID, fs=8.2)
box(82, 29, 17, 9, "本地文件系统\nuploads/", BOX_MID, fs=8.4)

# ── 连线（标签用短名，协议全称在正文说明） ──
edge(15, 67, 21, 58, "管理操作", 18, 64, fs=6.8)
edge(15, 33, 21, 42, "HTTP/\nSSE", 18, 37, fs=6.8)
edge(39, 48, 47, 48, "HTTP\nAPI", 43, 52, fs=6.8)

edge(68, 78, 82, 81, "SQL", 75, 84.5, fs=7.0)
edge(68, 68, 82, 69, "Qdrant", 75, 72, fs=7.0)
edge(68, 58, 82, 57, "OpenAI API", 75, 61.5, fs=6.6)
edge(68, 46, 82, 45, "OpenAI API", 75, 49.5, fs=6.6)
edge(68, 36, 82, 33, "文件读写", 75, 35, fs=6.8)

plt.tight_layout(pad=0.2)
base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "chapters", "images", "图4-2-组件交互图")
os.makedirs(os.path.dirname(base), exist_ok=True)
plt.savefig(base + ".png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
plt.savefig(base + ".svg", bbox_inches="tight", pad_inches=0.03, facecolor="white")
print("已生成:", base + ".png")
print("已生成:", base + ".svg")
