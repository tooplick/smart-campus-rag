from datetime import datetime
from sqlalchemy import DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QaSource(Base):
    __tablename__ = "qa_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qa_record_id: Mapped[int] = mapped_column(Integer, ForeignKey("qa_records.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_chunks.id"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
