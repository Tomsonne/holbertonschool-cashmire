"""Initialise le schéma Cashmire et les six catégories partagées."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

CATEGORIES = [
    ("11111111-1111-4111-8111-111111111111", "Alimentation"),
    ("22222222-2222-4222-8222-222222222222", "Factures"),
    ("33333333-3333-4333-8333-333333333333", "Loisirs"),
    ("44444444-4444-4444-8444-444444444444", "Transport"),
    ("55555555-5555-4555-8555-555555555555", "Santé"),
    ("66666666-6666-4666-8666-666666666666", "Autre"),
]


def upgrade() -> None:
    op.create_table(
        "utilisateurs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("mot_de_passe_hache", sa.String(255), nullable=False),
        sa.Column("nom_affichage", sa.String(100), nullable=False),
        sa.Column("date_creation", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uq_utilisateurs_email_insensible", "utilisateurs", [sa.text("lower(email)")], unique=True)
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nom", sa.String(80), nullable=False),
        sa.Column("date_creation", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uq_categories_nom_insensible", "categories", [sa.text("lower(nom)")], unique=True)
    op.create_table(
        "depenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("utilisateur_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categorie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("montant", sa.Numeric(12, 2), nullable=False),
        sa.Column("date_depense", sa.Date(), nullable=False),
        sa.Column("libelle", sa.String(200), nullable=False),
        sa.Column("date_creation", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("date_modification", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("montant > 0", name="ck_depenses_montant_positif"),
    )
    op.create_index("ix_depenses_utilisateur_date", "depenses", ["utilisateur_id", "date_depense"])
    op.create_index("ix_depenses_utilisateur_categorie", "depenses", ["utilisateur_id", "categorie_id"])
    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("utilisateur_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categorie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("montant_limite", sa.Numeric(12, 2), nullable=False),
        sa.Column("periode_mois", sa.Date(), nullable=False),
        sa.Column("seuil_alerte_pct", sa.SmallInteger(), server_default="80", nullable=False),
        sa.Column("date_creation", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("date_modification", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("montant_limite > 0", name="ck_budgets_montant_positif"),
        sa.CheckConstraint("EXTRACT(DAY FROM periode_mois) = 1", name="ck_budgets_premier_du_mois"),
        sa.CheckConstraint("seuil_alerte_pct BETWEEN 1 AND 100", name="ck_budgets_seuil_valide"),
        sa.UniqueConstraint("utilisateur_id", "categorie_id", "periode_mois", name="uq_budgets_utilisateur_categorie_mois"),
    )
    op.bulk_insert(sa.table("categories", sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("nom", sa.String())),
                   [{"id": id_, "nom": name} for id_, name in CATEGORIES])


def downgrade() -> None:
    op.drop_table("budgets")
    op.drop_index("ix_depenses_utilisateur_categorie", table_name="depenses")
    op.drop_index("ix_depenses_utilisateur_date", table_name="depenses")
    op.drop_table("depenses")
    op.drop_index("uq_categories_nom_insensible", table_name="categories")
    op.drop_table("categories")
    op.drop_index("uq_utilisateurs_email_insensible", table_name="utilisateurs")
    op.drop_table("utilisateurs")
