from pathlib import Path
from pypdf import PdfReader


def extract_text(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF.

    Keeps page boundaries marked so downstream prompts can reference them.
    """
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.strip()
        if text:
            pages.append(f"--- Page {i} ---\n{text}")
    return "\n\n".join(pages)


def load_paper(pdf_path: str | Path) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    text = extract_text(path)
    return {
        "path": str(path),
        "filename": path.name,
        "num_chars": len(text),
        "text": text,
    }
