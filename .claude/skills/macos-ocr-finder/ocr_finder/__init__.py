"""OCR-based text finder for macOS screenshots."""

from ocr_finder.actions import find_text, get_click_target, list_all_text
from ocr_finder.models import (
    BoundingBox,
    OcrFinderError,
    SearchOptions,
    TextMatch,
    TextNotFoundError,
)

__all__ = [
    # Models
    "BoundingBox",
    # Errors
    "OcrFinderError",
    "SearchOptions",
    "TextMatch",
    "TextNotFoundError",
    # Actions
    "find_text",
    "get_click_target",
    "list_all_text",
]
