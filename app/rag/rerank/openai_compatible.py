from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OpenAICompatibleRerank:
    """OpenAI 兼容协议的重排实现(SiliconFlow/Cohere 风格 POST {base}/rerank)。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        # base_url 可不带 /v1,调用前统一补齐(与其余 Provider 惯例一致)
        base = base_url.rstrip("/")
        self.base_url = base if base.endswith("/v1") else f"{base}/v1"
        self.api_key = api_key
        self.model = model
        self._client = client

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def rerank(
        self, query: str, documents: list[str], *, top_n: int
    ) -> list[tuple[int, float]]:
        if not documents:
            return []
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
        }
        resp = await self._http().post(
            f"{self.base_url}/rerank",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("results") or []
        out: list[tuple[int, float]] = []
        for item in items:
            idx = item.get("index")
            if not isinstance(idx, int) or not 0 <= idx < len(documents):
                continue
            score = item.get("relevance_score", item.get("score", 0.0))
            out.append((idx, float(score)))
        out.sort(key=lambda x: -x[1])
        return out
