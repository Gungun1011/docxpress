"""Canonical Document AST (Abstract Syntax Tree) Models.

Defines immutable data structures representing document elements, runs,
tables, figures, and metadata. Guarantees 100% text preservation and
document order fidelity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class ElementType(str, Enum):
    """Enumeration of canonical document element types (11 classes)."""
    PARAGRAPH = "paragraph"
    BODY_PARAGRAPH = "paragraph"        # Alias for standard body prose
    HEADING = "heading"                 # Major heading (H1)
    SUBHEADING = "subheading"           # Minor heading (H2/H3)
    CHAPTER = "chapter"                 # Chapter header / title
    CHAPTER_HEADING = "chapter"         # Alias for chapter heading
    TITLE = "title"                     # Book / manuscript title
    AUTHOR = "author"                   # Author name / credentials
    AUTHOR_DETAILS = "author"           # Alias for author details
    TABLE = "table"                     # Tabular data grid
    FIGURE = "figure"                   # Illustration, graphic, or image
    CAPTION = "caption"                 # Figure or table caption
    LIST = "list"                       # Bullet or numbered list
    LIST_ITEM = "list"                  # Alias for list item
    REFERENCE = "reference"             # Bibliography entry / citation
    REFERENCES = "reference"            # Alias for references
    UNKNOWN = "unknown"                 # Unclassified or ambiguous block


@dataclass(frozen=True)
class RunMetadata:
    """Represents an atomic text run and its inline typography metadata.
    
    Attributes:
        text: Raw verbatim string of the run.
        bold: Whether run is explicitly bolded (None if inherited).
        italic: Whether run is explicitly italicized (None if inherited).
        underline: Whether run is underlined (None if inherited).
        font_name: Explicit typeface name if defined in run properties.
        font_size_pt: Explicit font size in points if defined in run properties.
        superscript: Whether run is superscripted.
        subscript: Whether run is subscripted.
    """
    text: str
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    superscript: Optional[bool] = None
    subscript: Optional[bool] = None


@dataclass(frozen=True)
class ListInfo:
    """Metadata for list items detected in DOCX numbering definitions.
    
    Attributes:
        num_id: The numbering definition ID.
        ilvl: Indentation level (0-indexed).
        is_bullet: Whether numbering format is bullet-based.
        is_numbered: Whether numbering format is sequential/decimal/roman.
    """
    num_id: Optional[int] = None
    ilvl: Optional[int] = 0
    is_bullet: bool = False
    is_numbered: bool = False


@dataclass(frozen=True)
class TableCell:
    """Represents a single cell within a TableElement.
    
    Attributes:
        row_idx: Row index (0-indexed).
        col_idx: Column index (0-indexed).
        text: Verbatim raw text contained in the cell.
        paragraphs: Sequence of raw paragraph texts within the cell.
    """
    row_idx: int
    col_idx: int
    text: str
    paragraphs: Tuple[str, ...] = ()


@dataclass(frozen=True)
class BaseElement:
    """Abstract base class for all canonical document AST elements.
    
    All elements are strictly frozen/immutable after parsing.
    
    Attributes:
        element_id: Deterministic or unique identifier for the element.
        element_type: Structural element type (ElementType).
        paragraph_index: Sequential 0-indexed position in document flow.
        original_text: Verbatim immutable text content.
        original_style: Original Word style name (e.g., 'Normal', 'Heading 1').
        runs: Immutable sequence of atomic runs and their inline formatting.
    """
    element_id: str
    element_type: ElementType
    paragraph_index: int
    original_text: str
    original_style: Optional[str] = None
    runs: Tuple[RunMetadata, ...] = ()
    confidence: float = 1.0
    detection_method: Optional[str] = "native_parser"

    @property
    def element_index(self) -> int:
        """Alias for paragraph_index representing document sequence order."""
        return self.paragraph_index

    @property
    def run_metadata(self) -> Tuple[RunMetadata, ...]:
        """Alias for runs providing run-level formatting metadata."""
        return self.runs


@dataclass(frozen=True)
class ParagraphElement(BaseElement):
    """Represents a textual paragraph element (prose, heading, title, etc.).
    
    Attributes:
        list_info: Optional list/numbering metadata if part of a list.
        contains_drawing: Whether an inline image or drawing was detected.
        alignment: Word paragraph alignment (LEFT, CENTER, RIGHT, JUSTIFY).
    """
    list_info: Optional[ListInfo] = None
    contains_drawing: bool = False
    alignment: Optional[str] = None


@dataclass(frozen=True)
class TableElement(BaseElement):
    """Represents a tabular data grid element in the document.
    
    Attributes:
        rows_count: Number of rows in table.
        cols_count: Number of columns in table.
        cells: 2D grid of TableCell instances (row-major order).
    """
    rows_count: int = 0
    cols_count: int = 0
    cells: Tuple[Tuple[TableCell, ...], ...] = ()


@dataclass(frozen=True)
class FigureElement(BaseElement):
    """Represents an embedded graphic, photo, or inline illustration.
    
    Attributes:
        image_id: Relationship ID (rId) in DOCX package.
        image_filename: Extracted media filename if known.
        content_type: MIME content type (e.g., 'image/png').
        width_pt: Inferred or explicit image width in points.
        height_pt: Inferred or explicit image height in points.
        caption_text: Associated caption text if adjacent.
    """
    image_id: Optional[str] = None
    image_filename: Optional[str] = None
    content_type: Optional[str] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None
    caption_text: Optional[str] = None


@dataclass(frozen=True)
class DocumentMetadata:
    """Document-level properties and source file integrity markers.
    
    Attributes:
        filename: Name of the input DOCX file.
        title: Core property title if specified.
        author: Core property author/creator if specified.
        created: ISO creation timestamp if specified.
        modified: ISO last modified timestamp if specified.
        revision: Revision counter if specified.
        file_size_bytes: Size of source file in bytes.
        source_file_sha256: SHA-256 hash of raw source DOCX on disk.
        source_file_mtime: Last modification timestamp of file on disk.
    """
    filename: str
    title: Optional[str] = None
    author: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    revision: Optional[int] = None
    file_size_bytes: int = 0
    source_file_sha256: str = ""
    source_file_mtime: float = 0.0


@dataclass(frozen=True)
class CanonicalDocument:
    """The root Canonical Document AST container.
    
    Contains document metadata and the ordered sequence of all document
    elements. Document order is strictly preserved.
    
    Attributes:
        metadata: Document-level metadata and integrity checksums.
        elements: Immutable sequence of all parsed document elements.
    """
    metadata: DocumentMetadata
    elements: Tuple[BaseElement, ...] = ()

    @property
    def element_count(self) -> int:
        """Total number of elements in the document."""
        return len(self.elements)

    def get_element_by_id(self, element_id: str) -> Optional[BaseElement]:
        """Find an element by its unique element_id."""
        for elem in self.elements:
            if elem.element_id == element_id:
                return elem
        return None

    def get_elements_by_type(self, element_type: ElementType) -> List[BaseElement]:
        """Filter elements by their assigned ElementType."""
        return [elem for elem in self.elements if elem.element_type == element_type]

    def get_text_sequence(self) -> List[str]:
        """Returns the ordered list of original verbatim texts from all elements."""
        return [elem.original_text for elem in self.elements]

    def summary_dict(self) -> Dict[str, Any]:
        """Returns a concise summary dictionary of document structure."""
        type_counts: Dict[str, int] = {}
        for elem in self.elements:
            t = elem.element_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        total_words = sum(len(elem.original_text.split()) for elem in self.elements)
        total_chars = sum(len(elem.original_text) for elem in self.elements)

        return {
            "filename": self.metadata.filename,
            "title": self.metadata.title,
            "author": self.metadata.author,
            "total_elements": len(self.elements),
            "element_counts": type_counts,
            "total_words": total_words,
            "total_characters": total_chars,
            "source_file_sha256": self.metadata.source_file_sha256,
        }

    def with_elements(self, new_elements: Sequence[BaseElement]) -> CanonicalDocument:
        """Returns a new CanonicalDocument with updated elements, preserving metadata."""
        return CanonicalDocument(
            metadata=self.metadata,
            elements=tuple(new_elements),
        )
