"""Isolation des données entre utilisateurs (#25).

Ces tests regroupent la preuve qu'un utilisateur ne voit, ne modifie et ne supprime jamais les
données d'un autre, et qu'aucune route privée n'est accessible sans connexion. Ils complètent les
tests d'isolation de chaque route (dépenses, budgets) par une vue d'ensemble, avec de vrais cookies
JWT (inscription puis connexion) et non un utilisateur simulé.

Un client créé à la main envoie `Origin` : la fixture `client` le fait déjà, pas `TestClient(app)`.
"""

from datetime import date
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.budget import Budget
from app.models.categorie import Categorie
from app.models.depense import Depense
from app.models.utilisateur import Utilisateur

ORIGINE = "http://localhost:5173"
AUJOURD_HUI = date.today().isoformat()
MOIS = date.today().strftime("%Y-%m")

# Les seules routes ouvertes sans connexion : s'en ajouter une exige de modifier cette liste.
ROUTES_PUBLIQUES = {
    ("GET", "/api/health"),
    ("POST", "/api/authentification/inscription"),
    ("POST", "/api/authentification/connexion"),
}


def _nouveau_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False, headers={"Origin": ORIGINE})


def _se_connecter(client: TestClient, email: str) -> dict:
    identifiants = {"email": email, "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post(
        "/api/authentification/inscription", json={**identifiants, "nom_affichage": "Test"}
    ).status_code == 201
    assert client.post("/api/authentification/connexion", json=identifiants).status_code == 200
    return client.get("/api/authentification/moi").json()


def _categorie(db_session, nom: str) -> Categorie:
    return db_session.scalar(select(Categorie).where(Categorie.nom == nom))


def _depense(client, categorie, montant: str, libelle: str) -> dict:
    reponse = client.post(
        "/api/depenses",
        json={
            "montant": montant,
            "libelle": libelle,
            "date_depense": AUJOURD_HUI,
            "categorie_id": str(categorie.id),
        },
    )
    assert reponse.status_code == 201
    return reponse.json()


def _budget(client, categorie, limite: str) -> dict:
    reponse = client.post(
        "/api/budgets",
        json={"categorie_id": str(categorie.id), "montant_limite": limite, "mois": MOIS},
    )
    assert reponse.status_code == 201
    return reponse.json()


@pytest.fixture
def alimentation(db_session) -> Categorie:
    return _categorie(db_session, "Alimentation")


@pytest.fixture
def deux_comptes(client, db_session, alimentation):
    """Alice (via `client`) et Bob (second client) avec chacun des dépenses et un budget.

    Même catégorie et même mois pour les deux : si un filtre par utilisateur manquait, leurs
    données se mélangeraient.
    """
    client_bob = _nouveau_client()
    alice = _se_connecter(client, "alice@example.com")
    bob = _se_connecter(client_bob, "bob@example.com")
    donnees = {
        "alice": {
            "id": alice["id"],
            "depenses": [
                _depense(client, alimentation, "30.00", "Courses d'Alice"),
                _depense(client, alimentation, "20.00", "Repas d'Alice"),
            ],
            "budget": _budget(client, alimentation, "100.00"),
        },
        "bob": {
            "id": bob["id"],
            "depenses": [_depense(client_bob, alimentation, "7.00", "Café de Bob")],
            "budget": _budget(client_bob, alimentation, "200.00"),
        },
    }
    return client, client_bob, donnees


# === 1. Listes et agrégats isolés ===============================================================


def test_les_listes_de_depenses_et_leurs_totaux_sont_isoles(deux_comptes):
    client_alice, client_bob, d = deux_comptes
    chez_alice = client_alice.get("/api/depenses").json()
    chez_bob = client_bob.get("/api/depenses").json()
    assert chez_alice["total"] == 2
    assert {e["libelle"] for e in chez_alice["elements"]} == {"Courses d'Alice", "Repas d'Alice"}
    assert chez_bob["total"] == 1
    assert [e["libelle"] for e in chez_bob["elements"]] == ["Café de Bob"]


