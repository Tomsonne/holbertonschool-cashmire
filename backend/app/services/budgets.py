from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.schemas.budget import BudgetResponse, CategorieResume


def presenter_budget(session: Session, budget: Budget, categorie: Categorie) -> BudgetResponse:
    mois_suivant = date(
        budget.periode_mois.year + (budget.periode_mois.month == 12),
        budget.periode_mois.month % 12 + 1,
        1,
    )
    total = session.scalar(
        select(func.coalesce(func.sum(Depense.montant), 0)).where(
            Depense.utilisateur_id == budget.utilisateur_id,
            Depense.categorie_id == budget.categorie_id,
            Depense.date_depense >= budget.periode_mois,
            Depense.date_depense < mois_suivant,
        )
    )
    depense = Decimal(total or 0).quantize(Decimal("0.01"))
    limite = budget.montant_limite
    pourcentage = (depense * Decimal(100) / limite).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    statut = "depasse" if depense > limite else "attention" if pourcentage >= budget.seuil_alerte_pct else "ok"
    return BudgetResponse(
        id=budget.id,
        categorie=CategorieResume(id=categorie.id, nom=categorie.nom),
        mois=budget.periode_mois.strftime("%Y-%m"),
        montant_limite=f"{limite:.2f}",
        depense=f"{depense:.2f}",
        reste=f"{limite - depense:.2f}",
        pourcentage=pourcentage,
        seuil_alerte_pct=budget.seuil_alerte_pct,
        statut=statut,
    )
