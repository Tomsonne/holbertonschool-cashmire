"""Création d'une dépense (#13) : POST /api/depenses.

Les tests utilisent les fixtures de conftest.py (base de test dédiée). L'utilisateur connecté est
simulé en remplaçant la dépendance `utilisateur_courant` ; la vraie lecture du JWT relève de #9.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.authentification import utilisateur_courant
from app.main import app
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.models.utilisateur import Utilisateur

URL = "/api/depenses"


def _creer_utilisateur(db_session, email: str) -> Utilisateur:
    utilisateur = Utilisateur(email=email, mot_de_passe_hache="hash-de-test", nom_affichage="Test")
    db_session.add(utilisateur)
    db_session.commit()
    db_session.refresh(utilisateur)
    return utilisateur


@pytest.fixture
def utilisateur(db_session) -> Utilisateur:
    return _creer_utilisateur(db_session, "alice@example.com")


@pytest.fixture
def connecte(utilisateur):
    """Simule un utilisateur connecté (remplace la dépendance de #9)."""
    app.dependency_overrides[utilisateur_courant] = lambda: utilisateur
    try:
        yield utilisateur
    finally:
        app.dependency_overrides.pop(utilisateur_courant, None)


@pytest.fixture
def categorie(db_session) -> Categorie:
    return db_session.scalar(select(Categorie).where(Categorie.nom == "Loisirs"))


def _corps(categorie: Categorie, **surcharges) -> dict:
    corps = {
        "montant": "12.50",
        "libelle": "Cinéma",
        "date_depense": date.today().isoformat(),
        "categorie_id": str(categorie.id),
    }
    corps.update(surcharges)
    return corps


def _nombre_de_depenses(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(Depense))


# --- Création valide ---------------------------------------------------------------------


def test_creation_valide_renvoie_201_et_la_depense(client, connecte, categorie):
    reponse = client.post(URL, json=_corps(categorie))
    assert reponse.status_code == 201
    corps = reponse.json()
    assert set(corps) == {"id", "montant", "libelle", "date_depense", "categorie"}
    assert corps["montant"] == "12.50"
    assert corps["libelle"] == "Cinéma"
    assert corps["date_depense"] == date.today().isoformat()
    assert corps["categorie"] == {"id": str(categorie.id), "nom": "Loisirs"}


def test_la_depense_est_enregistree_pour_l_utilisateur_connecte(
    client, connecte, categorie, db_session
):
    reponse = client.post(URL, json=_corps(categorie))
    depense = db_session.get(Depense, reponse.json()["id"])
    assert depense.utilisateur_id == connecte.id
    assert depense.categorie_id == categorie.id
    assert depense.montant == Decimal("12.50")
    assert depense.libelle == "Cinéma"


@pytest.mark.parametrize("montant", ["0.01", "0.10", "1234.56", "9999999999.99"])
def test_la_precision_decimale_est_conservee(client, connecte, categorie, db_session, montant):
    reponse = client.post(URL, json=_corps(categorie, montant=montant))
    assert reponse.status_code == 201
    assert reponse.json()["montant"] == montant
    assert db_session.get(Depense, reponse.json()["id"]).montant == Decimal(montant)


def test_un_montant_a_une_decimale_est_renvoye_avec_deux(client, connecte, categorie):
    reponse = client.post(URL, json=_corps(categorie, montant="12.5"))
    assert reponse.status_code == 201
    assert reponse.json()["montant"] == "12.50"


def test_les_espaces_autour_du_libelle_sont_retires(client, connecte, categorie):
    reponse = client.post(URL, json=_corps(categorie, libelle="  Courses  "))
    assert reponse.status_code == 201
    assert reponse.json()["libelle"] == "Courses"


@pytest.mark.parametrize("decalage", [0, -1, -365, 1])
def test_dates_acceptees(client, connecte, categorie, decalage):
    jour = (date.today() + timedelta(days=decalage)).isoformat()
    reponse = client.post(URL, json=_corps(categorie, date_depense=jour))
    assert reponse.status_code == 201
    assert reponse.json()["date_depense"] == jour


# --- Le propriétaire vient de l'authentification, jamais du client --------------------------


def test_un_utilisateur_id_envoye_par_le_client_est_ignore(
    client, connecte, categorie, db_session
):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    reponse = client.post(URL, json=_corps(categorie, utilisateur_id=str(autre.id)))
    assert reponse.status_code == 201
    assert "utilisateur_id" not in reponse.json()
    depense = db_session.get(Depense, reponse.json()["id"])
    assert depense.utilisateur_id == connecte.id
    assert depense.utilisateur_id != autre.id


def test_sans_authentification_renvoie_401_et_n_enregistre_rien(client, categorie, db_session):
    reponse = client.post(URL, json=_corps(categorie))
    assert reponse.status_code == 401
    assert reponse.json()["erreur"]["code"] == "non_authentifie"
    assert _nombre_de_depenses(db_session) == 0


# --- Refus : données invalides -------------------------------------------------------------


@pytest.mark.parametrize("montant", ["0", "0.00", "-5", "12.345", "abc", "", 12.5, 12, None])
def test_montant_invalide_renvoie_422(client, connecte, categorie, db_session, montant):
    reponse = client.post(URL, json=_corps(categorie, montant=montant))
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"
    assert "montant" in reponse.json()["erreur"]["champs"]
    assert _nombre_de_depenses(db_session) == 0


@pytest.mark.parametrize("libelle", ["", "   ", "x" * 201, None, 123])
def test_libelle_invalide_renvoie_422(client, connecte, categorie, db_session, libelle):
    reponse = client.post(URL, json=_corps(categorie, libelle=libelle))
    assert reponse.status_code == 422
    assert "libelle" in reponse.json()["erreur"]["champs"]
    assert _nombre_de_depenses(db_session) == 0


def test_libelle_de_200_caracteres_est_accepte(client, connecte, categorie):
    reponse = client.post(URL, json=_corps(categorie, libelle="x" * 200))
    assert reponse.status_code == 201


@pytest.mark.parametrize(
    "jour", ["pas une date", "2026-13-45", "", None, "1999-12-31", "2100-01-01"]
)
def test_date_invalide_ou_hors_periode_renvoie_422(client, connecte, categorie, db_session, jour):
    reponse = client.post(URL, json=_corps(categorie, date_depense=jour))
    assert reponse.status_code == 422
    assert "date_depense" in reponse.json()["erreur"]["champs"]
    assert _nombre_de_depenses(db_session) == 0


def test_date_dans_deux_jours_est_refusee(client, connecte, categorie):
    jour = (date.today() + timedelta(days=2)).isoformat()
    reponse = client.post(URL, json=_corps(categorie, date_depense=jour))
    assert reponse.status_code == 422


@pytest.mark.parametrize("champ", ["montant", "libelle", "date_depense", "categorie_id"])
def test_champ_obligatoire_manquant_renvoie_422(client, connecte, categorie, db_session, champ):
    corps = _corps(categorie)
    del corps[champ]
    reponse = client.post(URL, json=corps)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {champ: "Champ obligatoire."}
    assert _nombre_de_depenses(db_session) == 0


def test_categorie_id_mal_forme_renvoie_422(client, connecte, categorie):
    reponse = client.post(URL, json=_corps(categorie, categorie_id="pas-un-uuid"))
    assert reponse.status_code == 422
    assert "categorie_id" in reponse.json()["erreur"]["champs"]


def test_corps_non_json_renvoie_400(client, connecte):
    reponse = client.post(URL, content="{pas du json", headers={"Content-Type": "application/json"})
    assert reponse.status_code == 400
    assert reponse.json()["erreur"]["code"] == "requete_invalide"


# --- Refus : catégorie inconnue ------------------------------------------------------------


def test_categorie_inconnue_renvoie_404_et_n_enregistre_rien(
    client, connecte, categorie, db_session
):
    reponse = client.post(URL, json=_corps(categorie, categorie_id="00000000-0000-4000-8000-000000000000"))
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"
    assert reponse.json()["erreur"]["champs"] == {"categorie_id": "Catégorie inconnue."}
    assert _nombre_de_depenses(db_session) == 0


# --- Avec la vraie authentification (cookie JWT posé par la connexion) -----------------------


def _se_connecter(client, email: str) -> dict:
    identifiants = {"email": email, "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post(
        "/api/authentification/inscription", json={**identifiants, "nom_affichage": "Test"}
    ).status_code == 201
    assert client.post("/api/authentification/connexion", json=identifiants).status_code == 200
    return client.get("/api/authentification/moi").json()


def test_creation_avec_un_vrai_cookie_appartient_a_l_utilisateur_connecte(
    client, categorie, db_session
):
    moi = _se_connecter(client, "alice@example.com")
    reponse = client.post(URL, json=_corps(categorie))
    assert reponse.status_code == 201
    depense = db_session.get(Depense, reponse.json()["id"])
    assert str(depense.utilisateur_id) == moi["id"]


def test_deux_utilisateurs_ont_chacun_leurs_depenses(client, categorie, db_session):
    from fastapi.testclient import TestClient

    moi_alice = _se_connecter(client, "alice@example.com")
    client_bob = TestClient(app, raise_server_exceptions=False)
    moi_bob = _se_connecter(client_bob, "bob@example.com")
    # Bob essaie d'imputer sa dépense à Alice via le corps de la requête : sans effet.
    reponse = client_bob.post(URL, json=_corps(categorie, utilisateur_id=moi_alice["id"]))
    assert reponse.status_code == 201
    depense = db_session.get(Depense, reponse.json()["id"])
    assert str(depense.utilisateur_id) == moi_bob["id"]
    assert str(depense.utilisateur_id) != moi_alice["id"]


def test_cookie_falsifie_renvoie_401_et_n_enregistre_rien(client, categorie, db_session):
    _se_connecter(client, "alice@example.com")
    for cookie in client.cookies.jar:
        cookie.value = cookie.value[:-3] + "xxx"
    reponse = client.post(URL, json=_corps(categorie))
    assert reponse.status_code == 401
    assert _nombre_de_depenses(db_session) == 0
