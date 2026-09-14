"""Tests verifying immutability of AST nodes and read-only preservation of source files."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from app.models.ast import (
    ElementType,
    ParagraphElement,
    RunMetadata,
    TableCell,
    TableElement,
)
from app.parser.docx_parser import DocxParser
from app.utils.file_utils import get_file_fingerprint, verify_file_unmodified


def test_source_file_unmodified_on_disk(deterministic_sample_path: Path):
    """Verifies that parsing a document performs zero disk writes and preserves file hashes."""
    fingerprint_before = get_file_fingerprint(deterministic_sample_path)

    # Parse document
    parser = DocxParser(enforce_read_only=True)
    doc = parser.parse(deterministic_sample_path)

    assert doc is not None

    fingerprint_after = get_file_fingerprint(deterministic_sample_path)

    unmodified, reason = verify_file_unmodified(fingerprint_before, fingerprint_after)
    assert unmodified is True, f"File on disk was mutated! Detail: {reason}"
    assert fingerprint_before.sha256 == fingerprint_after.sha256
    assert fingerprint_before.mtime == fingerprint_after.mtime
    assert fingerprint_before.file_size_bytes == fingerprint_after.file_size_bytes


def test_paragraph_element_immutability():
    """Verifies that ParagraphElement cannot be mutated after creation."""
    elem = ParagraphElement(
        element_id="elem_001",
        element_type=ElementType.PARAGRAPH,
        paragraph_index=0,
        original_text="Immutable manuscript sentence.",
        original_style="Normal",
        runs=(RunMetadata(text="Immutable manuscript sentence."),),
    )

    # Attempt to mutate original_text
    with pytest.raises((FrozenInstanceError, AttributeError)):
        elem.original_text = "Mutated text."  # type: ignore

    # Attempt to mutate element_type
    with pytest.raises((FrozenInstanceError, AttributeError)):
        elem.element_type = ElementType.TITLE  # type: ignore

    # Attempt to mutate runs
    with pytest.raises((FrozenInstanceError, AttributeError)):
        elem.runs = ()  # type: ignore


def test_run_metadata_immutability():
    """Verifies that RunMetadata cannot be mutated after creation."""
    run = RunMetadata(
        text="Sample run text",
        bold=True,
        italic=False,
        font_name="Garamond",
        font_size_pt=11.0,
    )

    with pytest.raises((FrozenInstanceError, AttributeError)):
        run.text = "Altered run text"  # type: ignore

    with pytest.raises((FrozenInstanceError, AttributeError)):
        run.bold = False  # type: ignore


def test_table_cell_immutability():
    """Verifies that TableCell cannot be mutated after creation."""
    cell = TableCell(
        row_idx=0,
        col_idx=0,
        text="Cell Header A",
    )

    with pytest.raises((FrozenInstanceError, AttributeError)):
        cell.text = "Modified Cell"  # type: ignore
