"""macOS Window Controller - Find, activate, and screenshot windows across Spaces."""

from .actions import activate_window, sanitize_app_name, take_screenshot
from .cli import main
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
    PlistReadError,
    ScreenshotError,
    WindowError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
)

__all__ = [
    "SPACES_PLIST_PATH",
    "ActivationError",
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
    "main",
    "sanitize_app_name",
    "take_screenshot",
]
