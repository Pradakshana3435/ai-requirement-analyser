import io
import re
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

import config
from models import Document

SUPPORTED = {".txt", ".docx", ".pdf"}


class ExtractionError(Exception):
    """Raised with a user-friendly message when a file cannot be read."""


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\ufeff", "")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_txt(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("Could not decode the text file.")


def _read_docx(data: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError("This DOCX file could not be opened.") from exc
    parts = []
    for item in doc.iter_inner_content():
        if isinstance(item, Paragraph):
            if item.text.strip():
                parts.append(item.text)
        elif isinstance(item, Table):
            for row in item.rows:
                cells = []
                for cell in row.cells:
                    value = cell.text.strip().replace("\n", " ")
                    if value and (not cells or cells[-1] != value):  # skip merged-cell repeats
                        cells.append(value)
                if cells:
                    parts.append(" | ".join(cells))
    return "\n".join(parts)


PDF_TEXT_FLOW = True  # read text in the order it is stored in the file; keeps table cells intact


def _join_wrapped_ids(text: str) -> str:
    """Rejoin IDs that wrapped over two lines: 'FR-0\\n3\\nThe app...' -> 'FR-03 The app...'."""
    return re.sub(r"(?m)^([A-Z]{2,4}-\d+)\n(\d+)\n", r"\1\2 ", text)


def _read_pdf(data: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [(page.extract_text(use_text_flow=PDF_TEXT_FLOW) or "") for page in pdf.pages]
    except Exception as exc:
        raise ExtractionError("This PDF file could not be opened.") from exc
    text = _join_wrapped_ids("\n\n".join(pages))
    if not text.strip():
        raise ExtractionError(
            "No text found in this PDF. It may be a scanned image; scanned PDFs are not supported."
        )
    return text


def extract_text(filename: str, data: bytes) -> Document:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ExtractionError(f"Unsupported file type '{ext}'. Use PDF, DOCX or TXT.")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ExtractionError(f"File is larger than {config.MAX_UPLOAD_MB} MB.")

    if ext == ".txt":
        raw = _read_txt(data)
    elif ext == ".docx":
        raw = _read_docx(data)
    else:
        raw = _read_pdf(data)

    return from_pasted_text(raw, filename)


def from_pasted_text(text: str, filename: str = "pasted_text") -> Document:
    clean = _normalise(text)
    if not clean:
        raise ExtractionError("The document is empty.")
    return Document(filename=filename, raw_text=clean)