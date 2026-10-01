from __future__ import annotations

import csv
import io
from pathlib import Path

from app.rag.models.blocks import ContentBlock
from app.rag.parser.base import BaseParser
from app.rag.parser.tabular import rows_to_blocks


class CsvParser(BaseParser):
    """CSV 解析:每行一块,表头注入;UTF-8/GB18030 双编码容错(校园表格常见 GBK)。"""

    async def parse(self, file_path: Path) -> list[ContentBlock]:
        raw = file_path.read_bytes()
        text = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("utf-8", errors="replace")

        rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(text))]
        return rows_to_blocks(rows, section_title=file_path.stem, source_start=0)