def test_le_total_de_la_pagination_ne_compte_pas_les_depenses_de_l_autre(deux_comptes):
    client_alice, client_bob, _ = deux_comptes
    assert client_alice.get("/api/depenses", params={"limite": 1}).json()["total"] == 2
    assert client_bob.get("/api/depenses", params={"limite": 1}).json()["total"] == 1
    mois = {"mois": MOIS}
    assert client_alice.get("/api/depenses", params=mois).json()["total"] == 2
    assert client_bob.get("/api/depenses", params=mois).json()["total"] == 1


def test_les_listes_de_budgets_sont_isolees(deux_comptes):
    client_alice, client_bob, d = deux_comptes
    assert [b["id"] for b in client_alice.get("/api/budgets").json()] == [d["alice"]["budget"]["id"]]
    assert [b["id"] for b in client_bob.get("/api/budgets").json()] == [d["bob"]["budget"]["id"]]


def test_la_consommation_d_un_budget_ne_compte_que_les_depenses_de_son_proprietaire(deux_comptes):
    client_alice, client_bob, d = deux_comptes
    chez_alice = client_alice.get(f"/api/budgets/{d['alice']['budget']['id']}").json()
    chez_bob = client_bob.get(f"/api/budgets/{d['bob']['budget']['id']}").json()
    # 30 + 20 pour Alice sur 100 ; 7 pour Bob sur 200 : jamais 57.
    assert (chez_alice["depense"], chez_alice["reste"]) == ("50.00", "50.00")
    assert (chez_bob["depense"], chez_bob["reste"]) == ("7.00", "193.00")


def test_supprimer_une_depense_ne_change_pas_la_consommation_de_l_autre(deux_comptes):
    client_alice, client_bob, d = deux_comptes
    assert client_alice.delete(f"/api/depenses/{d['alice']['depenses'][0]['id']}").status_code == 204
    chez_bob = client_bob.get(f"/api/budgets/{d['bob']['budget']['id']}").json()
    assert chez_bob["depense"] == "7.00"
    chez_alice = client_alice.get(f"/api/budgets/{d['alice']['budget']['id']}").json()
    assert chez_alice["depense"] == "20.00"


# === 2. Lire, modifier, supprimer la ressource de l'autre : 404 ================================


def _etat(db_session, d):
    """Photographie en base des données d'Alice, pour vérifier que rien n'a bougé."""
    db_session.expire_all()
    depenses = [
        (str(x.id), str(x.montant), x.libelle, x.date_depense, str(x.categorie_id))
        for x in db_session.scalars(
            select(Depense).where(Depense.utilisateur_id == d["alice"]["id"]).order_by(Depense.id)
        )
    ]
    budgets = [
        (str(x.id), str(x.montant_limite), x.seuil_alerte_pct)
        for x in db_session.scalars(select(Budget).where(Budget.utilisateur_id == d["alice"]["id"]))
    ]
    return depenses, budgets


def _requetes_contre(d):
    """Toutes les façons de viser les ressources d'Alice : (méthode, URL, corps)."""
    depense = d["alice"]["depenses"][0]["id"]
    budget = d["alice"]["budget"]["id"]
    return [
        ("GET", f"/api/depenses/{depense}", None),
        ("PATCH", f"/api/depenses/{depense}", {"libelle": "Piratée"}),
        ("PATCH", f"/api/depenses/{depense}", {"montant": "999.00"}),
        ("DELETE", f"/api/depenses/{depense}", None),
        ("GET", f"/api/budgets/{budget}", None),
        ("PATCH", f"/api/budgets/{budget}", {"montant_limite": "1.00"}),
        ("DELETE", f"/api/budgets/{budget}", None),
    ]


def test_bob_ne_peut_ni_lire_ni_modifier_ni_supprimer_les_ressources_d_alice(
    deux_comptes, db_session
):
    _, client_bob, d = deux_comptes
    avant = _etat(db_session, d)
    for methode, url, corps in _requetes_contre(d):
        reponse = client_bob.request(methode, url, json=corps)
        assert reponse.status_code == 404, f"{methode} {url}"
        assert reponse.json()["erreur"]["code"] == "introuvable"
    assert _etat(db_session, d) == avant


