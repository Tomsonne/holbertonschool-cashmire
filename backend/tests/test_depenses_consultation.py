"""Liste et détail des dépenses (#14) : GET /api/depenses et GET /api/depenses/{id}.

Même principe que test_depenses.py : fixtures de conftest.py (base de test dédiée), utilisateur
connecté simulé en remplaçant `utilisateur_courant`, sauf les tests marqués « vrai cookie ».
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

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


def _categorie(db_session, nom: str) -> Categorie:
    return db_session.scalar(select(Categorie).where(Categorie.nom == nom))


def _ajouter(db_session, proprietaire, categorie, jour: str, montant="10.00", libelle="Achat"):
    depense = Depense(
        utilisateur_id=proprietaire.id,
        categorie_id=categorie.id,
        montant=Decimal(montant),
        libelle=libelle,
        date_depense=date.fromisoformat(jour),
    )
    db_session.add(depense)
    db_session.commit()
    db_session.refresh(depense)
    return depense


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
def loisirs(db_session) -> Categorie:
    return _categorie(db_session, "Loisirs")


@pytest.fixture
def transport(db_session) -> Categorie:
    return _categorie(db_session, "Transport")


# --- Liste : format et cas simples ----------------------------------------------------------


def test_liste_vide_renvoie_200_avec_total_zero(client, connecte):
    reponse = client.get(URL)
    assert reponse.status_code == 200
    assert reponse.json() == {"elements": [], "total": 0}


def test_liste_renvoie_elements_et_total_au_bon_format(client, connecte, db_session, loisirs):
    depense = _ajouter(db_session, connecte, loisirs, "2026-03-10", "12.5", "Cinéma")
    corps = client.get(URL).json()
    assert set(corps) == {"elements", "total"}
    assert corps["total"] == 1
    assert corps["elements"] == [
        {
            "id": str(depense.id),
            "montant": "12.50",
            "libelle": "Cinéma",
            "date_depense": "2026-03-10",
            "categorie": {"id": str(loisirs.id), "nom": "Loisirs"},
        }
    ]


def test_tri_par_date_decroissante(client, connecte, db_session, loisirs):
    for jour in ["2026-03-10", "2026-03-31", "2026-01-05", "2026-03-11"]:
        _ajouter(db_session, connecte, loisirs, jour)
    dates = [e["date_depense"] for e in client.get(URL).json()["elements"]]
    assert dates == ["2026-03-31", "2026-03-11", "2026-03-10", "2026-01-05"]


def test_sans_filtre_mois_toutes_les_depenses_sont_renvoyees(client, connecte, db_session, loisirs):
    for annee in (2024, 2025, 2026):
        _ajouter(db_session, connecte, loisirs, f"{annee}-06-15")
    corps = client.get(URL).json()
    assert corps["total"] == 3
    assert len(corps["elements"]) == 3


# --- Filtres --------------------------------------------------------------------------------


def test_filtre_mois_garde_les_bornes_du_mois_seulement(
    client, connecte, db_session, loisirs
):
    for jour in ["2026-01-31", "2026-02-01", "2026-02-28", "2026-03-01"]:
        _ajouter(db_session, connecte, loisirs, jour)
    corps = client.get(URL, params={"mois": "2026-02"}).json()
    assert [e["date_depense"] for e in corps["elements"]] == ["2026-02-28", "2026-02-01"]
    assert corps["total"] == 2


def test_filtre_mois_de_decembre_s_arrete_au_31(client, connecte, db_session, loisirs):
    for jour in ["2025-11-30", "2025-12-01", "2025-12-31", "2026-01-01"]:
        _ajouter(db_session, connecte, loisirs, jour)
    corps = client.get(URL, params={"mois": "2025-12"}).json()
    assert [e["date_depense"] for e in corps["elements"]] == ["2025-12-31", "2025-12-01"]


def test_filtre_par_categorie(client, connecte, db_session, loisirs, transport):
    _ajouter(db_session, connecte, loisirs, "2026-03-10", libelle="Cinéma")
    _ajouter(db_session, connecte, transport, "2026-03-11", libelle="Bus")
    corps = client.get(URL, params={"categorie_id": str(transport.id)}).json()
    assert [e["libelle"] for e in corps["elements"]] == ["Bus"]
    assert corps["total"] == 1


def test_filtres_combines(client, connecte, db_session, loisirs, transport):
    _ajouter(db_session, connecte, loisirs, "2026-03-10", libelle="Mars loisirs")
    _ajouter(db_session, connecte, loisirs, "2026-04-10", libelle="Avril loisirs")
    _ajouter(db_session, connecte, transport, "2026-03-12", libelle="Mars transport")
    corps = client.get(URL, params={"mois": "2026-03", "categorie_id": str(loisirs.id)}).json()
    assert [e["libelle"] for e in corps["elements"]] == ["Mars loisirs"]
    assert corps["total"] == 1


def test_categorie_inconnue_dans_le_filtre_donne_une_liste_vide(client, connecte, db_session, loisirs):
    _ajouter(db_session, connecte, loisirs, "2026-03-10")
    reponse = client.get(URL, params={"categorie_id": str(uuid4())})
    assert reponse.status_code == 200
    assert reponse.json() == {"elements": [], "total": 0}


# --- Pagination -----------------------------------------------------------------------------


def test_limite_par_defaut_est_20_et_total_compte_tout(client, connecte, db_session, loisirs):
    for numero in range(25):
        _ajouter(db_session, connecte, loisirs, "2026-03-10", libelle=f"Achat {numero}")
    corps = client.get(URL).json()
    assert len(corps["elements"]) == 20
    assert corps["total"] == 25


def test_total_ne_depend_ni_de_la_limite_ni_du_decalage(client, connecte, db_session, loisirs):
    for numero in range(5):
        _ajouter(db_session, connecte, loisirs, f"2026-03-{10 + numero}")
    for params in [{}, {"limite": 2}, {"limite": 2, "decalage": 2}, {"decalage": 4}]:
        assert client.get(URL, params=params).json()["total"] == 5


def test_total_applique_les_memes_filtres_que_la_page(client, connecte, db_session, loisirs):
    for jour in ["2026-03-10", "2026-03-11", "2026-03-12", "2026-04-01"]:
        _ajouter(db_session, connecte, loisirs, jour)
    corps = client.get(URL, params={"mois": "2026-03", "limite": 1}).json()
    assert len(corps["elements"]) == 1
    assert corps["total"] == 3


def test_decalage_au_dela_du_total_donne_une_page_vide_et_le_bon_total(
    client, connecte, db_session, loisirs
):
    for jour in ["2026-03-10", "2026-03-11"]:
        _ajouter(db_session, connecte, loisirs, jour)
    corps = client.get(URL, params={"decalage": 50}).json()
    assert corps == {"elements": [], "total": 2}


def test_les_pages_se_suivent_sans_doublon_ni_oubli_meme_a_date_egale(
    client, connecte, db_session, loisirs
):
    identifiants = {
        str(_ajouter(db_session, connecte, loisirs, "2026-03-10", libelle=f"Achat {n}").id)
        for n in range(7)
    }
    vus = []
    for decalage in (0, 3, 6):
        page = client.get(URL, params={"limite": 3, "decalage": decalage}).json()["elements"]
        vus += [e["id"] for e in page]
    assert len(vus) == 7
    assert set(vus) == identifiants


@pytest.mark.parametrize("limite", [1, 100])
def test_limites_extremes_acceptees(client, connecte, limite):
    assert client.get(URL, params={"limite": limite}).status_code == 200


# --- Paramètres invalides -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "champ"),
    [
        ({"limite": 0}, "limite"),
        ({"limite": 101}, "limite"),
        ({"limite": -1}, "limite"),
        ({"limite": "abc"}, "limite"),
        ({"decalage": -1}, "decalage"),
        ({"decalage": "abc"}, "decalage"),
        ({"mois": "2026-13"}, "mois"),
        ({"mois": "2026-1"}, "mois"),
        ({"mois": "abc"}, "mois"),
        ({"categorie_id": "pas-un-uuid"}, "categorie_id"),
    ],
)
def test_parametres_invalides_renvoient_422(client, connecte, params, champ):
    reponse = client.get(URL, params=params)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"
    assert champ in reponse.json()["erreur"]["champs"]


# --- Isolation entre utilisateurs -----------------------------------------------------------


def test_la_liste_ne_contient_que_les_depenses_de_l_utilisateur_connecte(
    client, connecte, db_session, loisirs
):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    _ajouter(db_session, connecte, loisirs, "2026-03-10", libelle="À Alice")
    _ajouter(db_session, autre, loisirs, "2026-03-11", libelle="À Bob")
    _ajouter(db_session, autre, loisirs, "2026-03-12", libelle="À Bob aussi")
    corps = client.get(URL).json()
    assert [e["libelle"] for e in corps["elements"]] == ["À Alice"]
    assert corps["total"] == 1  # le total ne compte pas les dépenses de Bob


# --- Détail ---------------------------------------------------------------------------------


def test_detail_d_une_depense(client, connecte, db_session, loisirs):
    depense = _ajouter(db_session, connecte, loisirs, "2026-03-10", "7.3", "Café")
    reponse = client.get(f"{URL}/{depense.id}")
    assert reponse.status_code == 200
    assert reponse.json() == {
        "id": str(depense.id),
        "montant": "7.30",
        "libelle": "Café",
        "date_depense": "2026-03-10",
        "categorie": {"id": str(loisirs.id), "nom": "Loisirs"},
    }


def test_detail_de_la_depense_d_un_autre_utilisateur_renvoie_404(
    client, connecte, db_session, loisirs
):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    depense_de_bob = _ajouter(db_session, autre, loisirs, "2026-03-10")
    reponse = client.get(f"{URL}/{depense_de_bob.id}")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"


def test_detail_inexistant_et_detail_d_autrui_donnent_la_meme_reponse(
    client, connecte, db_session, loisirs
):
    # Aucune différence observable : le client ne peut pas deviner qu'un identifiant existe.
    autre = _creer_utilisateur(db_session, "bob@example.com")
    depense_de_bob = _ajouter(db_session, autre, loisirs, "2026-03-10")
    chez_autrui = client.get(f"{URL}/{depense_de_bob.id}")
    inexistante = client.get(f"{URL}/{uuid4()}")
    assert chez_autrui.status_code == inexistante.status_code == 404
    assert chez_autrui.json() == inexistante.json()


def test_detail_avec_un_identifiant_mal_forme_renvoie_422(client, connecte):
    reponse = client.get(f"{URL}/pas-un-uuid")
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"


# --- Authentification -----------------------------------------------------------------------


@pytest.mark.parametrize("chemin", ["", f"/{uuid4()}"])
def test_sans_authentification_renvoie_401(client, chemin):
    reponse = client.get(f"{URL}{chemin}")
    assert reponse.status_code == 401
    assert reponse.json()["erreur"]["code"] == "non_authentifie"


# --- Avec la vraie authentification (cookie JWT posé par la connexion) -----------------------


def _se_connecter(client, email: str) -> dict:
    identifiants = {"email": email, "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post(
        "/api/authentification/inscription", json={**identifiants, "nom_affichage": "Test"}
    ).status_code == 201
    assert client.post("/api/authentification/connexion", json=identifiants).status_code == 200
    return client.get("/api/authentification/moi").json()


def test_deux_utilisateurs_reels_ne_voient_que_leurs_depenses(client, db_session, loisirs):
    moi_alice = _se_connecter(client, "alice@example.com")
    client_bob = TestClient(app, raise_server_exceptions=False, headers={"Origin": "http://localhost:5173"})
    moi_bob = _se_connecter(client_bob, "bob@example.com")
    alice = db_session.get(Utilisateur, moi_alice["id"])
    bob = db_session.get(Utilisateur, moi_bob["id"])
    depense_alice = _ajouter(db_session, alice, loisirs, "2026-03-10", libelle="À Alice")
    depense_bob = _ajouter(db_session, bob, loisirs, "2026-03-11", libelle="À Bob")

    assert [e["libelle"] for e in client.get(URL).json()["elements"]] == ["À Alice"]
    assert [e["libelle"] for e in client_bob.get(URL).json()["elements"]] == ["À Bob"]
    assert client.get(f"{URL}/{depense_alice.id}").status_code == 200
    assert client.get(f"{URL}/{depense_bob.id}").status_code == 404
    assert client_bob.get(f"{URL}/{depense_alice.id}").status_code == 404
