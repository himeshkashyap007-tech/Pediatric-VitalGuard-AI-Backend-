"""Quality scoring service with transparent component breakdown."""
import numpy as np
from typing import Dict, List, Any
import logging

from app.core.constants import QUALITY_THRESHOLDS, QUALITY_LABELS
from app.core.config import settings

logger = logging.getLogger(__name__)

class QualityScorer:
    """Compute explainable signal quality scores."""
    
    def __init__(self):
        self.weights = settings.QUALITY_WEIGHTS
    
    def compute_quality_score(
        self,
        features: Dict[str, Any],
        artifacts: List[Dict[str, Any]],
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute transparent quality score with component breakdown.
        
        Returns:
            dict with overall score, components, contributions, explanations
        """
        feature_values = features.get("values", {})
        available = features.get("available", [])
        unavailable = features.get("unavailable", [])
        
        components = {}
        contributions = {}
        explanations = []
        
        # SNR component
        if "snr" in available:
            snr = feature_values["snr"]
            snr_score = self._snr_to_score(snr)
            components["snr"] = snr_score
            contributions["snr"] = snr_score * self.weights["snr"]
            
            if snr_score < 50:
                explanations.append(f"Low signal-to-noise ratio ({snr:.1f} dB)")
            elif snr_score < 80:
                explanations.append(f"Moderate SNR ({snr:.1f} dB)")
        else:
            unavailable.append("snr")
        
        # Stability component
        if "pulse_stability" in available:
            stability = feature_values["pulse_stability"]
            stability_score = stability * 100
            components["stability"] = stability_score
            contributions["stability"] = stability_score * self.weights["stability"]
            
            if stability_score < 50:
                explanations.append("High pulse variability detected")
        else:
            unavailable.append("stability")
        
        # Completeness component
        if "completeness" in available:
            completeness = feature_values["completeness"]
            completeness_score = completeness * 100
            components["completeness"] = completeness_score
            contributions["completeness"] = completeness_score * self.weights["completeness"]
            
            if completeness_score < 80:
                explanations.append(f"Only {completeness*100:.1f}% of data is valid")
        
        # Motion component
        if "motion_mean" in available:
            motion_mean = feature_values["motion_mean"]
            motion_score = (1 - motion_mean) * 100
            components["motion"] = motion_score
            contributions["motion"] = motion_score * self.weights["motion"]
            
            if motion_score < 50:
                explanations.append(f"Significant motion detected (intensity: {motion_mean:.2f})")
        else:
            unavailable.append("motion")
        
        # Contact component
        if "contact_mean" in available:
            contact_mean = feature_values["contact_mean"]
            contact_score = contact_mean * 100
            components["contact"] = contact_score
            contributions["contact"] = contact_score * self.weights["contact"]
            
            if contact_score < 70:
                explanations.append(f"Poor sensor contact (quality: {contact_mean:.2f})")
        else:
            unavailable.append("contact")
        
        # Sampling component
        if "sampling_regularity" in available:
            sampling = feature_values["sampling_regularity"]
            sampling_score = sampling * 100
            components["sampling"] = sampling_score
            contributions["sampling"] = sampling_score * self.weights["sampling"]
            
            if sampling_score < 85:
                explanations.append("Irregular sample timing")
        
        # Compute overall score from available components
        if contributions:
            # Normalize weights for available components
            total_weight = sum(
                self.weights[k] for k in contributions.keys()
            )
            
            if total_weight > 0:
                overall_score = sum(contributions.values()) / total_weight
            else:
                overall_score = 0.0
        else:
            overall_score = 0.0
            explanations.append("Insufficient features to compute quality score")
        
        # Determine category
        category, label = self._get_quality_category(overall_score, len(contributions))
        
        # Add artifact-based explanations
        severe_artifacts = [a for a in artifacts if a["severity"] in ["high", "moderate"]]
        if severe_artifacts:
            artifact_types = list(set(a["type"] for a in severe_artifacts))
            explanations.append(f"Detected {len(severe_artifacts)} significant artifacts: {', '.join(artifact_types)}")
        
        result = {
            "overall": round(overall_score, 2),
            "category": category,
            "label": label,
            "components": {k: round(v, 2) for k, v in components.items()},
            "contributions": {k: round(v, 2) for k, v in contributions.items()},
            "weights": self.weights,
            "available_features": available,
            "unavailable_features": list(set(unavailable)),
            "explanations": explanations
        }
        
        logger.info(f"Quality score: {overall_score:.2f} ({category})")
        
        return result
    
    def _snr_to_score(self, snr_db: float) -> float:
        """Convert SNR in dB to 0-100 score."""
        # Map: <10dB -> 0, 30dB -> 80, >50dB -> 100
        if snr_db < 10:
            return snr_db * 5  # 0-50
        elif snr_db < 30:
            return 50 + (snr_db - 10) * 1.5  # 50-80
        elif snr_db < 50:
            return 80 + (snr_db - 30) * 1.0  # 80-100
        else:
            return 100.0
    
    def _get_quality_category(
        self,
        score: float,
        num_components: int
    ) -> tuple[str, str]:
        """Determine quality category and label."""
        
        if num_components < 3:
            return "insufficient", QUALITY_LABELS["insufficient"]
        
        if score >= QUALITY_THRESHOLDS["high"]:
            return "high", QUALITY_LABELS["high"]
        elif score >= QUALITY_THRESHOLDS["moderate"]:
            return "moderate", QUALITY_LABELS["moderate"]
        else:
            return "low", QUALITY_LABELS["low"]
