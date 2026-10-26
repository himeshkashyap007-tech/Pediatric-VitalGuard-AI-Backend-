"""Test signal simulator."""
import pytest
import numpy as np
from app.services.simulator import SignalSimulator
from app.core.constants import SCENARIOS

def test_simulator_initialization():
    """Test simulator with seed."""
    sim = SignalSimulator(seed=42)
    assert sim.seed == 42

def test_generate_ppg_waveform():
    """Test PPG waveform generation."""
    sim = SignalSimulator(seed=42)
    signal = sim.generate_ppg_waveform(duration=10, sample_rate=100, pulse_rate=120)
    
    assert len(signal) == 1000  # 10s * 100Hz
    assert np.all(np.isfinite(signal))

def test_simulate_clean_scenario():
    """Test clean scenario simulation."""
    sim = SignalSimulator(seed=42)
    result = sim.simulate("clean", duration=30, sample_rate=100)
    
    assert "data" in result
    assert "metadata" in result
    assert len(result["data"]) == 3000
    assert result["metadata"]["scenario"] == "clean"
    assert result["metadata"]["synthetic_data"] is True

def test_simulate_all_scenarios():
    """Test all scenarios can be simulated."""
    sim = SignalSimulator(seed=42)
    
    for scenario in SCENARIOS.keys():
        result = sim.simulate(scenario, duration=10, sample_rate=50)
        assert len(result["data"]) > 0
        assert result["metadata"]["scenario"] == scenario

def test_scenario_reproducibility():
    """Test that same seed produces same results."""
    sim1 = SignalSimulator(seed=123)
    result1 = sim1.simulate("clean", duration=5, sample_rate=100)
    
    sim2 = SignalSimulator(seed=123)
    result2 = sim2.simulate("clean", duration=5, sample_rate=100)
    
    data1 = [d["pulse_bpm"] for d in result1["data"]]
    data2 = [d["pulse_bpm"] for d in result2["data"]]
    
    assert np.allclose(data1, data2)

def test_movement_scenario_has_motion():
    """Test movement scenario includes motion data."""
    sim = SignalSimulator(seed=42)
    result = sim.simulate("movement", duration=10, sample_rate=100)
    
    motion_values = [d.get("motion", 0) for d in result["data"]]
    assert np.max(motion_values) > 0.1  # Should have motion

def test_clean_unusual_value_scenario():
    """Test clean signal with unusual values."""
    sim = SignalSimulator(seed=42)
    result = sim.simulate("clean_unusual_value", duration=10, sample_rate=100)
    
    pulse_values = [d["pulse_bpm"] for d in result["data"]]
    mean_pulse = np.mean(pulse_values)
    
    # Should be high (unusual) but signal should be clean
    assert mean_pulse > 170
    motion_values = [d.get("motion", 0) for d in result["data"]]
    assert np.max(motion_values) < 0.1  # Clean signal

def test_dropout_scenario_has_missing_data():
    """Test dropout scenario has NaN values."""
    sim = SignalSimulator(seed=42)
    result = sim.simulate("signal_dropout", duration=10, sample_rate=100)
    
    ppg_values = [d.get("ppg_value") for d in result["data"]]
    none_count = sum(1 for v in ppg_values if v is None)
    
    assert none_count > 0  # Should have dropouts
