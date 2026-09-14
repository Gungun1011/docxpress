"""Service for generating human-readable AST and document summaries."""

from typing import Any, Dict
from app.models.ast import CanonicalDocument, ElementType, TableElement, FigureElement
from app.services.content_preservation import ContentPreservationService


class DocumentSummaryService:
    """Formats CanonicalDocument AST into a clean human-readable report."""

    @classmethod
    def format_summary(cls, doc: CanonicalDocument, max_preview_elements: int = 15) -> str:
        """Creates a formatted ASCII summary of the parsed document."""
        fp = ContentPreservationService.generate_fingerprint(doc)
        meta = doc.metadata

        lines = [
            "=" * 70,
            "DOCXPRESS CANONICAL DOCUMENT SUMMARY",
            "=" * 70,
            f"Filename:             {meta.filename}",
            f"Source File SHA-256:  {meta.source_file_sha256[:16]}... (Full: {meta.source_file_sha256})",
            f"File Size:            {meta.file_size_bytes:,} bytes",
            f"Title:                {meta.title or '(Not specified)'}",
            f"Author:               {meta.author or '(Not specified)'}",
            f"Total Elements:       {doc.element_count}",
            f"Normalized Hash:      {fp.sha256_hash[:16]}... (Full: {fp.sha256_hash})",
            f"Normalized Words:     {fp.word_count:,}",
            f"Normalized Chars:     {fp.char_count:,}",
            "-" * 70,
            "ELEMENT TYPE BREAKDOWN:",
        ]

        # Count types
        counts: Dict[str, int] = {}
        for elem in doc.elements:
            t = elem.element_type.value
            counts[t] = counts.get(t, 0) + 1

        for elem_type in ElementType:
            c = counts.get(elem_type.value, 0)
            if c > 0:
                lines.append(f"  - {elem_type.value.upper():<16}: {c}")

        lines.append("-" * 70)
        lines.append(f"ELEMENT STREAM PREVIEW (First {min(len(doc.elements), max_preview_elements)} of {len(doc.elements)}):")
        lines.append("-" * 70)

        for i, elem in enumerate(doc.elements[:max_preview_elements]):
            t_name = elem.element_type.value.upper()
            style_str = f" [Style: {elem.original_style}]" if elem.original_style else ""

            if isinstance(elem, TableElement):
                desc = f"Table ({elem.rows_count}x{elem.cols_count})"
                preview_text = elem.original_text.replace("\n", " | ")[:60]
                lines.append(f"[{i:03d}] {t_name:<12}{style_str} {desc} -> \"{preview_text}\"")
            elif isinstance(elem, FigureElement):
                desc = f"Figure (ID: {elem.image_id or 'unknown'}, Dim: {elem.width_pt}x{elem.height_pt} pt)"
                lines.append(f"[{i:03d}] {t_name:<12}{style_str} {desc}")
            else:
                raw_preview = elem.original_text.replace("\n", " ")[:65]
                run_info = f" ({len(elem.runs)} runs)" if elem.runs else ""
                lines.append(f"[{i:03d}] {t_name:<12}{style_str}{run_info} -> \"{raw_preview}\"")

        if len(doc.elements) > max_preview_elements:
            lines.append(f"... ({len(doc.elements) - max_preview_elements} additional elements omitted)")

        lines.append("=" * 70)
        return "\n".join(lines)
