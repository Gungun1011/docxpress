"""Unit tests for Phase 4: NLP-based structure detection and feature extraction."""

from pathlib import Path
import pytest

from app.core.nlp.detector import NLPStructureClassifier
from app.core.nlp.extractor import NLPFeatureExtractor
from app.core.nlp.schemas import NLPElementFeatures
from app.models.ast import (
    ElementType,
    ParagraphElement,
    RunMetadata,
    TableElement,
)
from app.parser.docx_parser import DocxParser
from app.services.content_preservation import ContentPreservationService


# =====================================================================
# 1. CORE DICTIONARY FORMAT TEST (Exact user example match)
# =====================================================================

def test_core_features_dictionary_format():
    """Verifies that to_core_dict() produces the exact required format from user prompt."""
    extractor = NLPFeatureExtractor()
    elem = ParagraphElement(
        element_id="p1",
        element_type=ElementType.PARAGRAPH,
        paragraph_index=1,
        original_text="1.2.1 Distributed consensus algorithms in practice",
    )
    feat = extractor.extract_element_features(
        elem=elem,
        index=1,
        total_elements=9,
    )

    core_dict = feat.to_core_dict()
    assert "text_length" in core_dict
    assert "word_count" in core_dict
    assert "is_all_caps" in core_dict
    assert "starts_with_number" in core_dict
    assert "contains_chapter_keyword" in core_dict
    assert "paragraph_position" in core_dict

    assert core_dict["starts_with_number"] is True
    assert core_dict["contains_chapter_keyword"] is False
    assert core_dict["is_all_caps"] is False
    assert core_dict["word_count"] >= 5
    assert core_dict["text_length"] == len("1.2.1 Distributed consensus algorithms in practice")
    assert round(core_dict["paragraph_position"], 2) == 0.12 or abs(core_dict["paragraph_position"] - 0.12) < 0.05


# =====================================================================
# 2. SENTENCE LENGTH & TOKENIZATION TESTS
# =====================================================================

def test_sentence_tokenization_and_length():
    """Verifies sentence splitting, sentence count, and average sentence length."""
    extractor = NLPFeatureExtractor()
    text = (
        "Distributed consensus is difficult across asynchronous networks. "
        "Each autonomous node coordinates through state transitions. "
        "Message latency remains bounded under normal load."
    )
    elem = ParagraphElement("p1", ElementType.PARAGRAPH, 5, text)
    feat = extractor.extract_element_features(elem, index=5, total_elements=10)

    assert feat.sentence_count == 3
    assert feat.word_count > 15
    assert feat.avg_sentence_length > 5.0
    assert feat.avg_word_length > 3.0


# =====================================================================
# 3. CAPITALIZATION ANALYSIS TESTS
# =====================================================================

def test_capitalization_features():
    """Verifies uppercase ratio, all-caps, and title-case detection."""
    extractor = NLPFeatureExtractor()

    # Case A: ALL CAPS
    caps_elem = ParagraphElement("p1", ElementType.PARAGRAPH, 0, "CHAPTER ONE: THE FOUNDATIONS")
    f_caps = extractor.extract_element_features(caps_elem, 0, 10)
    assert f_caps.is_all_caps is True
    assert f_caps.uppercase_ratio == 1.0

    # Case B: Title Case
    title_elem = ParagraphElement("p2", ElementType.PARAGRAPH, 1, "The Architecture of Distributed Systems")
    f_title = extractor.extract_element_features(title_elem, 1, 10)
    assert f_title.is_all_caps is False
    assert f_title.is_title_case is True
    assert 0.10 < f_title.uppercase_ratio < 0.50

    # Case C: Lowercase prose
    body_elem = ParagraphElement("p3", ElementType.PARAGRAPH, 2, "normal lowercase running text in paragraph.")
    f_body = extractor.extract_element_features(body_elem, 2, 10)
    assert f_body.is_all_caps is False
    assert f_body.is_title_case is False
    assert f_body.uppercase_ratio < 0.10


# =====================================================================
# 4. PUNCTUATION ANALYSIS TESTS
# =====================================================================

