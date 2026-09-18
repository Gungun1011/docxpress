"""Deterministic high-precision regex and structural rules engine for DocXpress.

Evaluates structural heuristics that can identify elements with near-certainty
(e.g., table objects, drawing containers, explicit chapter headers, standard citations).
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional

from app.models.ast import (
    BaseElement,
    ElementType,
    FigureElement,
    ParagraphElement,
    TableElement,
)


@dataclass(frozen=True)
class RuleMatch:
    """Result of a deterministic rule evaluation."""
    matched: bool
    element_type: ElementType
    confidence: float
    rule_name: str
    reason: str


class RegexRuleEngine:
    """Evaluates high-precision deterministic rules against document elements."""

    # Pre-compiled regular expressions
    RE_CHAPTER = re.compile(
        r"^(chapter|ch\.|part|book|section)\s+([0-9ivxlcdm]+|[a-z]+)\b[:\s\-—]*(.*)$",
        re.IGNORECASE,
    )
    RE_FRONT_MATTER_HEADERS = re.compile(
        r"^(prologue|epilogue|preface|foreword|acknowledgments?|abstract|introduction)\s*$",
        re.IGNORECASE,
    )
    RE_CAPTION = re.compile(
        r"^(figure|fig\.|table|tbl\.|plate|chart|graph|illustration)\s+\d+[\.:\s\-—]+",
        re.IGNORECASE,
    )
    RE_NUMBERED_HEADING = re.compile(
        r"^(\d+(\.\d+)*)\.?\s+([A-Z][\w\s,–—\-\?]+)$"
    )
    RE_NUMBERED_SUBHEADING = re.compile(
        r"^(\d+\.\d+\.\d+(\.\d+)*)\.?\s+([A-Z][\w\s,–—\-\?]+)$"
    )
    RE_BULLET_LIST = re.compile(
        r"^[\*\-\•\–\—\◦\▪\▫\►\⁃]\s+"
    )
    RE_NUMBERED_LIST = re.compile(
        r"^(\d+[\.\)]|\([0-9]+\)|[a-zA-Z][\.\)]|\([a-zA-Z]\))\s+"
    )
    RE_SHORT_TITLE_HEADING = re.compile(r"^[A-Z][\w'-]*(?:\s+[A-Za-z][\w'-]*){1,5}$")
    RE_REFERENCE_NUMERIC = re.compile(
        r"^\[\d+\]\s+[A-Z]"
    )
    RE_REFERENCE_AUTHOR_YEAR = re.compile(
        r"^[A-Z][a-zA-Z\s\-]+,\s+[A-Z]\.\s*(.*?\b(19|20)\d{2}\b)"
    )
    RE_REFERENCES_HEADER = re.compile(
        r"^(references|bibliography|works cited|literature cited)\s*$",
        re.IGNORECASE,
    )
    RE_AUTHOR_AFFILIATION = re.compile(
        r"\b(department of|university|faculty of|institute of|laboratory|dr\.|prof\.|ph\.d|m\.d|email:|@[\w\.\-]+\.(edu|org|ac\.uk|gov|com))\b",
        re.IGNORECASE,
    )

    @classmethod
    def evaluate(
        cls,
        elem: BaseElement,
        doc_position: float,
        total_elements: int,
    ) -> Optional[RuleMatch]:
        """Evaluates deterministic rules for an element.
        
        Args:
            elem: The document element to inspect.
            doc_position: Relative position in document from 0.0 (start) to 1.0 (end).
            total_elements: Total number of elements in the document.
            
        Returns:
            RuleMatch if a deterministic rule fired with high confidence, else None.
        """
        text = elem.original_text.strip()
        style_lower = (elem.original_style or "").lower()

        # Rule 1: Tabular data element
        if isinstance(elem, TableElement):
            return RuleMatch(
                matched=True,
                element_type=ElementType.TABLE,
                confidence=1.0,
                rule_name="rule_table_element",
                reason="Native TableElement structure",
            )

        # Rule 2: Standalone figure or drawing
        if isinstance(elem, FigureElement) or (
            isinstance(elem, ParagraphElement)
            and elem.contains_drawing
            and not text
        ):
            return RuleMatch(
                matched=True,
                element_type=ElementType.FIGURE,
                confidence=1.0,
                rule_name="rule_figure_element",
                reason="Native FigureElement or pure drawing block",
            )

        # Rule 3: Native List numbering metadata or bullet style
        if isinstance(elem, ParagraphElement) and elem.list_info is not None:
            return RuleMatch(
                matched=True,
                element_type=ElementType.LIST,
                confidence=0.99,
                rule_name="rule_native_list_metadata",
                reason=f"Word numbering numPr present (num_id={elem.list_info.num_id}, ilvl={elem.list_info.ilvl})",
            )

        if "bullet" in style_lower or "list" in style_lower:
            return RuleMatch(
                matched=True,
                element_type=ElementType.LIST,
                confidence=0.97,
                rule_name="rule_list_style",
                reason=f"Word style indicates list: '{elem.original_style}'",
            )

        # Rule 4: Figure or Table Caption
        if cls.RE_CAPTION.match(text) or "caption" in style_lower:
            return RuleMatch(
                matched=True,
                element_type=ElementType.CAPTION,
                confidence=0.98,
                rule_name="rule_caption_pattern",
                reason=f"Matches caption prefix or style '{elem.original_style}'",
            )

        # Rule 5: Explicit Chapter Heading
        if cls.RE_CHAPTER.match(text):
            return RuleMatch(
                matched=True,
                element_type=ElementType.CHAPTER,
                confidence=0.99,
                rule_name="rule_chapter_prefix",
                reason="Matches explicit chapter marker pattern",
            )

        if doc_position < 0.25 and cls.RE_FRONT_MATTER_HEADERS.match(text):
            return RuleMatch(
                matched=True,
                element_type=ElementType.CHAPTER,
                confidence=0.95,
                rule_name="rule_front_matter_chapter",
                reason="Matches standalone front-matter chapter/section title",
            )

        # Rule 6: References section header in back-matter
        if cls.RE_REFERENCES_HEADER.match(text) and doc_position > 0.50:
            return RuleMatch(
                matched=True,
                element_type=ElementType.HEADING,
                confidence=0.98,
                rule_name="rule_references_header",
                reason="Matches 'References' or 'Bibliography' section header in back-matter",
            )

        # Rule 7: Citation and bibliography entries in back-matter (evaluated before generic lists)
        re_reference_numbered = re.compile(
            r"^(\[\d+\]|\d+[\.\)])\s+[A-Z][a-zA-Z\s\-\.]+,?\s+.*?\b(18|19|20)\d{2}\b"
        )
        if doc_position > 0.50 and (
            re_reference_numbered.match(text)
            or cls.RE_REFERENCE_NUMERIC.match(text)
            or cls.RE_REFERENCE_AUTHOR_YEAR.match(text)
        ):
            return RuleMatch(
                matched=True,
                element_type=ElementType.REFERENCE,
                confidence=0.97,
                rule_name="rule_reference_entry_pattern",
                reason="Matches citation entry format [N] or Author (Year) in back-matter",
            )

        # Rule 8: Multi-level numbered subheadings (e.g. 1.2.3 Model Architecture)
        if cls.RE_NUMBERED_SUBHEADING.match(text) and len(text.split()) < 20 and not text.endswith("."):
            return RuleMatch(
                matched=True,
                element_type=ElementType.SUBHEADING,
                confidence=0.97,
                rule_name="rule_numbered_subheading",
                reason="Matches hierarchical decimal subheading pattern (X.Y.Z)",
            )

        # Rule 9: Single-level numbered heading (e.g. 1. Introduction or 1.1 Model Architecture)
        if cls.RE_NUMBERED_HEADING.match(text) and len(text.split()) < 15 and not text.endswith("."):
            match = cls.RE_NUMBERED_HEADING.match(text)
            assert match is not None
            num_prefix = match.group(1)
            target = ElementType.SUBHEADING if "." in num_prefix else ElementType.HEADING
            return RuleMatch(
                matched=True,
                element_type=target,
                confidence=0.96,
                rule_name="rule_numbered_heading",
                reason=f"Matches numbered heading pattern ({num_prefix})",
            )

        # Rule 10: Bullet or Numbered List Regex
        if cls.RE_BULLET_LIST.match(text) or cls.RE_NUMBERED_LIST.match(text):
            # Only if text is relatively concise or multi-line list
            if len(text.split()) < 80:
                return RuleMatch(
                    matched=True,
                    element_type=ElementType.LIST,
                    confidence=0.96,
                    rule_name="rule_list_regex_marker",
                    reason="Starts with bullet character or numbered list prefix",
                )

        # Short title-case labels are common unstyled headings. This is deliberately
        # restricted to non-sentence text so ordinary list items remain lists/body.
        if (
            doc_position >= 0.10
            and
            cls.RE_SHORT_TITLE_HEADING.match(text)
            and not text.endswith((".", ":", "?", "!"))
            and len(text.split()) <= 6
        ):
            return RuleMatch(
                matched=True,
                element_type=ElementType.HEADING,
                confidence=0.93,
                rule_name="rule_short_title_heading",
                reason="Short title-case label without list or sentence punctuation",
            )

        # Rule 10: Title and Author in Front-Matter
        if doc_position < 0.10:
            if style_lower == "title" or (doc_position == 0.0 and len(text.split()) <= 15 and not text.endswith(".")):
                return RuleMatch(
                    matched=True,
                    element_type=ElementType.TITLE,
                    confidence=0.95,
                    rule_name="rule_front_matter_title",
                    reason="First block in front-matter with title characteristics",
                )

            if cls.RE_AUTHOR_AFFILIATION.search(text) or style_lower in ("author", "subtitle"):
                return RuleMatch(
                    matched=True,
                    element_type=ElementType.AUTHOR,
                    confidence=0.96,
                    rule_name="rule_author_affiliation",
                    reason="Contains academic affiliation, email, or author credentials in front-matter",
                )

        return None
