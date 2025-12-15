"""OCR-based text finder for macOS screenshots."""

from ocr_finder.models import BoundingBox, OcrFinderError, TextMatch, TextNotFoundError

__all__ = [
    "BoundingBox",
    "OcrFinderError",
    "TextMatch",
    "TextNotFoundError",
]
