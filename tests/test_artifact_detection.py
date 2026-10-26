
"""Unit tests for the artifact detection service."""

import pytest

from app.services.artifact_detection import ArtifactDetector
from app.core.constants import ARTIFACT_THRESHOLDS


@pytest.fixture
def detector():
    return ArtifactDetector()


@pytest.fixture
def clean_data():
    return [
        {
            "pulse_bpm": 100.0,
            "spo2_percent": 98.0,
            "motion": 0.0,
            "contact": 1.0,
            "timestamp": float(i),
        }
        for i in range(20)
    ]


def artifact_of_type(artifacts, artifact_type):
    return [
        artifact for artifact in artifacts
        if artifact["type"] == artifact_type
    ]


def test_detector_initializes(detector):
    assert isinstance(detector, ArtifactDetector)


def test_clean_data_produces_no_artifacts(detector, clean_data):
    features = {
        "values": {
            "motion_mean": 0.0,
            "motion_max": 0.0,
            "contact_mean": 1.0,
            "contact_min": 1.0,
            "snr": 35.0,
            "baseline_drift": 0.0,
            "dropout_fraction": 0.0,
            "sampling_regularity": 1.0,
            "completeness": 1.0,
        }
    }

    assert detector.detect_all_artifacts(clean_data, features) == []


def test_empty_features_do_not_crash(detector, clean_data):
    assert isinstance(detector.detect_all_artifacts(clean_data, {}), list)


def test_motion_artifact_is_detected(detector, clean_data):
    thresholds = ARTIFACT_THRESHOLDS["motion"]
    motion_level = (thresholds["low"] + thresholds["moderate"]) / 2

    data = [dict(row) for row in clean_data]
    data[3]["motion"] = motion_level
    data[4]["motion"] = motion_level

    features = {
        "values": {
            "motion_mean": motion_level / len(data),
            "motion_max": motion_level + 0.01,
        }
    }

    found = artifact_of_type(
        detector.detect_all_artifacts(data, features), "movement"
    )

    assert found
    assert found[0]["severity"] in {"low", "moderate", "high"}
    assert "explanation" in found[0]
    assert "features" in found[0]


def test_sustained_motion_fallback(detector):
    thresholds = ARTIFACT_THRESHOLDS["motion"]
    motion_mean = thresholds["moderate"] + 0.1
    motion_max = thresholds["moderate"] + 0.2

    # No sample crosses the low threshold, so burst detection does not
    # create an artifact. The high aggregate mean exercises the fallback.
    data = [{"motion": 0.0} for _ in range(20)]
    features = {
        "motion_mean": motion_mean,
        "motion_max": motion_max,
    }

    artifacts = detector._detect_motion_artifacts(data, features)

    assert artifacts
    assert artifacts[0]["type"] == "movement"
    assert "Sustained motion activity detected" in artifacts[0]["explanation"]


def test_motion_below_threshold_is_ignored(detector, clean_data):
    thresholds = ARTIFACT_THRESHOLDS["motion"]
    features = {
        "motion_mean": 0.0,
        "motion_max": thresholds["low"],
    }

    assert detector._detect_motion_artifacts(clean_data, features) == []


def test_poor_contact_is_detected(detector, clean_data):
    thresholds = ARTIFACT_THRESHOLDS["poor_contact"]
    contact_min = thresholds["high"] - 0.01

    features = {
        "values": {
            "contact_mean": 0.8,
            "contact_min": contact_min,
        }
    }

    found = artifact_of_type(
        detector.detect_all_artifacts(clean_data, features), "poor_contact"
    )

    assert found
    assert found[0]["severity"] == "high"
    assert "contact_min" in found[0]["features"]


def test_good_contact_is_ignored(detector, clean_data):
    features = {"contact_mean": 1.0, "contact_min": 1.0}

    assert detector._detect_contact_artifacts(clean_data, features) == []


@pytest.mark.parametrize(
    ("snr", "expected_severity"),
    [(5.0, "high"), (15.0, "moderate"), (25.0, "low")],
)
def test_noise_severity(detector, snr, expected_severity):
    artifacts = detector._detect_noise_artifacts({"snr": snr})

    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "excessive_noise"
    assert artifacts[0]["severity"] == expected_severity
    assert "snr" in artifacts[0]["features"]


def test_good_snr_has_no_noise_artifact(detector):
    assert detector._detect_noise_artifacts({"snr": 30.0}) == []


