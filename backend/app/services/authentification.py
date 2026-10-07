import secrets
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import limiteur
from app.core.config import settings
from app.core.erreurs import ErreurApi
from app.core.securite import hacher_mot_de_passe, verifier_mot_de_passe
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import ConnexionEntree, InscriptionEntree

CONTRAINTE_EMAIL_UNIQUE = "uq_utilisateurs_email_insensible"

# Hash factice, généré une seule fois : un email inconnu coûte autant d'Argon2 qu'un email connu.
_HASH_FACTICE = hacher_mot_de_passe(secrets.token_urlsafe(32))


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


def _creer_jwt(utilisateur: Utilisateur) -> str:
    maintenant = datetime.now(timezone.utc)
    claims = {
        "sub": str(utilisateur.id),
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def connecter(db: Session, donnees: ConnexionEntree) -> tuple[Utilisateur, str]:
    """Vérifie les identifiants et renvoie l'utilisateur et son JWT (à poser en cookie)."""
    # Avant tout travail Argon2 : un compte bloqué ne coûte rien au serveur.
    limiteur.verifier_autorise(donnees.email)
    utilisateur = db.scalars(
        select(Utilisateur).where(func.lower(Utilisateur.email) == donnees.email)
    ).one_or_none()
    hache = utilisateur.mot_de_passe_hache if utilisateur else _HASH_FACTICE
    mot_de_passe_valide = verifier_mot_de_passe(hache, donnees.mot_de_passe)
    if utilisateur is None or not mot_de_passe_valide:
        limiteur.enregistrer_echec(donnees.email)
        raise ErreurApi(401, "Email ou mot de passe incorrect.")
    limiteur.reinitialiser(donnees.email)
    return utilisateur, _creer_jwt(utilisateur)
