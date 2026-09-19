from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.rag.models.blocks import ContentBlock


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file_path: Path) -> list[ContentBlock]:
        ...