def test_alice_non_plus_ne_peut_pas_toucher_aux_ressources_de_bob(deux_comptes, db_session):
    client_alice, _, d = deux_comptes
    depense_bob = d["bob"]["depenses"][0]["id"]
    budget_bob = d["bob"]["budget"]["id"]
    for methode, url, corps in [
        ("GET", f"/api/depenses/{depense_bob}", None),
        ("PATCH", f"/api/depenses/{depense_bob}", {"libelle": "Piratée"}),
        ("DELETE", f"/api/depenses/{depense_bob}", None),
        ("GET", f"/api/budgets/{budget_bob}", None),
        ("PATCH", f"/api/budgets/{budget_bob}", {"montant_limite": "1.00"}),
        ("DELETE", f"/api/budgets/{budget_bob}", None),
    ]:
        assert client_alice.request(methode, url, json=corps).status_code == 404, f"{methode} {url}"
    db_session.expire_all()
    assert db_session.get(Depense, depense_bob).libelle == "Café de Bob"
    assert db_session.get(Budget, budget_bob) is not None


def test_la_ressource_d_autrui_et_la_ressource_inexistante_donnent_la_meme_reponse(deux_comptes):
    # Aucune différence observable : on ne peut pas deviner qu'un identifiant existe chez un autre.
    _, client_bob, d = deux_comptes
    inconnu = uuid4()
    depense = d["alice"]["depenses"][0]["id"]
    budget = d["alice"]["budget"]["id"]
    for methode, url_reelle, url_inconnue, corps in [
        ("GET", f"/api/depenses/{depense}", f"/api/depenses/{inconnu}", None),
        ("PATCH", f"/api/depenses/{depense}", f"/api/depenses/{inconnu}", {"libelle": "x"}),
        ("DELETE", f"/api/depenses/{depense}", f"/api/depenses/{inconnu}", None),
        ("GET", f"/api/budgets/{budget}", f"/api/budgets/{inconnu}", None),
        ("PATCH", f"/api/budgets/{budget}", f"/api/budgets/{inconnu}", {"montant_limite": "1.00"}),
        ("DELETE", f"/api/budgets/{budget}", f"/api/budgets/{inconnu}", None),
    ]:
        chez_autrui = client_bob.request(methode, url_reelle, json=corps)
        inexistante = client_bob.request(methode, url_inconnue, json=corps)
        assert chez_autrui.status_code == inexistante.status_code == 404, f"{methode} {url_reelle}"
        # Statut, code et message identiques : rien ne distingue « existe chez un autre » de « n'existe pas ».
        assert chez_autrui.json() == inexistante.json(), f"{methode} {url_reelle}"


# === 3. Un utilisateur_id fourni par le client ne permet aucune usurpation ====================


def test_un_utilisateur_id_dans_le_corps_d_une_depense_ne_l_attribue_pas_a_alice(
    deux_comptes, db_session, alimentation
):
    _, client_bob, d = deux_comptes
    reponse = client_bob.post(
        "/api/depenses",
        json={
            "montant": "1.00",
            "libelle": "Usurpation",
            "date_depense": AUJOURD_HUI,
            "categorie_id": str(alimentation.id),
            "utilisateur_id": d["alice"]["id"],
        },
    )
    assert reponse.status_code == 201
    depense = db_session.get(Depense, reponse.json()["id"])
    assert str(depense.utilisateur_id) == d["bob"]["id"]  # le propriétaire vient du cookie
    assert "utilisateur_id" not in reponse.json()


def test_un_utilisateur_id_dans_le_corps_d_un_budget_est_refuse_et_rien_n_est_cree(
    deux_comptes, db_session, alimentation
):
    _, client_bob, d = deux_comptes
    avant = db_session.query(Budget).count()
    reponse = client_bob.post(
        "/api/budgets",
        json={
            "categorie_id": str(alimentation.id),
            "montant_limite": "10.00",
            "mois": "2030-01",
            "utilisateur_id": d["alice"]["id"],
        },
    )
    assert reponse.status_code == 422
    assert db_session.query(Budget).count() == avant


