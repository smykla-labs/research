"""macOS Window Controller - Find, activate, and screenshot windows across Spaces."""

from .actions import activate_window, take_screenshot
from .cli import build_filter, create_parser, main
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
    ActivationError,
    PlistReadError,
    ScreenshotError,
    WindowError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
)

__all__ = [
    "ActivationError",
    "PlistReadError",
    "ScreenshotError",
    "WindowError",
    "WindowFilter",
    "WindowInfo",
    "WindowNotFoundError",
    "activate_window",
    "build_filter",
    "create_parser",
    "filter_windows",
    "find_window",
    "find_windows",
    "get_all_windows",
    "get_process_info",
    "get_spaces_plist",
    "get_window_space_mapping",
    "main",
    "take_screenshot",
]
