from __future__ import annotations

import re
from pathlib import Path

from app.rag.models.blocks import ContentBlock, BlockType
from app.rag.parser.base import BaseParser


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class TxtParser(BaseParser):
    async def parse(self, file_path: Path) -> list[ContentBlock]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return []

        blocks: list[ContentBlock] = []
        current_title: str | None = None
        buf_lines: list[str] = []

        for line in text.splitlines(keepends=True):
            m = _HEADING_RE.match(line.strip())
            if m:
                if buf_lines:
                    content = "".join(buf_lines).strip()
                    if content:
                        blocks.append(ContentBlock(
                            block_type=BlockType.TEXT,
                            content=content,
                            section_title=current_title,
                            source_index=len(blocks),
                        ))
                    buf_lines = []
                current_title = m.group(2).strip()
            else:
                buf_lines.append(line)

        if buf_lines:
            content = "".join(buf_lines).strip()
            if content:
                blocks.append(ContentBlock(
                    block_type=BlockType.TEXT,
                    content=content,
                    section_title=current_title,
                    source_index=len(blocks),
                ))

        return blocks
