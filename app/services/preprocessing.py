"""Signal preprocessing service."""
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Preprocessor:
    """Preprocess signal data."""
    
    def preprocess(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Preprocess signal data.
        
        Returns: dict with preprocessed data and processing notes
        """
        
        notes = []
        
        # Check sample count
        if len(data) < 100:
            notes.append(f"Warning: Only {len(data)} samples (recommended: >100)")
        
        # Check timestamps
        timestamps = [d.get("timestamp") for d in data]
        if all(t is not None for t in timestamps):
            intervals = np.diff(timestamps)
            if np.any(intervals <= 0):
                notes.append("Warning: Non-monotonic timestamps detected")
        else:
            notes.append("Timestamps not available")
        
        # Check required fields
        pulse_count = sum(1 for d in data if d.get("pulse_bpm") is not None)
        spo2_count = sum(1 for d in data if d.get("spo2_percent") is not None)
        
        if pulse_count == 0:
            notes.append("Error: No valid pulse measurements")
        if spo2_count == 0:
            notes.append("Error: No valid SpO2 measurements")
        
        # Check optional fields
        has_motion = any(d.get("motion") is not None for d in data)
        has_contact = any(d.get("contact") is not None for d in data)
        has_ppg = any(d.get("ppg_value") is not None for d in data)
        
        if not has_motion:
            notes.append("Motion data not available")
        if not has_contact:
            notes.append("Contact quality data not available")
        if not has_ppg:
            notes.append("PPG waveform data not available")
        
        return {
            "data": data,
            "notes": notes,
            "sample_count": len(data),
            "valid_pulse": pulse_count,
            "valid_spo2": spo2_count,
            "has_motion": has_motion,
            "has_contact": has_contact,
            "has_ppg": has_ppg
        }
