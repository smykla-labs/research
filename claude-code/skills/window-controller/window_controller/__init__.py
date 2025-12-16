"""macOS Window Controller - Find, activate, and screenshot windows across Spaces."""

from .actions import activate_window, resolve_backend, sanitize_app_name, take_screenshot
from .core import (
    filter_windows,
    find_window,
    find_windows,
    get_all_windows,
    get_process_info,
    get_spaces_plist,
    get_window_space_mapping,
)
from .models import (
    SPACES_PLIST_PATH,
    ActivationError,
    CaptureBackend,
    PlistReadError,
    ScreenshotError,
    WindowError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
)
from .screencapturekit import is_screencapturekit_available

__all__ = [
    "SPACES_PLIST_PATH",
    "ActivationError",
    "CaptureBackend",
    "PlistReadError",
    "ScreenshotError",
    "WindowError",
    "WindowFilter",
    "WindowInfo",
    "WindowNotFoundError",
    "activate_window",
    "filter_windows",
    "find_window",
    "find_windows",
    "get_all_windows",
    "get_process_info",
    "get_spaces_plist",
    "get_window_space_mapping",
    "is_screencapturekit_available",
    "resolve_backend",
    "sanitize_app_name",
    "take_screenshot",
]
