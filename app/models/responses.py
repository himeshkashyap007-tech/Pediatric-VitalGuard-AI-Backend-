"""Response models."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    matlab_available: bool
    version: str

class ConfigResponse(BaseModel):
    """Configuration response."""
    scenarios: Dict[str, Any]
    physiological_ranges: Dict[str, Any]
    quality_thresholds: Dict[str, Any]
    matlab_available: bool

class SimulationResponse(BaseModel):
    """Simulation response."""
    success: bool
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    source: str
    message: Optional[str] = None

class ArtifactEvent(BaseModel):
    """Detected artifact event."""
    type: str
    severity: str
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    confidence: str
    explanation: str
    features: Dict[str, float]

class QualityScore(BaseModel):
    """Quality score breakdown."""
    overall: float
    category: str
    label: str
    components: Dict[str, float]
    contributions: Dict[str, float]
    weights: Dict[str, float]
    available_features: List[str]
    unavailable_features: List[str]
    explanations: List[str]

class PhysiologicalValidation(BaseModel):
    """Physiological value validation."""
    pulse_status: str
    spo2_status: str
    clinical_ranges_configured: bool
    warnings: List[str]
    data_integrity_issues: List[str]

class AnalysisResponse(BaseModel):
    """Analysis response."""
    success: bool
    timestamp: datetime
    data_source: str
    sample_count: int
    duration: Optional[float] = None
    quality_score: QualityScore
    artifacts: List[ArtifactEvent]
    features: Dict[str, Any]
    physiological: PhysiologicalValidation
    data_quality: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class ReportResponse(BaseModel):
    """Report response."""
    success: bool
    format: str
    content: Any
    timestamp: datetime
    filename: str
