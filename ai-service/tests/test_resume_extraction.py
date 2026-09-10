from io import BytesIO

import pytest
from docx import Document

from app.resume_extraction import extract_text


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_extract_text_docx_returns_paragraph_content():
    docx_bytes = _make_docx_bytes(["Jane Doe", "Software Engineer at Acme Corp"])
    text = extract_text(docx_bytes, "resume.docx")
    assert "Jane Doe" in text
    assert "Software Engineer at Acme Corp" in text


def test_extract_text_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        extract_text(b"irrelevant", "resume.txt")
