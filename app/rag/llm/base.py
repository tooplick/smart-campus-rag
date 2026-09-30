from __future__ import annotations

from typing import AsyncIterator, Protocol


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[dict],
        *,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict | AsyncIterator[str]:
        """Send chat completion request. Returns dict if not streaming, async iterator of tokens if streaming."""
        ...
