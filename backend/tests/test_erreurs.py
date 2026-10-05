from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.erreurs import ErreurApi
from app.core.gestionnaires import installer_gestionnaires
from app.main import app as app_cashmire

MOT_DE_PASSE_SECRET = "Secr3t!"


class Inscription(BaseModel):
    email: str
    mot_de_passe: str = Field(min_length=10)
    montant: Decimal = Field(gt=0)


def creer_app_de_test() -> FastAPI:
    """Petite application dédiée qui déclenche chaque type d'erreur."""
    app = FastAPI()
    installer_gestionnaires(app)

    @app.get("/erreur/{statut}")
    def lever_erreur(statut: int):
        raise ErreurApi(statut, "Message de test.")

    @app.get("/conflit")
    def lever_conflit():
        raise ErreurApi(409, "Doublon.", champs={"email": "Déjà utilisé."})

    @app.post("/valider")
    def valider(donnees: Inscription):
        return {"ok": True}

    @app.get("/liste")
    def liste(limite: int = 20):
        return {"limite": limite}

    @app.get("/boom")
    def boom():
        raise RuntimeError("SELECT * FROM utilisateurs WHERE mot_de_passe_hache = 'x'")

    return app


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False : on veut voir la réponse 500, pas l'exception.
    return TestClient(creer_app_de_test(), raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("statut", "code"),
    [
        (400, "requete_invalide"),
        (401, "non_authentifie"),
        (404, "introuvable"),
        (409, "conflit"),
        (422, "donnees_invalides"),
        (429, "trop_de_tentatives"),
    ],
)
def test_erreur_api_renvoie_le_code_du_contrat(client, statut, code):
    reponse = client.get(f"/erreur/{statut}")
    assert reponse.status_code == statut
    assert reponse.json() == {"erreur": {"code": code, "message": "Message de test."}}


def test_champs_est_omis_quand_il_n_y_en_a_pas(client):
    assert "champs" not in client.get("/erreur/404").json()["erreur"]


def test_champs_est_renvoye_quand_il_est_fourni(client):
    reponse = client.get("/conflit")
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["champs"] == {"email": "Déjà utilisé."}


def test_validation_renvoie_422_avec_les_champs_en_francais(client):
    reponse = client.post(
        "/valider", json={"email": "a@b.c", "mot_de_passe": MOT_DE_PASSE_SECRET, "montant": "-5"}
    )
    assert reponse.status_code == 422
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "donnees_invalides"
    assert erreur["champs"] == {
        "mot_de_passe": "Valeur trop courte.",
        "montant": "Valeur trop petite.",
    }


def test_validation_signale_un_champ_obligatoire_manquant(client):
    reponse = client.post("/valider", json={"email": "a@b.c", "montant": "5"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"mot_de_passe": "Champ obligatoire."}


def test_validation_signale_un_mauvais_format(client):
    reponse = client.get("/liste", params={"limite": "abc"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"limite": "Format invalide."}


def test_validation_ne_renvoie_jamais_la_valeur_envoyee(client):
    reponse = client.post(
        "/valider", json={"email": "a@b.c", "mot_de_passe": MOT_DE_PASSE_SECRET, "montant": "-5"}
    )
    assert MOT_DE_PASSE_SECRET not in reponse.text
    assert "input" not in reponse.text
    assert "detail" not in reponse.text


def test_json_mal_forme_renvoie_400(client):
    reponse = client.post(
        "/valider", content="{pas du json", headers={"Content-Type": "application/json"}
    )
    assert reponse.status_code == 400
    assert reponse.json()["erreur"]["code"] == "requete_invalide"


def test_erreur_http_de_starlette_garde_son_statut_et_le_format(client):
    reponse = client.post("/erreur/404")
    assert reponse.status_code == 405
    assert reponse.json() == {
        "erreur": {"code": "requete_invalide", "message": "Méthode non autorisée."}
    }


def test_exception_inattendue_renvoie_une_500_generique(client):
    reponse = client.get("/boom")
    assert reponse.status_code == 500
    assert reponse.json() == {
        "erreur": {"code": "erreur_interne", "message": "Une erreur interne est survenue."}
    }
    for fuite in ("SELECT", "utilisateurs", "RuntimeError", "Traceback"):
        assert fuite not in reponse.text


def test_route_inconnue_de_l_application_renvoie_404_au_format_commun():
    reponse = TestClient(app_cashmire).get("/api/n-existe-pas")
    assert reponse.status_code == 404
    assert reponse.json() == {"erreur": {"code": "introuvable", "message": "Ressource introuvable."}}
