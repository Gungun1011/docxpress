"""Thin HTTP routes delegating to the document job service."""

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import (
    AnalysisResponse,
    ElementResponse,
    FormatRequest,
    HealthResponse,
    PreservationResponse,
    ReportResponse,
    StatusResponse,
    UploadResponse,
)
from app.core.config import settings
from app.services.document_jobs import DocumentJob, DocumentJobError, DocumentJobService
from app.services.formatter import PUBLICATION_PROFILES


def create_router(service: DocumentJobService) -> APIRouter:
    router = APIRouter()

    def expected_error(exc: DocumentJobError) -> HTTPException:
        message = str(exc)
        status_code = 400 if message in {
            "Unsupported extension; only .docx files are accepted",
            "Unsupported MIME type for DOCX",
            "Malformed DOCX file",
            "File too large",
        } else 404 if message == "Invalid document ID" else 422
        return HTTPException(status_code=status_code, detail={"code": "document_error", "message": message})

    @router.get("/health", response_model=HealthResponse, tags=["health"])
    @router.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=settings.PROJECT_NAME, version=settings.VERSION)

    @router.post("/api/documents/upload", response_model=UploadResponse, status_code=201, tags=["documents"])
    async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
        try:
            job = await service.upload(file)
        except DocumentJobError as exc:
            raise expected_error(exc) from exc
        return UploadResponse(
            document_id=job.document_id,
            filename=job.original_filename,
            size=job.input_path.stat().st_size,
            status=job.status,
        )

    @router.post("/api/documents/{document_id}/analyze", response_model=AnalysisResponse, tags=["documents"])
    def analyze_document(document_id: str) -> AnalysisResponse:
        try:
            job = service.analyze(document_id)
        except DocumentJobError as exc:
            raise expected_error(exc) from exc
        return _analysis_response(job)

    @router.post("/api/documents/{document_id}/format", response_model=StatusResponse, tags=["documents"])
    def format_document(document_id: str, request: FormatRequest) -> StatusResponse:
        try:
            job = service.format(document_id, request.profile)
        except DocumentJobError as exc:
            raise expected_error(exc) from exc
        return _status_response(job)

    @router.get("/api/documents/{document_id}/status", response_model=StatusResponse, tags=["documents"])
    def document_status(document_id: str) -> StatusResponse:
        try:
            return _status_response(service.get(document_id))
        except DocumentJobError as exc:
            raise expected_error(exc) from exc

    @router.get("/api/documents/{document_id}/report", response_model=ReportResponse, tags=["documents"])
    def document_report(document_id: str) -> ReportResponse:
        try:
            return _report_response(service.get(document_id))
        except DocumentJobError as exc:
            raise expected_error(exc) from exc

    @router.get("/api/documents/{document_id}/download", response_class=FileResponse, tags=["documents"])
    def download_document(document_id: str) -> FileResponse:
        try:
            job = service.get(document_id)
        except DocumentJobError as exc:
            raise expected_error(exc) from exc
        if not job.output_path or not job.output_path.is_file() or job.status != "completed":
            raise HTTPException(status_code=404, detail={"code": "output_not_ready", "message": "Formatted output is not available"})
        return FileResponse(
            path=job.output_path,
            filename=job.output_path.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @router.get("/api/presets", response_model=Dict[str, Any], tags=["documents"])
    def presets() -> Dict[str, Any]:
        return {
            "profiles": [
                {
                    "name": profile.name,
                    "body_font": profile.body_font,
                    "body_size_pt": profile.body_size_pt,
                    "body_alignment": "justified" if profile.body_alignment == 3 else "left",
                    "body_line_spacing": profile.body_line_spacing,
                    "body_first_indent_cm": profile.body_first_indent_cm,
                    "heading_1_size_pt": profile.heading_1_size_pt,
                    "subheading_size_pt": profile.subheading_size_pt,
                }
                for profile in PUBLICATION_PROFILES.values()
            ]
        }

    return router


def _status_response(job: DocumentJob) -> StatusResponse:
    elapsed = sum(job.stage_timings.values())
    return StatusResponse(
        document_id=job.document_id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        elapsed_seconds=elapsed,
        error=job.error,
    )


def _elements(report) -> List[ElementResponse]:
    return [
        ElementResponse(
            element_id=element.element_id,
            type=element.final_type.value,
            confidence=element.confidence,
            detection_method=element.detection_tier,
            reason=element.rule_applied,
            text_preview=element.original_text[:160] if element.original_text else None,
        )
        for element in report.elements
    ]


def _analysis_response(job: DocumentJob) -> AnalysisResponse:
    report = job.analysis
    if report is None:
        raise HTTPException(status_code=422, detail={"code": "analysis_unavailable", "message": "Analysis is not available"})
    counts = report.type_counts
    return AnalysisResponse(
        document_id=job.document_id,
        status=job.status,
        total_elements=report.total_elements,
        chapters=counts.get("chapter", 0),
        titles=counts.get("title", 0),
        authors=counts.get("author", 0),
        headings=counts.get("heading", 0),
        subheadings=counts.get("subheading", 0),
        paragraphs=counts.get("paragraph", 0),
        tables=counts.get("table", 0),
        figures=counts.get("figure", 0),
        captions=counts.get("caption", 0),
        lists=counts.get("list", 0),
        references=counts.get("reference", 0),
        average_confidence=report.average_confidence,
        elements=_elements(report),
    )


def _report_response(job: DocumentJob) -> ReportResponse:
    report = job.analysis
    preservation = None
    if job.format_result is not None:
        result = job.format_result.preservation
        preservation = PreservationResponse(
            is_identical=result.is_identical,
            source_hash=result.source_hash,
            output_hash=result.output_hash,
            changed_elements=list(result.changed_elements),
            missing_elements=list(result.missing_elements),
            added_elements=list(result.added_elements),
        )
    statistics = report.type_counts if report else {}
    profile = PUBLICATION_PROFILES.get(job.format_result.profile_name) if job.format_result else None
    formatting = {
        "body_font": profile.body_font,
        "body_size_pt": profile.body_size_pt,
        "body_alignment": "justified" if profile.body_alignment == 3 else "left",
        "body_line_spacing": profile.body_line_spacing,
        "body_first_indent_cm": profile.body_first_indent_cm,
        "heading_1_size_pt": profile.heading_1_size_pt,
        "subheading_size_pt": profile.subheading_size_pt,
    } if profile else {}
    return ReportResponse(
        document_id=job.document_id,
        filename=job.original_filename,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        publication_profile=job.format_result.profile_name if job.format_result else None,
        formatting=formatting,
        statistics=statistics,
        elements=_elements(report) if report else [],
        processing=dict(job.stage_timings),
        preservation=preservation,
        errors=[job.error] if job.error else [],
    )