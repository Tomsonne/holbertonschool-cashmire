from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erreurs import ErreurApi
from app.db.session import engine, get_db
from app.main import app
from app.models.budget import Budget
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.models.utilisateur import Utilisateur
from app.services.budgets import presenter_budget
from app.services.utilisateur_courant import resoudre_utilisateur_courant


def test_creer_budget_persiste_et_convertit_le_mois(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    if categorie is None:
        categorie = Categorie(id=uuid4(), nom=f"Test {uuid4()}")
        db_session.add(categorie)
        db_session.flush()

    response = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "125.40", "mois": "2026-10"
    })
    assert response.status_code == 201
    assert response.json()["montant_limite"] == "125.40"
    assert response.json()["depense"] == "0.00"
    assert response.json()["mois"] == "2026-10"
    assert response.json()["seuil_alerte_pct"] == 80

    budget = db_session.get(Budget, response.json()["id"])
    assert budget.periode_mois.isoformat() == "2026-10-01"
    assert budget.montant_limite == Decimal("125.40")


@pytest.mark.parametrize(("payload", "champ"), [
    ({"montant_limite": "0"}, "montant_limite"),
    ({"montant_limite": "-1"}, "montant_limite"),
    ({"montant_limite": "12.345"}, "montant_limite"),
    ({"montant_limite": 12.5}, "montant_limite"),
    ({"mois": "2026-13"}, "mois"),
    ({"mois": "2026-2"}, "mois"),
    ({"seuil_alerte_pct": 0}, "seuil_alerte_pct"),
    ({"seuil_alerte_pct": 101}, "seuil_alerte_pct"),
    ({"seuil_alerte_pct": 80.5}, "seuil_alerte_pct"),
])
def test_donnees_invalides_repondent_422(client, payload, champ):
    corps = {"categorie_id": "11111111-1111-4111-8111-111111111111", "montant_limite": "10.00", "mois": "2026-10"}
    corps.update(payload)
    response = client.post("/api/budgets", json=corps)
    assert response.status_code == 422
    assert response.json()["erreur"]["code"] == "donnees_invalides"
    assert champ in response.json()["erreur"]["champs"]


def test_doublon_repond_409(client, db_session):
    categorie = Categorie(id=uuid4(), nom=f"Doublon {uuid4()}")
    db_session.add(categorie)
    db_session.flush()
    corps = {"categorie_id": str(categorie.id), "montant_limite": "60.00", "mois": "2026-11"}
    assert client.post("/api/budgets", json=corps).status_code == 201
    response = client.post("/api/budgets", json=corps)
    assert response.status_code == 409
    assert response.json()["erreur"]["code"] == "conflit"


def test_categorie_inconnue_repond_404(client):
    response = client.post("/api/budgets", json={
        "categorie_id": str(uuid4()), "montant_limite": "60.00", "mois": "2026-11"
    })
    assert response.status_code == 404
    assert response.json()["erreur"]["code"] == "introuvable"


def test_requetes_simultanees_ne_creent_qu_un_budget(base_propre):
    with Session(engine) as session:
        categorie = session.scalar(select(Categorie).limit(1))
        categorie_id = categorie.id
    mois = "2026-12"

    def session_par_requete():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = session_par_requete
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuts = list(pool.map(lambda _: TestClient(app).post("/api/budgets", json={
                "categorie_id": str(categorie_id), "montant_limite": "42.00", "mois": mois
            }).status_code, range(2)))
        assert sorted(statuts) == [201, 409]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_resolveur_utilisateur_de_test_est_interdit_en_production(db_session, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "environment", "production")
    with pytest.raises(ErreurApi) as erreur:
        resoudre_utilisateur_courant(db_session)
    assert erreur.value.statut == 401


def test_route_repond_401_formate_en_production(client, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "environment", "production")
    response = client.post("/api/budgets", json={
        "categorie_id": str(uuid4()), "montant_limite": "10.00", "mois": "2026-10"
    })
    assert response.status_code == 401
    assert response.json()["erreur"]["code"] == "non_authentifie"


