"""Integration tests for the Master HybridStructureClassifier."""

from pathlib import Path
import pytest

from app.core.ml.classifier import HybridStructureClassifier
from app.models.ast import ElementType
from app.parser.docx_parser import DocxParser
from app.services.content_preservation import ContentPreservationService


def test_hybrid_classification_deterministic_sample(deterministic_sample_path: Path):
    """Verifies end-to-end hybrid classification on the primary test manuscript."""
    parser = DocxParser()
    raw_doc = parser.parse(deterministic_sample_path)

    classifier = HybridStructureClassifier(model_type="logistic_regression")
    classified_doc, report = classifier.classify_document(raw_doc)

    assert classified_doc.element_count == raw_doc.element_count
    assert report.total_elements == 20
    assert report.average_confidence >= 0.90

    # Verify detected classes contain all major elements
    types_found = set(report.type_counts.keys())
    assert ElementType.TITLE.value in types_found
    assert ElementType.AUTHOR.value in types_found
    assert ElementType.CHAPTER.value in types_found
    assert ElementType.SUBHEADING.value in types_found
    assert ElementType.PARAGRAPH.value in types_found
    assert ElementType.TABLE.value in types_found
    assert ElementType.FIGURE.value in types_found
    assert ElementType.CAPTION.value in types_found
    assert ElementType.LIST.value in types_found
    assert ElementType.HEADING.value in types_found
    assert ElementType.REFERENCE.value in types_found

    # Crucial Invariant: Zero text modification
    # Raw document and classified document must have 100% identical text fingerprints
    is_identical, msg = ContentPreservationService.verify_content_identity(raw_doc, classified_doc)
    assert is_identical is True, f"Text was altered during classification! {msg}"

    for orig_elem, class_elem in zip(raw_doc.elements, classified_doc.elements):
        assert orig_elem.original_text == class_elem.original_text
        assert orig_elem.element_id == class_elem.element_id
        assert orig_elem.paragraph_index == class_elem.paragraph_index


def test_hybrid_classification_decision_tree(deterministic_sample_path: Path):
    """Verifies that the classifier works identically with the Decision Tree estimator."""
    parser = DocxParser()
    raw_doc = parser.parse(deterministic_sample_path)

    classifier = HybridStructureClassifier(model_type="decision_tree")
    classified_doc, report = classifier.classify_document(raw_doc)

    assert classified_doc.element_count == raw_doc.element_count
    assert report.average_confidence >= 0.90

    # Verify text preservation invariant
    is_identical, _ = ContentPreservationService.verify_content_identity(raw_doc, classified_doc)
    assert is_identical is True
