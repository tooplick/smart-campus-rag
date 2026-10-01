from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from app.rag.models.blocks import BlockType, ContentBlock
from app.rag.parser.base import BaseParser


class _Extractor(HTMLParser):
    """HTML 正文抽取:script/style 等不入正文,h1-h6/title 作为分节标题。"""

    _SKIP = {"script", "style", "noscript", "template"}
    _HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6", "title"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[tuple[str, str]] = []
        self._skip = 0
        self._in_heading = False
        self._buf: list[str] = []

    def _flush(self) -> None:
        text = "".join(self._buf).strip()
        self._buf = []
        if text:
            self.segments.append(("heading" if self._in_heading else "text", text))

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP:
            self._skip += 1
        elif self._skip == 0 and tag in self._HEADINGS:
            self._flush()
            self._in_heading = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP:
            self._skip = max(0, self._skip - 1)
        elif self._skip == 0 and tag in self._HEADINGS and self._in_heading:
            self._flush()
            self._in_heading = False

    def handle_data(self, data: str) -> None:
        if self._skip == 0:
            self._buf.append(data)


class HtmlParser(BaseParser):
    """HTML 解析:去标签取正文,h1-h6 分节。"""

    async def parse(self, file_path: Path) -> list[ContentBlock]:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
        extractor = _Extractor()
        extractor.feed(raw)
        extractor._flush()

        blocks: list[ContentBlock] = []
        current_title: str | None = None
        buf: list[str] = []

        def flush() -> None:
            nonlocal buf
            content = "\n".join(buf).strip()
            if content:
                blocks.append(ContentBlock(
                    block_type=BlockType.TEXT,
                    content=content,
                    section_title=current_title,
                    source_index=len(blocks),
                ))
            buf = []

        for kind, text in extractor.segments:
            if kind == "heading":
                flush()
                current_title = text
            # 标题文本也保留进正文(title+body):只进 section_title 会丢检索词
            buf.append(text)
        flush()
        return blocks
