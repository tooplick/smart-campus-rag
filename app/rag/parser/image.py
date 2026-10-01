from __future__ import annotations

import base64
from pathlib import Path

import httpx

from app.rag.models.blocks import BlockType, ContentBlock
from app.rag.parser.base import BaseParser

_PROMPT = "请提取图片中的全部文字内容,按阅读顺序输出纯文本,不要添加解释。"


class ImageParser(BaseParser):
    """图片解析:调用 OpenAI 兼容 Vision 模型 OCR 提取图中文字,产出单个文本块。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        # 与嵌入 provider 同惯例:base_url 可不带 /v1,调用前统一补齐
        base = base_url.rstrip("/")
        self.base_url = base if base.endswith("/v1") else f"{base}/v1"
        self.api_key = api_key
        self.model = model
        self._client = client

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def parse(self, file_path: Path) -> list[ContentBlock]:
        suffix = file_path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        b64 = base64.b64encode(file_path.read_bytes()).decode()

        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
            "max_tokens": 2048,
        }
        resp = await self._http().post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data["choices"][0]["message"].get("content") or "").strip()
        if not text:
            return []
        return [ContentBlock(block_type=BlockType.TEXT, content=text, page_number=1, source_index=0)]
