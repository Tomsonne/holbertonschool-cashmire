"""Tests de POST /api/authentification/inscription.

Hypothèses sur tests/conftest.py (fourni par ailleurs, non vérifié) :
- `client` : TestClient dont la dépendance get_db pointe vers la base de test `cashmire_test` ;
- `db_session` : Session sur cette même base, avec tables vidées entre deux tests.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.erreurs import ErreurApi
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import InscriptionEntree
from app.services import authentification as service

URL = "/api/authentification/inscription"
MOT_DE_PASSE = "Un-mot-de-passe-valide"


def corps(**surcharges):
    donnees = {"email": "ada@x.fr", "mot_de_passe": MOT_DE_PASSE, "nom_affichage": "Ada"}
    donnees.update(surcharges)
    return donnees


# --- Cas nominal ---------------------------------------------------------------------------


def test_inscription_valide_renvoie_201_sans_secret(client, db_session):
    reponse = client.post(URL, json=corps(email="  Ada@X.fr "))
    assert reponse.status_code == 201
    utilisateur = reponse.json()
    assert set(utilisateur) == {"id", "email", "nom_affichage", "date_creation"}
    assert utilisateur["email"] == "ada@x.fr"  # normalisé : strip + lower
    assert utilisateur["nom_affichage"] == "Ada"
    assert MOT_DE_PASSE not in reponse.text
    assert "argon2" not in reponse.text
    assert "mot_de_passe" not in reponse.text
    # Pas de connexion à l'inscription.
    assert "set-cookie" not in reponse.headers


def test_le_hash_stocke_est_argon2id(client, db_session):
    client.post(URL, json=corps())
    stocke = db_session.scalars(select(Utilisateur)).one()
    assert stocke.mot_de_passe_hache.startswith("$argon2id$")
    assert stocke.mot_de_passe_hache != MOT_DE_PASSE


@pytest.mark.parametrize("longueur", [10, 128])
def test_bornes_valides_du_mot_de_passe(client, longueur):
    assert client.post(URL, json=corps(mot_de_passe="a" * longueur)).status_code == 201


# --- 409 : doublon d'email -----------------------------------------------------------------


def test_doublon_exact_renvoie_409(client):
    assert client.post(URL, json=corps()).status_code == 201
    reponse = client.post(URL, json=corps())
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "conflit"


def test_doublon_avec_casse_differente_renvoie_409(client):
    assert client.post(URL, json=corps(email="A@x.fr")).status_code == 201
    reponse = client.post(URL, json=corps(email="a@x.fr"))
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "conflit"


def test_doublon_insensible_a_la_casse_au_niveau_de_la_base(db_session):
    """Le schéma normalise déjà l'email : on vérifie que l'index lower(email) est bien reconnu."""
    db_session.add(Utilisateur(email="A@x.fr", mot_de_passe_hache="h", nom_affichage="Ada"))
    db_session.commit()
    donnees = InscriptionEntree.model_construct(
        email="a@x.fr", mot_de_passe=MOT_DE_PASSE, nom_affichage="Bis"
    )
    with pytest.raises(ErreurApi) as info:
        service.inscrire(db_session, donnees)
    assert info.value.statut == 409


def test_inscription_valide_apres_un_409_reussit(client):
    client.post(URL, json=corps())
    assert client.post(URL, json=corps()).status_code == 409
    # La session ne doit pas être restée dans une transaction échouée.
    assert client.post(URL, json=corps(email="autre@x.fr")).status_code == 201


def test_le_corps_du_409_ne_contient_ni_mot_de_passe_ni_email(client):
    client.post(URL, json=corps(email="secret.perso@x.fr"))
    reponse = client.post(URL, json=corps(email="secret.perso@x.fr"))
    assert reponse.status_code == 409
    assert MOT_DE_PASSE not in reponse.text
    assert "secret.perso" not in reponse.text


def test_une_autre_contrainte_n_est_pas_convertie_en_409(db_session, monkeypatch):
    # Hash None -> violation NOT NULL sur mot_de_passe_hache : une IntegrityError qui n'est pas
    # le doublon d'email.
    monkeypatch.setattr(service, "hacher_mot_de_passe", lambda _mot_de_passe: None)
    donnees = InscriptionEntree(email="ada@x.fr", mot_de_passe=MOT_DE_PASSE, nom_affichage="Ada")
    with pytest.raises(IntegrityError):
        service.inscrire(db_session, donnees)


# --- 422 : données invalides ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("surcharge", "champ"),
    [
        ({"email": "pas-un-email"}, "email"),
        ({"email": ""}, "email"),
        ({"mot_de_passe": "a" * 9}, "mot_de_passe"),
        ({"mot_de_passe": "a" * 129}, "mot_de_passe"),
        ({"nom_affichage": ""}, "nom_affichage"),
        ({"nom_affichage": "   "}, "nom_affichage"),
        ({"nom_affichage": "a" * 101}, "nom_affichage"),
    ],
)
def test_donnees_invalides_renvoient_422(client, db_session, surcharge, champ):
    reponse = client.post(URL, json=corps(**surcharge))
    assert reponse.status_code == 422
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "donnees_invalides"
    assert champ in erreur["champs"]
    assert db_session.scalars(select(Utilisateur)).all() == []


def test_le_corps_du_422_ne_contient_ni_mot_de_passe_ni_email(client):
    reponse = client.post(
        URL, json=corps(email="pas-un-email-secret", mot_de_passe="court-secret")
    )
    assert reponse.status_code == 422
    assert "court-secret" not in reponse.text
    assert "pas-un-email-secret" not in reponse.text
