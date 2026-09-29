from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "checkup-api"}
    assert response.headers["X-Request-ID"]


def test_unknown_route_has_stable_error_code() -> None:
    response = TestClient(app).get("/api/v1/unknown")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
