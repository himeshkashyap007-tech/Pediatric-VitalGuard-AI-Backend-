"""Python-based signal simulator - fallback when MATLAB unavailable."""
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from app.core.constants import SCENARIOS
from app.core.config import settings

logger = logging.getLogger(__name__)

class SignalSimulator:
    """Generates synthetic PPG-like signals with configurable artifacts."""
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed is not None:
            np.random.seed(seed)
    
    def generate_ppg_waveform(
        self,
        duration: float,
        sample_rate: float,
        pulse_rate: float,
        amplitude: float = 1.0
    ) -> np.ndarray:
        """
        Generate synthetic PPG-like waveform.
        
        Uses a sum of harmonics to approximate PPG morphology:
        - Fundamental frequency from pulse rate
        - Second harmonic for dicrotic notch
        - Third harmonic for shape refinement
        """
        t = np.arange(0, duration, 1/sample_rate)
        n_samples = len(t)
        
        # Convert pulse rate to frequency
        f0 = pulse_rate / 60.0  # Hz
        
        # Fundamental + harmonics (simplified PPG model)
        signal = amplitude * (
            np.sin(2 * np.pi * f0 * t) +
            0.3 * np.sin(2 * np.pi * 2 * f0 * t + np.pi/4) +
            0.1 * np.sin(2 * np.pi * 3 * f0 * t + np.pi/2)
        )
        
        return signal
    
    def add_baseline_drift(
        self,
        signal: np.ndarray,
        drift_amplitude: float,
        sample_rate: float
    ) -> np.ndarray:
        """Add low-frequency baseline drift."""
        if drift_amplitude == 0:
            return signal
        
        n_samples = len(signal)
        t = np.arange(n_samples) / sample_rate
        
        # Low-frequency drift (0.1 Hz)
        drift = drift_amplitude * np.sin(2 * np.pi * 0.1 * t)
        
        return signal + drift
    
    def add_noise(self, signal: np.ndarray, noise_level: float) -> np.ndarray:
        """Add white Gaussian noise."""
        if noise_level == 0:
            return signal
        
        noise = np.random.normal(0, noise_level, len(signal))
        return signal + noise
    
    def add_motion_artifact(
        self,
        signal: np.ndarray,
        motion_intensity: float,
        sample_rate: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Add movement-associated artifacts and return motion indicator."""
        motion_signal = np.zeros(len(signal))
        
        if motion_intensity == 0:
            return signal, motion_signal
        
        n_samples = len(signal)
        
        # Create motion bursts (0.5-5 Hz band)
        n_bursts = int(motion_intensity * 10)
        for _ in range(n_bursts):
            start = np.random.randint(0, max(1, n_samples - int(sample_rate * 2)))
            duration = np.random.randint(int(sample_rate * 0.5), int(sample_rate * 3))
            end = min(start + duration, n_samples)
            
            t_burst = np.arange(end - start) / sample_rate
            freq = np.random.uniform(0.5, 5.0)
            amplitude = motion_intensity * np.random.uniform(0.5, 1.5)
            
            burst = amplitude * np.sin(2 * np.pi * freq * t_burst)
            signal[start:end] += burst
            motion_signal[start:end] = motion_intensity
        
        return signal, motion_signal
    
    def apply_contact_degradation(
        self,
        signal: np.ndarray,
        contact_quality: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Degrade signal amplitude based on contact quality."""
        contact_signal = np.ones(len(signal)) * contact_quality
        
        # Poor contact reduces amplitude and adds variability
        amplitude_factor = 0.3 + 0.7 * contact_quality
        variability = (1 - contact_quality) * 0.3
        
        random_variation = np.random.normal(1.0, variability, len(signal))
        degraded_signal = signal * amplitude_factor * random_variation
        
        return degraded_signal, contact_signal
    
    def apply_dropout(
        self,
        signal: np.ndarray,
        dropout_prob: float
    ) -> np.ndarray:
        """Apply signal dropout (missing samples marked as NaN)."""
        if dropout_prob == 0:
            return signal
        
        mask = np.random.random(len(signal)) < dropout_prob
        signal_with_dropout = signal.copy()
        signal_with_dropout[mask] = np.nan
        
        return signal_with_dropout
    
    def simulate(
        self,
        scenario: str,
        duration: float,
        sample_rate: float
    ) -> Dict[str, Any]:
        """
        Simulate a complete scenario.
        
        Returns:
            dict with keys: data (list of dicts), metadata (dict)
        """
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        config = SCENARIOS[scenario]
        logger.info(f"Simulating scenario: {scenario}")
        
        # Generate timestamps
        t = np.arange(0, duration, 1/sample_rate)
        n_samples = len(t)
        
        # Generate pulse values
        pulse_mean = config["pulse_mean"]
        pulse_std = config["pulse_std"]
        pulse_values = np.random.normal(pulse_mean, pulse_std, n_samples)
        pulse_values = np.clip(pulse_values, 40, 220)
        
        # Abrupt change scenario
        if config.get("abrupt_change"):
            change_point = n_samples // 2
            pulse_values[change_point:] += 40
        
        # Generate SpO2 values
        spo2_mean = config["spo2_mean"]
        spo2_std = config["spo2_std"]
        spo2_values = np.random.normal(spo2_mean, spo2_std, n_samples)
        spo2_values = np.clip(spo2_values, 70, 100)
        
        # Generate PPG waveform
        ppg_signal = self.generate_ppg_waveform(
            duration, sample_rate, pulse_mean, amplitude=1.0
        )
        
        # Apply artifacts in order
        ppg_signal = self.add_baseline_drift(
            ppg_signal, config["baseline_drift"], sample_rate
        )
        
        ppg_signal, motion_signal = self.add_motion_artifact(
            ppg_signal, config["motion_intensity"], sample_rate
        )
        
        ppg_signal, contact_signal = self.apply_contact_degradation(
            ppg_signal, config["contact_quality"]
        )
        
        ppg_signal = self.add_noise(ppg_signal, config["noise_level"])
        
        ppg_signal = self.apply_dropout(ppg_signal, config["dropout_prob"])
        
        # Irregular sampling
        if config.get("irregular_timing"):
            # Introduce timestamp jitter
            jitter = np.random.normal(0, 0.02, n_samples)
            t = t + jitter
            t = np.cumsum(np.diff(np.insert(t, 0, 0)))
        
        # Build data records
        data = []
        for i in range(n_samples):
            record = {
                "timestamp": float(t[i]),
                "pulse_bpm": float(pulse_values[i]) if not np.isnan(pulse_values[i]) else None,
                "spo2_percent": float(spo2_values[i]) if not np.isnan(spo2_values[i]) else None,
                "ppg_value": float(ppg_signal[i]) if not np.isnan(ppg_signal[i]) else None,
                "motion": float(motion_signal[i]),
                "contact": float(contact_signal[i]),
                "ppg_amplitude": float(np.abs(ppg_signal[i])) if not np.isnan(ppg_signal[i]) else None
            }
            data.append(record)
        
        metadata = {
            "scenario": scenario,
            "scenario_name": config["name"],
            "description": config["description"],
            "duration": duration,
            "sample_rate": sample_rate,
            "expected_samples": n_samples,
            "actual_samples": n_samples,
            "seed": self.seed,
            "generation_method": "python_simulator",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "synthetic_data": True
        }
        
        logger.info(f"Generated {n_samples} samples for {scenario}")
        
        return {"data": data, "metadata": metadata}

from typing import Tuple  # Add missing import