def test_punctuation_features():
    """Verifies terminal punctuation and punctuation count/ratio."""
    extractor = NLPFeatureExtractor()

    # Period
    p_elem = ParagraphElement("p1", ElementType.PARAGRAPH, 0, "This is a statement.")
    f_p = extractor.extract_element_features(p_elem, 0, 5)
    assert f_p.ends_with_period is True
    assert f_p.ends_with_colon is False
    assert f_p.punctuation_count >= 1

    # Colon
    c_elem = ParagraphElement("p2", ElementType.PARAGRAPH, 1, "Chapter 1:")
    f_c = extractor.extract_element_features(c_elem, 1, 5)
    assert f_c.ends_with_period is False
    assert f_c.ends_with_colon is True

    # Question mark
    q_elem = ParagraphElement("p3", ElementType.PARAGRAPH, 2, "Why does consensus fail?")
    f_q = extractor.extract_element_features(q_elem, 2, 5)
    assert f_q.ends_with_question is True


# =====================================================================
# 5. SURROUNDING PARAGRAPHS & CONTEXT TESTS
# =====================================================================

def test_surrounding_paragraphs_and_isolation():
    """Verifies prev/next paragraph token counts and isolated block detection."""
    extractor = NLPFeatureExtractor()

    prev_e = ParagraphElement("p0", ElementType.PARAGRAPH, 0, "A long narrative paragraph containing thirty-five words of standard running prose explanation and commentary about distributed network partitions.")
    short_heading = ParagraphElement("p1", ElementType.PARAGRAPH, 1, "System Overview")
    next_e = ParagraphElement("p2", ElementType.PARAGRAPH, 2, "Another long body paragraph providing detailed empirical evaluation of the throughput and latency metrics across fifty distinct server nodes.")

    feat = extractor.extract_element_features(
        elem=short_heading,
        index=1,
        total_elements=3,
        prev_elem=prev_e,
        next_elem=next_e,
    )

    assert feat.prev_paragraph_word_count > 10
    assert feat.next_paragraph_word_count > 10
    assert feat.word_count == 2
    assert feat.is_isolated is True


# =====================================================================
# 6. KEYWORD PATTERNS TESTS
# =====================================================================

def test_keyword_pattern_flags():
    """Verifies chapter, author, reference, abstract, and conclusion keyword extraction."""
    extractor = NLPFeatureExtractor()

    chap_elem = ParagraphElement("p1", ElementType.PARAGRAPH, 0, "Chapter 1 Foundations")
    f_chap = extractor.extract_element_features(chap_elem, 0, 10)
    assert f_chap.contains_chapter_keyword is True

    author_elem = ParagraphElement("p2", ElementType.PARAGRAPH, 1, "Department of Computer Science, University")
    f_auth = extractor.extract_element_features(author_elem, 1, 10)
    assert f_auth.contains_author_keyword is True

    ref_elem = ParagraphElement("p3", ElementType.PARAGRAPH, 8, "References and Works Cited")
    f_ref = extractor.extract_element_features(ref_elem, 8, 10)
    assert f_ref.contains_reference_keyword is True

    abs_elem = ParagraphElement("p4", ElementType.PARAGRAPH, 2, "Abstract: This research investigates...")
    f_abs = extractor.extract_element_features(abs_elem, 2, 10)
    assert f_abs.contains_abstract_keyword is True

    conc_elem = ParagraphElement("p5", ElementType.PARAGRAPH, 7, "Conclusion and Future Work")
    f_conc = extractor.extract_element_features(conc_elem, 7, 10)
    assert f_conc.contains_conclusion_keyword is True


# =====================================================================
# 7. LINGUISTIC FEATURES TESTS (Stopwords & Lexical Diversity)
# =====================================================================

