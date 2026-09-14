"""Unit tests for DocxParser and Canonical Document AST generation."""

from pathlib import Path
import pytest

from app.models.ast import (
    ElementType,
    FigureElement,
    ParagraphElement,
    TableElement,
)
from app.parser.docx_parser import DocxParser


def test_parser_initialization():
    """Verifies DocxParser can be instantiated with configuration options."""
    parser = DocxParser(enforce_read_only=True)
    assert parser.enforce_read_only is True

    parser_loose = DocxParser(enforce_read_only=False)
    assert parser_loose.enforce_read_only is False


def test_parser_file_not_found():
    """Verifies FileNotFoundError is raised when target file does not exist."""
    parser = DocxParser()
    with pytest.raises(FileNotFoundError):
        parser.parse("non_existent_document_12345.docx")


def test_empty_document(empty_doc_path: Path):
    """Verifies parsing an empty document produces a valid, empty CanonicalDocument AST."""
    parser = DocxParser()
    doc = parser.parse(empty_doc_path)

    assert doc is not None
    assert doc.metadata.filename == "empty.docx"
    assert doc.metadata.file_size_bytes > 0
    assert doc.metadata.source_file_sha256 != ""
    assert doc.element_count == 0
    assert len(doc.elements) == 0
    assert doc.get_text_sequence() == []


def test_normal_paragraphs(deterministic_sample_path: Path):
    """Verifies parsing of standard body prose paragraphs."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    paragraphs = [e for e in doc.elements if e.element_type == ElementType.PARAGRAPH and e.original_text.strip()]
    assert len(paragraphs) >= 2

    # Check first body paragraph text
    body_1 = paragraphs[0]
    assert "A distributed computational model operates across autonomous nodes" in body_1.original_text
    assert body_1.original_style == "Normal"
    assert body_1.paragraph_index >= 0
    assert len(body_1.runs) > 0


def test_headings_and_titles(deterministic_sample_path: Path):
    """Verifies extraction and classification of titles, authors, and headings."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    titles = doc.get_elements_by_type(ElementType.TITLE)
    assert len(titles) == 1
    assert titles[0].original_text == "The Architecture of Distributed Systems"

    authors = doc.get_elements_by_type(ElementType.AUTHOR)
    assert len(authors) == 1
    assert "Dr. Ada Lovelace & Alan Turing" in authors[0].original_text

    headings = doc.get_elements_by_type(ElementType.HEADING)
    assert len(headings) >= 2
    heading_texts = [h.original_text for h in headings]
    assert any("Chapter 1: Foundations of Computing" in t for t in heading_texts)
    assert any("1.1 The Theoretical Model" in t for t in heading_texts)


def test_run_level_formatting(deterministic_sample_path: Path):
    """Verifies that run-level formatting (bold, italic, underline, size, font) is retained."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    # Find the typography check paragraph
    target_elem = None
    for elem in doc.elements:
        if "Typography check:" in elem.original_text:
            target_elem = elem
            break

    assert target_elem is not None
    assert isinstance(target_elem, ParagraphElement)
    assert len(target_elem.runs) >= 8

    # Check specific runs
    bold_run = next(r for r in target_elem.runs if "bold statement" in r.text)
    assert bold_run.bold is True

    italic_run = next(r for r in target_elem.runs if "italicized caveat" in r.text)
    assert italic_run.italic is True

    underline_run = next(r for r in target_elem.runs if "underlined clause" in r.text)
    assert underline_run.underline is True

    size_run = next(r for r in target_elem.runs if "large emphasis text" in r.text)
    assert size_run.font_size_pt == 14.0
    assert size_run.font_name == "Georgia"


def test_tables_extraction(deterministic_sample_path: Path):
    """Verifies extraction of tables, cells, rows, and dimensions."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    tables = doc.get_elements_by_type(ElementType.TABLE)
    assert len(tables) == 1

    tbl = tables[0]
    assert isinstance(tbl, TableElement)
    assert tbl.rows_count == 3
    assert tbl.cols_count == 3
    assert len(tbl.cells) == 3

    # Check header row
    header_texts = [cell.text.strip() for cell in tbl.cells[0]]
    assert header_texts == ["Node ID", "Throughput (ops/s)", "Consensus State"]

    # Check data cells
    assert tbl.cells[1][0].text.strip() == "node-01"
    assert tbl.cells[1][1].text.strip() == "12500"
    assert tbl.cells[1][2].text.strip() == "Leader"

    assert tbl.cells[2][0].text.strip() == "node-02"
    assert tbl.cells[2][2].text.strip() == "Follower"

    # Check deterministic text
    assert "node-01\t12500\tLeader" in tbl.original_text


