"""Unit tests for the deterministic RegexRuleEngine."""

import pytest

from app.core.ml.rules import RegexRuleEngine
from app.models.ast import (
    ElementType,
    FigureElement,
    ParagraphElement,
    RunMetadata,
    TableElement,
)


def test_rule_table_element():
    """Verifies that TableElement triggers table rule with 1.0 confidence."""
    tbl = TableElement(
        element_id="t1",
        element_type=ElementType.TABLE,
        paragraph_index=0,
        original_text="Header1\tHeader2",
    )
    match = RegexRuleEngine.evaluate(tbl, doc_position=0.5, total_elements=10)
    assert match is not None
    assert match.matched is True
    assert match.element_type == ElementType.TABLE
    assert match.confidence == 1.0


def test_rule_chapter_prefix():
    """Verifies chapter regex triggers on various chapter marker variations."""
    variations = [
        "Chapter 1: The Machine",
        "Chapter IV — Concurrency",
        "CH. 12 Distributed Protocols",
        "Part I: Theoretical Models",
    ]
    for text in variations:
        elem = ParagraphElement(
            element_id="p1",
            element_type=ElementType.PARAGRAPH,
            paragraph_index=2,
            original_text=text,
        )
        match = RegexRuleEngine.evaluate(elem, doc_position=0.2, total_elements=10)
        assert match is not None, f"Failed to match chapter: {text}"
        assert match.element_type == ElementType.CHAPTER
        assert match.confidence >= 0.98


def test_rule_caption_patterns():
    """Verifies caption regex triggers on figure and table captions."""
    variations = [
        "Figure 1.1: System Node Architecture",
        "Fig. 2 — Network Latency Profile",
        "Table 3: Latency benchmarks in milliseconds",
        "Plate 1: The original Babbage Engine",
    ]
    for text in variations:
        elem = ParagraphElement(
            element_id="p1",
            element_type=ElementType.PARAGRAPH,
            paragraph_index=5,
            original_text=text,
        )
        match = RegexRuleEngine.evaluate(elem, doc_position=0.5, total_elements=10)
        assert match is not None, f"Failed to match caption: {text}"
        assert match.element_type == ElementType.CAPTION


def test_rule_reference_patterns():
    """Verifies reference citation patterns in back matter."""
    citations = [
        "[1] Shannon, C. E. (1948). A Mathematical Theory of Communication.",
        "1. Turing, A. M. (1936). On Computable Numbers.",
        "Knuth, D. E. (1997). The Art of Computer Programming, Vol 1.",
    ]
    for text in citations:
        elem = ParagraphElement(
            element_id="p1",
            element_type=ElementType.PARAGRAPH,
            paragraph_index=9,
            original_text=text,
        )
        match = RegexRuleEngine.evaluate(elem, doc_position=0.90, total_elements=10)
        assert match is not None, f"Failed to match reference: {text}"
        assert match.element_type == ElementType.REFERENCE


def test_rule_numbered_headings():
    """Verifies numbered headings (H1) and subheadings (H2/H3)."""
    h1_elem = ParagraphElement(
        element_id="h1",
        element_type=ElementType.PARAGRAPH,
        paragraph_index=3,
        original_text="1. Introduction and Motivations",
    )
    m1 = RegexRuleEngine.evaluate(h1_elem, doc_position=0.3, total_elements=10)
    assert m1 is not None
    assert m1.element_type == ElementType.HEADING

    h2_elem = ParagraphElement(
        element_id="h2",
        element_type=ElementType.PARAGRAPH,
        paragraph_index=4,
        original_text="1.2 System Architecture Overview",
    )
    m2 = RegexRuleEngine.evaluate(h2_elem, doc_position=0.4, total_elements=10)
    assert m2 is not None
    assert m2.element_type == ElementType.SUBHEADING
