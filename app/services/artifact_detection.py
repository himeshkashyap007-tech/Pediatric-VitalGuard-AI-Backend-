"""Artifact detection service."""
import numpy as np
from typing import List, Dict, Any
import logging

from app.core.constants import ARTIFACT_THRESHOLDS

logger = logging.getLogger(__name__)

class ArtifactDetector:
    """Detect various signal artifacts."""
    
    def detect_all_artifacts(
        self,
        data: List[Dict[str, Any]],
        features: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect all artifact types."""
        
        artifacts = []
        feature_values = features.get("values", {})
        
        # Motion artifacts
        if "motion_mean" in feature_values:
            motion_artifacts = self._detect_motion_artifacts(data, feature_values)
            artifacts.extend(motion_artifacts)
        
        # Poor contact
        if "contact_mean" in feature_values:
            contact_artifacts = self._detect_contact_artifacts(data, feature_values)
            artifacts.extend(contact_artifacts)
        
        # Excessive noise
        if "snr" in feature_values:
            noise_artifacts = self._detect_noise_artifacts(feature_values)
            artifacts.extend(noise_artifacts)
        
        # Baseline drift
        if "baseline_drift" in feature_values:
            drift_artifacts = self._detect_drift_artifacts(feature_values)
            artifacts.extend(drift_artifacts)
        
        # Signal dropout
        dropout_artifacts = self._detect_dropout_artifacts(data, feature_values)
        artifacts.extend(dropout_artifacts)
        
        # Abrupt pulse changes
        pulse_artifacts = self._detect_abrupt_changes(data)
        artifacts.extend(pulse_artifacts)
        
        # Irregular sampling
        sampling_artifacts = self._detect_sampling_irregularity(data, feature_values)
        artifacts.extend(sampling_artifacts)
        
        # Insufficient data
        if feature_values.get("completeness", 1.0) < 0.5:
            artifacts.append({
                "type": "insufficient_data",
                "severity": "high",
                "confidence": "high",
                "explanation": f"Only {feature_values['completeness']*100:.1f}% of data is valid",
                "features": {"completeness": feature_values["completeness"]}
            })
        
        logger.info(f"Detected {len(artifacts)} artifacts")
        return artifacts
    
    def _detect_motion_artifacts(
        self,
        data: List[Dict[str, Any]],
        features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Detect movement-associated disturbances."""
        artifacts = []
        
        motion_mean = features.get("motion_mean", 0)
        motion_max = features.get("motion_max", 0)
        
        thresholds = ARTIFACT_THRESHOLDS["motion"]
        
        if motion_max > thresholds["high"]:
            severity = "high"
        elif motion_max > thresholds["moderate"]:
            severity = "moderate"
        elif motion_max > thresholds["low"]:
            severity = "low"
        else:
            return artifacts
        
        # Find motion burst intervals
        motion_values = [d.get("motion", 0) for d in data]
        in_burst = False
        start_idx = None
        
        for i, motion in enumerate(motion_values):
            if motion > thresholds["low"] and not in_burst:
                in_burst = True
                start_idx = i
            elif motion <= thresholds["low"] and in_burst:
                in_burst = False
                artifacts.append({
                    "type": "movement",
                    "severity": severity,
                    "start_index": start_idx,
                    "end_index": i,
                    "confidence": "high",
                    "explanation": f"Motion intensity reached {motion_max:.2f} during this interval",
                    "features": {
                        "motion_mean": motion_mean,
                        "motion_max": motion_max
                    }
                })
        
        # If no specific bursts found but overall motion high
        if not artifacts and motion_mean > thresholds["moderate"]:
            artifacts.append({
                "type": "movement",
                "severity": severity,
                "confidence": "moderate",
                "explanation": f"Sustained motion activity detected (mean: {motion_mean:.2f})",
                "features": {"motion_mean": motion_mean}
            })
        
        return artifacts
    
    def _detect_contact_artifacts(
        self,
        data: List[Dict[str, Any]],
        features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Detect poor-contact disturbances."""
        artifacts = []
        
        contact_mean = features.get("contact_mean", 1.0)
        contact_min = features.get("contact_min", 1.0)
        
        thresholds = ARTIFACT_THRESHOLDS["poor_contact"]
        
        if contact_min < thresholds["high"]:
            severity = "high"
        elif contact_min < thresholds["moderate"]:
            severity = "moderate"
        elif contact_mean < thresholds["low"]:
            severity = "low"
        else:
            return artifacts
        
        artifacts.append({
            "type": "poor_contact",
            "severity": severity,
            "confidence": "high",
            "explanation": f"Contact quality degraded (min: {contact_min:.2f}, mean: {contact_mean:.2f})",
            "features": {
                "contact_mean": contact_mean,
                "contact_min": contact_min
            }
        })
        
        return artifacts
    
    def _detect_noise_artifacts(self, features: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect excessive noise."""
        artifacts = []
        
        snr = features.get("snr", 100)
        
        # SNR thresholds (dB)
        if snr < 10:
            severity = "high"
            explanation = f"Very low signal-to-noise ratio ({snr:.1f} dB)"
        elif snr < 20:
            severity = "moderate"
            explanation = f"Moderate noise contamination (SNR: {snr:.1f} dB)"
        elif snr < 30:
            severity = "low"
            explanation = f"Minor noise present (SNR: {snr:.1f} dB)"
        else:
            return artifacts
        
        artifacts.append({
            "type": "excessive_noise",
            "severity": severity,
            "confidence": "high",
            "explanation": explanation,
            "features": {"snr": snr}
        })
        
        return artifacts
    
    def _detect_drift_artifacts(self, features: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect baseline drift."""
        artifacts = []
        
        drift = features.get("baseline_drift", 0)
        thresholds = ARTIFACT_THRESHOLDS["drift"]
        
        if drift > thresholds["high"]:
            severity = "high"
        elif drift > thresholds["moderate"]:
            severity = "moderate"
        elif drift > thresholds["low"]:
            severity = "low"
        else:
            return artifacts
        
        artifacts.append({
            "type": "baseline_drift",
            "severity": severity,
            "confidence": "high",
            "explanation": f"Baseline drift magnitude: {drift:.3f}",
            "features": {"baseline_drift": drift}
        })
        
        return artifacts
    
    def _detect_dropout_artifacts(
        self,
        data: List[Dict[str, Any]],
        features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Detect signal dropout."""
        artifacts = []
        
        dropout_fraction = features.get("dropout_fraction", 0)
        thresholds = ARTIFACT_THRESHOLDS["dropout"]
        
        if dropout_fraction > thresholds["high"]:
            severity = "high"
        elif dropout_fraction > thresholds["moderate"]:
            severity = "moderate"
        elif dropout_fraction > thresholds["low"]:
            severity = "low"
        else:
            return artifacts
        
        artifacts.append({
            "type": "signal_dropout",
            "severity": severity,
            "confidence": "high",
            "explanation": f"{dropout_fraction*100:.1f}% of samples are missing",
            "features": {"dropout_fraction": dropout_fraction}
        })
        
        return artifacts
    
    def _detect_abrupt_changes(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect abrupt pulse value changes."""
        artifacts = []
        
        pulse_values = np.array([d.get("pulse_bpm") for d in data], dtype=float)
        pulse_values = pulse_values[~np.isnan(pulse_values)]
        
        if len(pulse_values) < 10:
            return artifacts
        
        # Compute differences
        diffs = np.abs(np.diff(pulse_values))
        mean_diff = np.mean(diffs)
        
        # Find abrupt changes (> 3 std above mean)
        threshold = mean_diff + 3 * np.std(diffs)
        abrupt_indices = np.where(diffs > threshold)[0]
        
        if len(abrupt_indices) > 0:
            max_change = np.max(diffs[abrupt_indices])
            artifacts.append({
                "type": "abrupt_pulse_change",
                "severity": "moderate",
                "confidence": "high",
                "explanation": f"Detected {len(abrupt_indices)} abrupt pulse changes (max: {max_change:.1f} bpm)",
                "features": {
                    "max_change": float(max_change),
                    "num_changes": int(len(abrupt_indices))
                }
            })
        
        return artifacts
    
    def _detect_sampling_irregularity(
        self,
        data: List[Dict[str, Any]],
        features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Detect irregular sampling."""
        artifacts = []
        
        sampling_score = features.get("sampling_regularity", 1.0)
        
        if sampling_score < 0.7:
            severity = "high"
        elif sampling_score < 0.85:
            severity = "moderate"
        elif sampling_score < 0.95:
            severity = "low"
        else:
            return artifacts
        
        artifacts.append({
            "type": "irregular_sampling",
            "severity": severity,
            "confidence": "high",
            "explanation": f"Sampling regularity score: {sampling_score:.2f}",
            "features": {"sampling_regularity": sampling_score}
        })
        
        return artifacts
