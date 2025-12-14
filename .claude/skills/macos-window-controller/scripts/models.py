"""Data models and exceptions for macOS Window Controller."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

# Spaces plist path
SPACES_PLIST_PATH = Path.home() / "Library/Preferences/com.apple.spaces.plist"


class WindowError(Exception):
    """Base exception for window operations."""


class WindowNotFoundError(WindowError):
    """Window not found."""


class ActivationError(WindowError):
    """Failed to activate window."""


class ScreenshotError(WindowError):
    """Failed to take screenshot."""


class PlistReadError(WindowError):
    """Failed to read plist file."""


@dataclass(frozen=True)
class WindowInfo:
    """Information about a macOS window."""

    app_name: str
    window_title: str
    window_id: int
    pid: int
    layer: int
    on_screen: bool | None
    alpha: float
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
        """Convert to dictionary."""
        data = asdict(self)
        data["bounds"] = self.bounds
        del data["bounds_x"]
        del data["bounds_y"]
        del data["bounds_width"]
        del data["bounds_height"]
        return data


@dataclass
class WindowFilter:
    """Filter criteria for window search."""

    app_name: str | None = None
    title_pattern: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None
    main_window_only: bool = True
