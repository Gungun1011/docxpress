"""Extensive unit tests for Phase 3: Rule-Based Structure Detection Engine."""

from pathlib import Path
import pytest

from app.core.rules.config import RuleEngineConfig
from app.core.rules.detector import RegexStructureDetector
from app.core.rules.schemas import DetectionResult
from app.models.ast import (
    ElementType,
    FigureElement,
    ParagraphElement,
    RunMetadata,
    TableElement,
)
from app.parser.docx_parser import DocxParser
from app.services.content_preservation import ContentPreservationService


# =====================================================================
# 1. CHAPTER PATTERN TESTS
# =====================================================================

def test_detect_chapter_numeric():
    """Verifies detection of 'Chapter 1', 'Chapter 1:', and variations."""
    detector = RegexStructureDetector()

    cases = [
        ("Chapter 1", "Chapter 1"),
        ("Chapter 1:", "Chapter 1"),
        ("Chapter 12: High-Performance Concurrency", "Chapter 12"),
        ("Ch. 4 - Algorithmic Complexity", "Chapter 4"),
    ]
    for text, expected_pattern in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 2, text)
        result = detector.evaluate_element(elem, doc_position=0.20, total_elements=20)

        assert result.element_type == "chapter_heading"
        assert result.confidence >= 0.98
        assert "matched chapter regex" in result.reason
        assert result.pattern_matched == expected_pattern


def test_detect_chapter_number_word():
    """Verifies detection of 'CHAPTER ONE', 'Chapter Two', 'Chapter Twenty-One'."""
    detector = RegexStructureDetector()

    cases = [
        ("CHAPTER ONE", "CHAPTER ONE"),
        ("Chapter Two:", "CHAPTER TWO"),
        ("CHAPTER THREE - The Beginning", "CHAPTER THREE"),
        ("Chapter Twenty", "CHAPTER TWENTY"),
    ]
    for text, expected_pattern in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 2, text)
        result = detector.evaluate_element(elem, doc_position=0.20, total_elements=20)

        assert result.element_type == "chapter_heading"
        assert result.confidence >= 0.98
        assert "matched chapter regex with spelled-out number word" in result.reason
        assert result.pattern_matched == expected_pattern


def test_detect_chapter_roman_numerals():
    """Verifies detection of 'CHAPTER I', 'Chapter IV', 'CHAPTER IX'."""
    detector = RegexStructureDetector()

    cases = [
        ("CHAPTER I", "CHAPTER I"),
        ("Chapter IV:", "CHAPTER IV"),
        ("CHAPTER IX — Fault Tolerance", "CHAPTER IX"),
        ("Chapter XIV", "CHAPTER XIV"),
    ]
    for text, expected_pattern in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 2, text)
        result = detector.evaluate_element(elem, doc_position=0.20, total_elements=20)

        assert result.element_type == "chapter_heading"
        assert result.confidence >= 0.98
        assert "matched chapter regex with Roman numeral" in result.reason
        assert result.pattern_matched == expected_pattern


# =====================================================================
# 2. HEADING PATTERN TESTS
# =====================================================================

def test_detect_headings_level_1():
    """Verifies detection of Level 1 headings like '1 Introduction', '1. Introduction'."""
    detector = RegexStructureDetector()

    cases = [
        ("1 Introduction", "1"),
        ("1. Introduction", "1"),
        ("2 Background and Motivations", "2"),
    ]
    for text, expected_pattern in cases:
        elem = ParagraphElement(
            "p1", ElementType.PARAGRAPH, 3, text,
            runs=(RunMetadata(text=text, bold=True, font_size_pt=14.0),)
        )
        result = detector.evaluate_element(elem, doc_position=0.25, total_elements=20)

        assert result.element_type == "heading_1"
        assert result.confidence >= 0.95
        assert result.pattern_matched == expected_pattern