def test_erreur_bdd_inconnue_est_relancee_apres_rollback(client, db_session, monkeypatch):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    rollback_original = db_session.rollback
    rollbacks = []

    def rollback_verifie():
        rollbacks.append(True)
        rollback_original()

    def commit_invalide():
        raise IntegrityError("INSERT budgets", {}, Exception("contrainte inconnue"))

    monkeypatch.setattr(db_session, "rollback", rollback_verifie)
    monkeypatch.setattr(db_session, "commit", commit_invalide)
    reponse = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "10.00", "mois": "2026-10"
    })
    assert reponse.status_code == 500
    assert reponse.json() == {
        "erreur": {"code": "erreur_interne", "message": "Une erreur interne est survenue."}
    }
    assert rollbacks == [True]
    assert "contrainte inconnue" not in reponse.text


@pytest.mark.parametrize(("montant", "pourcentage", "statut", "reste"), [
    ("799.99", Decimal("80.00"), "ok", "200.01"),
    ("800.00", Decimal("80.00"), "attention", "200.00"),
    ("1000.00", Decimal("100.00"), "attention", "0.00"),
    ("1000.01", Decimal("100.00"), "depasse", "-0.01"),
])
def test_consommation_et_statut_aux_bornes(client, db_session, montant, pourcentage, statut, reste):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    reponse = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "1000.00", "mois": "2026-10"
    })
    assert reponse.status_code == 201
    budget = db_session.get(Budget, reponse.json()["id"])
    assert reponse.json()["depense"] == "0.00"
    assert reponse.json()["reste"] == "1000.00"
    assert isinstance(reponse.json()["pourcentage"], (int, float))
    assert Decimal(str(reponse.json()["pourcentage"])) == 0
    assert reponse.json()["statut"] == "ok"

    db_session.add(Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal(montant), date_depense=date(2026, 10, 15), libelle="Test",
    ))
    db_session.flush()
    resultat = presenter_budget(db_session, budget, categorie)
    assert resultat.depense == Decimal(montant)
    assert resultat.reste == Decimal(reste)
    assert resultat.pourcentage == pourcentage
    assert resultat.statut == statut


def test_consommation_filtre_utilisateur_categorie_et_mois_et_suit_les_depenses(client, db_session):
    categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Alimentation"))
    autre_categorie = db_session.scalar(select(Categorie).where(Categorie.nom == "Transport"))
    reponse = client.post("/api/budgets", json={
        "categorie_id": str(categorie.id), "montant_limite": "100.00", "mois": "2026-12"
    })
    assert reponse.status_code == 201
    budget = db_session.get(Budget, reponse.json()["id"])
    autre_utilisateur = Utilisateur(
        email=f"autre-{uuid4()}@example.invalid", mot_de_passe_hache="inutilisable", nom_affichage="Autre"
    )
    db_session.add(autre_utilisateur)
    db_session.flush()
    depense = Depense(
        utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
        montant=Decimal("25.00"), date_depense=date(2026, 12, 31), libelle="Incluse",
    )
    db_session.add_all([
        depense,
        Depense(utilisateur_id=budget.utilisateur_id, categorie_id=autre_categorie.id,
                montant=Decimal("12.00"), date_depense=date(2026, 12, 15), libelle="Autre catégorie"),
        Depense(utilisateur_id=budget.utilisateur_id, categorie_id=categorie.id,
                montant=Decimal("13.00"), date_depense=date(2027, 1, 1), libelle="Autre mois"),
        Depense(utilisateur_id=autre_utilisateur.id, categorie_id=categorie.id,
                montant=Decimal("14.00"), date_depense=date(2026, 12, 15), libelle="Autre utilisateur"),
    ])
    db_session.flush()
    assert presenter_budget(db_session, budget, categorie).depense == Decimal("25.00")

    depense.montant = Decimal("30.00")
    db_session.flush()
    assert presenter_budget(db_session, budget, categorie).depense == Decimal("30.00")

    db_session.delete(depense)
    db_session.flush()
    resultat = presenter_budget(db_session, budget, categorie)
    assert resultat.depense == Decimal("0.00")
    assert resultat.pourcentage == Decimal("0.00")
