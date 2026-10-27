
"""Request models."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SimulationRequest(BaseModel):
    """Request for signal simulation."""

    scenario: str = Field(..., description="Scenario identifier")
    duration: float = Field(
        60.0,
        ge=10.0,
        le=600.0,
        description="Simulation duration in seconds",
    )
    sample_rate: float = Field(
        100.0,
        ge=10.0,
        le=1000.0,
        description="Sampling rate in Hz",
    )
    seed: int | None = Field(None, description="Random seed for reproducibility")
    use_matlab: bool = Field(
        False,
        description="Use MATLAB/Simulink if available",
    )

    @field_validator("scenario")
    @classmethod
    def validate_scenario(cls, value: str) -> str:
        from app.core.constants import SCENARIOS

        if value not in SCENARIOS:
            raise ValueError(
                f"Unknown scenario: {value}. "
                f"Must be one of {list(SCENARIOS.keys())}"
            )
        return value


class AnalysisRequest(BaseModel):
    """Request for signal analysis."""

    data: list[dict] = Field(..., description="Signal data to analyze")
    metadata: dict | None = Field(None, description="Optional metadata")
    source: Literal["matlab", "python", "upload"] = Field(
        "upload",
        description="Data source",
    )

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: list[dict]) -> list[dict]:
        if not value:
            raise ValueError("Data cannot be empty")
        if len(value) > 100000:
            raise ValueError("Data exceeds maximum row limit of 100,000")
        return value


class ReportRequest(BaseModel):
    """Request for report generation."""

    analysis_result: dict = Field(
        ...,
        description="Analysis result to convert to report",
    )
    format: Literal["json", "csv", "summary"] = Field(
        "json",
        description="Report format",
    )
    include_raw_data: bool = Field(
        False,
        description="Include raw signal data",
    )


class AIAnalysisRequest(BaseModel):
    """Request for AI-generated explanations."""
    payload: dict = Field(
        ...,
        description="Simulation summary or deterministic analysis result",
    )


class AIComparisonRequest(BaseModel):
    """Request to compare two simulation or analysis summaries."""
    baseline: dict = Field(..., description="First scenario summary")
    comparison: dict = Field(..., description="Second scenario summary")