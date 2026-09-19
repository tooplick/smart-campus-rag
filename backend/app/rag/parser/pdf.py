from __future__ import annotations

from pathlib import Path

from app.rag.models.blocks import ContentBlock, BlockType
from app.rag.parser.base import BaseParser

import fitz  # pymupdf


class PdfParser(BaseParser):
    async def parse(self, file_path: Path) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        doc = fitz.open(str(file_path))

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if not text.strip():
                continue

            current_title: str | None = None
            buf_lines: list[str] = []

            for line in text.splitlines(keepends=True):
                stripped = line.strip()
                if self._looks_like_heading(stripped, page):
                    if buf_lines:
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
                    current_title = stripped
                else:
                    buf_lines.append(line)

            if buf_lines:
                content = "".join(buf_lines).strip()
                if content:
                    blocks.append(ContentBlock(
                        block_type=BlockType.TEXT,
                        content=content,
                        page_number=page_num + 1,
                        section_title=current_title,
                        source_index=len(blocks),
                    ))

        doc.close()
        return blocks

    def _looks_like_heading(self, line: str, page) -> bool:
        if not line or len(line) > 200:
            return False
        # Check if font size is larger than body text
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for span_group in block["lines"]:
                for span in span_group.get("spans", []):
                    if span["text"].strip() == line:
                        if span["size"] > 13:
                            return True
        # Fallback: check common heading patterns
        if line.startswith(("第", "章", "节", "一、", "二、", "三、", "四、", "五、")):
            return True
        return False
