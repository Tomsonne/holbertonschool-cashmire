"""Tolérance au décalage d'horloge dans la lecture du JWT.

Un jeton dont l'`iat` est de quelques secondes dans le futur (horloge qui a reculé ou serveurs
légèrement décalés) reste accepté ; un jeton très en avance ou expiré est toujours refusé.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.securite import NOM_COOKIE_JWT, TOLERANCE_HORLOGE_SECONDES, decoder_jwt

ID = "11111111-2222-4333-8444-555555555555"


def _jeton(iat_decalage: float, exp_decalage: float = 1800) -> str:
    maintenant = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": ID,
            "iat": maintenant + timedelta(seconds=iat_decalage),
            "exp": maintenant + timedelta(seconds=exp_decalage),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.mark.parametrize("avance", [0, 1.3, 5, TOLERANCE_HORLOGE_SECONDES - 2])
def test_un_jeton_legerement_en_avance_est_accepte(avance):
    assert str(decoder_jwt(_jeton(avance))) == ID


@pytest.mark.parametrize("avance", [TOLERANCE_HORLOGE_SECONDES + 30, 300, 3600])
def test_un_jeton_tres_en_avance_est_refuse(avance):
    assert decoder_jwt(_jeton(avance)) is None


def test_un_jeton_expire_reste_refuse():
    assert decoder_jwt(_jeton(-3600, exp_decalage=-1800)) is None


def test_un_jeton_expire_depuis_plus_que_la_marge_est_refuse():
    assert decoder_jwt(_jeton(-1900, exp_decalage=-(TOLERANCE_HORLOGE_SECONDES + 30))) is None


def test_la_connexion_reste_utilisable_quand_l_horloge_recule(client, monkeypatch):
    # Scénario du défaut : le jeton est créé, puis l'horloge recule de ~1,3 s avant sa lecture.
    ident = {"email": "ada@example.com", "mot_de_passe": "un-mot-de-passe-long"}
    assert client.post("/api/authentification/inscription", json={**ident, "nom_affichage": "A"}).status_code == 201
    assert client.post("/api/authentification/connexion", json=ident).status_code == 200
    jeton = client.cookies.get(NOM_COOKIE_JWT)
    claims = jwt.decode(jeton, options={"verify_signature": False})
    # Un jeton émis 1,3 s « dans le futur » (comme après un recul d'horloge) est encore accepté.
    futur = jwt.encode(
        {**claims, "iat": datetime.now(timezone.utc) + timedelta(seconds=1.3)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    client.cookies.set(NOM_COOKIE_JWT, futur)
    assert client.get("/api/authentification/moi").status_code == 200
