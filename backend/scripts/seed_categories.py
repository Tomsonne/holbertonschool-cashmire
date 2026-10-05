"""Insère les six catégories de démo sans créer de doublons."""
from sqlalchemy import func, select
from app.db.session import SessionLocal
from app.models import Categorie

CATEGORIES = ("Alimentation", "Factures", "Loisirs", "Transport", "Santé", "Autre")


def main() -> None:
    with SessionLocal.begin() as session:
        existing = set(session.scalars(select(func.lower(Categorie.nom))))
        for nom in CATEGORIES:
            if nom.casefold() not in existing:
                session.add(Categorie(nom=nom))
                existing.add(nom.casefold())
    print("Catégories de démonstration présentes.")


if __name__ == "__main__":
    main()
