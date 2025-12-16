"""Data models for OCR text finding."""

from dataclasses import dataclass


class OcrFinderError(Exception):
    """Base exception for OCR finder errors."""


class TextNotFoundError(OcrFinderError):
    """Raised when text is not found in image."""


@dataclass(frozen=True)
class BoundingBox:
    """Bounding box for detected text region."""

    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> tuple[int, int]:
        """Return center point of bounding box."""
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    @property
    def width(self) -> int:
        """Return width of bounding box."""
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        """Return height of bounding box."""
        return self.y2 - self.y1

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary representation."""
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height,
            "center_x": self.center[0],
            "center_y": self.center[1],
        }


@dataclass(frozen=True)
class TextMatch:
    """A detected text region with bounding box and confidence."""

    text: str
    bbox: BoundingBox
    confidence: float

    @property
    def click_coords(self) -> tuple[int, int]:
        """Return click target (center of bounding box)."""
        return self.bbox.center

    def to_dict(self) -> dict[str, str | float | dict[str, int]]:
        """Convert to dictionary representation."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "click_x": self.click_coords[0],
            "click_y": self.click_coords[1],
        }


@dataclass(frozen=True)
class SearchOptions:
    """Options for text search operations."""

    exact: bool = False
    case_sensitive: bool = False
    min_confidence: float = 0.5
