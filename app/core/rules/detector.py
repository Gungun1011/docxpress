"""Robust Regex-Based Document Structure Detector for DocXpress.

Combines regular expression pattern matching with typography, positional cues,
and structural document context to identify 11+ element classes.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.core.rules.config import RuleEngineConfig
from app.core.rules.patterns import (
    RE_ABSTRACT,
    RE_ACKNOWLEDGEMENTS,
    RE_AUTHOR_AFFILIATION,
    RE_CHAPTER_DIGIT,
    RE_CHAPTER_ROMAN,
    RE_CHAPTER_STANDALONE,
    RE_CHAPTER_WORD,
    RE_CONCLUSION,
    RE_FIGURE_CAPTION,
    RE_FIGURE_STANDALONE,
    RE_HEADING_L1,
    RE_HEADING_L2,
    RE_HEADING_L3,
    RE_LIST_BULLET,
    RE_LIST_LETTERED,
    RE_LIST_NUMBERED,
    RE_REFERENCES_HEADER,
    RE_REFERENCE_ENTRY,
    RE_TABLE_CAPTION,
    RE_TABLE_STANDALONE,
)
from app.core.rules.schemas import DetectionResult
from app.models.ast import (
    BaseElement,
    CanonicalDocument,
    ElementType,
    FigureElement,
    ParagraphElement,
    TableElement,
)


class RegexStructureDetector:
    """Configurable rule-based document structure detector."""

    def __init__(self, config: Optional[RuleEngineConfig] = None) -> None:
        """Initializes detector with configuration."""
        self.config = config or RuleEngineConfig()

    def detect_document(self, doc: CanonicalDocument) -> List[DetectionResult]:
        """Detects structure for every element in a CanonicalDocument.
        
        Does NOT modify the document text or elements.
        
        Args:
            doc: The CanonicalDocument AST.
            
        Returns:
            List of DetectionResult objects corresponding to each element.
        """
        results: List[DetectionResult] = []
        n = len(doc.elements)
        if n == 0:
            return results

        for i, elem in enumerate(doc.elements):
            rel_pos = float(i) / max(1.0, float(n - 1)) if n > 1 else 0.0
            prev_e = doc.elements[i - 1] if i > 0 else None
            next_e = doc.elements[i + 1] if i < n - 1 else None

            res = self.evaluate_element(
                elem=elem,
                doc_position=rel_pos,
                total_elements=n,
                index=i,
                prev_elem=prev_e,
                next_elem=next_e,
            )
            results.append(res)

        return results

    def evaluate_element(
        self,
        elem: BaseElement,
        doc_position: float,
        total_elements: int,
        index: int = 0,
        prev_elem: Optional[BaseElement] = None,
        next_elem: Optional[BaseElement] = None,
    ) -> DetectionResult:
        """Evaluates rules across text patterns, typography, and positional signals.
        
        Args:
            elem: Canonical document element.
            doc_position: Relative document position (0.0 to 1.0).
            total_elements: Total element count.
            index: Sequential 0-based index.
            prev_elem: Preceding element in document sequence.
            next_elem: Following element in document sequence.
            
        Returns:
            DetectionResult with element_type, confidence, reason, pattern_matched.
        """
        text = elem.original_text.strip()
        style_lower = (elem.original_style or "").lower()
        words = text.split()
        word_count = len(words)

        # Typography signals
        is_bold = any(r.bold is True for r in elem.runs) if elem.runs else False
        is_italic = any(r.italic is True for r in elem.runs) if elem.runs else False
        font_sizes = [r.font_size_pt for r in elem.runs if r.font_size_pt is not None]
        max_font_size = max(font_sizes) if font_sizes else 11.0

        # -------------------------------------------------------------
        # 1. Structural Primitives (TableElement & FigureElement)
        # -------------------------------------------------------------
        if isinstance(elem, TableElement):
            conf = self.config.get_confidence("table_primitive", 1.0)
            return DetectionResult(
                element_type="table",
                confidence=conf,
                reason="native table grid structure",
                pattern_matched=f"{elem.rows_count}x{elem.cols_count} table",
            )

        if isinstance(elem, FigureElement) or (
            isinstance(elem, ParagraphElement) and elem.contains_drawing and not text
        ):
            conf = self.config.get_confidence("figure_primitive", 1.0)
            return DetectionResult(
                element_type="figure",
                confidence=conf,
                reason="native drawing or inline graphic object",
                pattern_matched=getattr(elem, "image_id", "drawing"),
            )

        # Empty spacer paragraph
        if not text:
            return DetectionResult(
                element_type="body_paragraph",
                confidence=1.0,
                reason="empty paragraph break",
                pattern_matched="",
            )

        # -------------------------------------------------------------
        # 2. User-Configured Custom Patterns
        # -------------------------------------------------------------
        for custom_type, pattern_list in self.config.custom_patterns.items():
            for pat_str in pattern_list:
                custom_re = re.compile(pat_str, re.IGNORECASE)
                m = custom_re.search(text)
                if m:
                    return DetectionResult(
                        element_type=custom_type,
                        confidence=self.config.get_confidence("custom_pattern", 0.99),
                        reason=f"matched custom user pattern '{pat_str}'",
                        pattern_matched=m.group(0),
                    )

        # -------------------------------------------------------------
        # 3. Chapter Headings (Chapter 1, Chapter 1:, CHAPTER ONE, CHAPTER I)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("chapter") and word_count <= 25:
            # 3a. "Chapter 1", "Chapter 1:"
            m_digit = RE_CHAPTER_DIGIT.match(text)
            if m_digit:
                conf = self.config.get_confidence("chapter_digit", 0.98)
                if is_bold or max_font_size >= 14.0:
                    conf = min(1.0, conf + 0.01)
                return DetectionResult(
                    element_type="chapter_heading",
                    confidence=conf,
                    reason="matched chapter regex with numeric digit",
                    pattern_matched=f"Chapter {m_digit.group(1)}",
                )

            # 3b. "CHAPTER ONE", "Chapter Two"
            m_word = RE_CHAPTER_WORD.match(text)
            if m_word:
                conf = self.config.get_confidence("chapter_word", 0.98)
                if text.isupper():
                    conf = min(1.0, conf + 0.01)
                return DetectionResult(
                    element_type="chapter_heading",
                    confidence=conf,
                    reason="matched chapter regex with spelled-out number word",
                    pattern_matched=f"CHAPTER {m_word.group(1).upper()}",
                )

            # 3c. "CHAPTER I", "Chapter IV"
            m_roman = RE_CHAPTER_ROMAN.match(text)
            if m_roman:
                conf = self.config.get_confidence("chapter_roman", 0.98)
                return DetectionResult(
                    element_type="chapter_heading",
                    confidence=conf,
                    reason="matched chapter regex with Roman numeral",
                    pattern_matched=f"CHAPTER {m_roman.group(1).upper()}",
                )

            # 3d. Standalone "Chapter 1"
            m_stand = RE_CHAPTER_STANDALONE.match(text)
            if m_stand:
                return DetectionResult(
                    element_type="chapter_heading",
                    confidence=0.99,
                    reason="matched standalone chapter header",
                    pattern_matched=m_stand.group(0),
                )

        # -------------------------------------------------------------
        # 4. Special Section Headings (Abstract, Acknowledgements, Conclusion)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("special_section") and word_count <= 10:
            if doc_position <= self.config.front_matter_threshold:
                m_abs = RE_ABSTRACT.match(text)
                if m_abs:
                    return DetectionResult(
                        element_type="abstract",
                        confidence=0.98,
                        reason="matched abstract section heading in front-matter",
                        pattern_matched=m_abs.group(0),
                    )

            m_ack = RE_ACKNOWLEDGEMENTS.match(text)
            if m_ack:
                return DetectionResult(
                    element_type="acknowledgements",
                    confidence=0.98,
                    reason="matched acknowledgements section heading",
                    pattern_matched=m_ack.group(0),
                )

            m_conc = RE_CONCLUSION.match(text)
            if m_conc:
                return DetectionResult(
                    element_type="conclusion",
                    confidence=0.97,
                    reason="matched conclusion section heading",
                    pattern_matched=m_conc.group(0),
                )

        # -------------------------------------------------------------
        # 5. References & Bibliography (Header & Entries)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("reference"):
            if RE_REFERENCES_HEADER.match(text) and doc_position >= self.config.front_matter_threshold:
                return DetectionResult(
                    element_type="references",
                    confidence=0.99,
                    reason="matched references/bibliography section header",
                    pattern_matched=text,
                )

            if doc_position >= self.config.back_matter_threshold:
                m_ref_entry = RE_REFERENCE_ENTRY.match(text)
                if m_ref_entry:
                    return DetectionResult(
                        element_type="reference_entry",
                        confidence=0.97,
                        reason="matched academic citation entry in back-matter",
                        pattern_matched=m_ref_entry.group(0)[:25],
                    )

        # -------------------------------------------------------------
        # 6. Figures & Captions (Figure 1, Figure 1:, Fig. 1)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("figure"):
            m_fig = RE_FIGURE_CAPTION.match(text)
            if m_fig or RE_FIGURE_STANDALONE.match(text):
                fig_num = m_fig.group(1) if m_fig else "1"
                prefix = f"Figure {fig_num}" if not text.lower().startswith("fig.") else f"Fig. {fig_num}"
                return DetectionResult(
                    element_type="figure_caption",
                    confidence=0.98,
                    reason="matched figure caption pattern",
                    pattern_matched=prefix,
                )

        # -------------------------------------------------------------
        # 7. Tables & Captions (Table 1, Table 1:)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("table"):
            m_tbl = RE_TABLE_CAPTION.match(text)
            if m_tbl or RE_TABLE_STANDALONE.match(text):
                tbl_num = m_tbl.group(1) if m_tbl else "1"
                return DetectionResult(
                    element_type="table_caption",
                    confidence=0.98,
                    reason="matched table caption pattern",
                    pattern_matched=f"Table {tbl_num}",
                )

        # -------------------------------------------------------------
        # 8. Headings (1 Introduction, 1.1 Background, 1.2.1 Subtopic)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("heading") and word_count <= 20 and not text.endswith("."):
            # 8a. Level 3 Subheading (1.2.1 Subtopic)
            m_l3 = RE_HEADING_L3.match(text)
            if m_l3:
                conf = self.config.get_confidence("heading_l3", 0.96)
                if is_bold:
                    conf = min(1.0, conf + 0.02)
                return DetectionResult(
                    element_type="heading_3",
                    confidence=conf,
                    reason="matched decimal level-3 subheading regex",
                    pattern_matched=m_l3.group(1),
                )

            # 8b. Level 2 Heading (1.1 Background)
            m_l2 = RE_HEADING_L2.match(text)
            if m_l2:
                conf = self.config.get_confidence("heading_l2", 0.96)
                if is_bold:
                    conf = min(1.0, conf + 0.02)
                return DetectionResult(
                    element_type="heading_2",
                    confidence=conf,
                    reason="matched decimal level-2 heading regex",
                    pattern_matched=m_l2.group(1),
                )

            # 8c. Level 1 Heading (1 Introduction)
            m_l1 = RE_HEADING_L1.match(text)
            if m_l1:
                conf = self.config.get_confidence("heading_l1", 0.95)
                if is_bold:
                    conf = min(1.0, conf + 0.02)
                return DetectionResult(
                    element_type="heading_1",
                    confidence=conf,
                    reason="matched numbered level-1 heading regex",
                    pattern_matched=m_l1.group(1),
                )

        # -------------------------------------------------------------
        # 9. Lists (1., 2., a., b., -, •, *)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("list"):
            # Native list numbering metadata
            if isinstance(elem, ParagraphElement) and elem.list_info is not None:
                return DetectionResult(
                    element_type="list_item",
                    confidence=0.99,
                    reason="native OpenXML numbering metadata (numPr)",
                    pattern_matched="numPr",
                )

            # Bullet items (-, •, *)
            m_bullet = RE_LIST_BULLET.match(text)
            if m_bullet:
                bullet_char = m_bullet.group(1)
                return DetectionResult(
                    element_type="list_item",
                    confidence=0.97,
                    reason="matched bullet list marker",
                    pattern_matched=bullet_char,
                )

            # Numbered items (1., 2., 3.)
            m_num = RE_LIST_NUMBERED.match(text)
            if m_num:
                num_marker = f"{m_num.group(1) or m_num.group(2)}."
                return DetectionResult(
                    element_type="list_item",
                    confidence=0.96,
                    reason="matched sequential numbered list prefix",
                    pattern_matched=num_marker,
                )

            # Lettered items (a., b.)
            m_let = RE_LIST_LETTERED.match(text)
            if m_let:
                let_marker = f"{m_let.group(1) or m_let.group(2)}."
                return DetectionResult(
                    element_type="list_item",
                    confidence=0.95,
                    reason="matched lettered list prefix",
                    pattern_matched=let_marker,
                )

        # -------------------------------------------------------------
        # 10. Front Matter Sections (Title, Author, Subtitle)
        # -------------------------------------------------------------
        if self.config.is_category_enabled("front_matter") and doc_position <= self.config.front_matter_threshold:
            # 10a. Author affiliations or credentials
            if RE_AUTHOR_AFFILIATION.search(text) or style_lower in ("author", "subtitle"):
                return DetectionResult(
                    element_type="author",
                    confidence=0.96,
                    reason="matched academic affiliation or author credential in front-matter",
                    pattern_matched=RE_AUTHOR_AFFILIATION.search(text).group(0) if RE_AUTHOR_AFFILIATION.search(text) else "Author",
                )

            # 10b. Title (typically the first substantial element)
            if style_lower == "title" or (index == 0 and word_count <= 15 and not text.endswith(".")):
                conf = 0.95
                if is_bold or max_font_size >= 16.0 or style_lower == "title":
                    conf = 0.98
                return DetectionResult(
                    element_type="title",
                    confidence=conf,
                    reason="front-matter title heuristic (prominence and position)",
                    pattern_matched="Title",
                )

            # 10c. Subtitle (immediately follows title)
            if index == 1 and word_count <= 15 and not text.endswith(".") and not is_bold:
                return DetectionResult(
                    element_type="subtitle",
                    confidence=0.90,
                    reason="front-matter block following title",
                    pattern_matched="Subtitle",
                )

        # -------------------------------------------------------------
        # 11. Word Style Fallbacks
        # -------------------------------------------------------------
        if style_lower:
            if "heading 1" in style_lower:
                return DetectionResult(
                    element_type="heading_1",
                    confidence=0.92,
                    reason=f"Word style indicates Heading 1 ('{elem.original_style}')",
                    pattern_matched=elem.original_style,
                )
            if "heading 2" in style_lower:
                return DetectionResult(
                    element_type="heading_2",
                    confidence=0.92,
                    reason=f"Word style indicates Heading 2 ('{elem.original_style}')",
                    pattern_matched=elem.original_style,
                )
            if "heading 3" in style_lower:
                return DetectionResult(
                    element_type="heading_3",
                    confidence=0.92,
                    reason=f"Word style indicates Heading 3 ('{elem.original_style}')",
                    pattern_matched=elem.original_style,
                )
            if "caption" in style_lower:
                return DetectionResult(
                    element_type="caption",
                    confidence=0.92,
                    reason=f"Word style indicates Caption ('{elem.original_style}')",
                    pattern_matched=elem.original_style,
                )

        # -------------------------------------------------------------
        # 12. Default Running Body Paragraph
        # -------------------------------------------------------------
        return DetectionResult(
            element_type="body_paragraph",
            confidence=0.88,
            reason="standard narrative body paragraph",
            pattern_matched=None,
        )
