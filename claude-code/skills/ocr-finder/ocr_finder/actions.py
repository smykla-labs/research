"""Action functions for OCR text finding."""

from pathlib import Path

from ocr_finder.core import extract_text_regions
from ocr_finder.models import SearchOptions, TextMatch, TextNotFoundError


def sanitize_image_path(image_path: str | Path) -> Path:
    """Validate and resolve image path.

    Args:
        image_path: Path to image file (string or Path).

    Returns:
        Resolved Path object.

    Raises:
        FileNotFoundError: If image does not exist.
        ValueError: If path is not a file.
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        msg = f"Image not found: {path}"
        raise FileNotFoundError(msg)

    if not path.is_file():
        msg = f"Path is not a file: {path}"
        raise ValueError(msg)

    return path


def find_text(
    image_path: Path | str,
    query: str,
    options: SearchOptions | None = None,
) -> tuple[TextMatch, ...]:
    """Find text matching query in image.

    Args:
        image_path: Path to image file.
        query: Text to search for.
        options: Search options (exact, case_sensitive, min_confidence).

    Returns:
        Tuple of TextMatch objects matching the query.
    """
    if options is None:
        options = SearchOptions()

    path = sanitize_image_path(image_path)
    regions = extract_text_regions(path)

    matches: list[TextMatch] = []

    for region in regions:
        if region.confidence < options.min_confidence:
            continue

        region_text = region.text if options.case_sensitive else region.text.lower()
        target = query if options.case_sensitive else query.lower()

        if options.exact:
            if region_text == target:
                matches.append(region)
        elif target in region_text:
            matches.append(region)

    return tuple(matches)


def get_click_target(
    image_path: Path | str,
    query: str,
    options: SearchOptions | None = None,
    index: int = 0,
) -> tuple[int, int]:
    """Get click coordinates for text in image.

    Args:
        image_path: Path to image file.
        query: Text to search for.
        options: Search options (exact, case_sensitive, min_confidence).
        index: Which match to return (0-indexed) if multiple found.

    Returns:
        Tuple of (x, y) coordinates for the center of the matched text.

    Raises:
        TextNotFoundError: If query not found in image.
    """
    matches = find_text(image_path, query, options)

    if not matches:
        msg = f"Text not found: '{query}'"
        raise TextNotFoundError(msg)

    if index >= len(matches):
        msg = f"Match index {index} out of range (found {len(matches)} matches)"
        raise TextNotFoundError(msg)

    return matches[index].click_coords


def list_all_text(
    image_path: Path | str,
    min_confidence: float = 0.0,
) -> tuple[TextMatch, ...]:
    """List all text regions in image.

    Args:
        image_path: Path to image file.
        min_confidence: Minimum OCR confidence threshold.

    Returns:
        Tuple of all TextMatch objects found in image.
    """
    path = sanitize_image_path(image_path)
    regions = extract_text_regions(path)

    if min_confidence > 0:
        regions = tuple(r for r in regions if r.confidence >= min_confidence)

    return regions
