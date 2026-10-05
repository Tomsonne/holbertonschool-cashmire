from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.utilisateur import Utilisateur


def resoudre_utilisateur_courant(session: Session) -> Utilisateur:
    """Point unique à remplacer par l'identité issue du futur JWT."""
    if settings.environment not in {"development", "test"}:
        raise HTTPException(status_code=401, detail="non_authentifie")

    email = settings.dev_user_email
    statement = (
        insert(Utilisateur)
        .values(email=email, mot_de_passe_hache="compte-de-developpement-inutilisable", nom_affichage="Utilisateur de développement")
        .on_conflict_do_nothing(index_elements=[text("lower(email)")])
    )
    session.execute(statement)
    utilisateur = session.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email.lower()))
    if utilisateur is None:
        raise HTTPException(status_code=500, detail="erreur_interne")
    return utilisateur
