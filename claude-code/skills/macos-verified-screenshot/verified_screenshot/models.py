"""Data models and exceptions for macOS Verified Screenshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class VerificationStrategy(Enum):
    """Available verification strategies."""

    BASIC = "basic"  # File exists, size > 0, valid image
    DIMENSIONS = "dimensions"  # Bounds match expected
    CONTENT = "content"  # Perceptual hash differs from blank/previous
    TEXT = "text"  # OCR verification of expected text
    ALL = "all"  # All strategies combined


class RetryStrategy(Enum):
    """Retry strategies on verification failure."""

    FIXED = "fixed"  # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    REACTIVATE = "reactivate"  # Re-activate window before retry


# Default settings
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_DELAY_MS = 500
DEFAULT_SETTLE_MS = 1000
DEFAULT_HASH_THRESHOLD = 5  # Hamming distance threshold for "different"


class ScreenshotError(Exception):
    """Base exception for screenshot operations."""


class CaptureError(ScreenshotError):
    """Failed to capture screenshot."""


class VerificationError(ScreenshotError):
    """Screenshot verification failed."""


class WindowNotFoundError(ScreenshotError):
    """Target window not found."""


class MaxRetriesError(ScreenshotError):
    """Max retries exceeded without successful verification."""


@dataclass(frozen=True)
class VerificationResult:
    """Result of a single verification check."""

    strategy: VerificationStrategy
    passed: bool
    message: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "strategy": self.strategy.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class CaptureResult:
    """Result of a screenshot capture attempt."""

    path: Path
    attempt: int
    window_id: int
    app_name: str
    window_title: str
    expected_width: float
    expected_height: float
    actual_width: int
    actual_height: int
    verifications: tuple[VerificationResult, ...] = field(default_factory=tuple)
    verified: bool = False
    image_hash: str | None = None

    @property
    def all_passed(self) -> bool:
        """True if all verifications passed."""
        return all(v.passed for v in self.verifications)

    @property
    def dimensions_match(self) -> bool:
        """True if dimensions approximately match (within 10%)."""
        width_ok = abs(self.actual_width - self.expected_width) < self.expected_width * 0.1
        height_ok = abs(self.actual_height - self.expected_height) < self.expected_height * 0.1
        return width_ok and height_ok

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "attempt": self.attempt,
            "window_id": self.window_id,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "expected_dimensions": {
                "width": self.expected_width,
                "height": self.expected_height,
            },
            "actual_dimensions": {
                "width": self.actual_width,
                "height": self.actual_height,
            },
            "verified": self.verified,
            "image_hash": self.image_hash,
            "verifications": [v.to_dict() for v in self.verifications],
        }


@dataclass(frozen=True)
class CaptureConfig:
    """Configuration for screenshot capture with verification."""

    # Target specification
    app_name: str | None = None
    title_pattern: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None

    # Output
    output_path: str | None = None

    # Capture behavior
    activate_first: bool = True
    settle_ms: int = DEFAULT_SETTLE_MS
    no_shadow: bool = True

    # Verification
    verification_strategies: tuple[VerificationStrategy, ...] = (VerificationStrategy.BASIC,)
    expected_text: tuple[str, ...] = field(default_factory=tuple)
    hash_threshold: int = DEFAULT_HASH_THRESHOLD

    # Retry
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay_ms: int = DEFAULT_RETRY_DELAY_MS
    retry_strategy: RetryStrategy = RetryStrategy.FIXED

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "app_name": self.app_name,
            "title_pattern": self.title_pattern,
            "pid": self.pid,
            "path_contains": self.path_contains,
            "path_excludes": self.path_excludes,
            "args_contains": self.args_contains,
            "output_path": self.output_path,
            "activate_first": self.activate_first,
            "settle_ms": self.settle_ms,
            "no_shadow": self.no_shadow,
            "verification_strategies": [s.value for s in self.verification_strategies],
            "expected_text": list(self.expected_text),
            "hash_threshold": self.hash_threshold,
            "max_retries": self.max_retries,
            "retry_delay_ms": self.retry_delay_ms,
            "retry_strategy": self.retry_strategy.value,
        }


@dataclass(frozen=True)
class WindowTarget:
    """Target window information for screenshot capture."""

    window_id: int
    app_name: str
    window_title: str
    pid: int
    bounds_x: float
    bounds_y: float
    bounds_width: float
    bounds_height: float
    space_index: int | None = None
    exe_path: str | None = None
    cmdline: tuple[str, ...] = field(default_factory=tuple)

    @property
    def bounds(self) -> dict:
        """Window bounds as dict."""
        return {
            "x": self.bounds_x,
            "y": self.bounds_y,
            "width": self.bounds_width,
            "height": self.bounds_height,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "window_id": self.window_id,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "pid": self.pid,
            "bounds": self.bounds,
            "space_index": self.space_index,
            "exe_path": self.exe_path,
            "cmdline": list(self.cmdline),
        }