@pytest.mark.parametrize("chemin", ["/api/depenses", "/api/budgets"])
def test_un_utilisateur_id_en_parametre_d_url_est_ignore_dans_les_listes(deux_comptes, chemin):
    _, client_bob, d = deux_comptes
    sans = client_bob.get(chemin).json()
    avec = client_bob.get(chemin, params={"utilisateur_id": d["alice"]["id"]}).json()
    assert avec == sans


def test_un_en_tete_d_identite_est_ignore(deux_comptes):
    # Seul le cookie identifie l'utilisateur : un en-tête arbitraire ne change rien.
    _, client_bob, d = deux_comptes
    reponse = client_bob.get("/api/depenses", headers={"X-Utilisateur-Id": d["alice"]["id"]})
    assert [e["libelle"] for e in reponse.json()["elements"]] == ["Café de Bob"]


def test_un_utilisateur_id_ne_permet_pas_de_se_faire_passer_pour_alice_sans_cookie(deux_comptes):
    _, _, d = deux_comptes
    anonyme = _nouveau_client()
    reponse = anonyme.get("/api/depenses", params={"utilisateur_id": d["alice"]["id"]})
    assert reponse.status_code == 401


# === 4. Sans cookie valide : 401 sur toutes les routes privées =================================


def _routes_de_l_api():
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            for methode in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield methode, route.path


def _routes_privees():
    return [(m, p) for m, p in _routes_de_l_api() if (m, p) not in ROUTES_PUBLIQUES]


def test_l_inventaire_des_routes_contient_bien_les_routes_attendues():
    # Garde-fou : si l'inventaire était vide, le test des 401 passerait sans rien vérifier.
    routes = set(_routes_de_l_api())
    attendues = {
        ("GET", "/api/authentification/moi"),
        ("POST", "/api/authentification/deconnexion"),
        ("GET", "/api/categories"),
        ("POST", "/api/depenses"),
        ("GET", "/api/depenses"),
        ("GET", "/api/depenses/{depense_id}"),
        ("PATCH", "/api/depenses/{depense_id}"),
        ("DELETE", "/api/depenses/{depense_id}"),
        ("GET", "/api/budgets"),
        ("POST", "/api/budgets"),
        ("GET", "/api/budgets/{budget_id}"),
        ("PATCH", "/api/budgets/{budget_id}"),
        ("DELETE", "/api/budgets/{budget_id}"),
    }
    assert attendues <= routes
    assert ROUTES_PUBLIQUES <= routes


@pytest.mark.parametrize(("methode", "chemin"), _routes_privees())
def test_toute_route_privee_exige_une_connexion(methode, chemin):
    # Aucun cookie. Un corps vide et un identifiant quelconque : la 401 doit passer avant le reste.
    url = chemin.replace("{depense_id}", str(uuid4())).replace("{budget_id}", str(uuid4()))
    anonyme = _nouveau_client()
    reponse = anonyme.request(methode, url, json={} if methode in {"POST", "PUT", "PATCH"} else None)
    assert reponse.status_code == 401, f"{methode} {chemin} répond {reponse.status_code}"
    assert reponse.json()["erreur"]["code"] == "non_authentifie"


def test_un_cookie_falsifie_est_refuse_sur_les_routes_de_donnees(deux_comptes):
    client_alice, _, _ = deux_comptes
    for cookie in client_alice.cookies.jar:
        cookie.value = cookie.value[:-3] + "xxx"
    for chemin in ("/api/depenses", "/api/budgets", "/api/categories"):
        assert client_alice.get(chemin).status_code == 401, chemin


def test_un_compte_supprime_perd_l_acces_meme_avec_un_cookie_encore_valide(
    deux_comptes, db_session
):
    # Le jeton n'est pas révocable, mais l'utilisateur est rechargé en base à chaque requête.
    client_alice, client_bob, d = deux_comptes
    assert client_alice.get("/api/depenses").status_code == 200
    db_session.delete(db_session.get(Utilisateur, d["alice"]["id"]))
    db_session.commit()
    for chemin in ("/api/depenses", "/api/budgets", "/api/authentification/moi"):
        assert client_alice.get(chemin).status_code == 401, chemin
    # La suppression en cascade n'a emporté que les données d'Alice.
    assert client_bob.get("/api/depenses").json()["total"] == 1