@pytest.mark.parametrize(
    ("drift", "expected_severity"),
    [
        (ARTIFACT_THRESHOLDS["drift"]["high"] + 0.01, "high"),
        (
            (
                ARTIFACT_THRESHOLDS["drift"]["moderate"]
                + ARTIFACT_THRESHOLDS["drift"]["high"]
            ) / 2,
            "moderate",
        ),
        (
            (
                ARTIFACT_THRESHOLDS["drift"]["low"]
                + ARTIFACT_THRESHOLDS["drift"]["moderate"]
            ) / 2,
            "low",
        ),
    ],
)
def test_drift_severity(detector, drift, expected_severity):
    artifacts = detector._detect_drift_artifacts({"baseline_drift": drift})

    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "baseline_drift"
    assert artifacts[0]["severity"] == expected_severity


def test_low_drift_is_ignored(detector):
    threshold = ARTIFACT_THRESHOLDS["drift"]["low"]

    assert detector._detect_drift_artifacts(
        {"baseline_drift": threshold}
    ) == []


@pytest.mark.parametrize(
    ("fraction", "expected_severity"),
    [
        (ARTIFACT_THRESHOLDS["dropout"]["high"] + 0.01, "high"),
        (
            (
                ARTIFACT_THRESHOLDS["dropout"]["moderate"]
                + ARTIFACT_THRESHOLDS["dropout"]["high"]
            ) / 2,
            "moderate",
        ),
        (
            (
                ARTIFACT_THRESHOLDS["dropout"]["low"]
                + ARTIFACT_THRESHOLDS["dropout"]["moderate"]
            ) / 2,
            "low",
        ),
    ],
)
def test_dropout_severity(detector, fraction, expected_severity):
    artifacts = detector._detect_dropout_artifacts(
        [], {"dropout_fraction": fraction}
    )

    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "signal_dropout"
    assert artifacts[0]["severity"] == expected_severity


def test_no_dropout_is_ignored(detector):
    assert detector._detect_dropout_artifacts(
        [], {"dropout_fraction": 0.0}
    ) == []


def test_insufficient_data_artifact(detector, clean_data):
    features = {"values": {"completeness": 0.3}}

    found = artifact_of_type(
        detector.detect_all_artifacts(clean_data, features),
        "insufficient_data",
    )

    assert len(found) == 1
    assert found[0]["severity"] == "high"
    assert found[0]["confidence"] == "high"
    assert "30.0%" in found[0]["explanation"]


def test_completeness_at_threshold_is_not_flagged(detector, clean_data):
    artifacts = detector.detect_all_artifacts(
        clean_data, {"values": {"completeness": 0.5}}
    )

    assert not artifact_of_type(artifacts, "insufficient_data")


@pytest.mark.parametrize(
    ("score", "expected_severity"),
    [
        (0.60, "high"),
        (0.80, "moderate"),
        (0.90, "low"),
    ],
)
def test_sampling_irregularity_severity(
    detector, score, expected_severity
):
    artifacts = detector._detect_sampling_irregularity(
        [], {"sampling_regularity": score}
    )

    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "irregular_sampling"
    assert artifacts[0]["severity"] == expected_severity


def test_regular_sampling_is_ignored(detector):
    assert detector._detect_sampling_irregularity(
        [], {"sampling_regularity": 0.95}
    ) == []


def test_abrupt_change_requires_at_least_ten_values(detector):
    data = [{"pulse_bpm": 100.0 + i} for i in range(9)]

    assert detector._detect_abrupt_changes(data) == []


def test_abrupt_pulse_change_is_detected(detector):
    # Small variations establish a baseline; the final jump is much larger.
    pulse_values = [
        100, 101, 100, 102, 101,
        100, 102, 101, 100, 102,
        101, 100, 101, 102, 101,
        100, 102, 101, 100, 180,
    ]
    data = [{"pulse_bpm": float(value)} for value in pulse_values]

    artifacts = detector._detect_abrupt_changes(data)

    assert artifacts
    assert artifacts[0]["type"] == "abrupt_pulse_change"
    assert artifacts[0]["severity"] == "moderate"
    assert artifacts[0]["features"]["num_changes"] >= 1
    assert artifacts[0]["features"]["max_change"] > 50


def test_nan_pulse_values_are_ignored(detector):
    data = [{"pulse_bpm": float("nan")} for _ in range(12)]

    assert detector._detect_abrupt_changes(data) == []


def test_artifact_results_have_common_fields(detector):
    artifacts = detector._detect_noise_artifacts({"snr": 5.0})

    assert artifacts
    for artifact in artifacts:
        assert "type" in artifact
        assert "severity" in artifact
        assert "confidence" in artifact
        assert "explanation" in artifact
        assert "features" in artifact
