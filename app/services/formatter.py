"""Formatting-only DOCX publication service."""

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable, Dict, Optional, Union

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Cm, Pt

from app.models.ast import CanonicalDocument, ElementType
from app.parser.docx_parser import DocxParser
from app.services.content_preservation import (
    ContentPreservationError,
    ContentPreservationReport,
    ContentPreservationService,
)
from app.utils.logger import get_logger


@dataclass(frozen=True)
class PublicationProfile:
    """Configurable page and typography rules for a publication."""

    name: str
    body_font: str = "Times New Roman"
    body_size_pt: float = 12.0
    body_alignment: int = WD_ALIGN_PARAGRAPH.JUSTIFY
    body_line_spacing: float = 1.5
    body_first_indent_cm: float = 1.27
    top_margin_cm: float = 1.52
    bottom_margin_cm: float = 1.52
    left_margin_cm: float = 1.97
    right_margin_cm: float = 1.96
    heading_1_size_pt: float = 16.0
    subheading_size_pt: float = 12.0
    title_size_pt: float = 20.0
    author_size_pt: float = 12.0
    caption_size_pt: float = 10.0
    reference_size_pt: float = 10.0
    list_size_pt: float = 12.0
    table_size_pt: float = 10.0


DEFAULT_PUBLICATION_PROFILE = PublicationProfile(name="hackathon_default")
PUBLICATION_PROFILES: Dict[str, PublicationProfile] = {
    "hackathon_default": DEFAULT_PUBLICATION_PROFILE,
    "trade": PublicationProfile(
        name="trade", body_size_pt=10.5, body_first_indent_cm=0.635,
        top_margin_cm=1.905, bottom_margin_cm=1.905, left_margin_cm=1.588,
        right_margin_cm=1.588, heading_1_size_pt=14.0, title_size_pt=26.0,
    ),
    "academic": PublicationProfile(
        name="academic", body_size_pt=11.0, body_first_indent_cm=0.635,
        top_margin_cm=2.54, bottom_margin_cm=2.54, left_margin_cm=2.54,
        right_margin_cm=2.54, heading_1_size_pt=14.0,
    ),
    "fiction": PublicationProfile(
        name="fiction", body_size_pt=11.0, body_first_indent_cm=0.635,
        top_margin_cm=2.0, bottom_margin_cm=2.0, left_margin_cm=2.0,
        right_margin_cm=2.0, heading_1_size_pt=15.0, title_size_pt=24.0,
    ),
}


@dataclass(frozen=True)
class FormattingProgress:
    processed: int
    total: int
    elapsed_seconds: float


@dataclass(frozen=True)
class FormattingResult:
    output_path: Path
    profile_name: str
    elapsed_seconds: float
    elements_processed: int
    preservation: ContentPreservationReport
    progress_events: int = 0


