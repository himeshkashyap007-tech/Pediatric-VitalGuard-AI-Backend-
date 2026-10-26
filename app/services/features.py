"""Signal feature extraction."""
import numpy as np
from scipy import signal as sp_signal
from scipy import stats
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FeatureExtractor:
    """Extract signal quality features from vital sign data."""
    
    def __init__(self, sample_rate: float = 100.0):
        self.sample_rate = sample_rate
    
    def extract_all_features(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract all available features from signal data."""
        
        features = {
            "available": [],
            "unavailable": [],
            "values": {}
        }
        
        # Convert to arrays
        pulse = np.array([d.get("pulse_bpm") for d in data], dtype=float)
        spo2 = np.array([d.get("spo2_percent") for d in data], dtype=float)
        timestamps = np.array([d.get("timestamp", i/self.sample_rate) for i, d in enumerate(data)], dtype=float)
        
        # Optional fields
        motion = np.array([d.get("motion") for d in data if d.get("motion") is not None], dtype=float)
        contact = np.array([d.get("contact") for d in data if d.get("contact") is not None], dtype=float)
        ppg_value = np.array([d.get("ppg_value") for d in data if d.get("ppg_value") is not None], dtype=float)
        
        # Data completeness
        completeness = self._compute_completeness(pulse)
        features["values"]["completeness"] = completeness
        features["available"].append("completeness")
        
        # Sampling regularity
        sampling_score = self._compute_sampling_regularity(timestamps)
        features["values"]["sampling_regularity"] = sampling_score
        features["available"].append("sampling_regularity")
        
        # Signal-to-noise ratio (if PPG available)
        if len(ppg_value) > 50:
            snr = self._compute_snr(ppg_value)
            features["values"]["snr"] = snr
            features["available"].append("snr")
        else:
            features["unavailable"].append("snr")
        
        # Pulse stability
        if np.sum(~np.isnan(pulse)) > 10:
            pulse_stability = self._compute_stability(pulse[~np.isnan(pulse)])
            features["values"]["pulse_stability"] = pulse_stability
            features["available"].append("pulse_stability")
        else:
            features["unavailable"].append("pulse_stability")
        
        # Motion features
        if len(motion) > 0:
            motion_mean = float(np.mean(motion))
            motion_max = float(np.max(motion))
            features["values"]["motion_mean"] = motion_mean
            features["values"]["motion_max"] = motion_max
            features["available"].extend(["motion_mean", "motion_max"])
        else:
            features["unavailable"].extend(["motion_mean", "motion_max"])
        
        # Contact features
        if len(contact) > 0:
            contact_mean = float(np.mean(contact))
            contact_min = float(np.min(contact))
            features["values"]["contact_mean"] = contact_mean
            features["values"]["contact_min"] = contact_min
            features["available"].extend(["contact_mean", "contact_min"])
        else:
            features["unavailable"].extend(["contact_mean", "contact_min"])
        
        # Baseline drift (if PPG available)
        if len(ppg_value) > 100:
            drift = self._compute_baseline_drift(ppg_value)
            features["values"]["baseline_drift"] = drift
            features["available"].append("baseline_drift")
        else:
            features["unavailable"].append("baseline_drift")
        
        # Dropout duration
        dropout_fraction = self._compute_dropout_fraction(pulse)
        features["values"]["dropout_fraction"] = dropout_fraction
        features["available"].append("dropout_fraction")
        
        logger.info(f"Extracted {len(features['available'])} features")
        
        return features
    
    def _compute_completeness(self, signal: np.ndarray) -> float:
        """Compute data completeness (0-1)."""
        if len(signal) == 0:
            return 0.0
        valid = np.sum(~np.isnan(signal))
        return float(valid / len(signal))
    
    def _compute_sampling_regularity(self, timestamps: np.ndarray) -> float:
        """Compute sampling regularity score (0-1)."""
        if len(timestamps) < 2:
            return 0.0
        
        intervals = np.diff(timestamps)
        intervals = intervals[intervals > 0]  # Remove zero intervals
        
        if len(intervals) == 0:
            return 0.0
        
        # Coefficient of variation
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        if mean_interval == 0:
            return 0.0
        
        cv = std_interval / mean_interval
        
        # Convert to score (low CV = high score)
        score = np.exp(-5 * cv)
        return float(np.clip(score, 0, 1))
    
    def _compute_snr(self, signal: np.ndarray) -> float:
        """Estimate signal-to-noise ratio (dB)."""
        signal = signal[~np.isnan(signal)]
        
        if len(signal) < 50:
            return 0.0
        
        # Estimate signal power (low-pass filtered)
        b, a = sp_signal.butter(4, 0.1, btype='low')
        signal_clean = sp_signal.filtfilt(b, a, signal)
        
        # Estimate noise (residual)
        noise = signal - signal_clean
        
        signal_power = np.var(signal_clean)
        noise_power = np.var(noise)
        
        if noise_power == 0:
            return 100.0  # Very high SNR
        
        snr_db = 10 * np.log10(signal_power / noise_power)
        return float(np.clip(snr_db, -20, 100))
    
    def _compute_stability(self, signal: np.ndarray) -> float:
        """Compute signal stability score (0-1)."""
        if len(signal) < 10:
            return 0.0
        
        # Use coefficient of variation
        mean_val = np.mean(signal)
        std_val = np.std(signal)
        
        if mean_val == 0:
            return 0.0
        
        cv = std_val / mean_val
        
        # Convert to score
        score = np.exp(-2 * cv)
        return float(np.clip(score, 0, 1))
    
    def _compute_baseline_drift(self, signal: np.ndarray) -> float:
        """Compute baseline drift magnitude (0-1)."""
        signal = signal[~np.isnan(signal)]
        
        if len(signal) < 100:
            return 0.0
        
        # Detrend and compute drift
        detrended = sp_signal.detrend(signal)
        drift = signal - detrended
        
        drift_magnitude = np.std(drift) / (np.std(signal) + 1e-6)
        return float(np.clip(drift_magnitude, 0, 1))
    
    def _compute_dropout_fraction(self, signal: np.ndarray) -> float:
        """Compute fraction of dropped samples."""
        if len(signal) == 0:
            return 1.0
        
        dropout = np.sum(np.isnan(signal))
        return float(dropout / len(signal))
