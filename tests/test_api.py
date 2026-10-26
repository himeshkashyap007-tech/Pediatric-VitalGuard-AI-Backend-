
"""API endpoint tests for Pediatric VitalGuard AI."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Pediatric VitalGuard AI"
    assert body["version"] == "1.0.0"
    assert body["identifier"] == "MED-PS-010"
    assert body["status"] == "operational"


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["version"] == "1.0.0"
    assert "timestamp" in body
    assert "matlab_available" in body


def test_config_endpoint():
    response = client.get("/api/v1/config")

    assert response.status_code == 200
    body = response.json()
    assert "scenarios" in body
    assert "physiological_ranges" in body
    assert "quality_thresholds" in body
    assert "matlab_available" in body


def test_scenarios_endpoint():
    response = client.get("/api/v1/scenarios")

    assert response.status_code == 200
    body = response.json()
    assert "scenarios" in body
    assert body["count"] == len(body["scenarios"])
    assert body["count"] > 0


def test_ranges_endpoint():
    response = client.get("/api/v1/ranges")

    assert response.status_code == 200
    body = response.json()
    assert "ranges" in body
    assert isinstance(body["ranges"], dict)


def test_example_csv_endpoint():
    response = client.get("/api/v1/example.csv")

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "example.csv"
    assert "timestamp,pulse_bpm,spo2_percent" in body["content"]
    assert "120,98" in body["content"]