class PublicationFormatter:
    """Applies publication formatting without assigning document text."""

    def __init__(self, parser: Optional[DocxParser] = None) -> None:
        self.parser = parser or DocxParser()
        self.logger = get_logger(__name__)

    def format_document(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        document: Optional[CanonicalDocument] = None,
        profile: Union[str, PublicationProfile] = DEFAULT_PUBLICATION_PROFILE,
        progress_callback: Optional[Callable[[FormattingProgress], None]] = None,
    ) -> FormattingResult:
        """Format a DOCX and fail if reparsed text differs from the source."""
        started = time.perf_counter()
        source_doc = document or self.parser.parse(input_path)
        selected_profile = self._resolve_profile(profile)
        source_fingerprint = ContentPreservationService.generate_fingerprint(source_doc)
        word_doc = docx.Document(str(input_path))
        self._apply_page_geometry(word_doc, selected_profile)

        blocks = word_doc.iter_inner_content()
        total = len(source_doc.elements)
        progress_events = 0
        for index, (block, element) in enumerate(zip(blocks, source_doc.elements), start=1):
            if hasattr(block, "paragraph_format"):
                self._format_paragraph(block, element, selected_profile)
            else:
                self._format_table(block, selected_profile)
            if progress_callback is not None:
                progress_callback(FormattingProgress(index, total, time.perf_counter() - started))
                progress_events += 1

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        word_doc.save(str(output))
        output_doc = self.parser.parse(output)
        report = ContentPreservationService.compare_fingerprints(
            source_fingerprint,
            ContentPreservationService.generate_fingerprint(output_doc),
        )
        if not report.is_identical:
            raise ContentPreservationError(report)

        elapsed = time.perf_counter() - started
        self.logger.info("Formatted %d elements in %.3fs", total, elapsed)
        return FormattingResult(
            output_path=output,
            profile_name=selected_profile.name,
            elapsed_seconds=elapsed,
            elements_processed=total,
            preservation=report,
            progress_events=progress_events,
        )

    @staticmethod
    def _resolve_profile(profile: Union[str, PublicationProfile]) -> PublicationProfile:
        if isinstance(profile, PublicationProfile):
            return profile
        try:
            return PUBLICATION_PROFILES[profile]
        except KeyError as exc:
            raise ValueError(f"Unknown publication profile: {profile}") from exc

    @staticmethod
    def _apply_page_geometry(word_doc: docx.Document, profile: PublicationProfile) -> None:
        for section in word_doc.sections:
            section.top_margin = Cm(profile.top_margin_cm)
            section.bottom_margin = Cm(profile.bottom_margin_cm)
            section.left_margin = Cm(profile.left_margin_cm)
            section.right_margin = Cm(profile.right_margin_cm)

    @classmethod
    def _format_paragraph(cls, paragraph, element, profile: PublicationProfile) -> None:
        element_type = getattr(element, "element_type", element)
        style_name = getattr(element, "original_style", None) or ""
        style_name = style_name.lower()
        original_text = getattr(element, "original_text", "")
        if element_type == ElementType.HEADING and "heading 1" in style_name:
            if original_text.strip().lower().startswith(("chapter ", "part ")):
                element_type = ElementType.CHAPTER
        elif element_type == ElementType.HEADING and any(
            marker in style_name for marker in ("heading 2", "heading 3")
        ):
            element_type = ElementType.SUBHEADING

        fmt = paragraph.paragraph_format
        fmt.line_spacing = profile.body_line_spacing
        fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(0)
        fmt.first_line_indent = Cm(profile.body_first_indent_cm)
        fmt.left_indent = Cm(0)
        fmt.right_indent = Cm(0)

        size = profile.body_size_pt
        bold = False
        italic = False
        alignment = profile.body_alignment
        if element_type == ElementType.TITLE:
            size, bold, alignment = profile.title_size_pt, True, WD_ALIGN_PARAGRAPH.CENTER
            fmt.first_line_indent = Cm(0)
        elif element_type == ElementType.AUTHOR:
            size, italic, alignment = profile.author_size_pt, True, WD_ALIGN_PARAGRAPH.CENTER
            fmt.first_line_indent = Cm(0)
        elif element_type == ElementType.CHAPTER:
            size, bold = profile.heading_1_size_pt, True
            fmt.first_line_indent = Cm(0)
            fmt.page_break_before = True
            fmt.keep_with_next = True
        elif element_type == ElementType.HEADING:
            size, bold = profile.heading_1_size_pt, True
            fmt.first_line_indent = Cm(0)
            fmt.keep_with_next = True
        elif element_type == ElementType.SUBHEADING:
            size, bold = profile.subheading_size_pt, True
            fmt.first_line_indent = Cm(0)
            fmt.keep_with_next = True
        elif element_type == ElementType.CAPTION:
            size, italic, alignment = profile.caption_size_pt, True, WD_ALIGN_PARAGRAPH.CENTER
            fmt.first_line_indent = Cm(0)
        elif element_type == ElementType.REFERENCE:
            size, alignment = profile.reference_size_pt, WD_ALIGN_PARAGRAPH.LEFT
            fmt.left_indent = Cm(0.762)
            fmt.first_line_indent = Cm(-0.762)
        elif element_type == ElementType.LIST:
            size, alignment = profile.list_size_pt, WD_ALIGN_PARAGRAPH.LEFT
            fmt.first_line_indent = Cm(-0.635)
            fmt.left_indent = Cm(0.635)
        elif element_type == ElementType.FIGURE:
            fmt.first_line_indent = Cm(0)
            alignment = WD_ALIGN_PARAGRAPH.CENTER

        fmt.alignment = alignment
        for run in paragraph.runs:
            run.font.name = profile.body_font
            run.font.size = Pt(size)
            if element_type not in (ElementType.BODY_PARAGRAPH, ElementType.PARAGRAPH):
                run.bold = bold
                run.italic = italic

    @staticmethod
    def _format_table(table, profile: PublicationProfile) -> None:
        table.autofit = True
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    PublicationFormatter._format_paragraph(paragraph, ElementType.TABLE, profile)
                    for run in paragraph.runs:
                        run.font.size = Pt(profile.table_size_pt)
                        run.bold = row_index == 0


FormatterEngine = PublicationFormatter