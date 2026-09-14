"""Tests for Content Preservation Baseline and Deterministic Fingerprinting."""

from pathlib import Path
import pytest

from app.models.ast import (
    CanonicalDocument,
    DocumentMetadata,
    ElementType,
    ParagraphElement,
)
from app.parser.docx_parser import DocxParser
from app.services.content_preservation import ContentPreservationService


def test_ordered_text_sequence_extraction(deterministic_sample_path: Path):
    """Verifies that the ordered text sequence extracted from AST contains all key elements."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    fp = ContentPreservationService.generate_fingerprint(doc)

    assert fp.element_count == len(doc.elements)
    assert len(fp.ordered_text_sequence) == len(doc.elements)

    # Verify first few elements in order
    assert fp.ordered_text_sequence[0] == "The Architecture of Distributed Systems"
    assert "Dr. Ada Lovelace & Alan Turing" in fp.ordered_text_sequence[1]
    assert fp.ordered_text_sequence[2] == "Chapter 1: Foundations of Computing"
    assert fp.ordered_text_sequence[3] == "1.1 The Theoretical Model"


def test_normalization_rules():
    """Verifies documented normalization rules: NFKC, whitespace collapse, CRLF, trimming."""
    # Test CRLF conversion and whitespace collapsing
    raw = "  Line 1   with   multiple    spaces.  \r\n\r\n  Line 2 with \t tabs.  "
    normalized = ContentPreservationService.normalize_string(raw)
    expected = "Line 1 with multiple spaces.\nLine 2 with tabs."
    assert normalized == expected

    # Test Unicode ligature decomposition/composition (NFKC: 'ﬁ' -> 'fi')
    ligature_text = "The ﬁrst deﬁnition."
    normalized_ligature = ContentPreservationService.normalize_string(ligature_text)
    assert normalized_ligature == "The first definition."


def test_content_hash_stability(deterministic_sample_path: Path):
    """Verifies SHA-256 fingerprint is 100% stable and deterministic across multiple runs."""
    parser = DocxParser()

    hashes = []
    for _ in range(5):
        doc = parser.parse(deterministic_sample_path)
        fp = ContentPreservationService.generate_fingerprint(doc)
        hashes.append(fp.sha256_hash)

    # All 5 hashes must be bit-for-bit identical
    assert len(set(hashes)) == 1
    assert len(hashes[0]) == 64  # Valid SHA-256 hex length


def test_content_identity_verification(deterministic_sample_path: Path):
    """Verifies verify_content_identity detects identical vs mutated content."""
    parser = DocxParser()
    doc_original = parser.parse(deterministic_sample_path)
    doc_clone = parser.parse(deterministic_sample_path)

    # Identical documents
    is_identical, msg = ContentPreservationService.verify_content_identity(doc_original, doc_clone)
    assert is_identical is True
    assert "100% textual content preservation verified" in msg

    # Mutated document (simulate an element text change)
    mutated_elements = list(doc_clone.elements)
    original_elem = mutated_elements[0]
    
    # Create an altered element
    mutated_elem = ParagraphElement(
        element_id="elem_mutated",
        element_type=ElementType.TITLE,
        paragraph_index=0,
        original_text="Altered Title Content That Violates Preservation",
        original_style="Title",
        runs=(),
    )
    mutated_elements[0] = mutated_elem
    doc_mutated = CanonicalDocument(
        metadata=doc_clone.metadata,
        elements=tuple(mutated_elements),
    )

    is_identical_mutated, fail_msg = ContentPreservationService.verify_content_identity(doc_original, doc_mutated)
    assert is_identical_mutated is False
    assert "Content mismatch" in fail_msg


def test_verbatim_text_preservation(deterministic_sample_path: Path):
    """Ensures that the extracted text matches expected author manuscript content verbatim."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)
    fp = ContentPreservationService.generate_fingerprint(doc)

    expected_snippets = [
        "The Architecture of Distributed Systems",
        "Chapter 1: Foundations of Computing",
        "1.1 The Theoretical Model",
        "A distributed computational model operates across autonomous nodes",
        "Typography check: bold statement, followed by an italicized caveat",
        "Throughput (ops/s)",
        "Figure 1.1: Distributed consensus state transition",
        "Initialize all consensus registers to state zero.",
        "High availability with zero single points of failure.",
        "Shannon, C. E. (1948). A Mathematical Theory of Communication.",
        "Turing, A. M. (1936). On Computable Numbers",
    ]

    for snippet in expected_snippets:
        assert snippet in fp.normalized_text, f"Expected snippet missing from normalized text: '{snippet}'"
