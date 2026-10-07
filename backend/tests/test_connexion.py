"""Tests de POST /api/authentification/connexion.

Hypothèses sur tests/conftest.py : `client` et `db_session` comme pour l'inscription ; JWT_SECRET,
JWT_EXPIRE_MINUTES=30 et ENVIRONMENT=development affectés avant l'import de l'application ; le
limiteur est remis à zéro avant chaque test (fixture autouse).
"""

from types import SimpleNamespace

import jwt
import pytest
from pydantic import ValidationError

from app.core import limiteur
from app.core.config import Settings, settings
from app.core.securite import NOM_COOKIE_JWT, hacher_mot_de_passe
from app.models.utilisateur import Utilisateur
from app.services import authentification as service

URL = "/api/authentification/connexion"
MOT_DE_PASSE = "Un-mot-de-passe-valide"
# Un seul hachage Argon2 pour tout le module.
HASH = hacher_mot_de_passe(MOT_DE_PASSE)
MESSAGE_401 = "Email ou mot de passe incorrect."


def corps(**surcharges):
    donnees = {"email": "ada@x.fr", "mot_de_passe": MOT_DE_PASSE}
    donnees.update(surcharges)
    return donnees


def creer_utilisateur(db_session, email="ada@x.fr", hache=HASH):
    utilisateur = Utilisateur(email=email, mot_de_passe_hache=hache, nom_affichage="Ada")
    db_session.add(utilisateur)
    db_session.commit()
    return utilisateur


@pytest.fixture
def utilisateur(db_session):
    return creer_utilisateur(db_session)


def lire_cookie(reponse):
    """(valeur, attributs en minuscules) du cookie access_token, lus dans l'en-tête brut."""
    brut = reponse.headers["set-cookie"]
    premier, *attributs = [morceau.strip() for morceau in brut.split(";")]
    nom, valeur = premier.split("=", 1)
    assert nom == NOM_COOKIE_JWT
    return valeur, [a.lower() for a in attributs]


class Espion:
    """Remplace verifier_mot_de_passe dans le service : compte les appels, sans payer Argon2."""

    def __init__(self, monkeypatch, resultat=False):
        self.resultat = resultat
        self.hashes = []
        monkeypatch.setattr(service, "verifier_mot_de_passe", self)

    def __call__(self, hache, mot_de_passe):
        self.hashes.append(hache)
        return self.resultat


# --- Cas nominal ---------------------------------------------------------------------------


def test_connexion_valide_renvoie_200_et_cookie(client, utilisateur):
    reponse = client.post(URL, json=corps())
    assert reponse.status_code == 200
    corps_json = reponse.json()
    assert set(corps_json) == {"id", "email", "nom_affichage", "date_creation"}
    assert corps_json["id"] == str(utilisateur.id)
    jeton, attributs = lire_cookie(reponse)
    # Le jeton et le hash n'apparaissent jamais dans le corps.
    assert jeton not in reponse.text
    assert "argon2" not in reponse.text
    assert MOT_DE_PASSE not in reponse.text
    assert "httponly" in attributs
    assert "samesite=lax" in attributs
    assert "path=/" in attributs
    assert "max-age=1800" in attributs
    assert "secure" not in attributs


