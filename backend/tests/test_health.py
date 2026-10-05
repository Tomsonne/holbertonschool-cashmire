from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


def test_health_returns_available_when_database_responds():
    with patch("app.routes.health.database_is_available", return_value=True):
        response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"statut": "ok", "base_de_donnees": "disponible"}


def test_health_returns_generic_degraded_response_when_database_fails():
    with patch("app.routes.health.database_is_available", return_value=False):
        response = TestClient(app).get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"statut": "degrade", "base_de_donnees": "indisponible"}
    assert "detail" not in response.text
