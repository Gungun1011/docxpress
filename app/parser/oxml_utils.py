"""Low-level OpenXML (oxml) utility functions for python-docx.

Provides helpers to inspect XML nodes for drawings, numbering properties,
font properties, and sequence preservation.
"""

from typing import Any, Dict, Generator, List, Optional, Tuple
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.models.ast import ListInfo, RunMetadata


# EMU to Point conversion factor (1 pt = 12700 EMUs)
EMUS_PER_POINT = 12700.0


def iter_document_blocks(doc: Document) -> Generator[Tuple[str, Any], None, None]:
    """Iterates over top-level body elements preserving exact document order.
    
    Yields:
        Tuple of (element_kind, element_obj) where kind is 'p' or 'tbl'.
    """
    for child in doc.element.body:
        tag = child.tag
        if tag.endswith("p"):
            yield ("p", Paragraph(child, doc))
        elif tag.endswith("tbl"):
            yield ("tbl", Table(child, doc))
        elif tag.endswith("sdt"):
            # Structured Document Tags (content controls) can wrap paragraphs/tables
            for subchild in child.xpath(".//w:p | .//w:tbl"):
                if subchild.tag.endswith("p"):
                    yield ("p", Paragraph(subchild, doc))
                elif subchild.tag.endswith("tbl"):
                    yield ("tbl", Table(subchild, doc))


def extract_run_metadata(run) -> RunMetadata:
    """Extracts run-level typographical metadata safely.
    
    Args:
        run: A docx.text.run.Run instance.
        
    Returns:
        RunMetadata instance with immutable formatting properties.
    """
    font = run.font
    font_size_pt: Optional[float] = None
    if font.size is not None:
        try:
            font_size_pt = float(font.size.pt)
        except Exception:
            font_size_pt = None

    font_name: Optional[str] = font.name
    
    # Superscript / Subscript
    superscript: Optional[bool] = font.superscript
    subscript: Optional[bool] = font.subscript

    return RunMetadata(
        text=run.text or "",
        bold=run.bold,
        italic=run.italic,
        underline=run.underline,
        font_name=font_name,
        font_size_pt=font_size_pt,
        superscript=superscript,
        subscript=subscript,
    )


def extract_list_info(paragraph: Paragraph) -> Optional[ListInfo]:
    """Extracts numbering metadata (w:numPr) or style-based list indicators.
    
    Args:
        paragraph: A docx.text.paragraph.Paragraph instance.
        
    Returns:
        ListInfo instance if the paragraph is a list item, else None.
    """
    p_pr = paragraph._p.pPr
    num_id: Optional[int] = None
    ilvl: Optional[int] = 0
    is_bullet = False
    is_numbered = False

    if p_pr is not None:
        num_pr = p_pr.find(qn("w:numPr"))
        if num_pr is not None:
            ilvl_elem = num_pr.find(qn("w:ilvl"))
            num_id_elem = num_pr.find(qn("w:numId"))
            if ilvl_elem is not None and ilvl_elem.get(qn("w:val")) is not None:
                try:
                    ilvl = int(ilvl_elem.get(qn("w:val")))
                except ValueError:
                    ilvl = 0
            if num_id_elem is not None and num_id_elem.get(qn("w:val")) is not None:
                try:
                    num_id = int(num_id_elem.get(qn("w:val")))
                except ValueError:
                    num_id = None
            is_numbered = True

    # Fallback to style-based naming (e.g., 'List Bullet', 'List Number')
    style_name = ""
    if paragraph.style and paragraph.style.name:
        style_name = paragraph.style.name.lower()
    
    if "bullet" in style_name:
        is_bullet = True
        is_numbered = False
    elif "number" in style_name or "list" in style_name:
        is_numbered = True

    if num_id is not None or is_bullet or is_numbered:
        return ListInfo(
            num_id=num_id,
            ilvl=ilvl,
            is_bullet=is_bullet,
            is_numbered=is_numbered,
        )
    return None


def extract_drawing_info(paragraph: Paragraph) -> List[Dict[str, Any]]:
    """Detects inline drawings or images embedded in the paragraph.
    
    Args:
        paragraph: A docx.text.paragraph.Paragraph instance.
        
    Returns:
        List of dicts containing image metadata (rId, dimensions).
    """
    drawings = paragraph._p.xpath(".//w:drawing | .//w:pict")
    results = []
    
    for drawing in drawings:
        info: Dict[str, Any] = {
            "image_id": None,
            "width_pt": None,
            "height_pt": None,
        }
        
        # Look for relationship ID in blip element
        blips = drawing.xpath(".//a:blip")
        for blip in blips:
            embed_id = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
            if embed_id:
                info["image_id"] = str(embed_id)
                break
                
        # Look for extents (dimensions)
        extents = drawing.xpath(".//wp:extent")
        for extent in extents:
            cx = extent.get("cx")
            cy = extent.get("cy")
            if cx and cy:
                try:
                    info["width_pt"] = float(cx) / EMUS_PER_POINT
                    info["height_pt"] = float(cy) / EMUS_PER_POINT
                except (ValueError, TypeError):
                    pass
            break
            
        results.append(info)
        
    return results
