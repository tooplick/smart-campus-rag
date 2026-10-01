from __future__ import annotations

from pathlib import Path

import openpyxl

from app.rag.models.blocks import ContentBlock
from app.rag.parser.base import BaseParser
from app.rag.parser.tabular import rows_to_blocks


class XlsxParser(BaseParser):
    """XLSX 解析:逐工作表读取,每行一块,表头注入行文本,表名作 section_title。"""

    async def parse(self, file_path: Path) -> list[ContentBlock]:
        workbook = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        blocks: list[ContentBlock] = []
        try:
            for sheet in workbook.worksheets:
                rows = [
                    [("" if v is None else str(v)) for v in row]
                    for row in sheet.iter_rows(values_only=True)
                ]
                blocks.extend(rows_to_blocks(rows, section_title=sheet.title, source_start=len(blocks)))
        finally:
            workbook.close()
        return blocks
