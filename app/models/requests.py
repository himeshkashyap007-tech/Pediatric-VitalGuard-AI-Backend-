"""Request models."""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime

class SimulationRequest(BaseModel):
    """Request for signal simulation."""
    
    scenario: str = Field(..., description="Scenario identifier")
    duration: float = Field(60.0, ge=10.0, le=600.0, description="Simulation duration in seconds")
    sample_rate: float = Field(100.0, ge=10.0, le=1000.0, description="Sampling rate in Hz")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    use_matlab: bool = Field(False, description="Use MATLAB/Simulink if available")
    
    @validator('scenario')
    def validate_scenario(cls, v):
        from app.core.constants import SCENARIOS
        if v not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {v}. Must be one of {list(SCENARIOS.keys())}")
        return v

class AnalysisRequest(BaseModel):
    """Request for signal analysis."""
    
    data: list[dict] = Field(..., description="Signal data to analyze")
    metadata: Optional[dict] = Field(None, description="Optional metadata")
    source: Literal["matlab", "python", "upload"] = Field("upload", description="Data source")
    
    @validator('data')
    def validate_data(cls, v):
        if not v:
            raise ValueError("Data cannot be empty")
        if len(v) > 100000:
            raise ValueError("Data exceeds maximum row limit of 100,000")
        return v

class ReportRequest(BaseModel):
    """Request for report generation."""
    
    analysis_result: dict = Field(..., description="Analysis result to convert to report")
    format: Literal["json", "csv", "summary"] = Field("json", description="Report format")
    include_raw_data: bool = Field(False, description="Include raw signal data")
