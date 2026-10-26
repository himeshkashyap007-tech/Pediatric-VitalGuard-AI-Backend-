
"""Extended API route tests for Pediatric VitalGuard AI."""

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import routes
from app.core.constants import SCENARIOS


client = TestClient(app)


def valid_simulation_payload(**overrides):
    payload = {
        "scenario": next(iter(SCENARIOS)),
        "duration": 10,
        "sample_rate": 10,
        "seed": 42,
        "use_matlab": False,
    }
    payload.update(overrides)
    return payload


def valid_signal_data(count=20):
    return [
        {
            "timestamp": i * 0.1,
            "pulse_bpm": 100 + (i % 5),
            "spo2_percent": 98,
            "motion": 0.0,
            "contact": 1.0,
            "ppg_value": 0.5,
        }
        for i in range(count)
    ]


def valid_analysis_payload(**overrides):
    payload = {
        "data": valid_signal_data(),
        "source": "upload",
        "metadata": {"test": True},
    }
    payload.update(overrides)
    return payload


def valid_report_payload(**overrides):
    payload = {
        "analysis_result": {
            "success": True,
            "sample_count": 20,
            "quality_score": {
                "overall": 90,
                "components": {},
            },
            "artifacts": [],
            "features": {"values": {}},
            "physiological": {},
            "data_quality": {},
            "metadata": {"test": True},
        },
        "format": "json",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------
# Simulation endpoint
# ---------------------------------------------------------


def test_simulate_python_success():
    response = client.post(
        "/api/v1/simulate",
        json=valid_simulation_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["source"] == "python"
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert isinstance(body["metadata"], dict)


def test_simulate_rejects_unknown_scenario():
    response = client.post(
        "/api/v1/simulate",
        json=valid_simulation_payload(scenario="unknown_scenario"),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field,value", [
    ("duration", 9),
    ("duration", 601),
    ("sample_rate", 9),
    ("sample_rate", 1001),
])
def test_simulate_rejects_out_of_range_parameters(field, value):
    response = client.post(
        "/api/v1/simulate",
        json=valid_simulation_payload(**{field: value}),
    )

    assert response.status_code == 422


def test_simulate_matlab_success(monkeypatch):
    monkeypatch.setattr(routes.settings, "MATLAB_AVAILABLE", True)

    expected = {
        "data": [{"timestamp": 0.0, "pulse_bpm": 100.0}],
        "metadata": {"generation_method": "matlab"},
    }

    monkeypatch.setattr(
        routes.matlab_adapter,
        "run_simulation",
        lambda *args: expected,
    )

    response = client.post(
        "/api/v1/simulate",
        json=valid_simulation_payload(use_matlab=True),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["source"] == "matlab"
    assert body["data"] == expected["data"]


def test_simulate_falls_back_to_python_when_matlab_fails(monkeypatch):
    monkeypatch.setattr(routes.settings, "MATLAB_AVAILABLE", True)

    def fail_matlab(*args):
        raise RuntimeError("MATLAB unavailable")

    monkeypatch.setattr(
        routes.matlab_adapter,
        "run_simulation",
        fail_matlab,
    )

    response = client.post(
        "/api/v1/simulate",
        json=valid_simulation_payload(use_matlab=True),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["source"] == "python_fallback"
    assert len(body["data"]) > 0


def test_simulate_returns_500_when_python_simulation_fails(monkeypatch):
    def fail_simulation(*args, **kwargs):
        raise RuntimeError("Simulation failure")

    monkeypatch.setattr(
        routes.SignalSimulator,
        "simulate",
        fail_simulation,
    )

    response = client.post(
        "/api/v1/simulate",
        json=valid_simulation_payload(),
    )

    assert response.status_code == 500
    assert "Simulation failure" in response.json()["detail"]


# ---------------------------------------------------------
# Analysis endpoint
# ---------------------------------------------------------


def test_analyze_success():
    response = client.post(
        "/api/v1/analyze",
        json=valid_analysis_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["sample_count"] == 20
    assert body["data_source"] == "upload"
    assert "quality_score" in body
    assert "artifacts" in body
    assert "features" in body
    assert "physiological" in body
    assert body["data_quality"]["artifact_count"] == len(body["artifacts"])


def test_analyze_accepts_matlab_source():
    response = client.post(
        "/api/v1/analyze",
        json=valid_analysis_payload(source="matlab"),
    )

    assert response.status_code == 200
    assert response.json()["data_source"] == "matlab"


def test_analyze_rejects_empty_data():
    response = client.post(
        "/api/v1/analyze",
        json=valid_analysis_payload(data=[]),
    )

    assert response.status_code == 422


def test_analyze_rejects_invalid_source():
    response = client.post(
        "/api/v1/analyze",
        json=valid_analysis_payload(source="invalid"),
    )

    assert response.status_code == 422


def test_analyze_returns_500_when_feature_extraction_fails(monkeypatch):
    def fail_extraction(*args, **kwargs):
        raise RuntimeError("Feature extraction failed")

    monkeypatch.setattr(
        routes.feature_extractor,
        "extract_all_features",
        fail_extraction,
    )

    response = client.post(
        "/api/v1/analyze",
        json=valid_analysis_payload(),
    )

    assert response.status_code == 500
    assert "Feature extraction failed" in response.json()["detail"]


# ---------------------------------------------------------
# CSV upload endpoint
# ---------------------------------------------------------


def test_upload_csv_success():
    csv_content = (
        "timestamp,pulse_bpm,spo2_percent\n"
        "0,100,98\n"
        "0.1,101,97\n"
    )

    response = client.post(
        "/api/v1/upload/csv",
        files={
            "file": (
                "signals.csv",
                io.BytesIO(csv_content.encode("utf-8")),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["filename"] == "signals.csv"
    assert "data" in body


def test_upload_csv_value_error_returns_400(monkeypatch):
    def fail_parse(*args, **kwargs):
        raise ValueError("Invalid CSV input")

    monkeypatch.setattr(routes.csv_parser, "parse", fail_parse)

    response = client.post(
        "/api/v1/upload/csv",
        files={
            "file": (
                "invalid.csv",
                io.BytesIO(b"invalid"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid CSV input"


def test_upload_csv_unexpected_error_returns_500(monkeypatch):
    def fail_parse(*args, **kwargs):
        raise RuntimeError("Unexpected parser error")

    monkeypatch.setattr(routes.csv_parser, "parse", fail_parse)

    response = client.post(
        "/api/v1/upload/csv",
        files={
            "file": (
                "signals.csv",
                io.BytesIO(b"timestamp,pulse_bpm,spo2_percent\n"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Unexpected parser error"


# ---------------------------------------------------------
# Report endpoint
# ---------------------------------------------------------


@pytest.mark.parametrize("report_format,extension", [
    ("json", ".json"),
    ("csv", ".csv"),
    ("summary", ".txt"),
])
def test_report_supported_formats(report_format, extension):
    response = client.post(
        "/api/v1/report",
        json=valid_report_payload(format=report_format),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["format"] == report_format
    assert body["filename"].startswith("pvg_report_")
    assert body["filename"].endswith(extension)
    assert "timestamp" in body
    assert "content" in body


def test_report_rejects_unknown_format():
    response = client.post(
        "/api/v1/report",
        json=valid_report_payload(format="xml"),
    )

    # The request model uses Literal, so FastAPI rejects this before
    # the endpoint's internal exception handler is reached.
    assert response.status_code == 422


def test_report_generator_error_returns_500(monkeypatch):
    def fail_report(*args, **kwargs):
        raise RuntimeError("Report generation failed")

    monkeypatch.setattr(
        routes.report_generator,
        "generate_json_report",
        fail_report,
    )

    response = client.post(
        "/api/v1/report",
        json=valid_report_payload(format="json"),
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Report generation failed"


def test_report_request_with_default_format():
    payload = valid_report_payload()
    payload.pop("format")

    response = client.post("/api/v1/report", json=payload)

    assert response.status_code == 200
    assert response.json()["format"] == "json"
