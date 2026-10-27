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


def test_list_datasets_endpoint():
    """Verify GET /api/datasets returns available dataset options."""
    client = TestClient(app)
    response = client.get("/api/datasets")
    assert response.status_code == 200
    payload = response.json()
    assert "datasets" in payload
    dataset_ids = [d["id"] for d in payload["datasets"]]
    assert "default" in dataset_ids
    assert "small" in dataset_ids
    assert "impossible" in dataset_ids


def test_get_latest_timetable_default():
    """Verify GET /api/timetable/latest returns timetable rows and metadata from SQLite."""
    client = TestClient(app)
    response = client.get("/api/timetable/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "sample", "ok")
    assert data["run_id"] is not None
    assert data["total_sessions"] > 0
    assert len(data["rows"]) == data["total_sessions"]
    assert len(data["divisions"]) > 0
    assert len(data["teachers"]) > 0
    assert len(data["rooms"]) > 0
    assert len(data["timeslots"]) > 0
    assert "violations" in data
    assert "score" in data


def test_get_latest_timetable_division_filter():
    """Verify GET /api/timetable/latest with division_id filter returns only matching sessions."""
    client = TestClient(app)
    response = client.get("/api/timetable/latest", params={"division_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert all(r["division_id"] == 1 for r in data["rows"])


def test_get_latest_timetable_empty_dataset():
    """Verify GET /api/timetable/latest handles datasets without successful runs gracefully."""
    client = TestClient(app)
    response = client.get("/api/timetable/latest", params={"dataset": "impossible"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "empty"
    assert data["run_id"] is None
    assert data["rows"] == []
    assert len(data["divisions"]) > 0


def test_get_conflict_graph_endpoint():
    """Verify GET /api/graph returns React Flow compatible nodes and edges."""
    client = TestClient(app)
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert data["metadata"]["total_nodes"] > 0
    assert data["metadata"]["total_edges"] > 0
    assert "nodes" in data
    assert "edges" in data
    # Verify React Flow node contract
    first_node = data["nodes"][0]
    assert "id" in first_node
    assert "position" in first_node
    assert "data" in first_node
    assert "sessionId" in first_node["data"]
    assert "subjectCode" in first_node["data"]
    # Verify React Flow edge contract
    first_edge = data["edges"][0]
    assert "id" in first_edge
    assert "source" in first_edge
    assert "target" in first_edge
    assert "data" in first_edge


def test_generate_timetable_success(tmp_path, monkeypatch):
    """Verify POST /api/generate invokes pipeline and persists timetable to SQLite."""
    import shutil
    import timetable.backend.db.config as cfg
    temp_db = tmp_path / "test_gen.db"
    shutil.copyfile(cfg.DATA_DIR / "small.db", temp_db)
    monkeypatch.setenv("TIMETABLE_DB_PATH", str(temp_db))

    client = TestClient(app)
    response = client.post(
        "/api/generate",
        json={"dataset": "default", "seed": 42, "optimizer_iterations": 20},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["run_id"] is not None
    assert data["colors_used"] > 0
    assert data["violations"] == []
    assert data["score"] is not None


def test_generate_timetable_impossible_failure(tmp_path, monkeypatch):
    """Verify POST /api/generate on impossible dataset fails safely and returns 422 with explanation."""
    import shutil
    import timetable.backend.db.config as cfg
    temp_db = tmp_path / "test_impossible.db"
    shutil.copyfile(cfg.DATA_DIR / "impossible.db", temp_db)
    monkeypatch.setenv("TIMETABLE_DB_PATH", str(temp_db))

    client = TestClient(app)
    response = client.post(
        "/api/generate",
        json={"dataset": "default", "max_attempts": 2},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "failed"
    assert "message" in data
    assert "violations" in data


def test_generate_timetable_invalid_dataset():
    """Verify POST /api/generate with unknown dataset returns 400 Bad Request."""
    client = TestClient(app)
    response = client.post(
        "/api/generate",
        json={"dataset": "non_existent_dataset"},
    )
    assert response.status_code == 400


