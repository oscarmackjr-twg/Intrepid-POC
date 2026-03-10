"""Application configuration and settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional
import os
from pathlib import Path
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Pydantic v2 settings config:
    # - Ignore extra env vars (e.g. AWS_PROFILE in dev/containers)
    # - Still load from .env when present
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_ignore_empty=True,
        extra="ignore",
    )

    # Database: support either full DATABASE_URL or individual env vars (for Elastic Beanstalk, etc.)
    DATABASE_URL: Optional[str] = None
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: str = "5432"
    DATABASE_NAME: str = "intrepid_poc"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = ""
    DATABASE_SSLMODE: Optional[str] = None  # e.g. "require" for RDS

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            return self
        # Build from components so EB/containers can set DATABASE_HOST, DATABASE_USER, etc.
        user = quote_plus(self.DATABASE_USER)
        password = quote_plus(self.DATABASE_PASSWORD) if self.DATABASE_PASSWORD else ""
        host = self.DATABASE_HOST
        port = self.DATABASE_PORT
        name = self.DATABASE_NAME
        if password:
            self.DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        else:
            self.DATABASE_URL = f"postgresql://{user}@{host}:{port}/{name}"
        if self.DATABASE_SSLMODE:
            self.DATABASE_URL = f"{self.DATABASE_URL}?sslmode={self.DATABASE_SSLMODE}"
        return self
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Local development mode: set LOCAL_DEV_MODE=true in .env to bypass the
    # SECRET_KEY sentinel check. NEVER set this to true in staging or production.
    LOCAL_DEV_MODE: bool = False

    KNOWN_FALLBACK_SECRET: str = "your-secret-key-change-in-production"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if not self.LOCAL_DEV_MODE and self.SECRET_KEY == self.KNOWN_FALLBACK_SECRET:
            raise ValueError(
                "SECRET_KEY is set to the default fallback value. "
                "Set a strong random SECRET_KEY, or set LOCAL_DEV_MODE=true in .env for local development."
            )
        return self
    
    # File Storage
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    INPUT_DIR: str = "./data/inputs"
    OUTPUT_DIR: str = "./data/outputs"
    OUTPUT_SHARE_DIR: str = "./data/output_share"
    ARCHIVE_DIR: str = "./data/archive"  # Per-run archive: archive/{run_id}/input, archive/{run_id}/output

    # Local development overrides: when running on a workstation (native or Docker),
    # you can point the pipeline at specific input/output folders by setting these.
    # When set and STORAGE_TYPE="local", they override INPUT_DIR / OUTPUT_DIR / OUTPUT_SHARE_DIR.
    DEV_INPUT: Optional[str] = None
    DEV_OUTPUT: Optional[str] = None
    DEV_OUTPUT_SHARED: Optional[str] = None
    
    # S3 Configuration (required when STORAGE_TYPE=s3)
    S3_BUCKET_NAME: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BASE_PREFIX: Optional[str] = None  # Optional prefix for all S3 paths (e.g., "test/" or "prod/")
    S3_INPUTS_PREFIX: str = "input"  # Legacy: inputs area prefix (bucket/input/...). Kept for backward compatibility.

    # S3 path overrides (bucket-relative prefixes). When set, these take precedence over S3_INPUTS_PREFIX/S3_BASE_PREFIX:
    #   S3_INPUT:         full prefix where files_required lives (e.g. "input/files_required")
    #   S3_OUTPUT:        prefix for outputs area (e.g. "outputs")
    #   S3_OUTPUT_SHARED: prefix for output_share area (e.g. "output_share")
    S3_INPUT: Optional[str] = None
    S3_OUTPUT: Optional[str] = None
    S3_OUTPUT_SHARED: Optional[str] = None
    
    # Pipeline
    IRR_TARGET: float = 8.05
    DEFAULT_PDATE: Optional[str] = None

    # Program runs: optional path to external tagging script (e.g. c:\temp\tagging.py). Uses inputs dir and writes to outputs/tagging/.
    TAGGING_SCRIPT_PATH: Optional[str] = None
    # Final funding: optional paths to workbook scripts. When unset, bundled scripts in backend/scripts/ are used.
    # Scripts receive FOLDER (temp dir with files_required/); they write to FOLDER/output and FOLDER/output_share;
    # we copy to outputs and output_share areas under final_funding_sg/ or final_funding_cibc/ (same convention as main runs).
    FINAL_FUNDING_SG_SCRIPT_PATH: Optional[str] = None
    FINAL_FUNDING_CIBC_SCRIPT_PATH: Optional[str] = None
    
    # Scheduler
    ENABLE_SCHEDULER: bool = True
    DAILY_RUN_TIME: str = "02:00"  # 2 AM
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    @model_validator(mode="after")
    def apply_dev_paths(self) -> "Settings":
        """
        Allow local development to override storage directories via DEV_INPUT / DEV_OUTPUT / DEV_OUTPUT_SHARED.
        Only applies when STORAGE_TYPE is 'local' so QA/prod S3 configs are unaffected.

        DEV_INPUT is expected to point at the concrete files_required directory
        (e.g. C:\\...\\93rd_buy\\files_required); we derive INPUT_DIR as its parent so the
        pipeline can continue to look under <INPUT_DIR>/files_required.
        """
        if self.STORAGE_TYPE.lower() == "local":
            if self.DEV_INPUT:
                dev_input = Path(self.DEV_INPUT.rstrip("\\/")).resolve()
                self.INPUT_DIR = str(dev_input.parent)
            if self.DEV_OUTPUT:
                self.OUTPUT_DIR = self.DEV_OUTPUT
            if self.DEV_OUTPUT_SHARED:
                self.OUTPUT_SHARE_DIR = self.DEV_OUTPUT_SHARED
        return self
    
# Load settings
# Note: If .env file has parsing errors, pydantic-settings will show a warning
# but the application will still start using defaults and environment variables
settings = Settings()
