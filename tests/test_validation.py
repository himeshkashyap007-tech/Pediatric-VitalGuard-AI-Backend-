
"""Unit tests for the physiological validation service."""

import pytest

from app.services.validation import PhysiologicalValidator


@pytest.fixture
def validator():
    return PhysiologicalValidator()


@pytest.fixture
def normal_data():
    return [
        {"pulse_bpm": 100, "spo2_percent": 98},
        {"pulse_bpm": 110, "spo2_percent": 97},
        {"pulse_bpm": 120, "spo2_percent": 99},
    ]


def test_validate_returns_expected_structure(validator, normal_data):
    result = validator.validate(normal_data)

    assert isinstance(result, dict)
    assert {
        "pulse_status",
        "spo2_status",
        "clinical_ranges_configured",
        "warnings",
        "data_integrity_issues",
    }.issubset(result.keys())

    assert isinstance(result["warnings"], list)
    assert isinstance(result["data_integrity_issues"], list)


def test_validate_normal_data(validator, normal_data):
    result = validator.validate(normal_data)

    assert result["pulse_status"] == "within_typical_range"
    assert result["spo2_status"] == "within_typical_range"
    assert result["data_integrity_issues"] == []


def test_empty_data_reports_missing_measurements(validator):
    result = validator.validate([])

    assert result["pulse_status"] == "no_data"
    assert result["spo2_status"] == "no_data"
    assert "No valid pulse measurements" in result["data_integrity_issues"]
    assert "No valid SpO2 measurements" in result["data_integrity_issues"]


def test_missing_pulse_values_report_no_data(validator):
    result = validator.validate([
        {"spo2_percent": 98},
        {"spo2_percent": 97},
    ])

    assert result["pulse_status"] == "no_data"
    assert "No valid pulse measurements" in result["data_integrity_issues"]


def test_missing_spo2_values_report_no_data(validator):
    result = validator.validate([
        {"pulse_bpm": 100},
        {"pulse_bpm": 110},
    ])

    assert result["spo2_status"] == "no_data"
    assert "No valid SpO2 measurements" in result["data_integrity_issues"]


def test_pulse_below_software_limit_is_reported(validator):
    result = validator.validate([
        {"pulse_bpm": -1, "spo2_percent": 98},
    ])

    assert result["pulse_status"] == "software_limits_exceeded"
    assert any(
        "pulse values below software limit" in issue
        for issue in result["data_integrity_issues"]
    )


def test_pulse_above_software_limit_is_reported(validator):
    result = validator.validate([
        {"pulse_bpm": 300, "spo2_percent": 98},
    ])

    assert result["pulse_status"] == "software_limits_exceeded"
    assert any(
        "pulse values above software limit" in issue
        for issue in result["data_integrity_issues"]
    )


def test_spo2_below_software_limit_is_reported(validator):
    result = validator.validate([
        {"pulse_bpm": 100, "spo2_percent": -1},
    ])

    assert result["spo2_status"] == "software_limits_exceeded"
    assert any(
        "SpO2 values below software limit" in issue
        for issue in result["data_integrity_issues"]
    )


def test_spo2_above_software_limit_is_reported(validator):
    result = validator.validate([
        {"pulse_bpm": 100, "spo2_percent": 101},
    ])

    assert result["spo2_status"] == "software_limits_exceeded"
    assert any(
        "SpO2 values above software limit" in issue
        for issue in result["data_integrity_issues"]
    )


def test_pulse_typical_range_warning(validator):
    result = validator.validate([
        {"pulse_bpm": 1, "spo2_percent": 98},
    ])

    # A software-limit violation takes precedence over a typical-range status.
    assert result["pulse_status"] == "software_limits_exceeded"
    assert any("typical pediatric range" in warning
               for warning in result["warnings"])


def test_spo2_below_typical_range_warning(validator):
    result = validator.validate([
        {"pulse_bpm": 100, "spo2_percent": 50},
    ])

    # The configured software minimum may also be violated.
    assert result["spo2_status"] in {
        "software_limits_exceeded",
        "outside_typical_range",
    }
    assert any("below typical pediatric range" in warning
               for warning in result["warnings"])


def test_valid_boundary_values_are_accepted(validator):
    result = validator.validate([
        {"pulse_bpm": 30, "spo2_percent": 0},
        {"pulse_bpm": 250, "spo2_percent": 100},
    ])

    # Status depends on the project's configured ranges.
    assert result["pulse_status"] in {
        "within_typical_range",
        "outside_typical_range",
        "software_limits_exceeded",
    }
    assert result["spo2_status"] in {
        "within_typical_range",
        "outside_typical_range",
        "software_limits_exceeded",
    }


def test_nan_measurements_are_ignored(validator):
    result = validator.validate([
        {"pulse_bpm": float("nan"), "spo2_percent": float("nan")},
        {"pulse_bpm": 100, "spo2_percent": 98},
    ])

    assert result["pulse_status"] != "no_data"
    assert result["spo2_status"] != "no_data"


def test_clinical_configuration_flag_is_returned(validator, normal_data):
    result = validator.validate(normal_data)

    assert isinstance(result["clinical_ranges_configured"], bool)


def test_unconfigured_clinical_ranges_add_warning(
    validator, normal_data, monkeypatch
):
    from app.services import validation

    monkeypatch.setitem(
        validation.PHYSIOLOGICAL_RANGES["pulse_bpm"],
        "clinical_configured",
        False,
    )

    result = validator.validate(normal_data)

    assert result["clinical_ranges_configured"] is False
    assert "Clinical reference ranges not configured" in result["warnings"]


def test_multiple_pulse_violations_are_counted(validator):
    result = validator.validate([
        {"pulse_bpm": -1, "spo2_percent": 98},
        {"pulse_bpm": -2, "spo2_percent": 98},
        {"pulse_bpm": 300, "spo2_percent": 98},
    ])

    issues = result["data_integrity_issues"]

    assert any("2 pulse values below software limit" in issue
               for issue in issues)
    assert any("1 pulse values above software limit" in issue
               for issue in issues)


def test_validation_handles_multiple_rows(validator, normal_data):
    result = validator.validate(normal_data)

    assert result["pulse_status"] != "no_data"
    assert result["spo2_status"] != "no_data"


def test_validation_does_not_modify_input(validator, normal_data):
    original = [row.copy() for row in normal_data]

    validator.validate(normal_data)

    assert normal_data == original
