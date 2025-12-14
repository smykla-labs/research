#!/usr/bin/env python3
"""
Find macOS Space/Desktop by application name.

This script reads the com.apple.spaces.plist to find which space
contains a specific application (especially full-screen apps).

Usage:
    ./find_space.py --list              # List all spaces
    ./find_space.py --current           # Show current space app name
    ./find_space.py "GoLand"            # Find space with GoLand
    ./find_space.py --go "GoLand"       # Switch to GoLand space, return to original
"""

from __future__ import annotations

import argparse
import plistlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

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


class AppActivationError(SpacesError):
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


def get_spaces_plist() -> dict:
    """
    Read the spaces plist file.

    Returns:
        Parsed plist data as a dictionary.

    Raises:
        PlistReadError: If the plist cannot be read or parsed.
    """
    result = subprocess.run(
        ["plutil", "-convert", "xml1", "-o", "-", str(SPACES_PLIST_PATH)],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise PlistReadError(f"Cannot read spaces plist: {stderr}")

    try:
        return plistlib.loads(result.stdout)
    except plistlib.InvalidFileException as e:
        raise PlistReadError(f"Invalid plist format: {e}") from e


def parse_spaces(plist_data: dict) -> list[SpaceInfo]:
    """
    Parse the plist data and extract space information.

    Args:
        plist_data: Parsed plist dictionary.

    Returns:
        List of SpaceInfo objects for all spaces.
    """
    spaces: list[SpaceInfo] = []

    config = plist_data.get("SpacesDisplayConfiguration", {})
    mgmt_data = config.get("Management Data", {})
    monitors = mgmt_data.get("Monitors", [])

    for monitor in monitors:
        display_id = monitor.get("Display Identifier", "Unknown")
        current_space = monitor.get("Current Space", {})
        current_space_id = current_space.get("ManagedSpaceID", 0)
        monitor_spaces = monitor.get("Spaces", [])

        for idx, space in enumerate(monitor_spaces, start=1):
            managed_id = space.get("ManagedSpaceID", 0)

            # Extract full-screen app info if present
            app_name = None
            window_title = None
            window_id = None
            pid = None

            tile_mgr = space.get("TileLayoutManager", {})
            tile_spaces = tile_mgr.get("TileSpaces", [])

            if tile_spaces:
                primary_tile = tile_spaces[0]
                app_name = primary_tile.get("appName")
                window_title = primary_tile.get("name")
                window_id = primary_tile.get("TileWindowID")
                pid = primary_tile.get("pid")

            space_info = SpaceInfo(
                index=idx,
                display=display_id,
                managed_space_id=managed_id,
                space_type=space.get("type", 0),
                uuid=space.get("uuid", ""),
                is_current=(managed_id == current_space_id),
                app_name=app_name,
                window_title=window_title,
                window_id=window_id,
                pid=pid,
            )
            spaces.append(space_info)

    return spaces


def find_space_by_app(spaces: Sequence[SpaceInfo], app_query: str) -> list[SpaceInfo]:
    """
    Find spaces by application name (case-insensitive partial match).

    Args:
        spaces: List of SpaceInfo objects to search.
        app_query: Search query string.

    Returns:
        List of matching SpaceInfo objects.
    """
    query_lower = app_query.lower()
    matches: list[SpaceInfo] = []

    for space in spaces:
        app = space.app_name or ""
        title = space.window_title or ""

        if query_lower in app.lower() or query_lower in title.lower():
            matches.append(space)

    return matches


def get_current_space(spaces: Sequence[SpaceInfo]) -> SpaceInfo | None:
    """
    Get the current space info.

    Args:
        spaces: List of SpaceInfo objects.

    Returns:
        The current SpaceInfo, or None if not found.
    """
    for space in spaces:
        if space.is_current:
            return space

    return None


def _sanitize_app_name(app_name: str) -> str:
    """
    Sanitize application name for safe use in AppleScript.

    Args:
        app_name: Raw application name.

    Returns:
        Sanitized application name safe for AppleScript.

    Raises:
        ValueError: If the app name contains invalid characters.
    """
    # Allow only alphanumeric, spaces, hyphens, underscores, and periods
    if not re.match(r"^[\w\s.\-]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")

    # Escape any remaining quotes (shouldn't exist after regex, but defense in depth)
    return app_name.replace('"', '\\"')


def activate_app(app_name: str) -> None:
    """
    Activate an application via AppleScript.

    Args:
        app_name: Name of the application to activate.

    Raises:
        AppActivationError: If the application cannot be activated.
        ValueError: If the app name contains invalid characters.
    """
    sanitized_name = _sanitize_app_name(app_name)
    script = f'tell application "{sanitized_name}" to activate'

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise AppActivationError(f"Failed to activate {app_name}: {stderr}")


def go_to_space(
    spaces: Sequence[SpaceInfo],
    app_query: str,
    return_delay: float = DEFAULT_RETURN_DELAY,
) -> tuple[SpaceInfo | None, SpaceInfo | None, bool]:
    """
    Switch to space containing app, wait, then return to original space.

    Args:
        spaces: List of SpaceInfo objects.
        app_query: Search query for target application.
        return_delay: Seconds to wait before returning to original space.

    Returns:
        Tuple of (target_space, original_space, success).
    """
    original = get_current_space(spaces)
    matches = find_space_by_app(spaces, app_query)

    if not matches:
        return None, original, False

    target = matches[0]

    if target.is_current:
        return target, original, True

    # Activate target app
    if target.app_name:
        activate_app(target.app_name)
        time.sleep(return_delay)

        # Return to original space
        if original and original.app_name:
            activate_app(original.app_name)
        elif original:
            # For normal desktop, activate Finder
            activate_app("Finder")

    return target, original, True


def list_spaces(spaces: Sequence[SpaceInfo]) -> None:
    """Print all spaces in a formatted table."""
    header = f"{'Idx':<4} {'Current':<8} {'Type':<6} {'App Name':<20} {'Window Title':<40}"
    print(header)
    print("-" * 80)

    for space in spaces:
        current_marker = "*" if space.is_current else ""
        print(
            f"{space.index:<4} {current_marker:<8} {space.type_name:<6} "
            f"{space.display_app_name:<20} {space.display_title:<40}"
        )


def print_space_details(space: SpaceInfo) -> None:
    """Print detailed information about a space."""
    print(f"Found: Space {space.index}")
    print(f"  App: {space.app_name}")
    print(f"  Title: {space.window_title}")
    print(f"  Current: {'Yes' if space.is_current else 'No'}")
    print(f"  Window ID: {space.window_id}")
    print(f"  PID: {space.pid}")
    print()


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Find and switch to macOS Spaces by application name.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list              List all spaces
  %(prog)s --current           Show current space's app name
  %(prog)s "GoLand"            Find space containing GoLand
  %(prog)s --go "GoLand"       Switch to GoLand space, then return
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all spaces with their details",
    )

    parser.add_argument(
        "--current",
        action="store_true",
        help="Print the current space's application name",
    )

    parser.add_argument(
        "--go",
        metavar="APP",
        help="Switch to the space containing APP, then return to original",
    )

    parser.add_argument(
        "app_query",
        nargs="?",
        metavar="APP",
        help="Find space containing this application (partial match)",
    )

    return parser


