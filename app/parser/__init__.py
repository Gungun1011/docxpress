"""DOCX parsing and OpenXML extraction package."""

from app.parser.docx_parser import DocxParser
from app.parser.oxml_utils import (
    extract_drawing_info,
    extract_list_info,
    extract_run_metadata,
    iter_document_blocks,
)

__all__ = [
    "DocxParser",
    "extract_drawing_info",
    "extract_list_info",
    "extract_run_metadata",
    "iter_document_blocks",
]