def test_le_cookie_est_secure_en_production(client, utilisateur, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    _, attributs = lire_cookie(client.post(URL, json=corps()))
    assert "secure" in attributs


def test_jwt_du_cookie(client, utilisateur):
    jeton, _ = lire_cookie(client.post(URL, json=corps()))
    assert jwt.get_unverified_header(jeton)["alg"] == "HS256"
    claims = jwt.decode(jeton, settings.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == str(utilisateur.id)
    assert isinstance(claims["sub"], str)
    assert claims["exp"] - claims["iat"] == settings.jwt_expire_minutes * 60 == 1800


def test_email_avec_espaces_et_majuscules_est_normalise(client, utilisateur):
    assert client.post(URL, json=corps(email="  Ada@X.fr ")).status_code == 200


def test_utilisateur_en_base_avec_majuscules(client, db_session):
    creer_utilisateur(db_session, email="Ada@X.fr")
    reponse = client.post(URL, json=corps(email="ada@x.fr"))
    assert reponse.status_code == 200
    assert reponse.json()["email"] == "Ada@X.fr"


# --- 401 -----------------------------------------------------------------------------------


def test_email_inconnu_et_mauvais_mot_de_passe_donnent_le_meme_401(client, utilisateur):
    inconnu = client.post(URL, json=corps(email="inconnu@x.fr"))
    mauvais = client.post(URL, json=corps(mot_de_passe="mauvais-mot-de-passe"))
    assert inconnu.status_code == mauvais.status_code == 401
    assert inconnu.json() == mauvais.json()
    erreur = inconnu.json()["erreur"]
    assert erreur["code"] == "non_authentifie"
    assert erreur["message"] == MESSAGE_401
    assert "champs" not in erreur
    for reponse in (inconnu, mauvais):
        assert "mauvais-mot-de-passe" not in reponse.text
        assert MOT_DE_PASSE not in reponse.text
        assert "ada@x.fr" not in reponse.text
        assert "inconnu@x.fr" not in reponse.text
        assert "set-cookie" not in reponse.headers


def test_email_inconnu_verifie_quand_meme_un_hash(client, monkeypatch):
    espion = Espion(monkeypatch)
    assert client.post(URL, json=corps(email="inconnu@x.fr")).status_code == 401
    assert len(espion.hashes) == 1
    assert espion.hashes[0].startswith("$argon2id$")


def test_apres_un_401_la_requete_suivante_reussit(client, utilisateur):
    assert client.post(URL, json=corps(mot_de_passe="mauvais-mot-de-passe")).status_code == 401
    # La session partagée ne doit pas être restée dans un état inutilisable.
    assert client.post(URL, json=corps()).status_code == 200


# --- 422 -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("donnees", "champ"),
    [
        ({"email": "pas-un-email", "mot_de_passe": "secret-envoye"}, "email"),
        ({"email": "ada@x.fr", "mot_de_passe": "s" * 129}, "mot_de_passe"),
        ({"mot_de_passe": "secret-envoye"}, "email"),
        ({"email": "ada@x.fr"}, "mot_de_passe"),
    ],
)
def test_donnees_invalides_renvoient_422(client, donnees, champ):
    reponse = client.post(URL, json=donnees)
    assert reponse.status_code == 422
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "donnees_invalides"
    assert champ in erreur["champs"]
    assert "secret-envoye" not in reponse.text
    assert "s" * 129 not in reponse.text


def test_mot_de_passe_de_129_caracteres_ne_declenche_pas_argon2(client, monkeypatch):
    espion = Espion(monkeypatch)
    client.post(URL, json=corps(mot_de_passe="a" * 129))
    assert espion.hashes == []


def test_mot_de_passe_court_donne_401_et_pas_422(client, monkeypatch):
    Espion(monkeypatch)
    reponse = client.post(URL, json=corps(mot_de_passe="a" * 9))
    assert reponse.status_code == 401
    assert reponse.json()["erreur"]["message"] == MESSAGE_401


# --- 429 -----------------------------------------------------------------------------------


def test_sixieme_essai_rate_renvoie_429_sans_argon2(client, utilisateur, monkeypatch):
    espion = Espion(monkeypatch)
    for _ in range(limiteur.MAX_ECHECS):
        assert client.post(URL, json=corps()).status_code == 401
    assert len(espion.hashes) == 5
    reponse = client.post(URL, json=corps())
    assert reponse.status_code == 429
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "trop_de_tentatives"
    assert erreur["message"] == "Trop de tentatives, réessayez plus tard."
    assert "champs" not in erreur
    assert "retry-after" not in reponse.headers
    # Le limiteur est consulté avant Argon2 : aucun nouvel appel.
    assert len(espion.hashes) == 5


def test_meme_le_bon_mot_de_passe_est_refuse_pendant_le_blocage(client, utilisateur, monkeypatch):
    espion = Espion(monkeypatch)
    for _ in range(limiteur.MAX_ECHECS):
        client.post(URL, json=corps())
    espion.resultat = True
    assert client.post(URL, json=corps()).status_code == 429


def test_un_succes_avant_le_seuil_remet_le_compteur_a_zero(client, utilisateur, monkeypatch):
    espion = Espion(monkeypatch)
    for _ in range(limiteur.MAX_ECHECS - 1):
        assert client.post(URL, json=corps()).status_code == 401
    espion.resultat = True
    assert client.post(URL, json=corps()).status_code == 200
    espion.resultat = False
    for _ in range(limiteur.MAX_ECHECS):
        assert client.post(URL, json=corps()).status_code == 401
    assert client.post(URL, json=corps()).status_code == 429


def test_un_email_inconnu_atteint_aussi_le_429(client, monkeypatch):
    Espion(monkeypatch)
    for _ in range(limiteur.MAX_ECHECS):
        assert client.post(URL, json=corps(email="inconnu@x.fr")).status_code == 401
    assert client.post(URL, json=corps(email="inconnu@x.fr")).status_code == 429


def test_le_compteur_est_par_email_normalise(client, monkeypatch):
    Espion(monkeypatch)
    for _ in range(limiteur.MAX_ECHECS):
        client.post(URL, json=corps(email="inconnu@x.fr"))
    assert client.post(URL, json=corps(email=" INCONNU@x.fr ")).status_code == 429
    assert client.post(URL, json=corps(email="autre@x.fr")).status_code == 401


def test_les_echecs_expirent_apres_la_fenetre(client, monkeypatch):
    Espion(monkeypatch)
    heure = [1000.0]
    monkeypatch.setattr(limiteur, "time", SimpleNamespace(monotonic=lambda: heure[0]))
    for _ in range(limiteur.MAX_ECHECS):
        client.post(URL, json=corps(email="inconnu@x.fr"))
    assert client.post(URL, json=corps(email="inconnu@x.fr")).status_code == 429
    heure[0] += limiteur.FENETRE_SECONDES + 1
    assert client.post(URL, json=corps(email="inconnu@x.fr")).status_code == 401


# --- Configuration -------------------------------------------------------------------------


def test_settings_valides(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    assert Settings(_env_file=None).jwt_secret == "s" * 32


@pytest.mark.parametrize("secret", [None, "", "s" * 31])
def test_jwt_secret_absent_vide_ou_trop_court_est_refuse(monkeypatch, secret):
    if secret is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(ValidationError) as info:
        Settings(_env_file=None)
    if secret:
        # L'erreur ne recopie pas la clé fournie.
        assert secret not in str(info.value)


@pytest.mark.parametrize("duree", ["0", "-5"])
def test_duree_du_jwt_non_positive_est_refusee(monkeypatch, duree):
    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", duree)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
