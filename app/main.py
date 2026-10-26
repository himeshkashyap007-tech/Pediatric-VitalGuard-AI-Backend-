"""
Pediatric VitalGuard AI - Main FastAPI Application
MED-PS-010
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pediatric VitalGuard AI",
    description="Adaptive Pediatric Measurement Reliability Analysis System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - restrictive for prototype
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=3600
)

app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Pediatric VitalGuard AI starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"MATLAB available: {settings.MATLAB_AVAILABLE}")

@app.get("/")
async def root():
    return {
        "name": "Pediatric VitalGuard AI",
        "version": "1.0.0",
        "identifier": "MED-PS-010",
        "status": "operational"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
