"""API route handlers."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime, timezone
from typing import Dict, Any
import logging

from app.models.requests import SimulationRequest, AnalysisRequest, ReportRequest
from app.models.responses import *
from app.services.simulator import SignalSimulator
from app.services.matlab_adapter import MATLABAdapter
from app.services.csv_parser import CSVParser
from app.services.preprocessing import Preprocessor
from app.services.features import FeatureExtractor
from app.services.artifact_detection import ArtifactDetector
from app.services.quality_scoring import QualityScorer
from app.services.validation import PhysiologicalValidator
from app.services.reporting import ReportGenerator
from app.core.constants import SCENARIOS, PHYSIOLOGICAL_RANGES, QUALITY_THRESHOLDS
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Service instances
simulator = SignalSimulator()
matlab_adapter = MATLABAdapter()
csv_parser = CSVParser()
preprocessor = Preprocessor()
feature_extractor = FeatureExtractor()
artifact_detector = ArtifactDetector()
quality_scorer = QualityScorer()
validator = PhysiologicalValidator()
report_generator = ReportGenerator()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        matlab_available=settings.MATLAB_AVAILABLE,
        version="1.0.0"
    )

@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get system configuration."""
    return ConfigResponse(
        scenarios=SCENARIOS,
        physiological_ranges=PHYSIOLOGICAL_RANGES,
        quality_thresholds=QUALITY_THRESHOLDS,
        matlab_available=settings.MATLAB_AVAILABLE
    )

@router.get("/scenarios")
async def list_scenarios():
    """List available scenarios."""
    return {
        "scenarios": SCENARIOS,
        "count": len(SCENARIOS)
    }

@router.get("/ranges")
async def get_ranges():
    """Get physiological ranges."""
    return {
        "ranges": PHYSIOLOGICAL_RANGES
    }

@router.get("/example.csv")
async def download_example_csv():
    """Download example CSV file."""
    
    csv_content = """timestamp,pulse_bpm,spo2_percent,motion,contact,ppg_amplitude
0.0,120,98,0.0,1.0,1.2
0.01,121,98,0.0,1.0,1.3
0.02,120,98,0.0,1.0,1.1
0.03,119,98,0.1,1.0,1.2
0.04,120,98,0.0,1.0,1.3
"""
    
    return JSONResponse(
        content={"content": csv_content, "filename": "example.csv"},
        headers={"Content-Disposition": "attachment; filename=example.csv"}
    )

@router.post("/simulate", response_model=SimulationResponse)
async def simulate_signal(request: SimulationRequest):
    """Simulate signal data."""
    
    try:
        # MATLAB or Python?
        if request.use_matlab and settings.MATLAB_AVAILABLE:
            try:
                result = matlab_adapter.run_simulation(
                    request.scenario,
                    request.duration,
                    request.sample_rate,
                    request.seed
                )
                source = "matlab"
            except Exception as e:
                logger.warning(f"MATLAB simulation failed: {str(e)}, falling back to Python")
                sim = SignalSimulator(seed=request.seed)
                result = sim.simulate(request.scenario, request.duration, request.sample_rate)
                source = "python_fallback"
        else:
            sim = SignalSimulator(seed=request.seed)
            result = sim.simulate(request.scenario, request.duration, request.sample_rate)
            source = "python"
        
        return SimulationResponse(
            success=True,
            data=result["data"],
            metadata=result["metadata"],
            source=source
        )
    
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_signal(request: AnalysisRequest):
    """Analyze signal data."""
    
    try:
        data = request.data
        
        # Extract features
        features = feature_extractor.extract_all_features(data)
        
        # Detect artifacts
        artifacts = artifact_detector.detect_all_artifacts(data, features)
        
        # Compute quality score
        quality_score = quality_scorer.compute_quality_score(features, artifacts, data)
        
        # Physiological validation
        physiological = validator.validate(data)
        
        # Data quality summary
        data_quality = {
            "completeness": features["values"].get("completeness", 0),
            "sampling_regularity": features["values"].get("sampling_regularity", 0),
            "artifact_count": len(artifacts)
        }
        
        return AnalysisResponse(
            success=True,
            timestamp=datetime.now(timezone.utc),
            data_source=request.source,
            sample_count=len(data),
            quality_score=quality_score,
            artifacts=artifacts,
            features=features,
            physiological=physiological,
            data_quality=data_quality,
            metadata=request.metadata
        )
    
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and validate CSV file."""
    
    try:
        content = await file.read()
        
        result = csv_parser.parse(content)
        
        return {
            "success": True,
            "filename": file.filename,
            **result
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/report")
async def generate_report(request: ReportRequest):
    """Generate analysis report."""
    
    try:
        analysis = request.analysis_result
        
        if request.format == "json":
            content = report_generator.generate_json_report(analysis)
            filename = f"pvg_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        
        elif request.format == "csv":
            content = report_generator.generate_csv_report(analysis)
            filename = f"pvg_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        
        elif request.format == "summary":
            content = report_generator.generate_summary_report(analysis)
            filename = f"pvg_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
        
        else:
            raise ValueError(f"Unknown format: {request.format}")
        
        return {
            "success": True,
            "format": request.format,
            "content": content,
            "filename": filename,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
    
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


