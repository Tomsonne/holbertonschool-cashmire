import re
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.core.gestionnaires import installer_gestionnaires
from app.schemas.montant import Montant, MontantCalcule, MontantPositif


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


# --- Contrat strict : seules les écritures annoncées sont acceptées ----------------------------


@pytest.mark.parametrize(
    "valeur",
    ["1e2", "1E1", "+5", " 12.5", "12.5 ", "12.", ".5", "1_000", "١٢.٥٠", "٣", "12.5e0", "0x10"],
)
def test_ecritures_non_decimales_sont_refusees(client, valeur):
    # Pydantic accepterait toutes ces chaînes ; le contrat de l'API n'annonce que « 12.50 ».
    reponse = client.post("/depenses", json={"montant": valeur})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"montant": "Valeur invalide."}


def test_zeros_de_fin_au_dela_de_deux_decimales_sont_refuses(client):
    reponse = client.post("/depenses", json={"montant": "12.500"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"montant": "Deux décimales maximum."}


def test_plus_de_dix_chiffres_avant_la_virgule_sont_refuses_meme_avec_des_zeros_devant(client):
    reponse = client.post("/depenses", json={"montant": "0000000000000001"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["champs"] == {"montant": "Valeur trop grande."}


@pytest.mark.parametrize("valeur", ["12", "12.5", "12.50", "0012.50", "0.01", "9999999999.99"])
def test_ecritures_annoncees_restent_acceptees(client, valeur):
    assert client.post("/depenses", json={"montant": valeur}).status_code == 200


def test_le_motif_publie_dans_l_openapi_correspond_exactement_a_la_validation():
    """Ce que le contrat annonce (motif de l'OpenAPI) = ce que l'API accepte vraiment."""
    schema = TypeAdapter(MontantPositif).json_schema(mode="validation")
    motif = re.compile(schema["pattern"])
    validateur = TypeAdapter(MontantPositif)
    # Valeurs strictement positives seulement : « 0 » correspond au motif mais est refusé à part.
    echantillon = [
        "12", "12.5", "12.50", "0012.50", "0.01", "9999999999.99", "1", "01.5", "5.00",
        "1e2", "1E1", "+5", " 1", "1 ", "12.", ".5", "1_000", "12.500", "12.345",
        "0000000000000001", "10000000000", "99999999999", "abc", "", "12,50", "-5",
        "١٢.٥٠", "٣", "1.", "..", "1.2.3", "NaN", "Infinity",
    ]
    for valeur in echantillon:
        try:
            validateur.validate_python(valeur)
            accepte = True
        except ValidationError:
            accepte = False
        assert accepte == bool(motif.fullmatch(valeur)), (
            f"{valeur!r} : validation={accepte}, motif publié={bool(motif.fullmatch(valeur))}"
        )


# --- Montant calculé : une somme n'est pas bornée à 10 chiffres ----------------------------------


class Somme(BaseModel):
    total: MontantCalcule


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        (Decimal("19999999999.98"), "19999999999.98"),
        ("123456789012.50", "123456789012.50"),
        ("-19999999899.98", "-19999999899.98"),
        (Decimal("0.1"), "0.10"),
    ],
)
def test_un_montant_calcule_n_est_pas_borne_a_dix_chiffres(valeur, attendu):
    assert Somme(total=valeur).model_dump(mode="json") == {"total": attendu}


@pytest.mark.parametrize("valeur", [12.5, 12, True, None, "1e2", "+5", " 1.00", "12.345", "abc", ""])
def test_un_montant_calcule_refuse_les_ecritures_non_decimales(valeur):
    with pytest.raises(ValidationError):
        Somme(total=valeur)


def test_un_montant_saisi_reste_borne_alors_qu_un_montant_calcule_ne_l_est_pas():
    with pytest.raises(ValidationError):
        TypeAdapter(MontantPositif).validate_python("10000000000")
    assert Somme(total="10000000000.00").total == Decimal("10000000000.00")
