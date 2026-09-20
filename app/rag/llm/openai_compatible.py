from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class OpenAICompatibleLLM:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        max_retries: int = 3,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict],
        *,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict | AsyncIterator[str]:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {"model": self.model, "messages": messages, "stream": stream}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        for attempt in range(self.max_retries):
            try:
                if stream:
                    return self._stream_chat(url, headers, payload)
                else:
                    return await self._sync_chat(url, headers, payload)
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"LLM error: {e}, retry in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise

        raise RuntimeError("LLM failed after all retries")

    async def _sync_chat(self, url: str, headers: dict, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def _stream_chat(self, url: str, headers: dict, payload: dict) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
