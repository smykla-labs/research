"""Core functionality for reading and parsing macOS Spaces."""

from __future__ import annotations

import plistlib
import subprocess
from typing import TYPE_CHECKING

from .models import SPACES_PLIST_PATH, PlistReadError, SpaceInfo

if TYPE_CHECKING:
    from collections.abc import Sequence


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