def test_linguistic_stopword_density():
    """Verifies that prose paragraphs have significantly higher stopword ratio than headings."""
    extractor = NLPFeatureExtractor()

    # Heading: low stopword density
    heading_elem = ParagraphElement("p1", ElementType.PARAGRAPH, 2, "Algorithmic Complexity Benchmarks")
    f_h = extractor.extract_element_features(heading_elem, 2, 10)
    assert f_h.stopword_ratio == 0.0

    # Running prose: high stopword density (e.g. 'the', 'of', 'in', 'and', 'that', 'is')
    prose_elem = ParagraphElement(
        "p2", ElementType.PARAGRAPH, 3,
        "This is the summary of the work that was done in the laboratory with all of the nodes."
    )
    f_p = extractor.extract_element_features(prose_elem, 3, 10)
    assert f_p.stopword_ratio > 0.40
    assert 0.0 < f_p.lexical_diversity <= 1.0


# =====================================================================
# 8. FONT & TYPOGRAPHY TESTS
# =====================================================================

def test_font_and_typography_signals():
    """Verifies extraction of font size, bold, italic, and prominence."""
    extractor = NLPFeatureExtractor()

    elem = ParagraphElement(
        "p1", ElementType.PARAGRAPH, 0, "Prominent Section Header",
        runs=(RunMetadata("Prominent Section Header", bold=True, italic=False, font_size_pt=16.0),)
    )
    feat = extractor.extract_element_features(elem, 0, 10, doc_median_font_size=11.0)

    assert feat.is_bold is True
    assert feat.is_italic is False
    assert feat.font_size_pt == 16.0
    assert feat.is_larger_than_surroundings is True


# =====================================================================
# 9. NLP STRUCTURE CLASSIFIER INFERENCE TESTS (Disambiguating unstyled manuscripts)
# =====================================================================

def test_nlp_classifier_unstyled_heading():
    """Verifies NLP classifier identifies an unstyled heading without Word styles or numbers."""
    classifier = NLPStructureClassifier()
    extractor = classifier.extractor

    prev_p = ParagraphElement("p0", ElementType.PARAGRAPH, 0, "A standard 50-word narrative body paragraph with full terminal periods and regular structure describing system requirements.")
    unstyled_h = ParagraphElement(
        "p1", ElementType.PARAGRAPH, 1, "Empirical Evaluation",
        original_style="Normal",  # Unstyled!
        runs=(RunMetadata("Empirical Evaluation", bold=True),)
    )
    next_p = ParagraphElement("p2", ElementType.PARAGRAPH, 2, "Another standard narrative prose paragraph presenting measurement data and comparative tables under various workloads.")

    feat = extractor.extract_element_features(
        elem=unstyled_h,
        index=1,
        total_elements=3,
        prev_elem=prev_p,
        next_elem=next_p,
    )

    res = classifier.classify_element(feat)
    assert res.element_type == "heading"
    assert res.confidence >= 0.88
    assert "short_isolated_block" in res.linguistic_cues


def test_nlp_classifier_prose_paragraph():
    """Verifies NLP classifier recognizes standard prose narrative."""
    classifier = NLPStructureClassifier()
    extractor = classifier.extractor

    prose = ParagraphElement(
        "p1", ElementType.PARAGRAPH, 3,
        "Distributed consensus remains one of the foundational challenges in computer science. "
        "When autonomous machines communicate over an asynchronous network, achieving consistent state "
        "requires strict adherence to algorithmic guarantees."
    )
    feat = extractor.extract_element_features(prose, index=3, total_elements=10)
    res = classifier.classify_element(feat)

    assert res.element_type == "body_paragraph"
    assert res.confidence >= 0.90
    assert "terminal_period_punctuation" in res.linguistic_cues


# =====================================================================
# 10. CONTENT PRESERVATION INVARIANT TEST
# =====================================================================

def test_nlp_extraction_preserves_document_text(deterministic_sample_path: Path):
    """Verifies that running NLP feature extraction modifies ZERO bytes or characters."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    extractor = NLPFeatureExtractor()
    features = extractor.extract_document_features(doc)

    assert len(features) == doc.element_count

    # Re-verify text fingerprint
    fp_before = ContentPreservationService.generate_fingerprint(doc)
    doc_reloaded = parser.parse(deterministic_sample_path)
    fp_after = ContentPreservationService.generate_fingerprint(doc_reloaded)

    assert fp_before.sha256_hash == fp_after.sha256_hash
    assert fp_before.ordered_text_sequence == fp_after.ordered_text_sequence
