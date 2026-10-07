"""Tests de POST /api/authentification/deconnexion.

Hypothèses sur tests/conftest.py : `client`, `db_session` et `base_propre` comme pour /moi ;
ENVIRONMENT=development affecté avant l'import de l'application. `fabriquer_jeton` et
`creer_utilisateur` viennent de test_moi.py (import possible car tests/ n'est pas un paquet).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from test_moi import AUTRE_CLE, creer_utilisateur, fabriquer_jeton

from app.core.config import settings
from app.core.securite import NOM_COOKIE_JWT

URL = "/api/authentification/deconnexion"
URL_MOI = "/api/authentification/moi"
EMAIL = "ada@x.fr"
MOT_DE_PASSE = "Un-mot-de-passe-valide"
CORPS_401 = {"erreur": {"code": "non_authentifie", "message": "Authentification requise."}}
# Attributs qui doivent être identiques entre la pose (/connexion) et l'effacement du cookie.
ATTRIBUTS_PARTAGES = ("path", "httponly", "samesite", "secure")


def lire_cookie(reponse):
    """(valeur, {attribut: valeur}) du cookie access_token, lus dans l'en-tête brut, en minuscules."""
    brut = reponse.headers["set-cookie"]
    premier, *morceaux = [morceau.strip() for morceau in brut.split(";")]
    nom, valeur = premier.split("=", 1)
    assert nom == NOM_COOKIE_JWT
    attributs = {}
    for morceau in morceaux:
        cle, _, val = morceau.partition("=")
        attributs[cle.lower()] = val.lower()
    return valeur, attributs


def partages(attributs):
    return {cle: val for cle, val in attributs.items() if cle in ATTRIBUTS_PARTAGES}


def inscrire_et_connecter(client):
    inscription = client.post(
        "/api/authentification/inscription",
        json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE, "nom_affichage": "Ada"},
    )
    assert inscription.status_code == 201
    connexion = client.post(
        "/api/authentification/connexion", json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE}
    )
    assert connexion.status_code == 200
    return connexion


# --- Succès --------------------------------------------------------------------------------


def test_deconnexion_renvoie_204_et_corps_vide(client, base_propre):
    inscrire_et_connecter(client)

    reponse = client.post(URL)

    assert reponse.status_code == 204
    assert reponse.content == b""


def test_deconnexion_efface_le_cookie(client, base_propre):
    inscrire_et_connecter(client)

    valeur, attributs = lire_cookie(client.post(URL))

    # Starlette écrit une valeur vide entre guillemets (`access_token=""`).
    assert valeur in ("", '""')
    assert attributs["max-age"] == "0"
    assert attributs["path"] == "/"
    assert "httponly" in attributs
    assert attributs["samesite"] == "lax"
    assert "secure" not in attributs


def test_attributs_identiques_a_la_connexion(client, base_propre):
    _, a_la_connexion = lire_cookie(inscrire_et_connecter(client))

    _, a_la_deconnexion = lire_cookie(client.post(URL))

    assert partages(a_la_deconnexion) == partages(a_la_connexion)


def test_secure_en_production_dans_les_deux_cookies(client, base_propre, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    jeton, a_la_connexion = lire_cookie(inscrire_et_connecter(client))
    # Le client de test parle en http : il ne renverrait pas un cookie Secure. On le repose à la main.
    client.cookies.clear()
    client.cookies.set(NOM_COOKIE_JWT, jeton)

    reponse = client.post(URL)

    assert reponse.status_code == 204
    _, a_la_deconnexion = lire_cookie(reponse)
    assert "secure" in a_la_connexion
    assert "secure" in a_la_deconnexion
    assert partages(a_la_deconnexion) == partages(a_la_connexion)


# --- 401 -----------------------------------------------------------------------------------


def test_sans_cookie_renvoie_401(client, base_propre):
    reponse = client.post(URL)

    assert reponse.status_code == 401
    assert reponse.json() == CORPS_401
    assert "set-cookie" not in reponse.headers


# Liste de couples plutôt qu'un dict : un identifiant dupliqué ne peut pas écraser un cas en silence.
CAS_ECHEC = [
    ("cookie_vide", lambda u: ""),
    ("valeur_illisible", lambda u: "n-importe-quoi"),
    ("autre_cle", lambda u: fabriquer_jeton(u.id, cle=AUTRE_CLE)),
    (
        "expire",
        lambda u: fabriquer_jeton(u.id, exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
    ),
    ("algorithme_hs384", lambda u: fabriquer_jeton(u.id, algo="HS384")),
    ("sub_absent", lambda u: fabriquer_jeton(None)),
    ("sub_pas_un_uuid", lambda u: fabriquer_jeton("pas-un-uuid")),
    ("exp_absent", lambda u: fabriquer_jeton(u.id, exp=None)),
    ("utilisateur_inexistant", lambda u: fabriquer_jeton(uuid.uuid4())),
]


@pytest.mark.parametrize(
    "fabrique", [fabrique for _, fabrique in CAS_ECHEC], ids=[nom for nom, _ in CAS_ECHEC]
)
def test_authentification_invalide_renvoie_la_meme_401(client, db_session, fabrique):
    # Un utilisateur existe : seul le défaut du jeton explique le 401.
    utilisateur = creer_utilisateur(db_session)
    client.cookies.set(NOM_COOKIE_JWT, fabrique(utilisateur))

    reponse = client.post(URL)

    assert reponse.status_code == 401
    assert reponse.json() == CORPS_401
    assert "set-cookie" not in reponse.headers


# --- Après la déconnexion ------------------------------------------------------------------


def test_moi_renvoie_401_apres_deconnexion(client, base_propre):
    inscrire_et_connecter(client)
    assert client.get(URL_MOI).status_code == 200

    assert client.post(URL).status_code == 204
    # Le client a appliqué l'effacement : il n'envoie plus de cookie.
    reponse = client.get(URL_MOI)

    assert reponse.status_code == 401
    assert reponse.json() == CORPS_401


def test_jeton_reste_accepte_apres_deconnexion_limite_connue(client, base_propre):
    # Ce test documente une LIMITE CONNUE du MVP : le JWT n'est pas révoqué côté serveur et reste
    # valable jusqu'à son expiration. Il devra être réécrit (401 attendu) le jour où la
    # révocation sera implémentée.
    jeton, _ = lire_cookie(inscrire_et_connecter(client))
    assert client.post(URL).status_code == 204

    client.cookies.set(NOM_COOKIE_JWT, jeton)
    reponse = client.get(URL_MOI)

    assert reponse.status_code == 200
    assert reponse.json()["email"] == EMAIL
