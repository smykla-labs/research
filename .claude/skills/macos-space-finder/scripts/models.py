"""Data models and exceptions for macOS Space Finder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Constants
SPACES_PLIST_PATH = Path.home() / "Library/Preferences/com.apple.spaces.plist"
DEFAULT_RETURN_DELAY = 1.0

# Space type constants
SPACE_TYPE_NORMAL = 0
SPACE_TYPE_FULLSCREEN = 4
SPACE_TYPE_TILE = 5
SPACE_TYPE_WALL = 6

SPACE_TYPE_NAMES = {
    SPACE_TYPE_NORMAL: "Normal",
    SPACE_TYPE_FULLSCREEN: "FullSc",
    SPACE_TYPE_TILE: "Tile",
    SPACE_TYPE_WALL: "Wall",
}


class SpacesError(Exception):
    """Base exception for spaces-related errors."""


class PlistReadError(SpacesError):
    """Failed to read the spaces plist file."""


class ActivationError(SpacesError):
    """Failed to activate an application."""


@dataclass(frozen=True)
class SpaceInfo:
    """Information about a macOS Space/Desktop."""

    index: int
    display: str
    managed_space_id: int
    space_type: int
    uuid: str
    is_current: bool
    app_name: str | None
    window_title: str | None
    window_id: int | None
    pid: int | None

    @property
    def type_name(self) -> str:
        """Human-readable space type name."""
        return SPACE_TYPE_NAMES.get(self.space_type, str(self.space_type))

    @property
    def display_app_name(self) -> str:
        """App name for display, with fallback."""
        return self.app_name or "-"

    @property
    def display_title(self) -> str:
        """Window title for display, truncated."""
        title = self.window_title or "-"
        return title[:38]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "index": self.index,
            "display": self.display,
            "managed_space_id": self.managed_space_id,
            "space_type": self.space_type,
            "type_name": self.type_name,
            "uuid": self.uuid,
            "is_current": self.is_current,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "window_id": self.window_id,
            "pid": self.pid,
        }
