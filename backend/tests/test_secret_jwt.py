"""Refus des secrets JWT d'exemple en production (#58).

Le dépôt est public : `.env.example`, `conftest.py` et la CI contiennent des secrets que n'importe qui
peut lire. Avec l'un d'eux, on peut fabriquer un jeton valide et ouvrir la session de n'importe quel
utilisateur. En production, l'application doit donc refuser de démarrer avec ces valeurs.

En développement, ces valeurs restent acceptées : on copie `.env.example` pour démarrer, et les tests
comme la CI les utilisent.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET_ENV_EXAMPLE = "replace-with-a-random-secret-of-at-least-32-characters"  # .env.example
SECRET_DES_TESTS = "cle-de-test-uniquement-0123456789-abcdef"  # tests/conftest.py
SECRET_DE_LA_CI = "ci-only-fictitious-secret-0123456789abcdef"  # .github/workflows/ci.yml
SECRETS_PUBLICS = [
    SECRET_ENV_EXAMPLE,
    SECRET_DES_TESTS,
    SECRET_DE_LA_CI,
    SECRET_ENV_EXAMPLE.upper(),  # la casse ne doit pas contourner le refus
    "  " + SECRET_ENV_EXAMPLE,  # ni des espaces en tête
]
BACKEND = Path(__file__).resolve().parents[1]


def _reglages(secret: str, environment: str) -> Settings:
    return Settings(_env_file=None, jwt_secret=secret, environment=environment)


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    return monkeypatch


# --- Production : les secrets publics sont refusés -----------------------------------------


@pytest.mark.parametrize("secret", SECRETS_PUBLICS)
def test_un_secret_public_est_refuse_en_production(secret):
    with pytest.raises(ValidationError) as erreur:
        _reglages(secret, "production")
    message = str(erreur.value)
    assert "JWT_SECRET" in message
    assert "openssl rand -hex 32" in message  # le message dit quoi faire
    # L'erreur ne recopie pas le secret fourni (ni sa version en majuscules ou avec espaces).
    assert secret.strip() not in message
    assert secret.strip().lower() not in message


@pytest.mark.parametrize("secret", SECRETS_PUBLICS)
def test_le_secret_public_est_refuse_aussi_quand_il_vient_de_l_environnement(env, secret):
    env.setenv("JWT_SECRET", secret)
    env.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_un_vrai_secret_aleatoire_est_accepte_en_production():
    reglages = _reglages(secrets.token_hex(32), "production")
    assert reglages.environment == "production"
    assert len(reglages.jwt_secret) == 64


def test_un_secret_de_32_caracteres_non_public_reste_accepte_en_production():
    # Le contrôle ne vise que les valeurs publiques du dépôt : il ne juge pas la qualité du secret.
    assert _reglages("s" * 32, "production").environment == "production"


# --- Développement : rien ne change --------------------------------------------------------


@pytest.mark.parametrize("secret", SECRETS_PUBLICS)
def test_les_secrets_publics_restent_acceptes_en_developpement(secret):
    assert _reglages(secret, "development").environment == "development"


def test_sans_environment_c_est_le_developpement_et_le_secret_d_exemple_passe(env):
    env.setenv("JWT_SECRET", SECRET_ENV_EXAMPLE)
    assert Settings(_env_file=None).environment == "development"


# --- Démarrage réel de l'application -------------------------------------------------------


def _demarrer(secret: str, environment: str) -> subprocess.CompletedProcess:
    environnement = {**os.environ, "JWT_SECRET": secret, "ENVIRONMENT": environment}
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND, env=environnement, capture_output=True, text=True, timeout=120,
    )


def test_l_application_ne_demarre_pas_en_production_avec_le_secret_d_exemple():
    resultat = _demarrer(SECRET_ENV_EXAMPLE, "production")
    assert resultat.returncode != 0
    sortie = resultat.stdout + resultat.stderr
    assert "JWT_SECRET" in sortie
    assert SECRET_ENV_EXAMPLE not in sortie  # rien n'est recopié dans les journaux


def test_l_application_demarre_en_production_avec_un_vrai_secret():
    resultat = _demarrer(secrets.token_hex(32), "production")
    assert resultat.returncode == 0, resultat.stderr


def test_l_application_demarre_en_developpement_avec_le_secret_d_exemple():
    assert _demarrer(SECRET_ENV_EXAMPLE, "development").returncode == 0


# --- Cohérence avec .env.example -----------------------------------------------------------


def test_le_secret_de_env_example_est_bien_celui_que_le_controle_refuse():
    """Si quelqu'un change la valeur d'exemple, le refus doit la couvrir toujours."""
    fichier = Path(__file__).resolve().parents[2] / ".env.example"
    if not fichier.exists():
        pytest.skip(f"{fichier} introuvable : le test ne tourne que depuis le dépôt (CI).")
    lignes = [ligne for ligne in fichier.read_text(encoding="utf-8").splitlines() if ligne.startswith("JWT_SECRET=")]
    assert len(lignes) == 1
    secret_exemple = lignes[0].split("=", 1)[1].strip()
    assert secret_exemple == SECRET_ENV_EXAMPLE
    with pytest.raises(ValidationError):
        _reglages(secret_exemple, "production")
