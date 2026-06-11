"""Extract plain text from PDF using PyMuPDF."""

from __future__ import annotations

import tempfile
from pathlib import Path

import fitz  # PyMuPDF


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Return concatenated text from all pages."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        path = tmp.name
    try:
        doc = fitz.open(path)
        parts: list[str] = []
        for page in doc:
            t = page.get_text("text") or ""
            if t.strip():
                parts.append(t.strip())
        doc.close()
        return "\n\n".join(parts)
    finally:
        Path(path).unlink(missing_ok=True)