def test_detect_headings_level_2():
    """Verifies detection of Level 2 headings like '1.1 Background'."""
    detector = RegexStructureDetector()

    cases = [
        ("1.1 Background", "1.1"),
        ("1.1. System Overview", "1.1"),
        ("2.3 Execution Pipeline", "2.3"),
    ]
    for text, expected_pattern in cases:
        elem = ParagraphElement(
            "p1", ElementType.PARAGRAPH, 4, text,
            runs=(RunMetadata(text=text, bold=True),)
        )
        result = detector.evaluate_element(elem, doc_position=0.30, total_elements=20)

        assert result.element_type == "heading_2"
        assert result.confidence >= 0.95
        assert result.pattern_matched == expected_pattern


def test_detect_headings_level_3():
    """Verifies detection of Level 3 headings like '1.2.1 Subtopic'."""
    detector = RegexStructureDetector()

    cases = [
        ("1.2.1 Subtopic", "1.2.1"),
        ("1.2.1. Detailed Implementation", "1.2.1"),
        ("3.1.2 Memory Optimization", "3.1.2"),
    ]
    for text, expected_pattern in cases:
        elem = ParagraphElement(
            "p1", ElementType.PARAGRAPH, 5, text,
            runs=(RunMetadata(text=text, bold=True),)
        )
        result = detector.evaluate_element(elem, doc_position=0.40, total_elements=20)

        assert result.element_type == "heading_3"
        assert result.confidence >= 0.96
        assert result.pattern_matched == expected_pattern


# =====================================================================
# 3. FIGURE & CAPTION TESTS
# =====================================================================

def test_detect_figure_captions():
    """Verifies detection of 'Figure 1', 'Figure 1:', 'Fig. 1'."""
    detector = RegexStructureDetector()

    cases = [
        ("Figure 1", "Figure 1"),
        ("Figure 1:", "Figure 1"),
        ("Fig. 1", "Fig. 1"),
        ("Figure 1.1: System Architecture Diagram", "Figure 1.1"),
        ("Fig. 2 — Network Latency Plot", "Fig. 2"),
    ]
    for text, expected_prefix in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 6, text)
        result = detector.evaluate_element(elem, doc_position=0.50, total_elements=20)

        assert result.element_type == "figure_caption"
        assert result.confidence >= 0.98
        assert result.pattern_matched == expected_prefix


def test_detect_native_figure_element():
    """Verifies detection of native FigureElement and drawing objects."""
    detector = RegexStructureDetector()
    fig = FigureElement("f1", ElementType.FIGURE, 5, "", image_id="rId12")
    result = detector.evaluate_element(fig, doc_position=0.50, total_elements=20)

    assert result.element_type == "figure"
    assert result.confidence == 1.0
    assert result.pattern_matched == "rId12"


# =====================================================================
# 4. TABLE & CAPTION TESTS
# =====================================================================

def test_detect_table_captions():
    """Verifies detection of 'Table 1', 'Table 1:'."""
    detector = RegexStructureDetector()

    cases = [
        ("Table 1", "Table 1"),
        ("Table 1:", "Table 1"),
        ("Table 1.1: Resource Benchmarks", "Table 1.1"),
        ("Tbl. 3: Latency Comparisons", "Table 3"),
    ]
    for text, expected_prefix in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 7, text)
        result = detector.evaluate_element(elem, doc_position=0.55, total_elements=20)

        assert result.element_type == "table_caption"
        assert result.confidence >= 0.98
        assert result.pattern_matched == expected_prefix


def test_detect_native_table_element():
    """Verifies detection of native TableElement objects."""
    detector = RegexStructureDetector()
    tbl = TableElement("t1", ElementType.TABLE, 7, "A\tB\n1\t2", rows_count=2, cols_count=2)
    result = detector.evaluate_element(tbl, doc_position=0.55, total_elements=20)

    assert result.element_type == "table"
    assert result.confidence == 1.0
    assert "2x2 table" in result.pattern_matched


# =====================================================================
# 5. REFERENCES & BIBLIOGRAPHY TESTS
# =====================================================================

def test_detect_references_header():
    """Verifies detection of 'References', 'Bibliography' section headers."""
    detector = RegexStructureDetector()

    cases = ["References", "REFERENCES", "Bibliography", "Works Cited"]
    for text in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 18, text)
        result = detector.evaluate_element(elem, doc_position=0.90, total_elements=20)

        assert result.element_type == "references"
        assert result.confidence == 0.99
        assert result.pattern_matched == text


