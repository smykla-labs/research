"""Data models for UI element inspection."""

from dataclasses import dataclass, field


class UiInspectorError(Exception):
    """Base exception for UI inspector errors."""


class AppNotFoundError(UiInspectorError):
    """Raised when application is not found."""


class WindowNotFoundError(UiInspectorError):
    """Raised when window is not found."""


class ElementNotFoundError(UiInspectorError):
    """Raised when UI element is not found."""


@dataclass(frozen=True)
class UIElement:
    """Information about a UI element from Accessibility API."""

    role: str
    title: str | None
    value: str | None
    position: tuple[int, int]
    size: tuple[int, int]
    enabled: bool
    focused: bool
    identifier: str | None = field(default=None)

    @property
    def center(self) -> tuple[int, int]:
        """Click target (center of element)."""
        x, y = self.position
        w, h = self.size
        return x + w // 2, y + h // 2

    @property
    def bounds(self) -> dict[str, int]:
        """Element bounds as dict."""
        return {
            "x": self.position[0],
            "y": self.position[1],
            "width": self.size[0],
            "height": self.size[1],
        }

    def to_dict(self) -> dict[str, str | int | bool | None | dict[str, int]]:
        """Convert to dictionary representation."""
        return {
            "role": self.role,
            "title": self.title,
            "value": self.value,
            "identifier": self.identifier,
            "position_x": self.position[0],
            "position_y": self.position[1],
            "width": self.size[0],
            "height": self.size[1],
            "center_x": self.center[0],
            "center_y": self.center[1],
            "enabled": self.enabled,
            "focused": self.focused,
            "bounds": self.bounds,
        }


@dataclass(frozen=True)
class ElementFilter:
    """Filter criteria for element search."""

    role: str | None = field(default=None)
    title: str | None = field(default=None)
    identifier: str | None = field(default=None)
    enabled_only: bool = field(default=True)
