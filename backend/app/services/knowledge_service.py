from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[dict]:
        stmt = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        result = await self.db.execute(stmt)
        bases = result.scalars().all()

        items = []
        for kb in bases:
            count_stmt = select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
            count_result = await self.db.execute(count_stmt)
            doc_count = count_result.scalar() or 0
            items.append({
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "icon": kb.icon,
                "is_enabled": kb.is_enabled,
                "document_count": doc_count,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at,
            })
        return items

    async def get_by_id(self, kb_id: int) -> KnowledgeBase | None:
        return await self.db.get(KnowledgeBase, kb_id)

    async def create(self, name: str, description: str | None = None, icon: str | None = None) -> KnowledgeBase:
        kb = KnowledgeBase(name=name, description=description, icon=icon)
        self.db.add(kb)
        await self.db.flush()
        await self.db.refresh(kb)
        return kb

    async def update(self, kb_id: int, **kwargs) -> KnowledgeBase | None:
        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(kb, key):
                setattr(kb, key, value)
        await self.db.flush()
        await self.db.refresh(kb)
        return kb

    async def delete(self, kb_id: int) -> bool:
        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb:
            return False
        await self.db.delete(kb)
        await self.db.flush()
        return True
