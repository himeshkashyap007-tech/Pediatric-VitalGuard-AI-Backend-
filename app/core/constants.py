"""Application constants - All 12 scenarios defined."""

SCENARIOS = {
    "clean": {
        "name": "Clean Signal",
        "description": "High-quality signal with minimal noise",
        "noise_level": 0.01,
        "motion_intensity": 0.0,
        "contact_quality": 1.0,
        "dropout_prob": 0.0,
        "baseline_drift": 0.0,
        "pulse_mean": 120,
        "pulse_std": 2,
        "spo2_mean": 98,
        "spo2_std": 0.5,
        "expected_quality": "high"
    },
    "movement": {
        "name": "Movement Artifact",
        "description": "Signal disturbed by patient movement",
        "noise_level": 0.05,
        "motion_intensity": 0.7,
        "contact_quality": 0.8,
        "dropout_prob": 0.02,
        "baseline_drift": 0.1,
        "pulse_mean": 125,
        "pulse_std": 8,
        "spo2_mean": 97,
        "spo2_std": 1.5,
        "expected_quality": "moderate"
    },
    "poor_contact": {
        "name": "Poor Contact",
        "description": "Degraded signal due to sensor contact issues",
        "noise_level": 0.08,
        "motion_intensity": 0.2,
        "contact_quality": 0.3,
        "dropout_prob": 0.05,
        "baseline_drift": 0.15,
        "pulse_mean": 110,
        "pulse_std": 6,
        "spo2_mean": 96,
        "spo2_std": 2.0,
        "expected_quality": "low"
    },
    "excessive_noise": {
        "name": "Excessive Noise",
        "description": "High noise contamination",
        "noise_level": 0.3,
        "motion_intensity": 0.1,
        "contact_quality": 0.7,
        "dropout_prob": 0.01,
        "baseline_drift": 0.05,
        "pulse_mean": 115,
        "pulse_std": 12,
        "spo2_mean": 97,
        "spo2_std": 3.0,
        "expected_quality": "low"
    },
    "baseline_drift": {
        "name": "Baseline Drift",
        "description": "Significant baseline variation",
        "noise_level": 0.03,
        "motion_intensity": 0.1,
        "contact_quality": 0.9,
        "dropout_prob": 0.0,
        "baseline_drift": 0.5,
        "pulse_mean": 118,
        "pulse_std": 4,
        "spo2_mean": 98,
        "spo2_std": 1.0,
        "expected_quality": "moderate"
    },
    "signal_dropout": {
        "name": "Signal Dropout",
        "description": "Intermittent signal loss",
        "noise_level": 0.02,
        "motion_intensity": 0.1,
        "contact_quality": 0.5,
        "dropout_prob": 0.15,
        "baseline_drift": 0.05,
        "pulse_mean": 122,
        "pulse_std": 5,
        "spo2_mean": 97,
        "spo2_std": 1.5,
        "expected_quality": "low"
    },
    "irregular_sampling": {
        "name": "Irregular Sampling",
        "description": "Non-uniform sample intervals",
        "noise_level": 0.03,
        "motion_intensity": 0.1,
        "contact_quality": 0.8,
        "dropout_prob": 0.08,
        "baseline_drift": 0.05,
        "irregular_timing": True,
        "pulse_mean": 116,
        "pulse_std": 6,
        "spo2_mean": 98,
        "spo2_std": 1.2,
        "expected_quality": "moderate"
    },
    "abrupt_pulse_change": {
        "name": "Abrupt Pulse Change",
        "description": "Sudden changes in pulse rate",
        "noise_level": 0.02,
        "motion_intensity": 0.3,
        "contact_quality": 0.9,
        "dropout_prob": 0.0,
        "baseline_drift": 0.05,
        "abrupt_change": True,
        "pulse_mean": 130,
        "pulse_std": 20,
        "spo2_mean": 98,
        "spo2_std": 0.8,
        "expected_quality": "moderate"
    },
    "clean_unusual_value": {
        "name": "Clean Signal, Unusual Value",
        "description": "High quality signal with physiologically unusual values",
        "noise_level": 0.01,
        "motion_intensity": 0.0,
        "contact_quality": 1.0,
        "dropout_prob": 0.0,
        "baseline_drift": 0.0,
        "pulse_mean": 185,  # Unusual but clean
        "pulse_std": 2,
        "spo2_mean": 92,  # Unusual but clean
        "spo2_std": 0.5,
        "unusual_value": True,
        "expected_quality": "high"
    },
    "mixed_quality": {
        "name": "Mixed Quality",
        "description": "Alternating good and poor signal quality",
        "noise_level": 0.1,
        "motion_intensity": 0.4,
        "contact_quality": 0.6,
        "dropout_prob": 0.03,
        "baseline_drift": 0.2,
        "mixed_segments": True,
        "pulse_mean": 120,
        "pulse_std": 10,
        "spo2_mean": 97,
        "spo2_std": 2.0,
        "expected_quality": "moderate"
    },
    "combined_artifacts": {
        "name": "Combined Artifacts",
        "description": "Multiple artifact types present",
        "noise_level": 0.15,
        "motion_intensity": 0.6,
        "contact_quality": 0.4,
        "dropout_prob": 0.1,
        "baseline_drift": 0.3,
        "pulse_mean": 128,
        "pulse_std": 15,
        "spo2_mean": 96,
        "spo2_std": 3.0,
        "expected_quality": "low"
    },
    "incomplete_data": {
        "name": "Incomplete Data",
        "description": "Sparse data with many gaps",
        "noise_level": 0.05,
        "motion_intensity": 0.2,
        "contact_quality": 0.5,
        "dropout_prob": 0.4,
        "baseline_drift": 0.1,
        "pulse_mean": 115,
        "pulse_std": 8,
        "spo2_mean": 97,
        "spo2_std": 2.0,
        "expected_quality": "low"
    }
}

PHYSIOLOGICAL_RANGES = {
    "pulse_bpm": {
        "software_limits": {"min": 30, "max": 250},
        "typical_pediatric": {"min": 60, "max": 180},
        "clinical_configured": False
    },
    "spo2_percent": {
        "software_limits": {"min": 0, "max": 100},
        "typical_pediatric": {"min": 95, "max": 100},
        "clinical_configured": False
    }
}

CSV_REQUIRED_COLUMNS = ["pulse_bpm", "spo2_percent"]
CSV_OPTIONAL_COLUMNS = ["timestamp", "motion", "contact", "ppg_amplitude", "signal_quality", "ppg_value"]

QUALITY_THRESHOLDS = {"high": 80, "moderate": 50, "low": 0}
QUALITY_LABELS = {
    "high": "High apparent signal quality",
    "moderate": "Moderate signal-quality concerns",
    "low": "Low apparent signal quality",
    "insufficient": "Insufficient evidence"
}

ARTIFACT_THRESHOLDS = {
    "motion": {"low": 0.1, "moderate": 0.3, "high": 0.5},
    "poor_contact": {"low": 0.7, "moderate": 0.5, "high": 0.3},
    "noise": {"low": 0.1, "moderate": 0.2, "high": 0.3},
    "drift": {"low": 0.1, "moderate": 0.3, "high": 0.5},
    "dropout": {"low": 0.05, "moderate": 0.15, "high": 0.3}
}
