"""FastAPI integration tests using isolated temporary document storage."""

from pathlib import Path
from types import SimpleNamespace
import io
import zipfile

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.content_preservation import ContentPreservationReport
from app.services.document_jobs import DocumentJobService
from scripts.generate_test_docs import generate_deterministic_sample


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(DocumentJobService(root_dir=tmp_path / "jobs")))


def _docx_bytes(tmp_path: Path) -> bytes:
    source = tmp_path / "sample.docx"
    generate_deterministic_sample(source)
    return source.read_bytes()


def test_health_and_presets(tmp_path: Path):
    client = _client(tmp_path)
    assert client.get("/health").json()["status"] == "ok"
    profile_names = [item["name"] for item in client.get("/api/presets").json()["profiles"]]
    assert "hackathon_default" in profile_names
    assert "trade" in profile_names


def test_upload_analyze_format_status_report_download_e2e(tmp_path: Path):
    client = _client(tmp_path)
    response = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "sample.docx",
                _docx_bytes(tmp_path),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201
    document_id = response.json()["document_id"]

    analysis = client.post(f"/api/documents/{document_id}/analyze")
    assert analysis.status_code == 200
    assert analysis.json()["total_elements"] > 0
    assert analysis.json()["tables"] >= 1
    assert analysis.json()["figures"] >= 1

    formatted = client.post(f"/api/documents/{document_id}/format", json={"profile": "hackathon_default"})
    assert formatted.status_code == 200
    assert formatted.json()["status"] == "completed"

    status = client.get(f"/api/documents/{document_id}/status")
    assert status.json()["progress"] == 100
    assert status.json()["current_stage"] == "completed"

    report = client.get(f"/api/documents/{document_id}/report")
    assert report.status_code == 200
    assert report.json()["preservation"]["is_identical"] is True
    assert report.json()["preservation"]["source_hash"] == report.json()["preservation"]["output_hash"]
    assert report.json()["formatting"]["body_alignment"] == "justified"
    assert report.json()["formatting"]["body_line_spacing"] == 1.5

    download = client.get(f"/api/documents/{document_id}/download")
    assert download.status_code == 200
    assert download.content[:2] == b"PK"


def test_upload_rejects_extension_and_malformed_docx(tmp_path: Path):
    client = _client(tmp_path)
    bad_extension = client.post("/api/documents/upload", files={"file": ("notes.txt", b"text", "text/plain")})
    assert bad_extension.status_code == 400

    malformed = client.post("/api/documents/upload", files={"file": ("broken.docx", b"not-docx", "application/octet-stream")})
    assert malformed.status_code == 400


def test_upload_sanitizes_filename_and_rejects_traversal_archive(tmp_path: Path):
    client = _client(tmp_path)
    safe_docx = _docx_bytes(tmp_path)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("../../secret report.docx", safe_docx, "application/octet-stream")},
    )
    assert response.status_code == 201
    assert ".." not in response.json()["filename"]
    assert "/" not in response.json()["filename"]

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("../outside.xml", "unsafe")
    traversal = client.post(
        "/api/documents/upload",
        files={"file": ("unsafe.docx", archive.getvalue(), "application/octet-stream")},
    )
    assert traversal.status_code == 400


def test_orphaned_job_directories_are_removed_on_service_start(tmp_path: Path):
    root = tmp_path / "jobs"
    orphan = root / "orphaned"
    orphan.mkdir(parents=True)
    (orphan / "source.docx").write_bytes(b"stale")

    DocumentJobService(root_dir=root)

    assert not orphan.exists()


def test_invalid_document_id_is_consistent(tmp_path: Path):
    client = _client(tmp_path)
    response = client.get("/api/documents/missing/status")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "document_error"


def test_formatting_failure_is_reported(tmp_path: Path):
    service = DocumentJobService(root_dir=tmp_path / "jobs")
    client = TestClient(create_app(service))
    upload = client.post("/api/documents/upload", files={"file": ("sample.docx", _docx_bytes(tmp_path), "application/octet-stream")})
    document_id = upload.json()["document_id"]

    def fail(*args, **kwargs):
        raise RuntimeError("test formatter failure")

    service.formatter.format_document = fail
    response = client.post(f"/api/documents/{document_id}/format", json={"profile": "trade"})
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Formatting failed"
    assert client.get(f"/api/documents/{document_id}/status").json()["status"] == "failed"


def test_content_preservation_failure_is_never_successful(tmp_path: Path):
    service = DocumentJobService(root_dir=tmp_path / "jobs")
    client = TestClient(create_app(service))
    upload = client.post("/api/documents/upload", files={"file": ("sample.docx", _docx_bytes(tmp_path), "application/octet-stream")})
    document_id = upload.json()["document_id"]

    failed_report = ContentPreservationReport(
        is_identical=False,
        source_hash="source",
        output_hash="output",
        changed_elements=(0,),
    )
    service.formatter.format_document = lambda *args, **kwargs: SimpleNamespace(
        preservation=failed_report,
        profile_name="trade",
    )
    response = client.post(f"/api/documents/{document_id}/format", json={"profile": "trade"})
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Content preservation validation failed"
    assert client.get(f"/api/documents/{document_id}/status").json()["status"] == "failed"