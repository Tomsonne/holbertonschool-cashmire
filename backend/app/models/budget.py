import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("montant_limite > 0", name="ck_budgets_montant_positif"),
        CheckConstraint("EXTRACT(DAY FROM periode_mois) = 1", name="ck_budgets_premier_du_mois"),
        CheckConstraint("seuil_alerte_pct BETWEEN 1 AND 100", name="ck_budgets_seuil_valide"),
        UniqueConstraint("utilisateur_id", "categorie_id", "periode_mois", name="uq_budgets_utilisateur_categorie_mois"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False)
    categorie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    montant_limite: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    periode_mois: Mapped[date] = mapped_column(Date, nullable=False)
    seuil_alerte_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=80, server_default="80")
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    date_modification: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
