"""Core window detection and filtering for macOS Window Controller."""

from __future__ import annotations

import functools
import plistlib
import re
import subprocess
from pathlib import Path

from .models import PlistReadError, WindowFilter, WindowInfo

# Spaces plist path
SPACES_PLIST_PATH = Path.home() / "Library/Preferences/com.apple.spaces.plist"


@functools.cache
def _get_quartz():
    """Lazy load Quartz framework (cached)."""
    import Quartz

    return Quartz


@functools.cache
def _get_psutil():
    """Lazy load psutil (cached)."""
    import psutil

    return psutil


def get_spaces_plist() -> dict:
    """Read the spaces plist file.

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


def get_window_space_mapping(plist_data: dict) -> dict[int, int]:
    """Map window IDs to Space indexes (1-based)."""
    window_to_space: dict[int, int] = {}

    config = plist_data.get("SpacesDisplayConfiguration", {})
    mgmt_data = config.get("Management Data", {})
    monitors = mgmt_data.get("Monitors", [])

    for monitor in monitors:
        monitor_spaces = monitor.get("Spaces", [])
        for idx, space in enumerate(monitor_spaces, start=1):
            tile_mgr = space.get("TileLayoutManager", {})
            for tile in tile_mgr.get("TileSpaces", []):
                window_id = tile.get("TileWindowID")
                if window_id:
                    window_to_space[window_id] = idx

    return window_to_space


def get_process_info(pid: int) -> tuple[str | None, list[str]]:
    """Get process executable path and command line."""
    psutil = _get_psutil()

    try:
        proc = psutil.Process(pid)
        return proc.exe(), proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None, []


def get_all_windows() -> list[WindowInfo]:
    """Get all windows using CGWindowListCopyWindowInfo."""
    Q = _get_quartz()

    all_windows = Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionAll, Q.kCGNullWindowID)
    if not all_windows:
        return []

    # Try to get space mapping, gracefully degrade if plist unavailable
    try:
        plist_data = get_spaces_plist()
        window_space_map = get_window_space_mapping(plist_data)
    except PlistReadError:
        window_space_map = {}
    process_cache: dict[int, tuple[str | None, list[str]]] = {}
    windows: list[WindowInfo] = []

    for window in all_windows:
        pid = window.get("kCGWindowOwnerPID", 0)
        if pid not in process_cache:
            process_cache[pid] = get_process_info(pid)
        exe_path, cmdline = process_cache[pid]
        bounds = window.get("kCGWindowBounds", {})

        windows.append(
            WindowInfo(
                app_name=window.get("kCGWindowOwnerName", "") or "",
                window_title=window.get("kCGWindowName", "") or "",
                window_id=window.get("kCGWindowNumber", 0),
                pid=pid,
                layer=window.get("kCGWindowLayer", 0),
                on_screen=window.get("kCGWindowIsOnscreen"),
                alpha=window.get("kCGWindowAlpha", 0.0),
                bounds_x=bounds.get("X", 0.0),
                bounds_y=bounds.get("Y", 0.0),
                bounds_width=bounds.get("Width", 0.0),
                bounds_height=bounds.get("Height", 0.0),
                space_index=window_space_map.get(window.get("kCGWindowNumber", 0)),
                exe_path=exe_path,
                cmdline=cmdline,
            )
        )

    return windows


def _matches_filter(w: WindowInfo, f: WindowFilter) -> bool:
    """Check if a window matches the filter criteria."""
    # Main window check
    if f.main_window_only and (w.layer != 0 or not w.window_title):
        return False

    # App name check (partial, case-insensitive)
    if f.app_name and f.app_name.lower() not in w.app_name.lower():
        return False

    # Title pattern check (regex)
    if f.title_pattern and not re.search(f.title_pattern, w.window_title, re.IGNORECASE):
        return False

    # PID and path checks combined
    pid_ok = f.pid is None or w.pid == f.pid
    path_contains_ok = not f.path_contains or (w.exe_path and f.path_contains in w.exe_path)
    path_excludes_ok = not f.path_excludes or not w.exe_path or f.path_excludes not in w.exe_path
    args_ok = not f.args_contains or f.args_contains in " ".join(w.cmdline)

    return pid_ok and path_contains_ok and path_excludes_ok and args_ok


def filter_windows(windows: list[WindowInfo], f: WindowFilter) -> list[WindowInfo]:
    """Filter windows based on criteria."""
    return [w for w in windows if _matches_filter(w, f)]


def find_window(f: WindowFilter) -> WindowInfo | None:
    """Find the first window matching filter."""
    matches = filter_windows(get_all_windows(), f)
    return matches[0] if matches else None


def find_windows(f: WindowFilter) -> list[WindowInfo]:
    """Find all windows matching filter."""
    return filter_windows(get_all_windows(), f)
