from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.db.session import get_db
from app.models.budget import Budget
from app.models.categorie import Categorie
from app.schemas.budget import BudgetCreation, BudgetResponse
from app.services.budgets import presenter_budget
from app.services.utilisateur_courant import resoudre_utilisateur_courant

router = APIRouter()


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
def creer_budget(donnees: BudgetCreation, session: Session = Depends(get_db)):
    utilisateur = resoudre_utilisateur_courant(session)
    categorie = session.get(Categorie, donnees.categorie_id)
    if categorie is None:
        raise ErreurApi(404, "La catégorie demandée est introuvable.")

    budget = Budget(
        utilisateur_id=utilisateur.id,
        categorie_id=categorie.id,
        montant_limite=donnees.montant_limite,
        periode_mois=donnees.periode_mois,
        seuil_alerte_pct=donnees.seuil_alerte_pct,
    )
    session.add(budget)
    try:
        session.commit()
    except IntegrityError as erreur:
        session.rollback()
        contrainte = getattr(getattr(erreur.orig, "diag", None), "constraint_name", None)
        if contrainte == "uq_budgets_utilisateur_categorie_mois":
            raise ErreurApi(409, "Un budget existe déjà pour cette catégorie et ce mois.") from None
        raise
    session.refresh(budget)
    return presenter_budget(session, budget, categorie)
