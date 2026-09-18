"""NLP and linguistic feature extraction engine using NLTK."""

from pathlib import Path
import re
import string
from typing import Any, Dict, List, Optional, Sequence, Set
import numpy as np

import nltk

from app.core.nlp.schemas import NLPElementFeatures
from app.models.ast import BaseElement, CanonicalDocument


# Fallback English stopwords if NLTK corpus is absent
FALLBACK_STOPWORDS: Set[str] = {
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
}


class NLPFeatureExtractor:
    """Extracts structured linguistic, lexical, and positional features from document elements."""

    RE_CHAPTER = re.compile(r"\b(?:chapter|ch\.|part|book)\b", re.IGNORECASE)
    RE_AUTHOR = re.compile(
        r"\b(?:department|university|faculty|school|institute|laboratory|ph\.d|m\.d|dr\.|prof\.|author:|email:|@[\w\.\-]+\.)\b",
        re.IGNORECASE,
    )
    RE_REFERENCE = re.compile(r"\b(?:references?|bibliography|works cited|literature cited)\b", re.IGNORECASE)
    RE_ABSTRACT = re.compile(r"\b(?:abstract|executive summary)\b", re.IGNORECASE)
    RE_ACKNOWLEDGEMENT = re.compile(r"\b(?:acknowledgements?|acknowledgments?)\b", re.IGNORECASE)
    RE_CONCLUSION = re.compile(r"\b(?:conclusions?|concluding remarks)\b", re.IGNORECASE)
    RE_ROMAN = re.compile(r"\b[IVXLCDM]+\b")
    RE_NUMBER_PREFIX = re.compile(r"^\d+")
    RE_NUMBERING_MARKER = re.compile(r"^(?:\d+[\.\)]|[\*\-\•\–\—\◦\▪\▫\►\⁃]|\([0-9a-zA-Z]\))\s+")
    TITLE_CASE_MINOR_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "the", "to", "via"}

    def __init__(self) -> None:
        """Initializes NLTK resources with graceful fallback."""
        try:
            from nltk.corpus import stopwords
            self.stopwords: Set[str] = set(stopwords.words("english"))
        except Exception:
            self.stopwords = FALLBACK_STOPWORDS

    def tokenize_sentences(self, text: str) -> List[str]:
        """Tokenizes text into sentences using NLTK sent_tokenize with regex fallback."""
        if not text.strip():
            return []
        try:
            return nltk.sent_tokenize(text)
        except Exception:
            # Fallback regex sentence splitter
            splits = re.split(r"(?<=[.!?])\s+", text.strip())
            return [s for s in splits if s]

    def tokenize_words(self, text: str) -> List[str]:
        """Tokenizes text into word tokens using NLTK word_tokenize with regex fallback."""
        if not text.strip():
            return []
        try:
            tokens = nltk.word_tokenize(text)
            # Filter pure punctuation for word metrics
            return [t for t in tokens if any(c.isalnum() for c in t)]
        except Exception:
            return re.findall(r"\b\w+\b", text)

    def extract_element_features(
        self,
        elem: BaseElement,
        index: int,
        total_elements: int,
        prev_elem: Optional[BaseElement] = None,
        next_elem: Optional[BaseElement] = None,
        doc_median_font_size: float = 11.0,
    ) -> NLPElementFeatures:
        """Extracts complete NLP and linguistic features for a single document element."""
        text = elem.original_text.strip()
        text_length = len(text)

        # 1. Tokenization & Sentence analysis
        sentences = self.tokenize_sentences(text)
        sentence_count = max(1, len(sentences)) if text else 0

        words = self.tokenize_words(text)
        word_count = len(words)
        avg_sentence_length = float(word_count) / float(sentence_count) if sentence_count > 0 else 0.0

        total_word_chars = sum(len(w) for w in words)
        avg_word_length = float(total_word_chars) / float(word_count) if word_count > 0 else 0.0

        # 2. Capitalization analysis
        alpha_chars = [c for c in text if c.isalpha()]
        alpha_count = len(alpha_chars)
        upper_chars = sum(1 for c in alpha_chars if c.isupper())
        uppercase_ratio = float(upper_chars) / float(alpha_count) if alpha_count > 0 else 0.0

        is_all_caps = text.isupper() and word_count >= 1
        title_words = [word for word in re.findall(r"[A-Za-z][A-Za-z'-]*", text) if word]
        is_title_case = (
            len(title_words) > 1
            and all(
                word[0].isupper() if index == 0 or word.lower() not in self.TITLE_CASE_MINOR_WORDS else True
                for index, word in enumerate(title_words)
            )
            and any(word[0].isupper() for word in title_words)
        )

        # 3. Punctuation analysis
        ends_with_period = text.endswith(".")
        ends_with_colon = text.endswith(":")
        ends_with_question = text.endswith("?")

        punct_count = sum(1 for c in text if c in string.punctuation)
        punctuation_ratio = float(punct_count) / float(text_length) if text_length > 0 else 0.0

        # 4. Positional analysis
        paragraph_position = float(index) / max(1.0, float(total_elements - 1)) if total_elements > 1 else 0.0

        # 5. Surrounding context
        prev_word_count = len(self.tokenize_words(prev_elem.original_text)) if prev_elem else 0
        next_word_count = len(self.tokenize_words(next_elem.original_text)) if next_elem else 0
        is_isolated = bool(
            word_count < 20
            and (prev_word_count > 10 or next_word_count > 10)
            and (prev_word_count > word_count * 2 or next_word_count > word_count * 2)
        )

        # 6. Keyword patterns
        contains_chapter_keyword = bool(self.RE_CHAPTER.search(text))
        contains_author_keyword = bool(self.RE_AUTHOR.search(text))
        contains_reference_keyword = bool(self.RE_REFERENCE.search(text))
        contains_abstract_keyword = bool(self.RE_ABSTRACT.search(text))
        contains_acknowledgement_keyword = bool(self.RE_ACKNOWLEDGEMENT.search(text))
        contains_conclusion_keyword = bool(self.RE_CONCLUSION.search(text))

        # 7. Linguistic features
        stopword_count = sum(1 for w in words if w.lower() in self.stopwords)
        stopword_ratio = float(stopword_count) / float(word_count) if word_count > 0 else 0.0

        unique_words = set(w.lower() for w in words)
        lexical_diversity = float(len(unique_words)) / float(word_count) if word_count > 0 else 0.0

        # 8. Paragraph style & typography
        style_name = elem.original_style
        style_lower = (style_name or "").lower()
        is_default_style = style_lower in ("normal", "body text", "")

        is_bold = any(r.bold is True for r in elem.runs) if elem.runs else False
        is_italic = any(r.italic is True for r in elem.runs) if elem.runs else False

        font_sizes = [r.font_size_pt for r in elem.runs if r.font_size_pt is not None]
        font_size_pt = max(font_sizes) if font_sizes else None
        is_larger_than_surroundings = bool(font_size_pt and font_size_pt >= (doc_median_font_size + 1.5))

        # 9. Numbering patterns
        starts_with_number = bool(self.RE_NUMBER_PREFIX.match(text))
        has_numbering_marker = bool(
            self.RE_NUMBERING_MARKER.match(text)
            or getattr(elem, "list_info", None) is not None
        )
        contains_roman_numeral = bool(self.RE_ROMAN.search(text))

        return NLPElementFeatures(
            text_length=text_length,
            word_count=word_count,
            is_all_caps=is_all_caps,
            starts_with_number=starts_with_number,
            contains_chapter_keyword=contains_chapter_keyword,
            paragraph_position=paragraph_position,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            avg_word_length=avg_word_length,
            is_title_case=is_title_case,
            uppercase_ratio=uppercase_ratio,
            ends_with_period=ends_with_period,
            ends_with_colon=ends_with_colon,
            ends_with_question=ends_with_question,
            punctuation_count=punct_count,
            punctuation_ratio=punctuation_ratio,
            prev_paragraph_word_count=prev_word_count,
            next_paragraph_word_count=next_word_count,
            is_isolated=is_isolated,
            contains_author_keyword=contains_author_keyword,
            contains_reference_keyword=contains_reference_keyword,
            contains_abstract_keyword=contains_abstract_keyword,
            contains_acknowledgement_keyword=contains_acknowledgement_keyword,
            contains_conclusion_keyword=contains_conclusion_keyword,
            stopword_ratio=stopword_ratio,
            lexical_diversity=lexical_diversity,
            original_style=style_name,
            is_default_style=is_default_style,
            font_size_pt=font_size_pt,
            is_bold=is_bold,
            is_italic=is_italic,
            is_larger_than_surroundings=is_larger_than_surroundings,
            has_numbering_marker=has_numbering_marker,
            contains_roman_numeral=contains_roman_numeral,
        )

    def extract_document_features(self, doc: CanonicalDocument) -> List[NLPElementFeatures]:
        """Extracts NLPElementFeatures for every element in a CanonicalDocument."""
        elements = doc.elements
        n = len(elements)
        if n == 0:
            return []

        # Calculate median font size
        sizes = [
            r.font_size_pt
            for elem in elements
            for r in elem.runs
            if r.font_size_pt is not None and r.font_size_pt > 0
        ]
        median_font = float(np.median(sizes)) if sizes else 11.0

        features_list: List[NLPElementFeatures] = []
        for i, elem in enumerate(elements):
            prev_e = elements[i - 1] if i > 0 else None
            next_e = elements[i + 1] if i < n - 1 else None

            feat = self.extract_element_features(
                elem=elem,
                index=i,
                total_elements=n,
                prev_elem=prev_e,
                next_elem=next_e,
                doc_median_font_size=median_font,
            )
            features_list.append(feat)

        return features_list
