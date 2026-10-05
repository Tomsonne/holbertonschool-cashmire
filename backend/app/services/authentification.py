from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.core.securite import hacher_mot_de_passe
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import InscriptionEntree

CONTRAINTE_EMAIL_UNIQUE = "uq_utilisateurs_email_insensible"


def _est_doublon_email(erreur: IntegrityError) -> bool:
    # On identifie la contrainte par l'exception du pilote (nom de la contrainte), pas par le
    # texte du message, qui dépend de la langue et de la version de PostgreSQL.
    diag = getattr(erreur.orig, "diag", None)
    return getattr(diag, "constraint_name", None) == CONTRAINTE_EMAIL_UNIQUE


def inscrire(db: Session, donnees: InscriptionEntree) -> Utilisateur:
    utilisateur = Utilisateur(
        email=donnees.email,
        mot_de_passe_hache=hacher_mot_de_passe(donnees.mot_de_passe),
        nom_affichage=donnees.nom_affichage,
    )
    db.add(utilisateur)
    try:
        db.commit()
    except IntegrityError as exc:
        if not _est_doublon_email(exc):
            # Autre contrainte : ce n'est pas un doublon, on laisse remonter (500 générique).
            raise
        # La session est inutilisable tant que la transaction n'est pas annulée.
        db.rollback()
        raise ErreurApi(
            409,
            "Un compte existe déjà avec cet email.",
            champs={"email": "Déjà utilisé."},
        ) from None
    db.refresh(utilisateur)  # charge date_creation (valeur par défaut posée par la base)
    return utilisateur
