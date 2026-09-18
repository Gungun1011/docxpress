"""Local document storage and synchronous processing orchestration."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
import zipfile

from fastapi import UploadFile

from app.core.config import Settings, settings
from app.core.ml.classifier import ClassificationReport, HybridStructureClassifier
from app.models.ast import CanonicalDocument
from app.parser.docx_parser import DocxParser
from app.services.content_preservation import ContentPreservationError
from app.services.formatter import (
    DEFAULT_PUBLICATION_PROFILE,
    PUBLICATION_PROFILES,
    FormattingProgress,
    PublicationFormatter,
)
from app.utils.logger import get_logger


class DocumentJobError(RuntimeError):
    """Expected document/job failure safe to expose to an API client."""


@dataclass
class DocumentJob:
    document_id: str
    original_filename: str
    input_path: Path
    output_path: Optional[Path]
    status: str = "uploaded"
    progress: int = 0
    current_stage: str = "uploaded"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    analysis: Optional[ClassificationReport] = None
    classified_document: Optional[CanonicalDocument] = None
    format_result: Any = None
    stage_timings: Dict[str, float] = field(default_factory=dict)
    model_type: str = "logistic_regression"


class DocumentJobService:
    """Owns local files and invokes the existing core pipeline."""

    def __init__(self, root_dir: Optional[Path] = None, app_settings: Settings = settings) -> None:
        self.root_dir = (root_dir or (app_settings.BASE_DIR / ".docxpress_data")).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, DocumentJob] = {}
        if app_settings.CLEANUP_ORPHANED_JOB_DIRS:
            self._cleanup_orphaned_job_dirs()
        self.max_file_size = app_settings.MAX_FILE_SIZE_BYTES
        self.max_uncompressed_size = app_settings.MAX_DOCX_UNCOMPRESSED_BYTES
        self.max_zip_entries = app_settings.MAX_DOCX_ZIP_ENTRIES
        self.parser = DocxParser(enforce_read_only=app_settings.ENFORCE_READ_ONLY)
        self.classifier = HybridStructureClassifier()
        self.formatter = PublicationFormatter(parser=self.parser)
        self.logger = get_logger(__name__)

    def get(self, document_id: str) -> DocumentJob:
        try:
            return self.jobs[document_id]
        except KeyError as exc:
            raise DocumentJobError("Invalid document ID") from exc

    async def upload(self, upload: UploadFile) -> DocumentJob:
        original_filename = self._safe_filename(upload.filename or "document.docx")
        if Path(original_filename).suffix.lower() != ".docx":
            raise DocumentJobError("Unsupported extension; only .docx files are accepted")
        if upload.content_type and upload.content_type not in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        }:
            raise DocumentJobError("Unsupported MIME type for DOCX")

        document_id = uuid4().hex
        job_dir = self.root_dir / document_id
        job_dir.mkdir(mode=0o700)
        input_path = job_dir / original_filename
        size = 0
        try:
            with input_path.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_file_size:
                        raise DocumentJobError("File too large")
                    destination.write(chunk)
            self._validate_docx_archive(input_path)
            self.parser.parse(input_path)
        except DocumentJobError:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            self.logger.exception("DOCX upload validation failed: %s", type(exc).__name__)
            raise DocumentJobError("Malformed DOCX file") from exc
        finally:
            await upload.close()

        job = DocumentJob(document_id, original_filename, input_path, None)
        self.jobs[document_id] = job
        return job

    def analyze(self, document_id: str, model_type: str = "logistic_regression") -> DocumentJob:
        job = self.get(document_id)
        if model_type not in {"logistic_regression", "decision_tree"}:
            raise DocumentJobError(f"Unknown ML model: {model_type}")
        started = time.perf_counter()
        try:
            job.status, job.current_stage, job.progress = "parsing", "parsing", 0
            parsed = self.parser.parse(job.input_path)
            job.status, job.current_stage, job.progress = "analyzing", "analyzing", 50
            classifier = HybridStructureClassifier(model_type=model_type)
            classified, report = classifier.classify_document(parsed)
            job.model_type = model_type
            job.classified_document, job.analysis = classified, report
            job.stage_timings["analysis"] = time.perf_counter() - started
            job.status, job.current_stage, job.progress = "completed", "analysis complete", 100
            job.completed_at = datetime.now(timezone.utc)
            return job
        except Exception as exc:
            self._fail(job, "Analysis failed")
            self.logger.exception("Document analysis failed: %s", type(exc).__name__)
            raise DocumentJobError("Analysis failed") from exc

    def format(self, document_id: str, profile: str, model_type: str = "logistic_regression") -> DocumentJob:
        job = self.get(document_id)
        if profile not in PUBLICATION_PROFILES:
            raise DocumentJobError(f"Unknown publication profile: {profile}")
        if job.classified_document is None or job.analysis is None or job.model_type != model_type:
            self.analyze(document_id, model_type=model_type)
        job_dir = job.input_path.parent
        job.output_path = job_dir / f"{job.input_path.stem}.formatted.docx"
        started = time.perf_counter()
        try:
            job.status, job.current_stage, job.progress = "formatting", "formatting", 0

            def on_progress(progress: FormattingProgress) -> None:
                job.progress = int((progress.processed / max(1, progress.total)) * 90)

            job.format_result = self.formatter.format_document(
                job.input_path,
                job.output_path,
                document=job.classified_document,
                profile=profile,
                progress_callback=on_progress,
            )
            job.status, job.current_stage, job.progress = "validating", "validating content preservation", 95
            if not job.format_result.preservation.is_identical:
                raise ContentPreservationError(job.format_result.preservation)
            job.stage_timings["formatting"] = time.perf_counter() - started
            job.status, job.current_stage, job.progress = "completed", "completed", 100
            job.completed_at = datetime.now(timezone.utc)
            return job
        except ContentPreservationError as exc:
            self._fail(job, "Content preservation validation failed")
            self.logger.error("Content preservation failed for document %s", job.document_id)
            raise DocumentJobError("Content preservation validation failed") from exc
        except Exception as exc:
            self._fail(job, "Formatting failed")
            self.logger.exception("Document formatting failed: %s", type(exc).__name__)
            raise DocumentJobError("Formatting failed") from exc

    def cleanup(self, document_id: str, remove_output: bool = False) -> None:
        job = self.get(document_id)
        if remove_output and job.output_path and job.output_path.exists():
            job.output_path.unlink()
        if job.input_path.parent.exists():
            shutil.rmtree(job.input_path.parent, ignore_errors=True)
        self.jobs.pop(document_id, None)

    def _fail(self, job: DocumentJob, message: str) -> None:
        job.status, job.current_stage, job.progress = "failed", "failed", 0
        job.error = message
        job.completed_at = datetime.now(timezone.utc)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        basename = Path(filename).name
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", basename).strip("._")
        return cleaned or "document.docx"

    def _cleanup_orphaned_job_dirs(self) -> None:
        """Remove job directories left by a previous local process session."""
        for child in self.root_dir.iterdir():
            if child.is_dir() and child.name not in self.jobs:
                shutil.rmtree(child, ignore_errors=True)

    def _validate_docx_archive(self, path: Path) -> None:
        """Reject malformed or expansion-heavy ZIP packages before parsing."""
        if not zipfile.is_zipfile(path):
            raise DocumentJobError("Malformed DOCX file")
        try:
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > self.max_zip_entries:
                    raise DocumentJobError("DOCX contains too many archive entries")
                uncompressed_size = 0
                for entry in entries:
                    entry_path = Path(entry.filename)
                    if entry.filename.startswith(("/", "\\")) or ".." in entry_path.parts:
                        raise DocumentJobError("Malformed DOCX file")
                    uncompressed_size += entry.file_size
                    if uncompressed_size > self.max_uncompressed_size:
                        raise DocumentJobError("DOCX expands beyond the allowed size")
        except DocumentJobError:
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise DocumentJobError("Malformed DOCX file") from exc