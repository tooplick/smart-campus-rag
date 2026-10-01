from __future__ import annotations

from app.rag.parser.base import BaseParser
from app.rag.parser.csv_parser import CsvParser
from app.rag.parser.docx_parser import DocxParser
from app.rag.parser.html_parser import HtmlParser
from app.rag.parser.image import ImageParser
from app.rag.parser.pdf import PdfParser
from app.rag.parser.pptx_parser import PptxParser
from app.rag.parser.txt import TxtParser
from app.rag.parser.xlsx_parser import XlsxParser


def get_parser(file_type: str, vision_config: dict | None = None) -> BaseParser:
    """按文件类型(无点扩展名)分派解析器;图片需 Vision 模型配置。"""
    ft = (file_type or "").lower().lstrip(".")
    if ft in ("txt", "md"):
        return TxtParser()
    if ft == "pdf":
        return PdfParser()
    if ft == "docx":
        return DocxParser()
    if ft == "xlsx":
        return XlsxParser()
    if ft == "pptx":
        return PptxParser()
    if ft == "csv":
        return CsvParser()
    if ft in ("html", "htm"):
        return HtmlParser()
    if ft in ("png", "jpg", "jpeg"):
        if not vision_config or not vision_config.get("base_url") or not vision_config.get("model"):
            raise ValueError("图片解析需要先在「模型」页配置并启用 Vision 模型")
        return ImageParser(
            base_url=vision_config["base_url"],
            api_key=vision_config.get("api_key", ""),
            model=vision_config["model"],
        )
    raise ValueError(f"Unsupported file type: {file_type}")
