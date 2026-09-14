"""DocXpress local FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import create_router
from app.core.config import settings
from app.services.document_jobs import DocumentJobService


def create_app(service: DocumentJobService | None = None) -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Offline DOCX analysis and publication formatting service.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(create_router(service or DocumentJobService()))
    return app


app = create_app()