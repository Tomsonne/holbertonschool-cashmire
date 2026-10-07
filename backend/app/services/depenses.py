from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.models.utilisateur import Utilisateur
from app.schemas.categorie import CategorieSortie
from app.schemas.depense import DepenseEntree, DepenseSortie


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
