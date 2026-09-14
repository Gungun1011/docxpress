"""Unit tests for ContextualSmoother sequential grammar rules."""

import pytest

from app.core.ml.smoother import ContextualSmoother
from app.models.ast import (
    ElementType,
    FigureElement,
    ParagraphElement,
    TableElement,
)


def test_demote_title_in_middle_of_document():
    """Verifies that a TITLE predicted deep in a document is demoted to HEADING."""
    elements = [
        ParagraphElement("p0", ElementType.PARAGRAPH, 0, "Introduction prose."),
        ParagraphElement("p1", ElementType.PARAGRAPH, 1, "Second paragraph."),
        ParagraphElement("p2", ElementType.PARAGRAPH, 2, "Misclassified Title Header"),
    ]
    predicted = [ElementType.PARAGRAPH, ElementType.PARAGRAPH, ElementType.TITLE]
    confidences = [0.95, 0.95, 0.88]

    smoothed, confs, reasons = ContextualSmoother.smooth_sequence(elements, predicted, confidences)

    assert smoothed[2] == ElementType.HEADING
    assert "smoothed_title_in_body_demoted" in reasons[2]


def test_demote_unanchored_caption():
    """Verifies that an unanchored caption in the middle of body prose is demoted to PARAGRAPH."""
    elements = [
        ParagraphElement("p0", ElementType.PARAGRAPH, 0, "Normal running body paragraph."),
        ParagraphElement("p1", ElementType.PARAGRAPH, 1, "Typography check: bold statement and caveats."),
        ParagraphElement("p2", ElementType.PARAGRAPH, 2, "Another body paragraph."),
    ]
    predicted = [ElementType.PARAGRAPH, ElementType.CAPTION, ElementType.PARAGRAPH]
    confidences = [0.95, 0.85, 0.95]

    smoothed, confs, reasons = ContextualSmoother.smooth_sequence(elements, predicted, confidences)

    assert smoothed[1] == ElementType.PARAGRAPH
    assert "smoothed_unanchored_caption_demoted_to_paragraph" in reasons[1]


def test_promote_post_figure_caption():
    """Verifies that text following a Figure with caption keywords is promoted to CAPTION."""
    elements = [
        FigureElement("f1", ElementType.FIGURE, 0, "", image_id="rId1"),
        ParagraphElement("p1", ElementType.PARAGRAPH, 1, "Figure 1.1: System architecture diagram."),
    ]
    predicted = [ElementType.FIGURE, ElementType.PARAGRAPH]
    confidences = [1.0, 0.70]

    smoothed, confs, reasons = ContextualSmoother.smooth_sequence(elements, predicted, confidences)

    assert smoothed[1] == ElementType.CAPTION
    assert "smoothed_post_figure_table_promoted_to_caption" in reasons[1]
