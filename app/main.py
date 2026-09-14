"""DocXpress local FastAPI application."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import create_router
from app.core.config import get_cors_origins, settings
from app.services.document_jobs import DocumentJobService


FRONTEND_DIST = settings.BASE_DIR / "frontend" / "dist"


def create_app(
    service: DocumentJobService | None = None,
    frontend_dist: Path = FRONTEND_DIST,
) -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Offline DOCX analysis and publication formatting service.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(create_router(service or DocumentJobService()))

    frontend_root = frontend_dist.resolve()
    index_file = frontend_root / "index.html"

    @app.get("/{frontend_path:path}", include_in_schema=False)
    def serve_frontend(frontend_path: str) -> FileResponse:
        if frontend_path == "api" or frontend_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        if not index_file.is_file():
            raise HTTPException(status_code=404, detail="Frontend build is unavailable")

        requested_file = (frontend_root / frontend_path).resolve()
        try:
            requested_file.relative_to(frontend_root)
        except ValueError:
            requested_file = index_file

        if requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(index_file)

    return app


app = create_app()