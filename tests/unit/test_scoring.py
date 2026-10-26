"""Test quality scoring."""
import pytest
from app.services.quality_scoring import QualityScorer

def test_quality_scorer_initialization():
    """Test scorer init."""
    scorer = QualityScorer()
    assert scorer.weights is not None

def test_compute_quality_with_high_quality():
    """Test scoring high quality signal."""
    scorer = QualityScorer()
    
    features = {
        "available": ["snr", "completeness", "pulse_stability"],
        "unavailable": ["motion_mean"],
        "values": {
            "snr": 40,  # High SNR
            "completeness": 1.0,
            "pulse_stability": 0.95
        }
    }
    
    artifacts = []
    data = []
    
    result = scorer.compute_quality_score(features, artifacts, data)
    
    assert result["overall"] >= 70  # Should be high
    assert result["category"] in ["high", "moderate"]
    assert "snr" in result["components"]

def test_compute_quality_with_low_quality():
    """Test scoring low quality signal."""
    scorer = QualityScorer()
    
    features = {
        "available": ["snr", "completeness"],
        "unavailable": [],
        "values": {
            "snr": 5,  # Very low SNR
            "completeness": 0.6  # 40% missing
        }
    }
    
    artifacts = [
        {"type": "noise", "severity": "high"},
        {"type": "dropout", "severity": "high"}
    ]
    data = []
    
    result = scorer.compute_quality_score(features, artifacts, data)
    
    assert result["overall"] < 60  # Should be low
    assert result["category"] in ["low", "moderate", "insufficient"]
    assert len(result["explanations"]) > 0

def test_quality_score_bounds():
    """Test quality score stays in bounds."""
    scorer = QualityScorer()
    
    features = {
        "available": ["completeness"],
        "unavailable": [],
        "values": {"completeness": 1.0}
    }
    
    result = scorer.compute_quality_score(features, [], [])
    
    assert 0 <= result["overall"] <= 100

def test_insufficient_features():
    """Test scoring with insufficient features."""
    scorer = QualityScorer()
    
    features = {
        "available": ["completeness"],
        "unavailable": ["snr", "stability", "motion", "contact"],
        "values": {"completeness": 0.8}
    }
    
    result = scorer.compute_quality_score(features, [], [])
    
    # With only 1 feature, might be marked insufficient
    assert result["category"] in ["insufficient", "moderate", "low"]
