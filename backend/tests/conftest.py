"""Fixtures de test : base PostgreSQL dédiée, jamais la base de développement.

TEST_DATABASE_URL est obligatoire et son nom de base doit se terminer par `_test`, sinon la
session pytest s'arrête avant tout accès à la base. Le schéma doit déjà exister (migrations
Alembic appliquées sur cette base) ; ce fichier ne crée ni la base ni les tables.
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

URL_DE_TEST = os.environ.get("TEST_DATABASE_URL", "")
# Origine du front, autorisée par ALLOWED_ORIGINS et envoyée par défaut par la fixture `client`.
ORIGINE_DE_TEST = "http://localhost:5173"


def _verifier_url_de_test(url: str) -> None:
    if not url:
        pytest.exit("TEST_DATABASE_URL est obligatoire pour lancer les tests.", returncode=2)
    nom_base = make_url(url).database or ""
    if not nom_base.endswith("_test"):
        pytest.exit(
            "TEST_DATABASE_URL doit viser une base dont le nom se termine par _test "
            "(refus d'exécuter les tests sur une autre base).",
            returncode=2,
        )


_verifier_url_de_test(URL_DE_TEST)

# L'application construit son moteur à l'import de app.db.session, à partir de DATABASE_URL :
# on la redirige vers la base de test AVANT d'importer l'application.
os.environ["DATABASE_URL"] = URL_DE_TEST
# Réglages déterministes, indépendants de l'environnement de la machine. Affectation directe
# (pas setdefault) : Settings() est construit à l'import de l'application et exige JWT_SECRET.
os.environ["JWT_SECRET"] = "cle-de-test-uniquement-0123456789-abcdef"
os.environ["JWT_EXPIRE_MINUTES"] = "30"
os.environ["ENVIRONMENT"] = "development"
os.environ["ALLOWED_ORIGINS"] = ORIGINE_DE_TEST

from app.core import limiteur  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Tables vidées entre deux tests. `categories` n'en fait pas partie : elle est remplie par la
# migration initiale. CASCADE vide aussi depenses et budgets (clés étrangères vers utilisateurs).
TABLES_A_VIDER = "utilisateurs"


@pytest.fixture(autouse=True)
def limiteur_a_zero() -> Iterator[None]:
    """Le compteur de tentatives est global au processus : on le vide avant chaque test."""
    limiteur.reinitialiser_tout()
    yield


@pytest.fixture(scope="session")
def moteur_de_test():
    moteur = create_engine(URL_DE_TEST, pool_pre_ping=True, hide_parameters=True)
    yield moteur
    moteur.dispose()


@pytest.fixture
def base_propre(moteur_de_test) -> Iterator[None]:
    def vider() -> None:
        with moteur_de_test.begin() as connexion:
            connexion.execute(text(f"TRUNCATE TABLE {TABLES_A_VIDER} CASCADE"))

    vider()
    yield
    vider()


@pytest.fixture
def db_session(moteur_de_test, base_propre) -> Iterator[Session]:
    """Session indépendante, qui commite réellement : les tests voient les vraies transactions.

    L'isolation vient du vidage des tables (base_propre), pas d'un rollback global : le service
    fait lui-même commit() et rollback(), ce qu'un test enveloppé dans une transaction masquerait.
    """
    session = sessionmaker(bind=moteur_de_test, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session) -> Iterator[TestClient]:
    """TestClient dont toutes les requêtes d'un test partagent la même `db_session`.

    La session n'est pas fermée entre deux requêtes : sa fermeture reste à la charge de la
    fixture `db_session`, en fin de test. Chaque requête envoie `Origin: ORIGINE_DE_TEST`, comme
    le navigateur derrière le proxy Vite ; un test peut le retirer avec `del client.headers["origin"]`.
    """

    def get_db_de_test() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = get_db_de_test
    # raise_server_exceptions=False : une exception inattendue donne la réponse 500 réelle.
    try:
        yield TestClient(app, raise_server_exceptions=False, headers={"Origin": ORIGINE_DE_TEST})
    finally:
        app.dependency_overrides.pop(get_db, None)
