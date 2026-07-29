from __future__ import annotations

from pathlib import Path


def extract_text(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install pypdf to read PDF resumes") from exc
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        if text.strip():
            return text
        raise ValueError("No embedded text was found. Convert the PDF to an image and use OCR.")
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tiff"}:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Install Pillow and pytesseract (plus the Tesseract binary) for OCR") from exc
        return pytesseract.image_to_string(Image.open(path))
    raise ValueError(f"Unsupported resume type: {suffix or 'unknown'}")
