
"""
Pediatric VitalGuard AI - Main FastAPI Application
MED-PS-010
"""

import logging
import os
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

# Explicitly allow the deployed frontend and local development origins.
# Additional origins can be configured using FRONTEND_ORIGINS.
default_origins = [
    "https://vitalguardai.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

configured_origins = os.getenv("FRONTEND_ORIGINS", "")

allowed_origins = list(
    dict.fromkeys(
        default_origins
        + [
            origin.strip().rstrip("/")
            for origin in configured_origins.split(",")
            if origin.strip()
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Register API routes.
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
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
```