def test_detect_reference_entry():
    """Verifies detection of academic citation entries in back-matter."""
    detector = RegexStructureDetector()

    citations = [
        "1. Shannon, C. E. (1948). A Mathematical Theory of Communication.",
        "[2] Lamport, L. (1978). Time, Clocks, and the Ordering of Events.",
    ]
    for text in citations:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 19, text)
        result = detector.evaluate_element(elem, doc_position=0.95, total_elements=20)

        assert result.element_type == "reference_entry"
        assert result.confidence >= 0.96


# =====================================================================
# 6. LIST ITEM TESTS (1., 2., 3., a., b., -, •, *)
# =====================================================================

def test_detect_numbered_lists():
    """Verifies detection of '1.', '2.', '3.' numbered list items."""
    detector = RegexStructureDetector()

    cases = [
        ("1. Initialize registers to state zero.", "1."),
        ("2. Broadcast request packet to all replicas.", "2."),
        ("3. Await quorum acknowledgment.", "3."),
    ]
    for text, expected_marker in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 10, text)
        result = detector.evaluate_element(elem, doc_position=0.60, total_elements=20)

        assert result.element_type == "list_item"
        assert result.confidence >= 0.96
        assert result.pattern_matched == expected_marker


def test_detect_lettered_lists():
    """Verifies detection of 'a.', 'b.' lettered list items."""
    detector = RegexStructureDetector()

    cases = [
        ("a. Primary election phase.", "a."),
        ("b. Secondary reconciliation phase.", "b."),
    ]
    for text, expected_marker in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 11, text)
        result = detector.evaluate_element(elem, doc_position=0.65, total_elements=20)

        assert result.element_type == "list_item"
        assert result.confidence >= 0.95
        assert result.pattern_matched == expected_marker


def test_detect_bullet_lists():
    """Verifies detection of '-', '•', '*' bullet list items."""
    detector = RegexStructureDetector()

    cases = [
        ("- First high-availability cluster node.", "-"),
        ("• Second cluster replica mirror.", "•"),
        ("* Third standby coordinator.", "*"),
    ]
    for text, expected_marker in cases:
        elem = ParagraphElement("p1", ElementType.PARAGRAPH, 12, text)
        result = detector.evaluate_element(elem, doc_position=0.70, total_elements=20)

        assert result.element_type == "list_item"
        assert result.confidence >= 0.96
        assert result.pattern_matched == expected_marker


# =====================================================================
# 7. SPECIAL SECTIONS (Title, Author, Subtitle, Abstract, Acknowledgements, Conclusion)
# =====================================================================

def test_detect_title_and_author():
    """Verifies detection of manuscript Title and Author credentials."""
    detector = RegexStructureDetector()

    # Title
    title_elem = ParagraphElement(
        "p0", ElementType.PARAGRAPH, 0, "The Architecture of Distributed Systems",
        original_style="Title",
        runs=(RunMetadata("The Architecture of Distributed Systems", bold=True, font_size_pt=24.0),)
    )
    res_title = detector.evaluate_element(title_elem, doc_position=0.0, total_elements=20, index=0)
    assert res_title.element_type == "title"
    assert res_title.confidence >= 0.95

    # Author
    author_elem = ParagraphElement(
        "p1", ElementType.PARAGRAPH, 1,
        "Dr. Ada Lovelace & Alan Turing, Department of Computer Science, email: ada@computing.ac.uk",
    )
    res_author = detector.evaluate_element(author_elem, doc_position=0.05, total_elements=20, index=1)
    assert res_author.element_type == "author"
    assert res_author.confidence >= 0.95


def test_detect_abstract_and_acknowledgements():
    """Verifies detection of Abstract and Acknowledgements headings."""
    detector = RegexStructureDetector()

    # Abstract in front-matter
    abs_elem = ParagraphElement("p2", ElementType.PARAGRAPH, 2, "Abstract: This paper presents a novel approach.")
    res_abs = detector.evaluate_element(abs_elem, doc_position=0.10, total_elements=20)
    assert res_abs.element_type == "abstract"
    assert res_abs.confidence >= 0.98

    # Acknowledgements
    ack_elem = ParagraphElement("p18", ElementType.PARAGRAPH, 18, "Acknowledgements")
    res_ack = detector.evaluate_element(ack_elem, doc_position=0.85, total_elements=20)
    assert res_ack.element_type == "acknowledgements"
    assert res_ack.confidence >= 0.98


