from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app
from app.models.budget import Budget
from app.models.categorie import Categorie
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
    with pytest.raises(HTTPException) as erreur:
        resoudre_utilisateur_courant(db_session)
    assert erreur.value.status_code == 401


def test_route_repond_401_formate_en_production(client, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "environment", "production")
    response = client.post("/api/budgets", json={
        "categorie_id": str(uuid4()), "montant_limite": "10.00", "mois": "2026-10"
    })
    assert response.status_code == 401
    assert response.json()["erreur"]["code"] == "non_authentifie"
