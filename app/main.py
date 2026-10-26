
"""
Pediatric VitalGuard AI - Main FastAPI Application
MED-PS-010
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Pediatric VitalGuard AI starting...")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("MATLAB available: %s", settings.MATLAB_AVAILABLE)

    yield

    logger.info("Pediatric VitalGuard AI shutting down...")


app = FastAPI(
    title="Pediatric VitalGuard AI",
    description="Adaptive Pediatric Measurement Reliability Analysis System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=3600,
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "Pediatric VitalGuard AI",
        "version": "1.0.0",
        "identifier": "MED-PS-010",
        "status": "operational",
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
