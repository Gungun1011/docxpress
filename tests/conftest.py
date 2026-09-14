"""Pytest fixtures and test environment setup for DocXpress."""

from pathlib import Path
import pytest

from scripts.generate_test_docs import generate_all_test_documents


@pytest.fixture(scope="session")
def sample_docs_dir(tmp_path_factory) -> Path:
    """Provides a directory with freshly generated deterministic test documents."""
    temp_dir = tmp_path_factory.mktemp("test_sample_docs")
    generate_all_test_documents(temp_dir)
    return temp_dir


@pytest.fixture(scope="session")
def deterministic_sample_path(sample_docs_dir: Path) -> Path:
    """Path to primary deterministic sample document."""
    return sample_docs_dir / "deterministic_sample.docx"


@pytest.fixture(scope="session")
def empty_doc_path(sample_docs_dir: Path) -> Path:
    """Path to empty test document."""
    return sample_docs_dir / "empty.docx"


@pytest.fixture(scope="session")
def unicode_doc_path(sample_docs_dir: Path) -> Path:
    """Path to multilingual unicode test document."""
    return sample_docs_dir / "unicode_sample.docx"


@pytest.fixture(scope="session")
def interleaved_doc_path(sample_docs_dir: Path) -> Path:
    """Path to interleaved table test document."""
    return sample_docs_dir / "interleaved_tables.docx"
