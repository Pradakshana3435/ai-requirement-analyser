import io

import pytest
from docx import Document as DocxDocument

from ingest.extract import ExtractionError, extract_text, from_pasted_text


def test_txt_is_normalised():
    doc = extract_text("req.txt", b"Line one.\r\n\r\n\r\n\r\nLine two.   \r\n")
    assert doc.raw_text == "Line one.\n\nLine two."
    assert doc.filename == "req.txt"


def test_docx_paragraphs_and_tables():
    d = DocxDocument()
    d.add_paragraph("The system shall allow login.")
    table = d.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "REQ-1"
    table.rows[0].cells[1].text = "Export reports"
    buf = io.BytesIO()
    d.save(buf)
    doc = extract_text("req.docx", buf.getvalue())
    assert "The system shall allow login." in doc.raw_text
    assert "REQ-1 | Export reports" in doc.raw_text


def test_unsupported_type():
    with pytest.raises(ExtractionError):
        extract_text("req.xlsx", b"data")


def test_empty_text():
    with pytest.raises(ExtractionError):
        from_pasted_text("   \n  ")

def test_wrapped_ids_are_rejoined():
    from ingest.extract import _join_wrapped_ids
    assert _join_wrapped_ids("FR-0\n3\nThe app shall log in.") == "FR-03 The app shall log in."
    assert _join_wrapped_ids("Version 2\n3 items\n") == "Version 2\n3 items\n"