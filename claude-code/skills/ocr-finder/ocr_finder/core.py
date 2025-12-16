"""EasyOCR wrapper for text extraction."""

from pathlib import Path
from typing import TYPE_CHECKING

from ocr_finder.models import BoundingBox, TextMatch

if TYPE_CHECKING:
    import easyocr

_reader_cache: dict[tuple[str, ...], "easyocr.Reader"] = {}


def get_reader(languages: tuple[str, ...] = ("en",)) -> "easyocr.Reader":
    """Get or create cached EasyOCR reader.

    Args:
        languages: Tuple of language codes (default: English only).

    Returns:
        Cached EasyOCR Reader instance.
    """
    import easyocr

    if languages not in _reader_cache:
        _reader_cache[languages] = easyocr.Reader(list(languages), gpu=False)

    return _reader_cache[languages]


def extract_text_regions(
    image_path: Path,
    languages: tuple[str, ...] = ("en",),
) -> tuple[TextMatch, ...]:
    """Extract all text regions with bounding boxes from image.

    Args:
        image_path: Path to image file.
        languages: Tuple of language codes for OCR.

    Returns:
        Tuple of TextMatch objects for each detected text region.
    """
    reader = get_reader(languages)

    # EasyOCR returns: [([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], text, confidence), ...]
    results = reader.readtext(str(image_path))

    matches: list[TextMatch] = []

    for bbox_coords, text, confidence in results:
        # bbox_coords is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        # Extract corners (top-left and bottom-right)
        x1 = int(bbox_coords[0][0])
        y1 = int(bbox_coords[0][1])
        x2 = int(bbox_coords[2][0])
        y2 = int(bbox_coords[2][1])

        bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
        match = TextMatch(text=str(text), bbox=bbox, confidence=float(confidence))
        matches.append(match)

    return tuple(matches)
