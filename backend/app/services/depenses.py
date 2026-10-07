import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.models.utilisateur import Utilisateur
from app.schemas.categorie import CategorieSortie
from app.schemas.depense import (
    DepenseEntree,
    DepenseModification,
    DepenseSortie,
    ListeDepensesSortie,
)


def presenter_depense(depense: Depense, categorie: Categorie) -> DepenseSortie:
    return DepenseSortie(
        id=depense.id,
        montant=depense.montant,
        libelle=depense.libelle,
        date_depense=depense.date_depense,
        categorie=CategorieSortie(id=categorie.id, nom=categorie.nom),
    )


def creer_depense(db: Session, utilisateur: Utilisateur, donnees: DepenseEntree) -> DepenseSortie:
    categorie = db.get(Categorie, donnees.categorie_id)
    if categorie is None:
        raise ErreurApi(
            404, "Catégorie introuvable.", champs={"categorie_id": "Catégorie inconnue."}
        )
    depense = Depense(
        utilisateur_id=utilisateur.id,  # toujours l'utilisateur connecté, jamais le corps de la requête
        categorie_id=categorie.id,
        montant=donnees.montant,
        libelle=donnees.libelle,
        date_depense=donnees.date_depense,
    )
    db.add(depense)
    db.commit()
    db.refresh(depense)
    return presenter_depense(depense, categorie)


def _bornes_du_mois(mois: str) -> tuple[date, date]:
    """Premier jour du mois (inclus) et premier jour du mois suivant (exclu)."""
    debut = date.fromisoformat(f"{mois}-01")
    fin = date(debut.year + (debut.month == 12), debut.month % 12 + 1, 1)
    return debut, fin


def lister_depenses(
    db: Session,
    utilisateur: Utilisateur,
    mois: str | None,
    categorie_id: uuid.UUID | None,
    limite: int,
    decalage: int,
) -> ListeDepensesSortie:
    # Les mêmes conditions servent au total et à la page : `total` ne dépend pas de la pagination.
    conditions = [Depense.utilisateur_id == utilisateur.id]
    if mois is not None:
        debut, fin = _bornes_du_mois(mois)
        conditions += [Depense.date_depense >= debut, Depense.date_depense < fin]
    if categorie_id is not None:
        conditions.append(Depense.categorie_id == categorie_id)

    total = db.scalar(select(func.count()).select_from(Depense).where(*conditions))
    lignes = db.execute(
        select(Depense, Categorie)
        .join(Categorie, Depense.categorie_id == Categorie.id)
        .where(*conditions)
        # date_creation puis id départagent les dépenses du même jour : l'ordre reste stable
        # d'une page à l'autre.
        .order_by(Depense.date_depense.desc(), Depense.date_creation.desc(), Depense.id)
        .limit(limite)
        .offset(decalage)
    )
    return ListeDepensesSortie(
        elements=[presenter_depense(depense, categorie) for depense, categorie in lignes],
        total=total,
    )


def obtenir_depense(db: Session, utilisateur: Utilisateur, depense_id: uuid.UUID) -> DepenseSortie:
    # Le filtre par propriétaire est dans la requête : la dépense d'autrui est « introuvable ».
    ligne = db.execute(
        select(Depense, Categorie)
        .join(Categorie, Depense.categorie_id == Categorie.id)
        .where(Depense.id == depense_id, Depense.utilisateur_id == utilisateur.id)
    ).one_or_none()
    if ligne is None:
        raise ErreurApi(404, "Dépense introuvable.")
    return presenter_depense(*ligne)


def _depense_de_l_utilisateur(db: Session, utilisateur: Utilisateur, depense_id: uuid.UUID) -> Depense:
    # Même règle que le détail : le propriétaire est dans la requête, donc la dépense d'autrui
    # est « introuvable » et personne ne peut modifier ou supprimer celle d'un autre.
    depense = db.scalar(
        select(Depense).where(Depense.id == depense_id, Depense.utilisateur_id == utilisateur.id)
    )
    if depense is None:
        raise ErreurApi(404, "Dépense introuvable.")
    return depense


def modifier_depense(
    db: Session, utilisateur: Utilisateur, depense_id: uuid.UUID, donnees: DepenseModification
) -> DepenseSortie:
    depense = _depense_de_l_utilisateur(db, utilisateur, depense_id)
    envoyes = donnees.model_fields_set  # seuls les champs réellement présents dans le corps
    if "categorie_id" in envoyes:
        categorie = db.get(Categorie, donnees.categorie_id)
        if categorie is None:
            raise ErreurApi(
                404, "Catégorie introuvable.", champs={"categorie_id": "Catégorie inconnue."}
            )
        depense.categorie_id = categorie.id
    else:
        categorie = db.get(Categorie, depense.categorie_id)
    for champ in ("montant", "libelle", "date_depense"):
        if champ in envoyes:
            setattr(depense, champ, getattr(donnees, champ))
    # Posé explicitement : si les valeurs envoyées sont identiques aux anciennes, SQLAlchemy
    # n'émettrait aucun UPDATE et `onupdate` ne se déclencherait pas.
    depense.date_modification = datetime.now(timezone.utc)
    db.commit()
    db.refresh(depense)
    return presenter_depense(depense, categorie)


def supprimer_depense(db: Session, utilisateur: Utilisateur, depense_id: uuid.UUID) -> None:
    depense = _depense_de_l_utilisateur(db, utilisateur, depense_id)
    db.delete(depense)
    db.commit()
