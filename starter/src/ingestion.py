"""Extract PDF pages while retaining physical page numbers."""
from pathlib import Path
import re
import unicodedata
import warnings

from pypdf import PdfReader
from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str,
             selected_pages: set[int] | None = None) -> list[DocumentPage]:
    """Extract text pages; warn about pages that need OCR or manual inspection."""
    reader = PdfReader(path)
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        if selected_pages is not None and number not in selected_pages:
            continue
        text = normalize_text(page.extract_text() or "")
        if not text:
            warnings.warn(f"No extractable text: {path}, page {number}", stacklevel=2)
            continue
        pages.append(DocumentPage(document_id, source, number, text))
    return pages


def normalize_text(text: str) -> str:
    """Normalize Unicode and spaces while preserving paragraph boundaries."""
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t\f\v ]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def evidence_text(text: str) -> str:
    """Collapse whitespace for matching quotes across PDF line breaks."""
    return " ".join(normalize_text(text).casefold().split())
