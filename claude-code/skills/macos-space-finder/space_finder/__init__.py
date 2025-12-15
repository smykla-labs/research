"""macOS Space Finder - Find and navigate Spaces by application name."""

from .actions import (
    activate_app,
    go_to_space,
    return_to_space,
    sanitize_app_name,
    switch_to_space,
)
from .cli import list_spaces, main, print_space_details
from .core import find_space_by_app, get_current_space, get_spaces_plist, parse_spaces
from .models import (
    DEFAULT_RETURN_DELAY,
    SPACE_TYPE_FULLSCREEN,
    SPACE_TYPE_NAMES,
    SPACE_TYPE_NORMAL,
    SPACE_TYPE_TILE,
    SPACE_TYPE_WALL,
    SPACES_PLIST_PATH,
    ActivationError,
    PlistReadError,
    SpaceInfo,
    SpacesError,
)

__all__ = [
    "DEFAULT_RETURN_DELAY",
    "SPACES_PLIST_PATH",
    "SPACE_TYPE_FULLSCREEN",
    "SPACE_TYPE_NAMES",
    "SPACE_TYPE_NORMAL",
    "SPACE_TYPE_TILE",
    "SPACE_TYPE_WALL",
    "ActivationError",
    "PlistReadError",
    "SpaceInfo",
    "SpacesError",
    "activate_app",
    "find_space_by_app",
    "get_current_space",
    "get_spaces_plist",
    "go_to_space",
    "list_spaces",
    "main",
    "parse_spaces",
    "print_space_details",
    "return_to_space",
    "sanitize_app_name",
    "switch_to_space",
]
