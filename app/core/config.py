"""Core configuration and settings for DocXpress."""

from dataclasses import dataclass
import os
from pathlib import Path


LOCAL_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_origins() -> list[str]:
    """Return local defaults plus explicitly configured frontend origins."""
    configured_origins = os.getenv("DOCXPRESS_CORS_ORIGINS", "")
    origins = list(LOCAL_CORS_ORIGINS)

    for origin in configured_origins.split(","):
        normalized_origin = origin.strip()
        if not normalized_origin:
            continue
        if normalized_origin == "*":
            raise ValueError("DOCXPRESS_CORS_ORIGINS must not contain '*'.")
        if normalized_origin not in origins:
            origins.append(normalized_origin)

    return origins


@dataclass(frozen=True)
class Settings:
    """System-wide configuration settings."""
    PROJECT_NAME: str = "DocXpress"
    VERSION: str = "0.1.0"
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    SAMPLE_DOCS_DIR: Path = BASE_DIR / "sample_documents"
    
    # Invariant enforcement
    ENFORCE_READ_ONLY: bool = True
    MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB
    MAX_DOCX_UNCOMPRESSED_BYTES: int = 500 * 1024 * 1024
    MAX_DOCX_ZIP_ENTRIES: int = 10000
    CLEANUP_ORPHANED_JOB_DIRS: bool = True


settings = Settings()
