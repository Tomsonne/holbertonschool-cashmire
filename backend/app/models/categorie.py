import uuid
from datetime import datetime
from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Categorie(Base):
    __tablename__ = "categories"
    __table_args__ = (Index("uq_categories_nom_insensible", text("lower(nom)"), unique=True),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom: Mapped[str] = mapped_column(String(80), nullable=False)
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
