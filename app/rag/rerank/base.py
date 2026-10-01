from __future__ import annotations

from typing import Protocol


class RerankProvider(Protocol):
    """重排协议:输入查询与候选文本,返回按相关度降序的 (候选下标, 相关度) 列表。"""

    async def rerank(
        self, query: str, documents: list[str], *, top_n: int
    ) -> list[tuple[int, float]]: ...
