"""Action functions for OCR text finding."""

from pathlib import Path

from ocr_finder.models import TextMatch


def find_text(
    image_path: Path,
    query: str,
    *,
    exact: bool = False,
    case_sensitive: bool = False,
    min_confidence: float = 0.5,
) -> tuple[TextMatch, ...]:
    """Find text matching query in image."""
    raise NotImplementedError("Phase 2: Implement find_text")


def get_click_target(image_path: Path, query: str, *, index: int = 0) -> tuple[int, int]:
    """Get click coordinates for text in image."""
    raise NotImplementedError("Phase 2: Implement get_click_target")
