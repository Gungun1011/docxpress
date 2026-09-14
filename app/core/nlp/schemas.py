"""NLP feature schemas and data structures for document structure detection."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class NLPElementFeatures:
    """Structured NLP and linguistic features for a document element.
    
    Attributes:
        text_length: Total character count of the trimmed text.
        word_count: Number of extracted word tokens.
        is_all_caps: True if text is entirely uppercase.
        starts_with_number: True if text begins with numeric digits.
        contains_chapter_keyword: True if text contains chapter keywords.
        paragraph_position: Relative document position (0.0 to 1.0).
        sentence_count: Number of sentences identified via NLTK sentence tokenization.
        avg_sentence_length: Average word count per sentence.
        avg_word_length: Average character count per word token.
        is_title_case: True if words follow title capitalization.
        uppercase_ratio: Proportion of alphabetical characters that are uppercase.
        ends_with_period: True if terminal punctuation is a period.
        ends_with_colon: True if terminal punctuation is a colon.
        ends_with_question: True if terminal punctuation is a question mark.
        punctuation_count: Total count of punctuation marks.
        punctuation_ratio: Proportion of characters that are punctuation.
        prev_paragraph_word_count: Word count of the immediately preceding element.
        next_paragraph_word_count: Word count of the immediately following element.
        is_isolated: True if paragraph is surrounded by significantly longer blocks.
        contains_author_keyword: True if text contains author/affiliation keywords.
        contains_reference_keyword: True if text contains bibliography/reference keywords.
        contains_abstract_keyword: True if text contains abstract/summary keywords.
        contains_acknowledgement_keyword: True if text contains acknowledgement keywords.
        contains_conclusion_keyword: True if text contains conclusion keywords.
        stopword_ratio: Ratio of tokens that are common function/stopwords.
        lexical_diversity: Ratio of unique words to total words.
        original_style: Native Word style name if present.
        is_default_style: True if style is 'Normal' or default body style.
        font_size_pt: Explicit font size in points if present.
        is_bold: True if paragraph contains bold runs.
        is_italic: True if paragraph contains italic runs.
        is_larger_than_surroundings: True if font size exceeds median document font.
        has_numbering_marker: True if paragraph has numbering definition or bullet.
        contains_roman_numeral: True if text contains valid Roman numerals.
    """
    text_length: int
    word_count: int
    is_all_caps: bool
    starts_with_number: bool
    contains_chapter_keyword: bool
    paragraph_position: float
    sentence_count: int = 1
    avg_sentence_length: float = 0.0
    avg_word_length: float = 0.0
    is_title_case: bool = False
    uppercase_ratio: float = 0.0
    ends_with_period: bool = False
    ends_with_colon: bool = False
    ends_with_question: bool = False
    punctuation_count: int = 0
    punctuation_ratio: float = 0.0
    prev_paragraph_word_count: int = 0
    next_paragraph_word_count: int = 0
    is_isolated: bool = False
    contains_author_keyword: bool = False
    contains_reference_keyword: bool = False
    contains_abstract_keyword: bool = False
    contains_acknowledgement_keyword: bool = False
    contains_conclusion_keyword: bool = False
    stopword_ratio: float = 0.0
    lexical_diversity: float = 0.0
    original_style: Optional[str] = None
    is_default_style: bool = True
    font_size_pt: Optional[float] = None
    is_bold: bool = False
    is_italic: bool = False
    is_larger_than_surroundings: bool = False
    has_numbering_marker: bool = False
    contains_roman_numeral: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes features into the required dictionary format."""
        return {
            "text_length": self.text_length,
            "word_count": self.word_count,
            "is_all_caps": self.is_all_caps,
            "starts_with_number": self.starts_with_number,
            "contains_chapter_keyword": self.contains_chapter_keyword,
            "paragraph_position": round(self.paragraph_position, 4),
            "sentence_count": self.sentence_count,
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "avg_word_length": round(self.avg_word_length, 2),
            "is_title_case": self.is_title_case,
            "uppercase_ratio": round(self.uppercase_ratio, 4),
            "ends_with_period": self.ends_with_period,
            "ends_with_colon": self.ends_with_colon,
            "ends_with_question": self.ends_with_question,
            "punctuation_count": self.punctuation_count,
            "punctuation_ratio": round(self.punctuation_ratio, 4),
            "prev_paragraph_word_count": self.prev_paragraph_word_count,
            "next_paragraph_word_count": self.next_paragraph_word_count,
            "is_isolated": self.is_isolated,
            "contains_author_keyword": self.contains_author_keyword,
            "contains_reference_keyword": self.contains_reference_keyword,
            "contains_abstract_keyword": self.contains_abstract_keyword,
            "contains_acknowledgement_keyword": self.contains_acknowledgement_keyword,
            "contains_conclusion_keyword": self.contains_conclusion_keyword,
            "stopword_ratio": round(self.stopword_ratio, 4),
            "lexical_diversity": round(self.lexical_diversity, 4),
            "original_style": self.original_style,
            "is_default_style": self.is_default_style,
            "font_size_pt": self.font_size_pt,
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "is_larger_than_surroundings": self.is_larger_than_surroundings,
            "has_numbering_marker": self.has_numbering_marker,
            "contains_roman_numeral": self.contains_roman_numeral,
        }

    def to_core_dict(self) -> Dict[str, Any]:
        """Returns the concise core dictionary matching the prompt example."""
        return {
            "text_length": self.text_length,
            "word_count": self.word_count,
            "is_all_caps": self.is_all_caps,
            "starts_with_number": self.starts_with_number,
            "contains_chapter_keyword": self.contains_chapter_keyword,
            "paragraph_position": round(self.paragraph_position, 2),
        }
