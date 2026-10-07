"""Tests de GET /api/authentification/moi et de la dépendance `utilisateur_courant`.

Hypothèses sur tests/conftest.py : `client`, `db_session` et `moteur_de_test` comme pour la
connexion ; JWT_SECRET (32 caractères au moins) affecté avant l'import de l'application.
Hors test de bout en bout, aucun appel à /connexion : le jeton est fabriqué ici (pas d'Argon2).
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.securite import NOM_COOKIE_JWT
from app.models.utilisateur import Utilisateur

URL = "/api/authentification/moi"
HASH_FACTICE = "hash-factice"
CORPS_401 = {"erreur": {"code": "non_authentifie", "message": "Authentification requise."}}
AUTRE_CLE = "une-autre-cle-de-signature-0123456789-xyz"


def creer_utilisateur(db_session, email="ada@x.fr", nom="Ada"):
    utilisateur = Utilisateur(email=email, mot_de_passe_hache=HASH_FACTICE, nom_affichage=nom)
    db_session.add(utilisateur)
    db_session.commit()
    return utilisateur


def fabriquer_jeton(sub, cle=None, algo="HS256", **ecarts):
    """JWT valide par défaut ; un écart remplace le claim, un écart à None le retire."""
    maintenant = datetime.now(timezone.utc)
    claims = {
        "sub": None if sub is None else str(sub),
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=10),
    }
    claims.update(ecarts)
    claims = {nom: valeur for nom, valeur in claims.items() if valeur is not None}
    return jwt.encode(claims, cle or settings.jwt_secret, algorithm=algo)


def test_moi_nominal(client, db_session):
    utilisateur = creer_utilisateur(db_session)
    client.cookies.set(NOM_COOKIE_JWT, fabriquer_jeton(utilisateur.id))

    reponse = client.get(URL)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert set(corps) == {"id", "email", "nom_affichage", "date_creation"}
    assert corps["id"] == str(utilisateur.id)
    assert corps["email"] == "ada@x.fr"
    for valeur in corps.values():
        assert "$argon2" not in str(valeur)
        assert HASH_FACTICE not in str(valeur)


def test_moi_renvoie_l_utilisateur_du_jeton_et_ignore_utilisateur_id(client, db_session):
    premier = creer_utilisateur(db_session, email="premier@x.fr", nom="Premier")
    second = creer_utilisateur(db_session, email="second@x.fr", nom="Second")
    client.cookies.set(NOM_COOKIE_JWT, fabriquer_jeton(second.id))

    sans_parametre = client.get(URL)
    avec_parametre = client.get(URL, params={"utilisateur_id": str(premier.id)})

    assert sans_parametre.status_code == avec_parametre.status_code == 200
    assert sans_parametre.json()["id"] == str(second.id)
    assert avec_parametre.json() == sans_parametre.json()


# Chaque cas reçoit un utilisateur existant : seul le défaut du jeton explique le 401.
# Une valeur None signifie « pas de cookie ».
CAS_ECHEC = {
    "cookie_absent": lambda u: None,
    "cookie_vide": lambda u: "",
    "valeur_illisible": lambda u: "n-importe-quoi",
    "autre_cle": lambda u: fabriquer_jeton(u.id, cle=AUTRE_CLE),
    "expire": lambda u: fabriquer_jeton(
        u.id, exp=datetime.now(timezone.utc) - timedelta(minutes=1)
    ),
    "algorithme_hs384": lambda u: fabriquer_jeton(u.id, algo="HS384"),
    "sub_absent": lambda u: fabriquer_jeton(None),
    "sub_pas_un_uuid": lambda u: fabriquer_jeton("pas-un-uuid"),
    "exp_absent": lambda u: fabriquer_jeton(u.id, exp=None),
    "utilisateur_inexistant": lambda u: fabriquer_jeton(uuid.uuid4()),
}


@pytest.mark.parametrize("fabrique", CAS_ECHEC.values(), ids=CAS_ECHEC.keys())
def test_moi_echecs_identiques(client, db_session, fabrique):
    utilisateur = creer_utilisateur(db_session)
    valeur = fabrique(utilisateur)
    if valeur is not None:
        client.cookies.set(NOM_COOKIE_JWT, valeur)

    reponse = client.get(URL)

    assert reponse.status_code == 401
    assert reponse.json() == CORPS_401


def test_moi_utilisateur_supprime_apres_emission_du_jeton(client, db_session, moteur_de_test):
    utilisateur = creer_utilisateur(db_session)
    client.cookies.set(NOM_COOKIE_JWT, fabriquer_jeton(utilisateur.id))
    assert client.get(URL).status_code == 200

    # Suppression par une AUTRE connexion : la session partagée garde l'objet dans sa mémoire
    # (expire_on_commit=False). Un `session.get` le renverrait encore ; seul un SELECT donne 401.
    with moteur_de_test.begin() as connexion:
        connexion.execute(text("DELETE FROM utilisateurs WHERE id = :id"), {"id": utilisateur.id})

    reponse = client.get(URL)

    assert reponse.status_code == 401
    assert reponse.json() == CORPS_401


def test_moi_de_bout_en_bout(client):
    inscription = client.post(
        "/api/authentification/inscription",
        json={"email": "ada@x.fr", "mot_de_passe": "Un-mot-de-passe-valide", "nom_affichage": "Ada"},
    )
    assert inscription.status_code == 201
    connexion = client.post(
        "/api/authentification/connexion",
        json={"email": "ada@x.fr", "mot_de_passe": "Un-mot-de-passe-valide"},
    )
    assert connexion.status_code == 200

    # Le cookie posé par la connexion est renvoyé automatiquement par le client.
    reponse = client.get(URL)

    assert reponse.status_code == 200
    assert reponse.json()["id"] == inscription.json()["id"]


def test_moi_ne_lit_que_le_cookie(client, db_session):
    utilisateur = creer_utilisateur(db_session)
    jeton = fabriquer_jeton(utilisateur.id)

    reponse = client.get(URL, headers={"Authorization": f"Bearer {jeton}"})

    assert reponse.status_code == 401
    assert reponse.json() == CORPS_401
