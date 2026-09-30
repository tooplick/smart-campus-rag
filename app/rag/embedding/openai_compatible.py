from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class OpenAICompatibleEmbedding:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        batch_size: int = 32,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            vectors = await self._embed_batch(batch)
            all_vectors.extend(vectors)
        return all_vectors

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.base_url}/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": self.model}

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 429:
                        wait = 2 ** attempt
                        logger.warning(f"Embedding rate limited, retry in {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    vectors = [item["embedding"] for item in data["data"]]
                    return vectors
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Embedding error: {e}, retry in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError("Embedding failed after all retries")
