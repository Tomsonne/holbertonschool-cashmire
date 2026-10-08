"""Consommation d'un budget supérieure à 10 chiffres (#59).

Un montant saisi est limité à 10 chiffres avant la virgule (`NUMERIC(12,2)`), mais la consommation
d'un budget est une **somme** de dépenses : elle peut légitimement dépasser cette limite. Elle ne
doit jamais faire échouer la réponse (500), ni rendre la liste des budgets illisible.

Les tests utilisent un vrai cookie (inscription puis connexion).
"""

from datetime import date

import pytest

AUJOURD_HUI = date.today().isoformat()
MOIS = date.today().strftime("%Y-%m")
GROS_MONTANT = "9999999999.99"  # le plus grand montant qu'une dépense peut avoir


@pytest.fixture
def connecte(client):
    identifiants = {"email": "ada@example.com", "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post(
        "/api/authentification/inscription", json={**identifiants, "nom_affichage": "Ada"}
    ).status_code == 201
    assert client.post("/api/authentification/connexion", json=identifiants).status_code == 200
    return client


def _categorie(client) -> str:
    return client.get("/api/categories").json()[0]["id"]


def _depenser(client, categorie: str, montant: str) -> None:
    reponse = client.post(
        "/api/depenses",
        json={"montant": montant, "libelle": "Gros achat", "date_depense": AUJOURD_HUI, "categorie_id": categorie},
    )
    assert reponse.status_code == 201


def _creer_budget(client, categorie: str, limite: str = "100.00"):
    return client.post("/api/budgets", json={"categorie_id": categorie, "montant_limite": limite, "mois": MOIS})


@pytest.fixture
def budget_enorme(connecte):
    """Deux dépenses de 9 999 999 999,99 puis un budget de 100 € : consommation de 19 999 999 999,98."""
    categorie = _categorie(connecte)
    _depenser(connecte, categorie, GROS_MONTANT)
    _depenser(connecte, categorie, GROS_MONTANT)
    reponse = _creer_budget(connecte, categorie)
    return connecte, categorie, reponse


def test_la_creation_d_un_budget_dont_la_consommation_depasse_10_chiffres_reussit(budget_enorme):
    _, _, creation = budget_enorme
    assert creation.status_code == 201  # avant la correction : 500, alors que le budget était créé
    corps = creation.json()
    assert corps["depense"] == "19999999999.98"
    assert corps["reste"] == "-19999999899.98"
    assert corps["statut"] == "depasse"
    assert corps["pourcentage"] == pytest.approx(19999999999.98)


def test_le_detail_et_la_liste_du_mois_repondent_au_lieu_d_echouer_en_permanence(budget_enorme):
    client, _, creation = budget_enorme
    budget = creation.json()
    detail = client.get(f"/api/budgets/{budget['id']}")
    liste = client.get("/api/budgets", params={"mois": MOIS})
    assert detail.status_code == 200
    assert detail.json() == budget
    assert liste.status_code == 200  # avant la correction : 500 en permanence pour ce mois
    assert liste.json() == [budget]


def test_le_budget_n_est_cree_qu_une_fois(budget_enorme):
    client, categorie, _ = budget_enorme
    # Avant la correction, la première création répondait 500 mais enregistrait le budget : le
    # relancer donnait 409. Maintenant, la première réussit et la seconde seule est un doublon.
    assert _creer_budget(client, categorie).status_code == 409


def test_la_consommation_continue_de_croitre_sans_borne(budget_enorme):
    client, categorie, _ = budget_enorme
    _depenser(client, categorie, GROS_MONTANT)
    budget = client.get("/api/budgets", params={"mois": MOIS}).json()[0]
    assert budget["depense"] == "29999999999.97"
    assert budget["reste"] == "-29999999899.97"


def test_modifier_un_budget_enorme_renvoie_aussi_la_consommation(budget_enorme):
    client, _, creation = budget_enorme
    reponse = client.patch(f"/api/budgets/{creation.json()['id']}", json={"montant_limite": "50.00"})
    assert reponse.status_code == 200
    assert reponse.json()["depense"] == "19999999999.98"
    assert reponse.json()["reste"] == "-19999999949.98"


def test_supprimer_un_budget_enorme_conserve_les_depenses(budget_enorme):
    client, _, creation = budget_enorme
    assert client.delete(f"/api/budgets/{creation.json()['id']}").status_code == 204
    assert client.get("/api/depenses").json()["total"] == 2


def test_les_montants_saisis_restent_bornes_a_10_chiffres(connecte):
    categorie = _categorie(connecte)
    assert _creer_budget(connecte, categorie, "10000000000").status_code == 422
    depense = connecte.post(
        "/api/depenses",
        json={"montant": "10000000000", "libelle": "x", "date_depense": AUJOURD_HUI, "categorie_id": categorie},
    )
    assert depense.status_code == 422


def test_une_consommation_normale_est_inchangee(connecte):
    categorie = _categorie(connecte)
    _depenser(connecte, categorie, "30.00")
    corps = _creer_budget(connecte, categorie).json()
    assert (corps["depense"], corps["reste"], corps["statut"]) == ("30.00", "70.00", "ok")
