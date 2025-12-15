"""EasyOCR wrapper for text extraction."""

from pathlib import Path

from ocr_finder.models import TextMatch


def get_reader(languages: tuple[str, ...] = ("en",)):  # type: ignore[no-untyped-def]
    """Get or create cached EasyOCR reader."""
    raise NotImplementedError("Phase 2: Implement EasyOCR reader")


def extract_text_regions(image_path: Path) -> tuple[TextMatch, ...]:
    """Extract all text regions with bounding boxes from image."""
    raise NotImplementedError("Phase 2: Implement text extraction")