def test_detect_conclusion():
    """Verifies detection of Conclusion section heading."""
    detector = RegexStructureDetector()

    conc_elem = ParagraphElement("p15", ElementType.PARAGRAPH, 15, "Conclusion and Future Directions")
    result = detector.evaluate_element(conc_elem, doc_position=0.75, total_elements=20)
    assert result.element_type == "conclusion"
    assert result.confidence >= 0.96


# =====================================================================
# 8. MULTI-SIGNAL & CONFIGURABILITY TESTS
# =====================================================================

def test_non_text_signals_typography_and_position():
    """Verifies that non-text signals (bold, font size, position) influence confidence."""
    detector = RegexStructureDetector()

    # Regular text chapter vs bold + large font chapter
    plain_elem = ParagraphElement("p1", ElementType.PARAGRAPH, 2, "Chapter 1: Foundations")
    bold_elem = ParagraphElement(
        "p2", ElementType.PARAGRAPH, 2, "Chapter 1: Foundations",
        runs=(RunMetadata("Chapter 1: Foundations", bold=True, font_size_pt=18.0),)
    )

    res_plain = detector.evaluate_element(plain_elem, doc_position=0.20, total_elements=20)
    res_bold = detector.evaluate_element(bold_elem, doc_position=0.20, total_elements=20)

    assert res_bold.confidence >= res_plain.confidence


def test_detector_configuration_overrides():
    """Verifies configurable custom patterns and disabled rule categories."""
    # Custom configuration
    config = RuleEngineConfig(
        enabled_categories={"chapter", "custom"},
        custom_patterns={"custom_module": [r"^MODULE\s+\d+"]},
        confidence_overrides={"chapter_digit": 0.999},
    )
    detector = RegexStructureDetector(config=config)

    # 1. Custom pattern matches
    custom_elem = ParagraphElement("p1", ElementType.PARAGRAPH, 1, "MODULE 5: Storage Engines")
    res_custom = detector.evaluate_element(custom_elem, doc_position=0.20, total_elements=10)
    assert res_custom.element_type == "custom_module"

    # 2. Confidence override is applied
    chap_elem = ParagraphElement("p2", ElementType.PARAGRAPH, 2, "Chapter 1: Intro")
    res_chap = detector.evaluate_element(chap_elem, doc_position=0.20, total_elements=10)
    assert res_chap.confidence >= 0.999

    # 3. Disabled category (heading) defaults to body_paragraph
    h_elem = ParagraphElement("p3", ElementType.PARAGRAPH, 3, "1.1 Background")
    res_h = detector.evaluate_element(h_elem, doc_position=0.30, total_elements=10)
    assert res_h.element_type == "body_paragraph"


def test_required_json_dict_format():
    """Verifies that DetectionResult.to_dict() produces the exact required JSON structure."""
    detector = RegexStructureDetector()
    elem = ParagraphElement("p1", ElementType.PARAGRAPH, 2, "Chapter 1")
    res = detector.evaluate_element(elem, doc_position=0.10, total_elements=10)

    d = res.to_dict()
    assert "element_type" in d
    assert "confidence" in d
    assert "reason" in d
    assert "pattern_matched" in d
    assert d["element_type"] == "chapter_heading"
    assert d["pattern_matched"] == "Chapter 1"


def test_detect_document_preserves_text(deterministic_sample_path: Path):
    """Verifies that running detection across a document modifies ZERO text."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    detector = RegexStructureDetector()
    results = detector.detect_document(doc)

    assert len(results) == doc.element_count
    # Verify no elements or texts were mutated
    for elem, res in zip(doc.elements, results):
        assert res.element_type is not None
        assert 0.0 <= res.confidence <= 1.0
        assert isinstance(res.reason, str)