def test_figure_extraction(deterministic_sample_path: Path):
    """Verifies detection of embedded inline images and drawings."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    figures = doc.get_elements_by_type(ElementType.FIGURE)
    assert len(figures) == 1

    fig = figures[0]
    assert isinstance(fig, FigureElement)
    assert fig.image_id is not None
    assert fig.width_pt is not None and fig.width_pt > 0
    assert fig.height_pt is not None and fig.height_pt > 0


def test_caption_extraction(deterministic_sample_path: Path):
    """Verifies caption extraction associated with figure."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    captions = doc.get_elements_by_type(ElementType.CAPTION)
    assert len(captions) == 1
    assert "Figure 1.1: Distributed consensus state transition" in captions[0].original_text


def test_list_items_extraction(deterministic_sample_path: Path):
    """Verifies detection of both numbered and bulleted list items."""
    parser = DocxParser()
    doc = parser.parse(deterministic_sample_path)

    lists = doc.get_elements_by_type(ElementType.LIST)
    assert len(lists) == 6

    # 3 numbered items
    numbered = [e for e in lists if isinstance(e, ParagraphElement) and e.list_info and e.list_info.is_numbered]
    assert len(numbered) == 3
    assert "Initialize all consensus registers to state zero." in [n.original_text for n in numbered]

    # 3 bullet items
    bullets = [e for e in lists if isinstance(e, ParagraphElement) and e.list_info and e.list_info.is_bullet]
    assert len(bullets) == 3
    assert "High availability with zero single points of failure." in [b.original_text for b in bullets]


def test_document_order_interleaved(interleaved_doc_path: Path):
    """Verifies strict sequential document order when paragraphs and tables are interleaved."""
    parser = DocxParser()
    doc = parser.parse(interleaved_doc_path)

    assert doc.element_count == 5

    # Sequence must be: Paragraph -> Table -> Paragraph -> Table -> Paragraph
    assert doc.elements[0].element_type == ElementType.PARAGRAPH
    assert "Paragraph Alpha" in doc.elements[0].original_text

    assert doc.elements[1].element_type == ElementType.TABLE
    assert isinstance(doc.elements[1], TableElement)
    assert doc.elements[1].rows_count == 2

    assert doc.elements[2].element_type == ElementType.PARAGRAPH
    assert "Paragraph Beta" in doc.elements[2].original_text

    assert doc.elements[3].element_type == ElementType.TABLE
    assert isinstance(doc.elements[3], TableElement)

    assert doc.elements[4].element_type == ElementType.PARAGRAPH
    assert "Paragraph Gamma" in doc.elements[4].original_text

    # Indexes must be strictly monotonic
    for idx, elem in enumerate(doc.elements):
        assert elem.paragraph_index == idx


def test_unicode_text_handling(unicode_doc_path: Path):
    """Verifies flawless handling of international alphabets, accents, symbols, and emojis."""
    parser = DocxParser()
    doc = parser.parse(unicode_doc_path)

    text_seq = doc.get_text_sequence()
    combined_text = " ".join(text_seq)

    # French accents
    assert "Système d'Édition Décentralisée" in combined_text
    assert "Genève" in combined_text

    # German umlauts
    assert "Müller Schmidt" in combined_text
    assert "München" in combined_text

    # Chinese characters
    assert "普适计算与量子通信" in combined_text

    # Russian Cyrillic
    assert "В теории информации энтропия определяет меру неопределенности." in combined_text

    # Greek
    assert "Η κβαντική υπολογιστική χρησιμοποιεί qubits για παράλληλο υπολογισμό." in combined_text

    # Math symbols & Emojis
    assert "∀x ∈ S" in combined_text
    assert "🚀" in combined_text
    assert "📚" in combined_text
    assert "✨" in combined_text
