"""Tests de la vérification d'origine (dépendance globale `verifier_origine`) et de sa configuration.

Hypothèses sur tests/conftest.py : ALLOWED_ORIGINS ne contient que `http://localhost:5173`,
affecté avant l'import de l'application ; la fixture `client` envoie cette origine par défaut ;
le limiteur est remis à zéro avant chaque test.

La matrice des méthodes utilise une petite application dédiée : l'API n'a aucune route PUT, et
une méthode sans route répond 405 avant toute dépendance.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.gestionnaires import installer_gestionnaires
from app.core.origine import verifier_origine

ORIGINE_AUTORISEE = settings.origines_autorisees[0]
MAUVAISE_ORIGINE = "https://malveillant.example"
CORPS_403 = {"erreur": {"code": "origine_refusee", "message": "Origine non autorisée."}}
METHODES_ECRITURE = ["POST", "PUT", "PATCH", "DELETE"]
URL_INSCRIPTION = "/api/authentification/inscription"
URL_CONNEXION = "/api/authentification/connexion"
EMAIL = "ada@x.fr"
MOT_DE_PASSE = "Un-mot-de-passe-valide"


def creer_app_de_test() -> FastAPI:
    app = FastAPI(dependencies=[Depends(verifier_origine)])
    installer_gestionnaires(app)

    @app.api_route("/ressource", methods=["GET", "HEAD", "OPTIONS", *METHODES_ECRITURE])
    def ressource():
        return {"ok": True}

    return app


@pytest.fixture
def client_brut() -> TestClient:
    """Client sans en-tête par défaut : chaque test choisit Origin et Referer."""
    return TestClient(creer_app_de_test(), raise_server_exceptions=False)


def assert_refus(reponse):
    assert reponse.status_code == 403
    # Format commun, sans `champs`.
    assert reponse.json() == CORPS_403


# --- Méthodes contrôlées ---------------------------------------------------------------------


@pytest.mark.parametrize("methode", METHODES_ECRITURE)
def test_ecriture_avec_origine_autorisee_passe(client_brut, methode):
    reponse = client_brut.request(methode, "/ressource", headers={"Origin": ORIGINE_AUTORISEE})
    assert reponse.status_code == 200


@pytest.mark.parametrize("methode", METHODES_ECRITURE)
def test_ecriture_avec_origine_inconnue_est_refusee(client_brut, methode):
    assert_refus(client_brut.request(methode, "/ressource", headers={"Origin": MAUVAISE_ORIGINE}))


@pytest.mark.parametrize("methode", ["GET", "HEAD", "OPTIONS"])
def test_lecture_sans_origine_passe(client_brut, methode):
    assert client_brut.request(methode, "/ressource").status_code == 200


@pytest.mark.parametrize("methode", ["GET", "HEAD", "OPTIONS"])
def test_lecture_avec_origine_inconnue_passe(client_brut, methode):
    reponse = client_brut.request(methode, "/ressource", headers={"Origin": MAUVAISE_ORIGINE})
    assert reponse.status_code == 200


# --- Règle Origin puis Referer ----------------------------------------------------------------


@pytest.mark.parametrize(
    "origine",
    [
        "null",
        "",
        # Comparaison exacte : ni `/` final, ni autre port, ni autre schéma, ni autre casse.
        f"{ORIGINE_AUTORISEE}/",
        "http://localhost:5174",
        "https://localhost:5173",
        "http://LOCALHOST:5173",
        "http://localhost:5173.malveillant.example",
    ],
)
def test_origin_hors_liste_est_refuse(client_brut, origine):
    assert_refus(client_brut.post("/ressource", headers={"Origin": origine}))


def test_sans_origin_ni_referer_est_refuse(client_brut):
    assert_refus(client_brut.post("/ressource"))


def test_sans_origin_avec_referer_autorise_passe(client_brut):
    reponse = client_brut.post("/ressource", headers={"Referer": f"{ORIGINE_AUTORISEE}/budgets?mois=2026-10"})
    assert reponse.status_code == 200


@pytest.mark.parametrize(
    "referer",
    [
        f"{MAUVAISE_ORIGINE}/page",
        "http://localhost:5173.malveillant.example/",
        "http://localhost:5174/",
        "pas-une-url",
        "",
        "http://[abc/",
        "http://localhost:5173@malveillant.example/",
    ],
)
def test_sans_origin_avec_referer_refuse_est_refuse(client_brut, referer):
    assert_refus(client_brut.post("/ressource", headers={"Referer": referer}))


def test_origin_refuse_l_emporte_sur_un_referer_autorise(client_brut):
    reponse = client_brut.post(
        "/ressource", headers={"Origin": MAUVAISE_ORIGINE, "Referer": f"{ORIGINE_AUTORISEE}/"}
    )
    assert_refus(reponse)


# --- Application réelle -----------------------------------------------------------------------


def inscrire(client):
    reponse = client.post(
        URL_INSCRIPTION, json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE, "nom_affichage": "Ada"}
    )
    assert reponse.status_code == 201


def test_inscription_avec_origine_autorisee_passe(client):
    inscrire(client)


@pytest.mark.parametrize(
    ("url", "corps"),
    [
        (URL_INSCRIPTION, {"email": EMAIL, "mot_de_passe": MOT_DE_PASSE, "nom_affichage": "Ada"}),
        (URL_CONNEXION, {"email": EMAIL, "mot_de_passe": MOT_DE_PASSE}),
        # Sans cookie : 403 et pas 401, l'origine est vérifiée avant l'authentification.
        ("/api/authentification/deconnexion", None),
    ],
)
def test_routes_d_authentification_refusent_une_mauvaise_origine(client, url, corps):
    assert_refus(client.post(url, json=corps, headers={"Origin": MAUVAISE_ORIGINE}))


def test_mauvaise_origine_et_corps_invalide_donnent_403_et_pas_422(client):
    reponse = client.post(
        URL_INSCRIPTION, json={"email": "pas-un-email"}, headers={"Origin": MAUVAISE_ORIGINE}
    )
    assert_refus(reponse)


def test_ecriture_sur_route_inconnue_donne_404(client):
    reponse = client.post("/api/n-existe-pas", headers={"Origin": MAUVAISE_ORIGINE})
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"


def test_get_sans_origine_atteint_la_route(client):
    del client.headers["origin"]
    # 401 et pas 403 : la route a été atteinte.
    assert client.get("/api/authentification/moi").status_code == 401


def test_connexions_refusees_n_incrementent_pas_le_limiteur(client):
    inscrire(client)
    mauvais = {"email": EMAIL, "mot_de_passe": "mauvais-mot-de-passe"}
    for _ in range(5):
        assert_refus(client.post(URL_CONNEXION, json=mauvais, headers={"Origin": MAUVAISE_ORIGINE}))
    # Si les refus avaient compté, cette tentative recevrait 429.
    reponse = client.post(URL_CONNEXION, json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE})
    assert reponse.status_code == 200


# --- Configuration ------------------------------------------------------------------------------


@pytest.fixture
def env_minimal(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    return monkeypatch


def test_valeurs_par_defaut(env_minimal):
    reglages = Settings(_env_file=None)
    assert reglages.origines_autorisees == ["http://localhost:5173"]
    assert reglages.environment == "development"


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        ("http://localhost:5173,https://cashmire.example", ["http://localhost:5173", "https://cashmire.example"]),
        (
            " http://localhost:5173 , https://cashmire.example:8443 ",
            ["http://localhost:5173", "https://cashmire.example:8443"],
        ),
        ("http://127.0.0.1:8080", ["http://127.0.0.1:8080"]),
    ],
)
def test_allowed_origins_valides(env_minimal, valeur, attendu):
    env_minimal.setenv("ALLOWED_ORIGINS", valeur)
    assert Settings(_env_file=None).origines_autorisees == attendu


@pytest.mark.parametrize(
    "valeur",
    [
        "*",
        "http://*",
        "http://localhost:5173,*",
        "http://localhost:5173/",
        "http://localhost:5173/app",
        "localhost:5173",
        "//localhost:5173",
        "ftp://localhost",
        "http://localhost:5173,",
        ",http://localhost:5173",
        "",
        " ",
    ],
)
def test_allowed_origins_invalides_empechent_de_demarrer(env_minimal, valeur):
    env_minimal.setenv("ALLOWED_ORIGINS", valeur)
    with pytest.raises(ValidationError) as info:
        Settings(_env_file=None)
    if valeur.strip():
        # L'erreur ne recopie pas la valeur fournie.
        assert valeur not in str(info.value)


@pytest.mark.parametrize("valeur", ["prod", "Production", "dev", "test", ""])
def test_environment_inconnu_empeche_de_demarrer(env_minimal, valeur):
    env_minimal.setenv("ENVIRONMENT", valeur)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_environment_production_est_accepte(env_minimal):
    env_minimal.setenv("ENVIRONMENT", "production")
    assert Settings(_env_file=None).environment == "production"
