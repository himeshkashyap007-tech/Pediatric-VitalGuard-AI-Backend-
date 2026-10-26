"""Test feature extraction."""
import pytest
import numpy as np
from app.services.features import FeatureExtractor

def test_feature_extractor_initialization():
    """Test feature extractor init."""
    extractor = FeatureExtractor(sample_rate=100)
    assert extractor.sample_rate == 100

def test_extract_completeness():
    """Test completeness calculation."""
    extractor = FeatureExtractor()
    
    data = [
        {"pulse_bpm": 120, "spo2_percent": 98},
        {"pulse_bpm": 121, "spo2_percent": 98},
        {"pulse_bpm": None, "spo2_percent": 97},
        {"pulse_bpm": 119, "spo2_percent": None}
    ]
    
    features = extractor.extract_all_features(data)
    
    assert "completeness" in features["available"]
    assert 0 <= features["values"]["completeness"] <= 1

def test_extract_snr_with_ppg():
    """Test SNR calculation with PPG data."""
    extractor = FeatureExtractor()
    
    # Generate synthetic clean signal
    t = np.arange(0, 10, 0.01)
    signal = np.sin(2 * np.pi * 2 * t) + 0.1 * np.random.randn(len(t))
    
    data = [
        {"pulse_bpm": 120, "spo2_percent": 98, "ppg_value": s}
        for s in signal
    ]
    
    features = extractor.extract_all_features(data)
    
    if "snr" in features["available"]:
        assert features["values"]["snr"] > 0  # Should have positive SNR

def test_extract_without_optional_fields():
    """Test extraction with only required fields."""
    extractor = FeatureExtractor()
    
    data = [
        {"pulse_bpm": 120 + i % 10, "spo2_percent": 98}
        for i in range(100)
    ]
    
    features = extractor.extract_all_features(data)
    
    assert "completeness" in features["available"]
    assert "motion_mean" in features["unavailable"]
    assert "contact_mean" in features["unavailable"]
