
"""Application configuration."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    APP_NAME: str = "Pediatric VitalGuard AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    MAX_CSV_ROWS: int = 100000

    MATLAB_AVAILABLE: bool = False
    MATLAB_PATH: str = ""
    MATLAB_TIMEOUT: int = 60

    DEFAULT_DURATION: float = 60.0
    DEFAULT_SAMPLE_RATE: float = 100.0
    MIN_SAMPLES: int = 100

    QUALITY_WEIGHTS: dict = {
        "snr": 0.25,
        "stability": 0.20,
        "completeness": 0.20,
        "motion": 0.15,
        "contact": 0.10,
        "sampling": 0.10,
    }

    BASE_DIR: Path = Path(__file__).parent.parent.parent
    TEMP_DIR: Path = BASE_DIR / "temp"
    EXPORT_DIR: Path = BASE_DIR / "export"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

        if self.MATLAB_PATH and os.path.exists(self.MATLAB_PATH):
            self.MATLAB_AVAILABLE = True


settings = Settings()
