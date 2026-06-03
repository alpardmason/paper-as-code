from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: Path, *, max_pages: int | None = None) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""

    texts: list[str] = []
    pages = reader.pages if max_pages is None else reader.pages[:max_pages]
    for page in pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            texts.append(text)
    return "\n\n".join(texts)