def _handle_list(spaces: Sequence[SpaceInfo]) -> int:
    """Handle --list command."""
    list_spaces(spaces)
    return 0


def _handle_current(spaces: Sequence[SpaceInfo]) -> int:
    """Handle --current command."""
    current = get_current_space(spaces)
    if current:
        print(current.app_name or "Desktop")
    else:
        print("Unknown")
    return 0


def _handle_go(spaces: Sequence[SpaceInfo], app_query: str) -> int:
    """Handle --go command."""
    try:
        target, original, success = go_to_space(spaces, app_query)
    except (AppActivationError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not success:
        print(f"No space found for app: {app_query}")
        return 1

    orig_name = original.app_name if original else "Desktop"
    target_name = target.app_name if target else "Unknown"
    print(f"Switched to: {target_name}")
    print(f"Returned to: {orig_name}")
    return 0


def _handle_find(spaces: Sequence[SpaceInfo], app_query: str) -> int:
    """Handle find (positional argument) command."""
    matches = find_space_by_app(spaces, app_query)

    if not matches:
        print(f"No space found for app: {app_query}")
        print("\nAvailable spaces:")
        list_spaces(spaces)
        return 1

    for match in matches:
        print_space_details(match)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """
    Main entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Validate arguments
    if not any([args.list, args.current, args.go, args.app_query]):
        parser.print_help()
        return 1

    # Load spaces data
    try:
        plist_data = get_spaces_plist()
        spaces = parse_spaces(plist_data)
    except PlistReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Dispatch to handlers
    if args.list:
        return _handle_list(spaces)

    if args.current:
        return _handle_current(spaces)

    if args.go:
        return _handle_go(spaces, args.go)

    if args.app_query:
        return _handle_find(spaces, args.app_query)

    return 0


if __name__ == "__main__":
    sys.exit(main())
