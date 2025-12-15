"""Data models and exceptions for Browser Controller."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class BrowserType(Enum):
    """Browser type for connection."""

    CHROME = "chrome"
    FIREFOX = "firefox"
    AUTO = "auto"  # Auto-detect running browser


class ConnectionStatus(Enum):
    """Connection status to browser."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# Base exception


class BrowserError(Exception):
    """Base exception for browser operations."""


# Connection errors


class BrowserConnectionError(BrowserError):
    """Failed to connect to browser."""


class BrowserNotFoundError(BrowserError):
    """No running browser found with remote debugging enabled."""


# Tab errors


class TabNotFoundError(BrowserError):
    """Tab not found."""


# Navigation errors


class NavigationError(BrowserError):
    """Failed to navigate to URL."""


# Element errors


class ElementNotFoundError(BrowserError):
    """Element not found on page."""


class ElementInteractionError(BrowserError):
    """Failed to interact with element."""


# Script errors


class ScriptExecutionError(BrowserError):
    """Failed to execute JavaScript."""


# Data classes


@dataclass(frozen=True)
class TabInfo:
    """Information about a browser tab."""

    tab_id: str
    url: str
    title: str
    browser_type: BrowserType
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["browser_type"] = self.browser_type.value
        return data


@dataclass(frozen=True)
class BrowserConnection:
    """Connection to a browser instance."""

    browser_type: BrowserType
    endpoint: str
    status: ConnectionStatus
    tabs: tuple[TabInfo, ...] = field(default_factory=tuple)
    # Internal connection handle (websocket, marionette client, etc.)
    _handle: Any = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excludes internal handle)."""
        return {
            "browser_type": self.browser_type.value,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "tabs": [tab.to_dict() for tab in self.tabs],
        }


@dataclass(frozen=True)
class ElementInfo:
    """Information about a DOM element."""

    selector: str
    tag_name: str
    text: str | None
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class PageContent:
    """Content of a web page."""

    url: str
    title: str
    html: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class ActionResult:
    """Result of a browser action."""

    success: bool
    action: str
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
