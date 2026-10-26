
import pytest

from app.services.preprocessing import Preprocessor


@pytest.fixture
def preprocessor():
    """Create a fresh Preprocessor instance for each test."""
    return Preprocessor()


def make_sample(
    timestamp=1.0,
    pulse_bpm=100,
    spo2_percent=98,
    motion=0.1,
    contact=True,
    ppg_value=0.5,
):
    """Create a sample containing all supported signal fields."""
    return {
        "timestamp": timestamp,
        "pulse_bpm": pulse_bpm,
        "spo2_percent": spo2_percent,
        "motion": motion,
        "contact": contact,
        "ppg_value": ppg_value,
    }


def test_complete_data_returns_expected_summary(preprocessor):
    data = [
        make_sample(timestamp=float(i))
        for i in range(150)
    ]

    result = preprocessor.preprocess(data)

    assert result["data"] == data
    assert result["sample_count"] == 150
    assert result["valid_pulse"] == 150
    assert result["valid_spo2"] == 150

    assert result["has_motion"] is True
    assert result["has_contact"] is True
    assert result["has_ppg"] is True

    assert result["notes"] == []


def test_small_sample_count_adds_warning(preprocessor):
    data = [
        make_sample(timestamp=float(i))
        for i in range(10)
    ]

    result = preprocessor.preprocess(data)

    assert result["sample_count"] == 10
    assert any(
        "Only 10 samples" in note
        for note in result["notes"]
    )


def test_exactly_100_samples_does_not_add_small_sample_warning(
    preprocessor,
):
    data = [
        make_sample(timestamp=float(i))
        for i in range(100)
    ]

    result = preprocessor.preprocess(data)

    assert not any(
        "Only" in note and "samples" in note
        for note in result["notes"]
    )


def test_non_monotonic_timestamps_add_warning(preprocessor):
    data = [
        make_sample(timestamp=1.0),
        make_sample(timestamp=2.0),
        make_sample(timestamp=2.0),
        make_sample(timestamp=1.5),
    ]

    result = preprocessor.preprocess(data)

    assert any(
        "Non-monotonic timestamps detected" in note
        for note in result["notes"]
    )


def test_missing_timestamps_add_note(preprocessor):
    data = [
        make_sample(timestamp=1.0),
        make_sample(timestamp=None),
    ]

    result = preprocessor.preprocess(data)

    assert "Timestamps not available" in result["notes"]


def test_no_valid_pulse_adds_error(preprocessor):
    data = [
        make_sample(pulse_bpm=None),
        make_sample(pulse_bpm=None),
    ]

    result = preprocessor.preprocess(data)

    assert result["valid_pulse"] == 0
    assert (
        "Error: No valid pulse measurements"
        in result["notes"]
    )


def test_no_valid_spo2_adds_error(preprocessor):
    data = [
        make_sample(spo2_percent=None),
        make_sample(spo2_percent=None),
    ]

    result = preprocessor.preprocess(data)

    assert result["valid_spo2"] == 0
    assert (
        "Error: No valid SpO2 measurements"
        in result["notes"]
    )


def test_missing_optional_signals_add_notes(preprocessor):
    data = [
        make_sample(
            timestamp=float(i),
            motion=None,
            contact=None,
            ppg_value=None,
        )
        for i in range(120)
    ]

    result = preprocessor.preprocess(data)

    assert result["has_motion"] is False
    assert result["has_contact"] is False
    assert result["has_ppg"] is False

    assert "Motion data not available" in result["notes"]
    assert "Contact quality data not available" in result["notes"]
    assert "PPG waveform data not available" in result["notes"]


def test_empty_input_reports_missing_measurements_and_signals(
    preprocessor,
):
    result = preprocessor.preprocess([])

    assert result["data"] == []
    assert result["sample_count"] == 0
    assert result["valid_pulse"] == 0
    assert result["valid_spo2"] == 0

    assert (
        "Warning: Only 0 samples (recommended: >100)"
        in result["notes"]
    )

    # The current implementation does not add this note for empty data:
    # all([]) evaluates to True, so the missing-timestamp branch is skipped.
    assert "Timestamps not available" not in result["notes"]

    assert (
        "Error: No valid pulse measurements"
        in result["notes"]
    )
    assert (
        "Error: No valid SpO2 measurements"
        in result["notes"]
    )

    assert "Motion data not available" in result["notes"]
    assert "Contact quality data not available" in result["notes"]
    assert "PPG waveform data not available" in result["notes"]


def test_partial_optional_signal_availability(preprocessor):
    data = [
        make_sample(
            timestamp=1.0,
            motion=None,
            contact=True,
            ppg_value=None,
        ),
        make_sample(
            timestamp=2.0,
            motion=0.2,
            contact=None,
            ppg_value=0.6,
        ),
    ]

    result = preprocessor.preprocess(data)

    # A field is considered available if any sample has a non-None value.
    assert result["has_motion"] is True
    assert result["has_contact"] is True
    assert result["has_ppg"] is True

    assert "Motion data not available" not in result["notes"]
    assert "Contact quality data not available" not in result["notes"]
    assert "PPG waveform data not available" not in result["notes"]


def test_non_numeric_timestamp_behavior_is_not_silently_assumed(
    preprocessor,
):
    data = [
        make_sample(timestamp="invalid"),
        make_sample(timestamp="also-invalid"),
    ]

    # The current implementation passes non-None timestamps to numpy.diff.
    # Malformed timestamp values are therefore expected to raise an error.
    with pytest.raises((TypeError, ValueError)):
        preprocessor.preprocess(data)
