from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.gestionnaires import installer_gestionnaires
from app.schemas.montant import Montant, MontantPositif


class Depense(BaseModel):
    montant: MontantPositif


class Solde(BaseModel):
    reste: Montant


def creer_app_de_test() -> FastAPI:
    app = FastAPI()
    installer_gestionnaires(app)

    @app.post("/depenses", response_model=Depense)
    def creer(depense: Depense):
        return depense

    @app.post("/soldes", response_model=Solde)
    def solde(solde: Solde):
        return solde

    @app.get("/sortie/{valeur}", response_model=Depense)
    def sortie(valeur: str):
        # Valeur construite en Python, comme le ferait un service qui lit la base ou calcule.
        return Depense(montant=Decimal(valeur))

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(creer_app_de_test())


# --- Sortie : toujours une chaîne à deux décimales -------------------------------------------


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [("12.5", "12.50"), ("12.50", "12.50"), ("300", "300.00"), ("0.1", "0.10"), ("9999999999.99", "9999999999.99")],
)
def test_sortie_est_une_chaine_a_deux_decimales(client, valeur, attendu):
    reponse = client.get(f"/sortie/{valeur}")
    assert reponse.json() == {"montant": attendu}
    assert isinstance(reponse.json()["montant"], str)


def test_sortie_negative_est_possible_pour_un_montant_quelconque(client):
    reponse = client.post("/soldes", json={"reste": "-44.60"})
    assert reponse.status_code == 200
    assert reponse.json() == {"reste": "-44.60"}


def test_la_valeur_reste_un_decimal_exact_en_python():
    assert Depense(montant="0.10").montant + Depense(montant="0.20").montant == Decimal("0.30")
    assert isinstance(Depense(montant="12.50").montant, Decimal)


# --- Entrée : chaîne décimale valide uniquement --------------------------------------------


def test_entree_chaine_valide_est_acceptee(client):
    reponse = client.post("/depenses", json={"montant": "12.50"})
    assert reponse.status_code == 200
    assert reponse.json() == {"montant": "12.50"}


@pytest.mark.parametrize("valeur", [12.5, 12, True, None])
def test_entree_nombre_json_est_refusee(client, valeur):
    reponse = client.post("/depenses", json={"montant": valeur})
    assert reponse.status_code == 422
    assert "montant" in reponse.json()["erreur"]["champs"]


def test_entree_avec_trois_decimales_est_refusee_au_lieu_d_etre_arrondie(client):
    reponse = client.post("/depenses", json={"montant": "12.345"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"montant": "Deux décimales maximum."}


@pytest.mark.parametrize("valeur", ["10000000000", "12345678901.00", "99999999999999.99"])
def test_entree_trop_grande_est_refusee_car_la_base_la_rejetterait(client, valeur):
    # NUMERIC(12,2) : 10 chiffres avant la virgule au plus. Sans ce contrôle, l'insertion
    # échouerait en base avec une erreur 500.
    reponse = client.post("/depenses", json={"montant": valeur})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"montant": "Valeur trop grande."}


def test_montant_negatif_trop_grand_est_refuse(client):
    reponse = client.post("/soldes", json={"reste": "-10000000000"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"reste": "Valeur trop petite."}


def test_plus_grand_montant_accepte_est_9999999999_99(client):
    reponse = client.post("/depenses", json={"montant": "9999999999.99"})
    assert reponse.status_code == 200
    assert reponse.json() == {"montant": "9999999999.99"}


@pytest.mark.parametrize("valeur", ["0", "0.00", "-5"])
def test_montant_positif_refuse_zero_et_negatif(client, valeur):
    reponse = client.post("/depenses", json={"montant": valeur})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"montant": "Valeur trop petite."}


@pytest.mark.parametrize("valeur", ["abc", "", "12,50", "NaN", "Infinity"])
def test_entree_non_numerique_est_refusee(client, valeur):
    reponse = client.post("/depenses", json={"montant": valeur})
    assert reponse.status_code == 422
    assert "montant" in reponse.json()["erreur"]["champs"]
