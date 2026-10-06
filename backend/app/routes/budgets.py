from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.authentification import utilisateur_courant
from app.core.erreurs import ErreurApi
from app.db.session import get_db
from app.models.budget import Budget
from app.models.categorie import Categorie
from app.models.utilisateur import Utilisateur
from app.schemas.budget import BudgetCreation, BudgetModification, BudgetResponse, MoisBudget
from app.services.budgets import presenter_budget

router = APIRouter()


@router.get("/budgets", response_model=list[BudgetResponse])
def lister_budgets(
    mois: MoisBudget | None = None,
    session: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(utilisateur_courant),
):
    requete = (
        select(Budget, Categorie)
        .join(Categorie, Budget.categorie_id == Categorie.id)
        .where(Budget.utilisateur_id == utilisateur.id)
        .order_by(Budget.periode_mois.desc(), Categorie.nom)
    )
    if mois is not None:
        requete = requete.where(Budget.periode_mois == date.fromisoformat(f"{mois}-01"))
    return [presenter_budget(session, budget, categorie) for budget, categorie in session.execute(requete)]


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
def obtenir_budget(
    budget_id: UUID,
    session: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(utilisateur_courant),
):
    ligne = session.execute(
        select(Budget, Categorie)
        .join(Categorie, Budget.categorie_id == Categorie.id)
        .where(Budget.id == budget_id, Budget.utilisateur_id == utilisateur.id)
    ).one_or_none()
    if ligne is None:
        raise ErreurApi(404, "Budget introuvable.")
    budget, categorie = ligne
    return presenter_budget(session, budget, categorie)


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
def creer_budget(
    donnees: BudgetCreation,
    session: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(utilisateur_courant),
):
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


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
def modifier_budget(
    budget_id: UUID,
    donnees: BudgetModification,
    session: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(utilisateur_courant),
):
    budget = session.scalar(select(Budget).where(Budget.id == budget_id, Budget.utilisateur_id == utilisateur.id))
    if budget is None:
        raise ErreurApi(404, "Budget introuvable.")
    if "montant_limite" in donnees.model_fields_set:
        budget.montant_limite = donnees.montant_limite
    if "seuil_alerte_pct" in donnees.model_fields_set:
        budget.seuil_alerte_pct = donnees.seuil_alerte_pct
    budget.date_modification = datetime.now(timezone.utc)
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    session.refresh(budget)
    categorie = session.get(Categorie, budget.categorie_id)
    return presenter_budget(session, budget, categorie)


@router.delete("/budgets/{budget_id}", status_code=204, response_model=None)
def supprimer_budget(
    budget_id: UUID,
    session: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(utilisateur_courant),
) -> Response:
    budget = session.scalar(select(Budget).where(Budget.id == budget_id, Budget.utilisateur_id == utilisateur.id))
    if budget is None:
        raise ErreurApi(404, "Budget introuvable.")
    session.delete(budget)
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    return Response(status_code=204)
