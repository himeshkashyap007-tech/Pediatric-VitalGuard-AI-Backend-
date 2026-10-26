"""Physiological validation service - separate from quality scoring."""
import numpy as np
from typing import Dict, List, Any
import logging

from app.core.constants import PHYSIOLOGICAL_RANGES

logger = logging.getLogger(__name__)

class PhysiologicalValidator:
    """Validate physiological values - separate from signal quality."""
    
    def validate(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate physiological values."""
        
        pulse_values = np.array([d.get("pulse_bpm") for d in data], dtype=float)
        pulse_values = pulse_values[~np.isnan(pulse_values)]
        
        spo2_values = np.array([d.get("spo2_percent") for d in data], dtype=float)
        spo2_values = spo2_values[~np.isnan(spo2_values)]
        
        warnings = []
        data_integrity_issues = []
        
        # Pulse validation
        pulse_status = self._validate_pulse(pulse_values, warnings, data_integrity_issues)
        
        # SpO2 validation
        spo2_status = self._validate_spo2(spo2_values, warnings, data_integrity_issues)
        
        # Clinical ranges configured?
        clinical_configured = PHYSIOLOGICAL_RANGES["pulse_bpm"]["clinical_configured"]
        
        if not clinical_configured:
            warnings.append("Clinical reference ranges not configured")
        
        result = {
            "pulse_status": pulse_status,
            "spo2_status": spo2_status,
            "clinical_ranges_configured": clinical_configured,
            "warnings": warnings,
            "data_integrity_issues": data_integrity_issues
        }
        
        logger.info(f"Validation: pulse={pulse_status}, spo2={spo2_status}")
        
        return result
    
    def _validate_pulse(
        self,
        values: np.ndarray,
        warnings: List[str],
        issues: List[str]
    ) -> str:
        """Validate pulse values."""
        
        if len(values) == 0:
            issues.append("No valid pulse measurements")
            return "no_data"
        
        ranges = PHYSIOLOGICAL_RANGES["pulse_bpm"]
        sw_min = ranges["software_limits"]["min"]
        sw_max = ranges["software_limits"]["max"]
        typ_min = ranges["typical_pediatric"]["min"]
        typ_max = ranges["typical_pediatric"]["max"]
        
        # Software limits
        below_limit = np.sum(values < sw_min)
        above_limit = np.sum(values > sw_max)
        
        if below_limit > 0:
            issues.append(f"{below_limit} pulse values below software limit ({sw_min} bpm)")
        if above_limit > 0:
            issues.append(f"{above_limit} pulse values above software limit ({sw_max} bpm)")
        
        # Typical range (informational only)
        below_typical = np.sum(values < typ_min)
        above_typical = np.sum(values > typ_max)
        
        if below_typical > 0:
            warnings.append(f"{below_typical} pulse values below typical pediatric range ({typ_min} bpm)")
        if above_typical > 0:
            warnings.append(f"{above_typical} pulse values above typical pediatric range ({typ_max} bpm)")
        
        # Determine status
        if below_limit > 0 or above_limit > 0:
            return "software_limits_exceeded"
        elif below_typical > 0 or above_typical > 0:
            return "outside_typical_range"
        else:
            return "within_typical_range"
    
    def _validate_spo2(
        self,
        values: np.ndarray,
        warnings: List[str],
        issues: List[str]
    ) -> str:
        """Validate SpO2 values."""
        
        if len(values) == 0:
            issues.append("No valid SpO2 measurements")
            return "no_data"
        
        ranges = PHYSIOLOGICAL_RANGES["spo2_percent"]
        sw_min = ranges["software_limits"]["min"]
        sw_max = ranges["software_limits"]["max"]
        typ_min = ranges["typical_pediatric"]["min"]
        typ_max = ranges["typical_pediatric"]["max"]
        
        # Software limits
        below_limit = np.sum(values < sw_min)
        above_limit = np.sum(values > sw_max)
        
        if below_limit > 0:
            issues.append(f"{below_limit} SpO2 values below software limit ({sw_min}%)")
        if above_limit > 0:
            issues.append(f"{above_limit} SpO2 values above software limit ({sw_max}%)")
        
        # Typical range
        below_typical = np.sum(values < typ_min)
        
        if below_typical > 0:
            warnings.append(f"{below_typical} SpO2 values below typical pediatric range ({typ_min}%)")
        
        # Determine status
        if below_limit > 0 or above_limit > 0:
            return "software_limits_exceeded"
        elif below_typical > 0:
            return "outside_typical_range"
        else:
            return "within_typical_range"
