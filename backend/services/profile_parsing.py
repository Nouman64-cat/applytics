import io

import docx
from pypdf import PdfReader


def extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_text_from_docx(content: bytes) -> str:
    document = docx.Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def extract_text(filename: str, content: bytes) -> str:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return extract_text_from_pdf(content)
    if lowered.endswith(".docx"):
        return extract_text_from_docx(content)
    return content.decode("utf-8", errors="ignore").strip()
