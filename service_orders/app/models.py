from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow():
    return datetime.utcnow()

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    items_json: Mapped[str] = mapped_column(String, nullable=False)  # json array
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    total_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_public(self) -> dict:
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items": json.loads(self.items_json),
            "status": self.status,
            "total_sum": self.total_sum,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
