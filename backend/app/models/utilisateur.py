import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, func, text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    __table_args__ = (Index("uq_utilisateurs_email_insensible", text("lower(email)"), unique=True),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    mot_de_passe_hache: Mapped[str] = mapped_column(String(255), nullable=False)
    nom_affichage: Mapped[str] = mapped_column(String(100), nullable=False)
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
