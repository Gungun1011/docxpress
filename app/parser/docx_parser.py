"""Read-only DOCX parser into the Canonical Document AST.

Safely traverses Word document bodies in sequential order without modifying
the input file, extracting paragraphs, runs, tables, images, and metadata.
"""

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union
import uuid

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.models.ast import (
    BaseElement,
    CanonicalDocument,
    DocumentMetadata,
    ElementType,
    FigureElement,
    ParagraphElement,
    RunMetadata,
    TableCell,
    TableElement,
)
from app.parser.oxml_utils import (
    extract_drawing_info,
    extract_list_info,
    extract_run_metadata,
    iter_document_blocks,
)
from app.utils.file_utils import get_file_fingerprint, verify_file_unmodified


class DocxParser:
    """Read-only parser extracting CanonicalDocument AST from .docx files."""

    def __init__(self, enforce_read_only: bool = True) -> None:
        """Initializes the parser.
        
        Args:
            enforce_read_only: If True, asserts source file is byte-identical
                               before and after parsing.
        """
        self.enforce_read_only = enforce_read_only

    def parse(self, file_path: Union[str, Path]) -> CanonicalDocument:
        """Parses a DOCX file into a CanonicalDocument AST.
        
        Args:
            file_path: Path to the target .docx file.
            
        Returns:
            CanonicalDocument AST containing metadata and ordered elements.
            
        Raises:
            FileNotFoundError: If the target file does not exist.
            ValueError: If the file is not a valid DOCX.
            RuntimeError: If read-only invariant is violated.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Source file not found: {path}")

        # Capture source file fingerprint before reading
        before_fingerprint = get_file_fingerprint(path)

        # Open file in python-docx in read-only manner
        with open(path, "rb") as f:
            doc = docx.Document(f)

        # Extract document-level metadata
        metadata = self._extract_metadata(doc, path, before_fingerprint.sha256, before_fingerprint.mtime)

        # Extract elements in exact sequential document order
        elements: List[BaseElement] = []
        element_idx = 0

        for kind, block in iter_document_blocks(doc):
            if kind == "p":
                parsed_elem = self._parse_paragraph(block, element_idx)
                elements.append(parsed_elem)
                element_idx += 1
            elif kind == "tbl":
                parsed_table = self._parse_table(block, element_idx)
                elements.append(parsed_table)
                element_idx += 1

        # Verify read-only invariant: source file on disk must be identical
        if self.enforce_read_only:
            after_fingerprint = get_file_fingerprint(path)
            unmodified, reason = verify_file_unmodified(before_fingerprint, after_fingerprint)
            if not unmodified:
                raise RuntimeError(f"Read-only invariant violation: {reason}")

        return CanonicalDocument(
            metadata=metadata,
            elements=tuple(elements),
        )

    def _extract_metadata(
        self,
        doc: docx.Document,
        path: Path,
        sha256_hash: str,
        mtime: float,
    ) -> DocumentMetadata:
        """Extracts core document metadata from python-docx core_properties."""
        core_props = doc.core_properties
        title = core_props.title or None
        author = core_props.author or None
        
        created = None
        if core_props.created:
            created = core_props.created.isoformat()
            
        modified = None
        if core_props.modified:
            modified = core_props.modified.isoformat()
            
        revision = core_props.revision

        return DocumentMetadata(
            filename=path.name,
            title=title,
            author=author,
            created=created,
            modified=modified,
            revision=revision,
            file_size_bytes=path.stat().st_size,
            source_file_sha256=sha256_hash,
            source_file_mtime=mtime,
        )

    def _parse_paragraph(self, p: Paragraph, index: int) -> BaseElement:
        """Parses a paragraph block into either a ParagraphElement or FigureElement."""
        element_id = f"elem_{index:05d}_{uuid.uuid4().hex[:8]}"
        raw_text = p.text
        style_name = p.style.name if p.style else None

        # Extract runs and formatting
        runs: List[RunMetadata] = [extract_run_metadata(r) for r in p.runs]

        # Extract drawings and numbering
        drawings = extract_drawing_info(p)
        list_info = extract_list_info(p)

        # Alignment
        alignment = None
        if p.alignment is not None:
            alignment = str(p.alignment)

        # Check if this paragraph is solely an embedded image/drawing
        if drawings and not raw_text.strip():
            first_draw = drawings[0]
            return FigureElement(
                element_id=element_id,
                element_type=ElementType.FIGURE,
                paragraph_index=index,
                original_text=raw_text,
                original_style=style_name,
                runs=tuple(runs),
                image_id=first_draw.get("image_id"),
                width_pt=first_draw.get("width_pt"),
                height_pt=first_draw.get("height_pt"),
            )

        # Initial structural classification based on Word styles and XML primitives
        elem_type = self._determine_initial_type(style_name, list_info, raw_text)

        return ParagraphElement(
            element_id=element_id,
            element_type=elem_type,
            paragraph_index=index,
            original_text=raw_text,
            original_style=style_name,
            runs=tuple(runs),
            list_info=list_info,
            contains_drawing=bool(drawings),
            alignment=alignment,
        )

    def _parse_table(self, tbl: Table, index: int) -> TableElement:
        """Parses a table block into a TableElement preserving all cell contents."""
        element_id = f"elem_{index:05d}_{uuid.uuid4().hex[:8]}"
        rows_data: List[Tuple[TableCell, ...]] = []
        table_text_lines: List[str] = []

        for r_idx, row in enumerate(tbl.rows):
            row_cells: List[TableCell] = []
            row_texts: List[str] = []
            for c_idx, cell in enumerate(row.cells):
                cell_paragraphs = tuple(p.text for p in cell.paragraphs)
                cell_text = cell.text
                row_cells.append(
                    TableCell(
                        row_idx=r_idx,
                        col_idx=c_idx,
                        text=cell_text,
                        paragraphs=cell_paragraphs,
                    )
                )
                row_texts.append(cell_text.strip())
            rows_data.append(tuple(row_cells))
            table_text_lines.append("\t".join(row_texts))

        # Build deterministic table text representation
        original_text = "\n".join(table_text_lines)

        cols_count = len(tbl.columns) if tbl.rows else 0
        rows_count = len(tbl.rows)

        return TableElement(
            element_id=element_id,
            element_type=ElementType.TABLE,
            paragraph_index=index,
            original_text=original_text,
            original_style=None,
            runs=(),
            rows_count=rows_count,
            cols_count=cols_count,
            cells=tuple(rows_data),
        )

    def _determine_initial_type(
        self,
        style_name: Optional[str],
        list_info: Optional[Any],
        text: str,
    ) -> ElementType:
        """Maps native Word styles and XML attributes to initial ElementTypes.
        
        Note: This is the baseline structural identification. Advanced ML/NLP/Regex
        classification will be performed in Phase 2.
        """
        if list_info is not None:
            return ElementType.LIST

        if style_name:
            s_lower = style_name.lower()
            if s_lower == "title":
                return ElementType.TITLE
            if s_lower == "subtitle" or s_lower == "author":
                return ElementType.AUTHOR
            if "heading" in s_lower:
                return ElementType.HEADING
            if "caption" in s_lower:
                return ElementType.CAPTION
            if "reference" in s_lower or "bibliography" in s_lower:
                return ElementType.REFERENCE
            if "list" in s_lower or "bullet" in s_lower:
                return ElementType.LIST

        return ElementType.PARAGRAPH
