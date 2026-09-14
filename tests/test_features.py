"""Unit tests for the 32-dimensional feature extraction engine."""

from pathlib import Path
import numpy as np
import pytest

from app.core.ml.features import FEATURE_NAMES, FeatureExtractor
from app.models.ast import (
    ElementType,
    ParagraphElement,
    RunMetadata,
    TableElement,
)
from app.parser.docx_parser import DocxParser


def test_feature_names_count():
    """Verifies that exactly 32 features are defined and named."""
    assert len(FEATURE_NAMES) == 32
    assert "char_length" in FEATURE_NAMES
    assert "stopword_ratio" in FEATURE_NAMES
    assert "relative_doc_position" in FEATURE_NAMES
    assert "is_table" in FEATURE_NAMES


def test_element_feature_extraction():
    """Verifies individual feature calculations on a known paragraph."""
    runs = (
        RunMetadata(text="Chapter 1: ", bold=True, font_size_pt=18.0),
        RunMetadata(text="Foundations", bold=True, font_size_pt=18.0),
    )
    elem = ParagraphElement(
        element_id="test_01",
        element_type=ElementType.CHAPTER,
        paragraph_index=0,
        original_text="Chapter 1: Foundations",
        original_style="Heading 1",
        runs=runs,
    )

    features = FeatureExtractor.extract_element_features(
        elem=elem,
        index=0,
        total_elements=10,
        prev_elem=None,
        next_elem=None,
        median_font_size=11.0,
    )

    assert len(features) == 32
    assert features["char_length"] == len("Chapter 1: Foundations")
    assert features["word_count"] == 3.0
    assert features["starts_with_number"] == 0.0
    assert features["is_bold"] == 1.0
    assert features["all_runs_bold"] == 1.0
    assert features["font_size_pt"] == 18.0
    assert features["relative_font_size"] == 7.0  # 18.0 - 11.0
    assert features["relative_doc_position"] == 0.0
    assert features["is_front_matter"] == 1.0
    assert features["is_table"] == 0.0


def test_table_feature_extraction():
    """Verifies feature extraction on a TableElement."""
    tbl = TableElement(
        element_id="tbl_01",
        element_type=ElementType.TABLE,
        paragraph_index=5,
        original_text="Col1\tCol2\nVal1\tVal2",
        rows_count=2,
        cols_count=2,
    )

    features = FeatureExtractor.extract_element_features(
        elem=tbl,
        index=5,
        total_elements=10,
    )

    assert features["is_table"] == 1.0
    assert features["relative_doc_position"] == 5.0 / 9.0


def test_document_features_matrix(deterministic_sample_path: Path):
    """Verifies feature extraction across an entire CanonicalDocument."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    X = FeatureExtractor.extract_document_features(doc)

    assert isinstance(X, np.ndarray)
    assert X.shape == (len(doc.elements), 32)
    assert not np.isnan(X).any(), "Feature matrix contains NaN values"
    assert not np.isinf(X).any(), "Feature matrix contains Inf values"
