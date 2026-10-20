"""Unit and integration tests for Member 4 FastAPI backend."""
from fastapi.testclient import TestClient

from timetable.backend.api.main import app, create_app
import backend.api.main as backend_api_main


def test_app_instances():
    """Verify both canonical and compatibility entrypoints provide configured FastAPI instances."""
    assert app is not None
    assert backend_api_main.app is not None
    assert app.title == "Smart College Timetable Generator API"
    assert backend_api_main.app.title == "Smart College Timetable Generator API"


def test_health_endpoint():
    """Verify /api/health returns 200 and status ok."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_endpoint():
    """Verify OpenAPI Swagger docs are accessible at /docs."""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_cors_allowed_localhost():
    """Verify CORS preflight succeeds for http://localhost:5173."""
    client = TestClient(app)
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_allowed_127_0_0_1():
    """Verify CORS preflight succeeds for http://127.0.0.1:5173."""
    client = TestClient(app)
    headers = {
        "Origin": "http://127.0.0.1:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_disallowed_origin():
    """Verify CORS does not grant access to unapproved origins."""
    client = TestClient(app)
    headers = {
        "Origin": "http://unauthorized-origin.com",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") != "http://unauthorized-origin.com"


def test_cors_configured_frontend_origin(monkeypatch):
    """Verify CORS permits the configured FRONTEND_ORIGIN environment variable."""
    vercel_domain = "https://timetable-manager-swara.vercel.app"
    monkeypatch.setenv("FRONTEND_ORIGIN", vercel_domain)

    custom_app = create_app()
    client = TestClient(custom_app)
    headers = {
        "Origin": vercel_domain,
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == vercel_domain


def test_cors_multiple_frontend_origins(monkeypatch):
    """Verify CORS permits multiple comma-separated FRONTEND_ORIGIN values with trailing slashes."""
    monkeypatch.setenv(
        "FRONTEND_ORIGIN",
        "https://preview-1.vercel.app/, https://production.vercel.app",
    )
    custom_app = create_app()
    client = TestClient(custom_app)

    # Test preview domain
    headers = {
        "Origin": "https://preview-1.vercel.app",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://preview-1.vercel.app"

    # Test production domain
    headers = {
        "Origin": "https://production.vercel.app",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://production.vercel.app"

