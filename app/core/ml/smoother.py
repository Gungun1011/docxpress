"""Contextual sequence smoother and Markov transition constraints for DocXpress.

Enforces publishing structural grammar rules across adjacent element predictions
to eliminate illegal or nonsensical sequence transitions.
"""

from typing import List, Sequence, Tuple
from app.models.ast import BaseElement, ElementType, FigureElement


class ContextualSmoother:
    """Applies sequential transition rules across element classification streams."""

    @classmethod
    def smooth_sequence(
        cls,
        elements: Sequence[BaseElement],
        predicted_types: List[ElementType],
        confidences: List[float],
    ) -> Tuple[List[ElementType], List[float], List[str]]:
        """Applies contextual smoothing across the document stream.
        
        Args:
            elements: The ordered list of canonical AST elements.
            predicted_types: Initial predictions from rules/ML.
            confidences: Confidence scores corresponding to predictions.
            
        Returns:
            Tuple of (smoothed_types, smoothed_confidences, adjustment_reasons).
        """
        n = len(elements)
        if n == 0:
            return [], [], []

        smoothed = list(predicted_types)
        smoothed_conf = list(confidences)
        reasons: List[str] = ["initial_prediction"] * n

        has_seen_chapter = False
        has_seen_heading = False
        has_seen_references_header = False

        for i in range(n):
            elem = elements[i]
            cur_type = smoothed[i]
            rel_pos = float(i) / max(1.0, float(n - 1)) if n > 1 else 0.0

            # Track global structural headers
            if cur_type == ElementType.CHAPTER:
                has_seen_chapter = True
            elif cur_type == ElementType.HEADING:
                has_seen_heading = True
                if "reference" in elem.original_text.lower() or "bibliography" in elem.original_text.lower():
                    if rel_pos > 0.50:
                        has_seen_references_header = True

            # Constraint 1: TITLE can only exist in front matter (rel_pos < 0.15)
            if cur_type == ElementType.TITLE and rel_pos >= 0.15:
                # Reassign to HEADING if short, else PARAGRAPH
                if len(elem.original_text.split()) < 15:
                    smoothed[i] = ElementType.HEADING
                    smoothed_conf[i] = 0.85
                    reasons[i] = "smoothed_title_in_body_demoted_to_heading"
                else:
                    smoothed[i] = ElementType.PARAGRAPH
                    smoothed_conf[i] = 0.90
                    reasons[i] = "smoothed_title_in_body_demoted_to_paragraph"

            # Constraint 2: AUTHOR details can only exist in front matter (rel_pos < 0.15)
            if cur_type == ElementType.AUTHOR and rel_pos >= 0.15:
                smoothed[i] = ElementType.PARAGRAPH
                smoothed_conf[i] = 0.85
                reasons[i] = "smoothed_author_in_body_demoted_to_paragraph"

            # Constraint 3: Caption boost immediately following FIGURE or TABLE
            if i > 0:
                prev_type = smoothed[i - 1]
                if prev_type in (ElementType.FIGURE, ElementType.TABLE):
                    text_clean = elem.original_text.strip()
                    text_lower = text_clean.lower()
                    if text_clean:  # Must have actual text
                        if (
                            text_lower.startswith(("fig", "table", "tbl", "illustration", "source:", "note:"))
                            or (len(text_clean.split()) < 35 and any(cue in text_lower for cue in ["figure", "fig", "table", "tbl", "shown", "diagram", "chart", "state transition"]))
                        ):
                            if cur_type != ElementType.CAPTION and not text_lower.startswith("chapter"):
                                smoothed[i] = ElementType.CAPTION
                                smoothed_conf[i] = 0.95
                                reasons[i] = "smoothed_post_figure_table_promoted_to_caption"

            # Constraint 3b: Demote unanchored captions without caption prefixes to PARAGRAPH
            if smoothed[i] == ElementType.CAPTION:
                text_clean = elem.original_text.strip()
                text_lower = text_clean.lower()
                has_caption_prefix = text_lower.startswith(("figure", "fig.", "fig ", "table", "tbl.", "tbl ", "illustration", "plate", "chart"))
                prev_was_anchor = (i > 0 and smoothed[i - 1] in (ElementType.FIGURE, ElementType.TABLE))
                if not has_caption_prefix and not prev_was_anchor:
                    smoothed[i] = ElementType.PARAGRAPH
                    smoothed_conf[i] = 0.90
                    reasons[i] = "smoothed_unanchored_caption_demoted_to_paragraph"

            # Constraint 3c: Demote text-only elements classified as FIGURE to PARAGRAPH
            if smoothed[i] == ElementType.FIGURE:
                if elem.original_text.strip() and not getattr(elem, "contains_drawing", False) and not isinstance(elem, FigureElement):
                    smoothed[i] = ElementType.PARAGRAPH
                    smoothed_conf[i] = 0.85
                    reasons[i] = "smoothed_text_element_demoted_from_figure"

            # Constraint 4: SUBHEADING cannot precede any HEADING or CHAPTER
            if cur_type == ElementType.SUBHEADING and not has_seen_chapter and not has_seen_heading:
                smoothed[i] = ElementType.HEADING
                smoothed_conf[i] = 0.88
                reasons[i] = "smoothed_initial_subheading_promoted_to_heading"
                has_seen_heading = True

            # Constraint 5: Back-matter citations following REFERENCES header
            if has_seen_references_header and rel_pos > 0.60:
                # If an item looks like a citation (has year, starts with [N] or author)
                text = elem.original_text.strip()
                if cur_type == ElementType.PARAGRAPH and (
                    text.startswith("[") or any(yr in text for yr in ["19", "20"])
                ):
                    smoothed[i] = ElementType.REFERENCE
                    smoothed_conf[i] = 0.92
                    reasons[i] = "smoothed_back_matter_paragraph_promoted_to_reference"

        return smoothed, smoothed_conf, reasons
