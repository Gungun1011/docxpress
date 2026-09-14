"""Feature engineering pipeline for document structure classification.

Computes a deterministic 32-dimensional feature vector for each document
block incorporating orthographic, lexical, syntactic, positional, and typography signals.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from app.models.ast import (
    BaseElement,
    CanonicalDocument,
    FigureElement,
    ParagraphElement,
    TableElement,
)

# Common English stopwords for heading vs body discrimination
COMMON_STOPWORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves",
})

FEATURE_NAMES: List[str] = [
    # Orthographic & Surface (10)
    "char_length",
    "word_count",
    "avg_word_length",
    "uppercase_ratio",
    "is_all_caps",
    "is_title_case",
    "digit_ratio",
    "ends_with_period",
    "ends_with_colon",
    "ends_with_question",
    # Lexical & Syntactic (6)
    "stopword_ratio",
    "sentence_count",
    "starts_with_number",
    "contains_roman_numeral",
    "citation_marker_count",
    "year_mention_count",
    # Positional & Contextual (8)
    "relative_doc_position",
    "is_front_matter",
    "is_back_matter",
    "prev_elem_word_count",
    "next_elem_word_count",
    "distance_from_doc_start",
    "distance_to_doc_end",
    "is_isolated",
    # Formatting & Run XML (8)
    "is_bold",
    "is_italic",
    "all_runs_bold",
    "font_size_pt",
    "relative_font_size",
    "has_drawing",
    "is_table",
    "is_list_marker",
]


class FeatureExtractor:
    """Extracts 32 structural features from document elements."""

    RE_ROMAN = re.compile(r"\b[IVXLCDM]+\b")
    RE_CITATION = re.compile(r"(\[\d+\]|\([A-Za-z]+(\s+et\s+al\.)?,\s*\d{4}\))")
    RE_YEAR = re.compile(r"\b(18|19|20)\d{2}\b")
    RE_BULLET = re.compile(r"^[\*\-\•\–\—\◦\▪\▫\►\⁃]\s+")
    RE_NUMBER_START = re.compile(r"^\d+")

    @classmethod
    def extract_element_features(
        cls,
        elem: BaseElement,
        index: int,
        total_elements: int,
        prev_elem: Optional[BaseElement] = None,
        next_elem: Optional[BaseElement] = None,
        median_font_size: float = 11.0,
    ) -> Dict[str, float]:
        """Extracts the 32 features for a single element in document context."""
        text = elem.original_text.strip()
        words = [w.lower() for w in re.findall(r"\b\w+\b", text)]
        raw_words = text.split()

        char_length = float(len(text))
        word_count = float(len(raw_words))
        avg_word_length = char_length / max(1.0, word_count)

        alpha_chars = [c for c in text if c.isalpha()]
        alpha_count = float(len(alpha_chars))
        upper_count = float(sum(1 for c in alpha_chars if c.isupper()))
        uppercase_ratio = upper_count / max(1.0, alpha_count)

        is_all_caps = 1.0 if text.isupper() and len(text) > 3 else 0.0
        is_title_case = 1.0 if text.istitle() and word_count > 1 else 0.0

        digit_count = float(sum(1 for c in text if c.isdigit()))
        digit_ratio = digit_count / max(1.0, char_length)

        ends_with_period = 1.0 if text.endswith(".") else 0.0
        ends_with_colon = 1.0 if text.endswith(":") else 0.0
        ends_with_question = 1.0 if text.endswith("?") else 0.0

        # Stopword ratio
        if words:
            stop_count = sum(1 for w in words if w in COMMON_STOPWORDS)
            stopword_ratio = float(stop_count) / float(len(words))
        else:
            stopword_ratio = 0.0

        # Estimated sentence count
        sentence_count = float(len(re.findall(r"[.!?]+(?:\s+|$)", text))) if text else 0.0

        starts_with_number = 1.0 if cls.RE_NUMBER_START.match(text) else 0.0
        contains_roman_numeral = 1.0 if cls.RE_ROMAN.search(text) else 0.0
        citation_marker_count = float(len(cls.RE_CITATION.findall(text)))
        year_mention_count = float(len(cls.RE_YEAR.findall(text)))

        # Positional features
        relative_doc_position = float(index) / max(1.0, float(total_elements - 1)) if total_elements > 1 else 0.0
        is_front_matter = 1.0 if relative_doc_position < 0.10 else 0.0
        is_back_matter = 1.0 if relative_doc_position > 0.80 else 0.0

        prev_word_count = float(len(prev_elem.original_text.split())) if prev_elem else 0.0
        next_word_count = float(len(next_elem.original_text.split())) if next_elem else 0.0

        distance_from_doc_start = float(index)
        distance_to_doc_end = float(total_elements - index - 1)

        is_isolated = 1.0 if (word_count < 20 and (prev_word_count > 25 or next_word_count > 25)) else 0.0

        # Formatting & XML features
        runs = elem.runs
        is_bold = 1.0 if any(r.bold is True for r in runs) else 0.0
        is_italic = 1.0 if any(r.italic is True for r in runs) else 0.0
        
        non_empty_runs = [r for r in runs if r.text.strip()]
        all_runs_bold = 1.0 if (non_empty_runs and all(r.bold is True for r in non_empty_runs)) else 0.0

        sizes = [r.font_size_pt for r in runs if r.font_size_pt is not None]
        font_size_pt = float(max(sizes)) if sizes else 0.0
        relative_font_size = (font_size_pt - median_font_size) if font_size_pt > 0 else 0.0

        has_drawing = 1.0 if (
            isinstance(elem, FigureElement)
            or (isinstance(elem, ParagraphElement) and elem.contains_drawing)
        ) else 0.0

        is_table = 1.0 if isinstance(elem, TableElement) else 0.0

        is_list_marker = 0.0
        if isinstance(elem, ParagraphElement) and elem.list_info is not None:
            is_list_marker = 1.0
        elif cls.RE_BULLET.match(text):
            is_list_marker = 1.0

        return {
            "char_length": char_length,
            "word_count": word_count,
            "avg_word_length": avg_word_length,
            "uppercase_ratio": uppercase_ratio,
            "is_all_caps": is_all_caps,
            "is_title_case": is_title_case,
            "digit_ratio": digit_ratio,
            "ends_with_period": ends_with_period,
            "ends_with_colon": ends_with_colon,
            "ends_with_question": ends_with_question,
            "stopword_ratio": stopword_ratio,
            "sentence_count": sentence_count,
            "starts_with_number": starts_with_number,
            "contains_roman_numeral": contains_roman_numeral,
            "citation_marker_count": citation_marker_count,
            "year_mention_count": year_mention_count,
            "relative_doc_position": relative_doc_position,
            "is_front_matter": is_front_matter,
            "is_back_matter": is_back_matter,
            "prev_elem_word_count": prev_word_count,
            "next_elem_word_count": next_word_count,
            "distance_from_doc_start": distance_from_doc_start,
            "distance_to_doc_end": distance_to_doc_end,
            "is_isolated": is_isolated,
            "is_bold": is_bold,
            "is_italic": is_italic,
            "all_runs_bold": all_runs_bold,
            "font_size_pt": font_size_pt,
            "relative_font_size": relative_font_size,
            "has_drawing": has_drawing,
            "is_table": is_table,
            "is_list_marker": is_list_marker,
        }

    @classmethod
    def extract_document_features(cls, doc: CanonicalDocument) -> np.ndarray:
        """Extracts the feature matrix X for all elements in a CanonicalDocument.
        
        Args:
            doc: The CanonicalDocument AST.
            
        Returns:
            NumPy array of shape (N_elements, 32).
        """
        n = len(doc.elements)
        if n == 0:
            return np.empty((0, len(FEATURE_NAMES)), dtype=np.float32)

        # Estimate median font size
        all_sizes = []
        for elem in doc.elements:
            for r in elem.runs:
                if r.font_size_pt is not None and r.font_size_pt > 0:
                    all_sizes.append(r.font_size_pt)
        median_size = float(np.median(all_sizes)) if all_sizes else 11.0

        rows: List[List[float]] = []
        for i, elem in enumerate(doc.elements):
            prev_e = doc.elements[i - 1] if i > 0 else None
            next_e = doc.elements[i + 1] if i < n - 1 else None

            feat_dict = cls.extract_element_features(
                elem=elem,
                index=i,
                total_elements=n,
                prev_elem=prev_e,
                next_elem=next_e,
                median_font_size=median_size,
            )
            rows.append([feat_dict[name] for name in FEATURE_NAMES])

        return np.array(rows, dtype=np.float32)
