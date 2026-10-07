"""Modification et suppression des dépenses (#15) : PATCH et DELETE /api/depenses/{id}.

Même principe que les autres fichiers de dépenses : fixtures de conftest.py (base de test dédiée),
utilisateur connecté simulé en remplaçant `utilisateur_courant`, sauf les tests « vrai cookie ».
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
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


def _categorie(db_session, nom: str) -> Categorie:
    return db_session.scalar(select(Categorie).where(Categorie.nom == nom))


def _ajouter(db_session, proprietaire, categorie, jour="2026-03-10", montant="10.00", libelle="Achat"):
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


def _relire(db_session, depense_id):
    """Relit la dépense directement en base (et non dans la mémoire de la session)."""
    db_session.expire_all()
    return db_session.get(Depense, depense_id)


def _nombre_de_depenses(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(Depense))


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


@pytest.fixture
def depense(db_session, connecte, loisirs) -> Depense:
    return _ajouter(db_session, connecte, loisirs, "2026-03-10", "10.00", "Cinéma")


# === PATCH =====================================================================================


def test_modifier_un_seul_champ_laisse_les_autres_inchanges(client, db_session, depense, loisirs):
    reponse = client.patch(f"{URL}/{depense.id}", json={"montant": "25.50"})
    assert reponse.status_code == 200
    assert reponse.json() == {
        "id": str(depense.id),
        "montant": "25.50",
        "libelle": "Cinéma",
        "date_depense": "2026-03-10",
        "categorie": {"id": str(loisirs.id), "nom": "Loisirs"},
    }
    relue = _relire(db_session, depense.id)
    assert relue.montant == Decimal("25.50")
    assert relue.libelle == "Cinéma"
    assert relue.date_depense == date(2026, 3, 10)
    assert relue.categorie_id == loisirs.id


def test_modifier_plusieurs_champs_a_la_fois(client, db_session, depense, transport):
    reponse = client.patch(
        f"{URL}/{depense.id}",
        json={
            "montant": "3.20",
            "libelle": "  Bus  ",
            "date_depense": "2026-03-12",
            "categorie_id": str(transport.id),
        },
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["montant"] == "3.20"
    assert corps["libelle"] == "Bus"  # espaces retirés, comme à la création
    assert corps["date_depense"] == "2026-03-12"
    assert corps["categorie"] == {"id": str(transport.id), "nom": "Transport"}
    relue = _relire(db_session, depense.id)
    assert (relue.montant, relue.libelle, relue.categorie_id) == (Decimal("3.20"), "Bus", transport.id)


def test_changer_de_categorie_renvoie_le_nouveau_nom(client, depense, transport):
    reponse = client.patch(f"{URL}/{depense.id}", json={"categorie_id": str(transport.id)})
    assert reponse.json()["categorie"] == {"id": str(transport.id), "nom": "Transport"}


def test_la_modification_est_visible_dans_le_detail_et_la_liste(client, depense):
    client.patch(f"{URL}/{depense.id}", json={"libelle": "Théâtre"})
    assert client.get(f"{URL}/{depense.id}").json()["libelle"] == "Théâtre"
    assert client.get(URL).json()["elements"][0]["libelle"] == "Théâtre"


def test_date_modification_est_mise_a_jour_et_pas_date_creation(client, db_session, depense):
    avant = _relire(db_session, depense.id)
    creation, modification = avant.date_creation, avant.date_modification
    client.patch(f"{URL}/{depense.id}", json={"libelle": "Autre"})
    apres = _relire(db_session, depense.id)
    assert apres.date_creation == creation
    assert apres.date_modification > modification


def test_date_modification_est_mise_a_jour_meme_si_les_valeurs_sont_identiques(
    client, db_session, depense
):
    modification = _relire(db_session, depense.id).date_modification
    reponse = client.patch(f"{URL}/{depense.id}", json={"libelle": "Cinéma"})  # même libellé
    assert reponse.status_code == 200
    assert _relire(db_session, depense.id).date_modification > modification


def test_modifier_une_depense_ne_touche_pas_aux_autres(client, db_session, connecte, loisirs, depense):
    autre = _ajouter(db_session, connecte, loisirs, "2026-03-11", "99.00", "Autre dépense")
    client.patch(f"{URL}/{depense.id}", json={"montant": "1.00"})
    relue = _relire(db_session, autre.id)
    assert (relue.montant, relue.libelle) == (Decimal("99.00"), "Autre dépense")


def test_le_proprietaire_ne_change_jamais(client, db_session, connecte, depense):
    client.patch(f"{URL}/{depense.id}", json={"montant": "5.00"})
    assert _relire(db_session, depense.id).utilisateur_id == connecte.id


# --- Corps invalide : 422, et rien n'est modifié ---------------------------------------------


def _inchangee(db_session, depense):
    relue = _relire(db_session, depense.id)
    return (relue.montant, relue.libelle, relue.date_depense, relue.categorie_id) == (
        Decimal("10.00"),
        "Cinéma",
        date(2026, 3, 10),
        depense.categorie_id,
    )


def test_corps_vide_renvoie_422(client, db_session, depense):
    reponse = client.patch(f"{URL}/{depense.id}", json={})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"
    assert _inchangee(db_session, depense)


@pytest.mark.parametrize("champ", ["utilisateur_id", "id", "date_creation", "n_importe_quoi"])
def test_champ_inconnu_est_refuse_et_rien_n_est_modifie(client, db_session, depense, champ):
    reponse = client.patch(f"{URL}/{depense.id}", json={"montant": "5.00", champ: str(uuid4())})
    assert reponse.status_code == 422
    assert champ in reponse.json()["erreur"]["champs"]
    assert _inchangee(db_session, depense)


def test_utilisateur_id_ne_peut_pas_changer_le_proprietaire(client, db_session, depense):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    reponse = client.patch(f"{URL}/{depense.id}", json={"utilisateur_id": str(autre.id)})
    assert reponse.status_code == 422
    assert _relire(db_session, depense.id).utilisateur_id != autre.id


@pytest.mark.parametrize("champ", ["montant", "libelle", "date_depense", "categorie_id"])
def test_champ_null_est_refuse(client, db_session, depense, champ):
    reponse = client.patch(f"{URL}/{depense.id}", json={champ: None})
    assert reponse.status_code == 422
    assert champ in reponse.json()["erreur"]["champs"]
    assert _inchangee(db_session, depense)


@pytest.mark.parametrize("montant", ["0", "0.00", "-5", "12.345", "abc", "", 12.5, 12])
def test_montant_invalide_renvoie_422(client, db_session, depense, montant):
    reponse = client.patch(f"{URL}/{depense.id}", json={"montant": montant})
    assert reponse.status_code == 422
    assert "montant" in reponse.json()["erreur"]["champs"]
    assert _inchangee(db_session, depense)


@pytest.mark.parametrize("libelle", ["", "   ", "x" * 201, 123])
def test_libelle_invalide_renvoie_422(client, db_session, depense, libelle):
    reponse = client.patch(f"{URL}/{depense.id}", json={"libelle": libelle})
    assert reponse.status_code == 422
    assert "libelle" in reponse.json()["erreur"]["champs"]
    assert _inchangee(db_session, depense)


@pytest.mark.parametrize("jour", ["pas une date", "2026-13-45", "", "1999-12-31", "2100-01-01"])
def test_date_invalide_ou_hors_periode_renvoie_422(client, db_session, depense, jour):
    reponse = client.patch(f"{URL}/{depense.id}", json={"date_depense": jour})
    assert reponse.status_code == 422
    assert "date_depense" in reponse.json()["erreur"]["champs"]
    assert _inchangee(db_session, depense)


def test_date_dans_deux_jours_est_refusee_et_demain_est_accepte(client, depense):
    refusee = (date.today() + timedelta(days=2)).isoformat()
    acceptee = (date.today() + timedelta(days=1)).isoformat()
    assert client.patch(f"{URL}/{depense.id}", json={"date_depense": refusee}).status_code == 422
    assert client.patch(f"{URL}/{depense.id}", json={"date_depense": acceptee}).status_code == 200


def test_categorie_id_mal_forme_renvoie_422(client, db_session, depense):
    reponse = client.patch(f"{URL}/{depense.id}", json={"categorie_id": "pas-un-uuid"})
    assert reponse.status_code == 422
    assert "categorie_id" in reponse.json()["erreur"]["champs"]
    assert _inchangee(db_session, depense)


def test_corps_non_json_renvoie_400(client, depense):
    reponse = client.patch(
        f"{URL}/{depense.id}", content="{pas du json", headers={"Content-Type": "application/json"}
    )
    assert reponse.status_code == 400
    assert reponse.json()["erreur"]["code"] == "requete_invalide"


def test_erreur_422_ne_renvoie_pas_la_valeur_envoyee(client, depense):
    reponse = client.patch(f"{URL}/{depense.id}", json={"libelle": "x" * 201})
    assert "xxxxxxxxxx" not in reponse.text


def test_categorie_inconnue_renvoie_404_et_rien_n_est_modifie(client, db_session, depense):
    reponse = client.patch(
        f"{URL}/{depense.id}", json={"montant": "5.00", "categorie_id": str(uuid4())}
    )
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"
    assert reponse.json()["erreur"]["champs"] == {"categorie_id": "Catégorie inconnue."}
    assert _inchangee(db_session, depense)  # le montant n'a pas été modifié non plus


# --- Propriétaire et identifiant ---------------------------------------------------------------


def test_modifier_la_depense_d_un_autre_utilisateur_renvoie_404(client, db_session, connecte, loisirs):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    depense_de_bob = _ajouter(db_session, autre, loisirs, libelle="À Bob")
    reponse = client.patch(f"{URL}/{depense_de_bob.id}", json={"libelle": "Piraté"})
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "introuvable"
    assert _relire(db_session, depense_de_bob.id).libelle == "À Bob"


def test_patch_inexistante_et_patch_d_autrui_donnent_la_meme_reponse(
    client, db_session, connecte, loisirs
):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    depense_de_bob = _ajouter(db_session, autre, loisirs)
    chez_autrui = client.patch(f"{URL}/{depense_de_bob.id}", json={"libelle": "x"})
    inexistante = client.patch(f"{URL}/{uuid4()}", json={"libelle": "x"})
    assert chez_autrui.status_code == inexistante.status_code == 404
    assert chez_autrui.json() == inexistante.json()


def test_patch_avec_un_identifiant_mal_forme_renvoie_422(client, connecte):
    reponse = client.patch(f"{URL}/pas-un-uuid", json={"libelle": "x"})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "donnees_invalides"


# === DELETE ====================================================================================


def test_supprimer_renvoie_204_sans_corps_et_retire_la_depense(client, db_session, depense):
    reponse = client.delete(f"{URL}/{depense.id}")
    assert reponse.status_code == 204
    assert reponse.content == b""
    assert _relire(db_session, depense.id) is None
    assert client.get(f"{URL}/{depense.id}").status_code == 404


def test_supprimer_ne_retire_que_la_depense_visee(client, db_session, connecte, loisirs, depense):
    gardee = _ajouter(db_session, connecte, loisirs, "2026-03-11", libelle="Gardée")
    client.delete(f"{URL}/{depense.id}")
    assert _relire(db_session, gardee.id) is not None
    assert _nombre_de_depenses(db_session) == 1


def test_supprimer_ne_supprime_ni_la_categorie_ni_l_utilisateur(client, db_session, connecte, loisirs, depense):
    client.delete(f"{URL}/{depense.id}")
    assert db_session.get(Categorie, loisirs.id) is not None
    assert db_session.get(Utilisateur, connecte.id) is not None


def test_supprimer_deux_fois_renvoie_404_la_seconde_fois(client, depense):
    assert client.delete(f"{URL}/{depense.id}").status_code == 204
    seconde = client.delete(f"{URL}/{depense.id}")
    assert seconde.status_code == 404
    assert seconde.json()["erreur"]["code"] == "introuvable"


def test_supprimer_la_depense_d_un_autre_utilisateur_renvoie_404_et_ne_supprime_rien(
    client, db_session, connecte, loisirs
):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    depense_de_bob = _ajouter(db_session, autre, loisirs)
    reponse = client.delete(f"{URL}/{depense_de_bob.id}")
    assert reponse.status_code == 404
    assert _relire(db_session, depense_de_bob.id) is not None


def test_delete_inexistante_et_delete_d_autrui_donnent_la_meme_reponse(
    client, db_session, connecte, loisirs
):
    autre = _creer_utilisateur(db_session, "bob@example.com")
    depense_de_bob = _ajouter(db_session, autre, loisirs)
    chez_autrui = client.delete(f"{URL}/{depense_de_bob.id}")
    inexistante = client.delete(f"{URL}/{uuid4()}")
    assert chez_autrui.status_code == inexistante.status_code == 404
    assert chez_autrui.json() == inexistante.json()


def test_delete_avec_un_identifiant_mal_forme_renvoie_422(client, connecte):
    assert client.delete(f"{URL}/pas-un-uuid").status_code == 422


# === Authentification ==========================================================================


@pytest.mark.parametrize("methode", ["PATCH", "DELETE"])
def test_sans_authentification_renvoie_401_et_ne_modifie_rien(client, db_session, loisirs, methode):
    proprietaire = _creer_utilisateur(db_session, "alice@example.com")
    cible = _ajouter(db_session, proprietaire, loisirs, libelle="Intacte")
    reponse = client.request(methode, f"{URL}/{cible.id}", json={"libelle": "Piratée"} if methode == "PATCH" else None)
    assert reponse.status_code == 401
    assert reponse.json()["erreur"]["code"] == "non_authentifie"
    assert _relire(db_session, cible.id).libelle == "Intacte"


# === Avec la vraie authentification (cookie JWT posé par la connexion) ========================


def _se_connecter(client, email: str) -> dict:
    identifiants = {"email": email, "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post(
        "/api/authentification/inscription", json={**identifiants, "nom_affichage": "Test"}
    ).status_code == 201
    assert client.post("/api/authentification/connexion", json=identifiants).status_code == 200
    return client.get("/api/authentification/moi").json()


def test_deux_utilisateurs_reels_ne_peuvent_pas_modifier_ni_supprimer_les_depenses_de_l_autre(
    client, db_session, loisirs
):
    moi_alice = _se_connecter(client, "alice@example.com")
    client_bob = TestClient(app, raise_server_exceptions=False)
    moi_bob = _se_connecter(client_bob, "bob@example.com")
    alice = db_session.get(Utilisateur, moi_alice["id"])
    bob = db_session.get(Utilisateur, moi_bob["id"])
    depense_alice = _ajouter(db_session, alice, loisirs, libelle="À Alice")
    depense_bob = _ajouter(db_session, bob, loisirs, libelle="À Bob")

    # Chacun agit sur ses propres dépenses...
    assert client.patch(f"{URL}/{depense_alice.id}", json={"libelle": "Alice 2"}).status_code == 200
    assert client_bob.patch(f"{URL}/{depense_bob.id}", json={"libelle": "Bob 2"}).status_code == 200
    # ... mais pas sur celles de l'autre.
    assert client_bob.patch(f"{URL}/{depense_alice.id}", json={"libelle": "Piratée"}).status_code == 404
    assert client_bob.delete(f"{URL}/{depense_alice.id}").status_code == 404
    assert client.delete(f"{URL}/{depense_bob.id}").status_code == 404

    assert _relire(db_session, depense_alice.id).libelle == "Alice 2"
    assert _relire(db_session, depense_bob.id).libelle == "Bob 2"
    assert client.delete(f"{URL}/{depense_alice.id}").status_code == 204
    assert _relire(db_session, depense_alice.id) is None
