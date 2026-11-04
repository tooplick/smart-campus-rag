# -*- coding: utf-8 -*-
"""绘制 图4-1 系统总体架构图 → chapters/images/图4-1-总体架构图.png/.svg

黑白矢量版：客户端/前端在左侧，后端四层（接口、服务、RAG 管线、资源）纵向排列，
横切模块在右侧。与正文“四层结构”的表述一致。
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "path"

fig, ax = plt.subplots(figsize=(6.4, 4.9), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(4, 84)
ax.axis("off")

BAND = "#F2F2F2"
BOX_WHITE = "#FFFFFF"
BOX_LIGHT = "#E6E6E6"
EDGE = "#000000"
TEXT = "#000000"


def box(x, y, w, h, text, fc=BOX_WHITE, fs=8.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.7",
                                fc=fc, ec=EDGE, lw=1.0, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=TEXT, linespacing=1.3, zorder=3)


def layer(y, h, label):
    ax.add_patch(FancyBboxPatch((46, y), 36, h, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=BAND, ec=EDGE, lw=0.9, zorder=1))
    ax.text(48.6, y + h / 2, label, ha="center", va="center", fontsize=8.0,
            fontweight="bold", color=TEXT, rotation=90, zorder=3)


def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None, fs=6.6, dashed=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
                                 lw=1.0, color=EDGE, linestyle="--" if dashed else "solid",
                                 zorder=4))
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2,
                ly if ly is not None else (y1 + y2) / 2,
                label, ha="center", va="center", fontsize=fs, color=TEXT,
                bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none"), zorder=5)


# ── 客户端 ──
box(1, 71, 17, 9, "管理员(管理端)", BOX_LIGHT, fs=8.6)
box(1, 11, 17, 9, "师生用户(聊天端)", BOX_LIGHT, fs=8.6)

# ── 前端 ──
box(23, 42, 17, 27, "前端(Vue 3)\n\n统一壳层\n路由守卫\nPinia·SSE\n引用预览", BOX_WHITE, fs=8.0)

# ── 后端四层 ──
layer(54, 12, "接口层")
box(53, 55, 28, 10, "API 路由(FastAPI)\n统一响应 · JWT · X-Client-ID", BOX_WHITE, fs=8.0)

layer(38, 12, "服务层")
box(53, 39, 14, 10, "业务服务\n知识库·文档\n会话·问答·日志", BOX_WHITE, fs=7.2)
box(69, 39, 12, 10, "文档 Worker\n轮询领取\n阶段进度", BOX_WHITE, fs=6.9)

layer(22, 12, "RAG 层")
box(53, 23, 14, 10, "入库管线\n解析→切块\n增强→向量化", BOX_LIGHT, fs=7.2)
box(69, 23, 12, 10, "查询管线\n检索→融合\n过滤→重排", BOX_LIGHT, fs=7.0)

layer(6, 12, "资源层")
box(53, 7, 13, 10, "PostgreSQL\nQdrant\n业务与向量数据", BOX_LIGHT, fs=6.8)
box(68, 7, 13, 10, "模型服务\n嵌入·生成\n视觉·重排", BOX_LIGHT, fs=7.0)

# ── 纵向流程 ──
arrow(64, 54, 64, 50)
arrow(64, 38, 64, 34)
arrow(64, 22, 64, 18)

# ── 客户端到前端 ──
arrow(18, 75.5, 23, 64.5, "管理操作", 19.8, 72.5, fs=6.0)
arrow(18, 15.5, 23, 46.5, "HTTP/SSE", 20.5, 31, fs=6.4)

# ── 前端到接口层 ──
arrow(40, 58, 46, 59.5, "HTTP API", 42.2, 62.2, fs=6.0)

# ── 横切模块 ──
ax.add_patch(FancyBboxPatch((85, 22), 14, 44, boxstyle="round,pad=0,rounding_size=0.8",
                            fc="white", ec=EDGE, lw=1.0, ls="--", zorder=2))
ax.text(92, 62, "横切模块", ha="center", va="center", fontsize=8.2,
        fontweight="bold", color=TEXT, zorder=3)
ax.text(92, 49, "app-config.yaml\n\n模型配置档案\nRAG 检索参数\n(保存即热更新)",
        ha="center", va="center", fontsize=6.9, color=TEXT, linespacing=1.4, zorder=3)
ax.text(92, 32, "model_swap\n\n启用切换时\n热替换服务连接",
        ha="center", va="center", fontsize=6.9, color=TEXT, linespacing=1.4, zorder=3)

arrow(85, 44, 82, 44, dashed=True)
arrow(85, 28, 82, 28, dashed=True)

plt.tight_layout(pad=0.2)
base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "chapters", "images", "图4-1-总体架构图")
os.makedirs(os.path.dirname(base), exist_ok=True)
plt.savefig(base + ".png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
plt.savefig(base + ".svg", bbox_inches="tight", pad_inches=0.03, facecolor="white")
print("已生成:", base + ".png")
print("已生成:", base + ".svg")
