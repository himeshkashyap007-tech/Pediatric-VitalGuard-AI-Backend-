
"""Unit tests for the report generation service."""

import json
import pytest

from app.services.reporting import ReportGenerator


@pytest.fixture
def generator():
    return ReportGenerator()


@pytest.fixture
def sample_analysis():
    return {
        "data_source": "test_data.csv",
        "sample_count": 100,
        "quality_score": {
            "overall": 87.456,
            "category": "good",
            "label": "High quality",
            "components": {
                "completeness": 90.0,
                "signal_quality": 85.5,
            },
            "explanations": [
                "Some samples contain movement noise",
                "Signal completeness is acceptable",
            ],
        },
        "artifacts": [
            {
                "type": "motion",
                "severity": "medium",
                "explanation": "Movement-related signal disturbance",
            },
        ],
        "physiological": {
            "pulse_status": "within_typical_range",
            "spo2_status": "within_typical_range",
            "clinical_ranges_configured": False,
            "warnings": ["Clinical reference ranges not configured"],
        },
    }


# JSON report tests

def test_json_report_returns_dictionary(generator, sample_analysis):
    result = generator.generate_json_report(sample_analysis)

    assert isinstance(result, dict)


def test_json_report_contains_required_fields(generator, sample_analysis):
    result = generator.generate_json_report(sample_analysis)

    assert result["report_type"] == "json"
    assert "generated_at" in result
    assert "system" in result
    assert "disclaimer" in result
    assert "analysis" in result


def test_json_report_contains_correct_system_metadata(
    generator, sample_analysis
):
    result = generator.generate_json_report(sample_analysis)

    assert result["system"]["name"] == "Pediatric VitalGuard AI"
    assert result["system"]["version"] == "1.0.0"
    assert result["system"]["identifier"] == "MED-PS-010"


def test_json_report_contains_prototype_disclaimer(
    generator, sample_analysis
):
    result = generator.generate_json_report(sample_analysis)

    assert result["disclaimer"]["prototype_status"] is True
    assert result["disclaimer"]["not_for_medical_use"] is True
    assert "not clinically validated" in result["disclaimer"]["warning"]


def test_json_report_preserves_analysis(generator, sample_analysis):
    result = generator.generate_json_report(sample_analysis)

    assert result["analysis"] == sample_analysis


def test_json_report_is_serializable(generator, sample_analysis):
    result = generator.generate_json_report(sample_analysis)

    serialized = json.dumps(result)
    restored = json.loads(serialized)

    assert restored["analysis"] == sample_analysis


def test_json_report_handles_empty_analysis(generator):
    result = generator.generate_json_report({})

    assert result["analysis"] == {}
    assert result["report_type"] == "json"


def test_json_report_timestamp_ends_with_z(generator, sample_analysis):
    result = generator.generate_json_report(sample_analysis)

    assert result["generated_at"].endswith("Z")


# CSV report tests

def test_csv_report_returns_string(generator, sample_analysis):
    result = generator.generate_csv_report(sample_analysis)

    assert isinstance(result, str)


def test_csv_report_contains_report_title(generator, sample_analysis):
    result = generator.generate_csv_report(sample_analysis)

    assert "Pediatric VitalGuard AI - Analysis Report" in result


def test_csv_report_contains_quality_score(generator, sample_analysis):
    result = generator.generate_csv_report(sample_analysis)

    assert "Overall Score,87.46" in result
    assert "Category,good" in result
    assert "Label,High quality" in result


def test_csv_report_contains_component_scores(generator, sample_analysis):
    result = generator.generate_csv_report(sample_analysis)

    assert "completeness,90.00" in result
    assert "signal_quality,85.50" in result


def test_csv_report_contains_artifact_information(
    generator, sample_analysis
):
    result = generator.generate_csv_report(sample_analysis)

    assert "Artifacts Detected" in result
    assert "Total Count,1" in result
    assert "motion,medium,Movement-related signal disturbance" in result


def test_csv_report_handles_empty_analysis(generator):
    result = generator.generate_csv_report({})

    assert "Overall Score,0.00" in result
    assert "Category,unknown" in result
    assert "Label,N/A" in result
    assert "Total Count,0" in result


def test_csv_report_handles_multiple_artifacts(generator):
    analysis = {
        "quality_score": {},
        "artifacts": [
            {
                "type": "motion",
                "severity": "low",
                "explanation": "Small movement",
            },
            {
                "type": "dropout",
                "severity": "high",
                "explanation": "Signal interruption",
            },
        ],
    }

    result = generator.generate_csv_report(analysis)

    assert "Total Count,2" in result
    assert "motion,low,Small movement" in result
    assert "dropout,high,Signal interruption" in result


# Human-readable summary tests

def test_summary_report_returns_string(generator, sample_analysis):
    result = generator.generate_summary_report(sample_analysis)

    assert isinstance(result, str)


def test_summary_report_contains_title(generator, sample_analysis):
    result = generator.generate_summary_report(sample_analysis)

    assert "PEDIATRIC VITALGUARD AI - ANALYSIS SUMMARY" in result


def test_summary_report_contains_data_metadata(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "Data Source: test_data.csv" in result
    assert "Sample Count: 100" in result


def test_summary_report_contains_quality_assessment(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "QUALITY ASSESSMENT" in result
    assert "Overall Score: 87.46 / 100" in result
    assert "Category: GOOD" in result
    assert "Label: High quality" in result


def test_summary_report_contains_component_breakdown(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "COMPLETENESS: 90.00" in result
    assert "SIGNAL_QUALITY: 85.50" in result


def test_summary_report_contains_quality_explanations(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "Quality Factors:" in result
    assert "Some samples contain movement noise" in result
    assert "Signal completeness is acceptable" in result


def test_summary_report_contains_artifact_details(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "ARTIFACTS DETECTED" in result
    assert "MOTION [medium]" in result
    assert "Movement-related signal disturbance" in result


def test_summary_report_handles_no_artifacts(generator):
    result = generator.generate_summary_report({
        "quality_score": {},
        "artifacts": [],
        "physiological": {},
    })

    assert "No significant artifacts detected" in result


def test_summary_report_contains_physiological_validation(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "PHYSIOLOGICAL VALIDATION" in result
    assert "Pulse Status: within_typical_range" in result
    assert "SpO2 Status: within_typical_range" in result
    assert "Clinical Ranges Configured: False" in result
    assert "Clinical reference ranges not configured" in result


def test_summary_report_contains_medical_disclaimer(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "IMPORTANT DISCLAIMER" in result
    assert "Quality scores are not clinically validated." in result
    assert "DO NOT USE FOR MEDICAL DECISIONS." in result


def test_summary_report_uses_defaults_for_missing_fields(generator):
    result = generator.generate_summary_report({})

    assert "Data Source: unknown" in result
    assert "Sample Count: 0" in result
    assert "Overall Score: 0.00 / 100" in result
    assert "Category: UNKNOWN" in result
    assert "Label: N/A" in result
    assert "Pulse Status: unknown" in result
    assert "SpO2 Status: unknown" in result


def test_summary_report_contains_separator_lines(
    generator, sample_analysis
):
    result = generator.generate_summary_report(sample_analysis)

    assert "=" * 60 in result
    assert "-" * 60 in result
