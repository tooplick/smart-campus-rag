from __future__ import annotations

import re
from pathlib import Path

import fitz  # pymupdf

from app.rag.models.blocks import ContentBlock, BlockType
from app.rag.parser.base import BaseParser

# 标题行长度上限;相对字号比(≥ 正文 × 该值视为标题)
_HEADING_MAX_LEN = 200
_RELATIVE_RATIO = 1.1
_NUMBERING_PREFIXES = ("第", "章", "节", "一、", "二、", "三、", "四、", "五、")


class PdfParser(BaseParser):
    async def parse(self, file_path: Path) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        doc = fitz.open(str(file_path))

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if not text.strip():
                continue

            profile, body_size = self._line_profile(page)
            current_title: str | None = None
            buf_lines: list[str] = []

            def flush() -> None:
                nonlocal buf_lines
                content = "".join(buf_lines).strip()
                if content:
                    blocks.append(ContentBlock(
                        block_type=BlockType.TEXT,
                        content=content,
                        page_number=page_num + 1,
                        section_title=current_title,
                        source_index=len(blocks),
                    ))
                buf_lines = []

            for line in text.splitlines(keepends=True):
                stripped = line.strip()
                if self._looks_like_heading(stripped, profile, body_size):
                    flush()
                    current_title = stripped
                if stripped:
                    # 标题文本保留进正文(title+body):只进 section_title 会丢检索词
                    buf_lines.append(line)
            flush()

        doc.close()
        return blocks

    def _line_profile(self, page) -> tuple[dict[str, tuple[float, bool]], float]:
        """按版面行聚合 span 得到 行文本 → (字号, 粗体),并按字数加权估出正文字号。

        真实 PDF(如简历)常把一行拆成多个 span('掌握'|'技'|'能'),
        必须整行聚合后再匹配,逐 span 整串比较永远不中。
        """
        profile: dict[str, tuple[float, bool]] = {}
        size_weight: dict[float, int] = {}
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                joined = "".join(s.get("text", "") for s in spans).strip()
                if joined:
                    size = max((s.get("size", 0.0) for s in spans), default=0.0)
                    bold = any(s.get("flags", 0) & 16 for s in spans)
                    profile[joined] = (size, bold)
                for s in spans:
                    t = s.get("text", "").strip()
                    if t:
                        sz = s.get("size", 0.0)
                        size_weight[sz] = size_weight.get(sz, 0) + len(t)
        body_size = max(size_weight, key=size_weight.get) if size_weight else 0.0
        return profile, body_size

    def _looks_like_heading(
        self, line: str, profile: dict[str, tuple[float, bool]], body_size: float
    ) -> bool:
        if not line or len(line) > _HEADING_MAX_LEN:
            return False
        size, bold = profile.get(line, (0.0, False))
        # 绝对字号(原规则)或明显大于正文(相对规则):简历类标题常在 11~13pt
        if size > 13 or (body_size and size >= body_size * _RELATIVE_RATIO):
            return True
        # 同字号粗体短行且非句末收尾
        if (
            bold and body_size and size >= body_size
            and len(line) <= 30 and not re.search(r"[。！？．.!?]$", line)
        ):
            return True
        # 常见编号标题样式
        return line.startswith(_NUMBERING_PREFIXES)
