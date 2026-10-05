from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import erreur_api
from app.db.session import SessionLocal
from app.models.budget import Budget
from app.models.categorie import Categorie
from app.schemas.budget import BudgetCreation, BudgetResponse
from app.services.budgets import presenter_budget
from app.services.utilisateur_courant import resoudre_utilisateur_courant

router = APIRouter()


def obtenir_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
def creer_budget(donnees: BudgetCreation, session: Session = Depends(obtenir_session)):
    utilisateur = resoudre_utilisateur_courant(session)
    categorie = session.get(Categorie, donnees.categorie_id)
    if categorie is None:
        return erreur_api(404, "introuvable", "La catégorie demandée est introuvable.")

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
            return erreur_api(409, "conflit", "Un budget existe déjà pour cette catégorie et ce mois.")
        return erreur_api(500, "erreur_interne", "Une erreur interne est survenue.")
    session.refresh(budget)
    return presenter_budget(session, budget, categorie)
