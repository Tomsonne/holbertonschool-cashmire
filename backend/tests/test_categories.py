from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine, obtenir_session
from app.main import app

# Les six catégories créées par la migration initiale, dans l'ordre alphabétique attendu.
NOMS_ATTENDUS = ["Alimentation", "Autre", "Factures", "Loisirs", "Santé", "Transport"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def base_migree():
    """Ces tests utilisent la vraie base : ils se sautent si elle n'est pas disponible."""
    try:
        with engine.connect() as connexion:
            connexion.execute(text("SELECT count(*) FROM categories"))
    except Exception:
        pytest.skip("PostgreSQL migré indisponible : lancer les tests dans le conteneur api.")


# --- Avec la vraie base PostgreSQL (migration appliquée) -----------------------------------


def test_liste_les_six_categories_predefinies_au_format_id_nom(client, base_migree):
    reponse = client.get("/api/categories")
    assert reponse.status_code == 200
    categories = reponse.json()
    assert [c["nom"] for c in categories] == NOMS_ATTENDUS
    for categorie in categories:
        assert set(categorie) == {"id", "nom"}
        UUID(categorie["id"])  # lève une erreur si ce n'est pas un UUID
    assert len({c["id"] for c in categories}) == 6


def test_ordre_stable_d_un_appel_a_l_autre(client, base_migree):
    premiere = client.get("/api/categories").json()
    seconde = client.get("/api/categories").json()
    assert premiere == seconde


# --- Sans base : format de la réponse avec une fausse session ------------------------------


class FausseSession:
    def scalars(self, _requete):
        return [
            SimpleNamespace(id=uuid4(), nom="Loisirs", date_creation="ne-doit-pas-sortir"),
            SimpleNamespace(id=uuid4(), nom="Santé", date_creation="ne-doit-pas-sortir"),
        ]


def test_reponse_n_expose_que_id_et_nom(client):
    app.dependency_overrides[obtenir_session] = lambda: FausseSession()
    try:
        reponse = client.get("/api/categories")
    finally:
        app.dependency_overrides.clear()
    assert reponse.status_code == 200
    assert all(set(c) == {"id", "nom"} for c in reponse.json())
    assert "ne-doit-pas-sortir" not in reponse.text


# --- Lecture seule : aucune route d'écriture ------------------------------------------------


@pytest.mark.parametrize("methode", ["POST", "PUT", "PATCH", "DELETE"])
def test_ecriture_sur_la_collection_est_refusee_en_405(client, methode):
    reponse = client.request(methode, "/api/categories")
    assert reponse.status_code == 405
    assert reponse.json()["erreur"]["code"] == "requete_invalide"


@pytest.mark.parametrize("methode", ["GET", "PUT", "PATCH", "DELETE"])
def test_aucune_route_sur_une_categorie_precise(client, methode):
    reponse = client.request(methode, f"/api/categories/{uuid4()}")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"
