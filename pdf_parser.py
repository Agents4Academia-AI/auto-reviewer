import base64
from pathlib import Path


def load_paper(pdf_path: str | Path) -> dict:
    """Load a local PDF as a Claude document input block."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path}")

    pdf_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {
        "path": str(path),
        "filename": path.name,
        "num_bytes": path.stat().st_size,
        "document": {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_data,
            },
            "cache_control": {"type": "ephemeral"},
        },
    }
