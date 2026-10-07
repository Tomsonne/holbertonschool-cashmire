"""Consultation des catégories (#12) : GET /api/categories.

Les tests utilisent les fixtures de conftest.py (base de test dédiée). Les six catégories viennent
de la migration initiale.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete

from app.core.authentification import utilisateur_courant
from app.main import app
from app.models.categorie import Categorie
from app.models.utilisateur import Utilisateur

URL = "/api/categories"

# Les six catégories créées par la migration initiale, dans l'ordre alphabétique attendu.
NOMS_ATTENDUS = ["Alimentation", "Autre", "Factures", "Loisirs", "Santé", "Transport"]


@pytest.fixture(autouse=True)
def categories_predefinies_seules(db_session):
    """D'autres tests (budgets) laissent des catégories en base : on ne garde que les six."""
    db_session.execute(delete(Categorie).where(Categorie.nom.not_in(NOMS_ATTENDUS)))
    db_session.commit()


@pytest.fixture
def connecte(db_session):
    """Simule un utilisateur connecté (remplace la dépendance de #9)."""
    utilisateur = Utilisateur(
        email="alice@example.com", mot_de_passe_hache="hash-de-test", nom_affichage="Alice"
    )
    db_session.add(utilisateur)
    db_session.commit()
    db_session.refresh(utilisateur)
    app.dependency_overrides[utilisateur_courant] = lambda: utilisateur
    try:
        yield utilisateur
    finally:
        app.dependency_overrides.pop(utilisateur_courant, None)


# --- Utilisateur connecté ---------------------------------------------------------------------


def test_liste_les_six_categories_predefinies_au_format_id_nom(client, connecte):
    reponse = client.get(URL)
    assert reponse.status_code == 200
    categories = reponse.json()
    assert [c["nom"] for c in categories] == NOMS_ATTENDUS
    for categorie in categories:
        assert set(categorie) == {"id", "nom"}
        UUID(categorie["id"])  # lève une erreur si ce n'est pas un UUID
    assert len({c["id"] for c in categories}) == 6


def test_ordre_stable_d_un_appel_a_l_autre(client, connecte):
    assert client.get(URL).json() == client.get(URL).json()


def test_les_categories_sont_les_memes_pour_tous_les_utilisateurs(client, connecte, db_session):
    autre = Utilisateur(
        email="bob@example.com", mot_de_passe_hache="hash-de-test", nom_affichage="Bob"
    )
    db_session.add(autre)
    db_session.commit()
    pour_alice = client.get(URL).json()
    app.dependency_overrides[utilisateur_courant] = lambda: autre
    pour_bob = client.get(URL).json()
    assert pour_alice == pour_bob


# --- Authentification -------------------------------------------------------------------------


def test_sans_authentification_renvoie_401(client):
    reponse = client.get(URL)
    assert reponse.status_code == 401
    assert reponse.json()["erreur"]["code"] == "non_authentifie"


def test_avec_un_vrai_cookie_la_liste_est_accessible(client):
    identifiants = {"email": "alice@example.com", "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post(
        "/api/authentification/inscription", json={**identifiants, "nom_affichage": "Alice"}
    ).status_code == 201
    assert client.post("/api/authentification/connexion", json=identifiants).status_code == 200
    reponse = client.get(URL)
    assert reponse.status_code == 200
    assert [c["nom"] for c in reponse.json()] == NOMS_ATTENDUS


def test_cookie_falsifie_renvoie_401(client):
    identifiants = {"email": "alice@example.com", "mot_de_passe": "un-mot-de-passe-long"}
    client.post("/api/authentification/inscription", json={**identifiants, "nom_affichage": "A"})
    client.post("/api/authentification/connexion", json=identifiants)
    for cookie in client.cookies.jar:
        cookie.value = cookie.value[:-3] + "xxx"
    assert client.get(URL).status_code == 401


# --- Lecture seule : aucune route d'écriture --------------------------------------------------


@pytest.mark.parametrize("methode", ["POST", "PUT", "PATCH", "DELETE"])
def test_ecriture_sur_la_collection_est_refusee_en_405(client, connecte, methode):
    reponse = client.request(methode, URL)
    assert reponse.status_code == 405
    assert reponse.json()["erreur"]["code"] == "requete_invalide"


@pytest.mark.parametrize("methode", ["GET", "PUT", "PATCH", "DELETE"])
def test_aucune_route_sur_une_categorie_precise(client, connecte, methode):
    reponse = client.request(methode, f"{URL}/{uuid4()}")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"
