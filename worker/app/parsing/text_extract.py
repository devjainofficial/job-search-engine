"""Extract plain text from a resume file (pdf, docx, or txt), from a path or bytes."""

import io
from pathlib import Path


def extract_text(path: str | Path) -> str:
    path = Path(path)
    return extract_text_from_bytes(path.read_bytes(), path.name)


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extract text from in-memory file bytes (used by the upload/parse endpoint)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(io.BytesIO(data))
    if suffix in (".docx", ".doc"):
        return _extract_docx(io.BytesIO(data))
    if suffix in (".txt", ".md"):
        return data.decode("utf-8", errors="ignore").strip()
    raise ValueError(f"Unsupported resume type: {suffix}")


def _extract_pdf(stream: io.BytesIO) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(stream) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_docx(stream: io.BytesIO) -> str:
    import docx

    document = docx.Document(stream)
    return "\n".join(p.text for p in document.paragraphs).strip()
