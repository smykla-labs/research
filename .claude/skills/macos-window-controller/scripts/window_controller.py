#!/usr/bin/env python3
"""
macOS Window Controller - Versatile window detection and control.

Find, activate, and take screenshots of macOS windows across Spaces.
Supports filtering by app name, title patterns, process path, and command line.

Usage:
    ./window_controller.py --list                     # List all windows
    ./window_controller.py --find "GoLand"            # Find by app name
    ./window_controller.py --find "GoLand" --path-contains ".gradle"  # Sandbox only
    ./window_controller.py --activate "GoLand"        # Activate window
    ./window_controller.py --screenshot "GoLand"      # Take screenshot

Requirements:
    pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa psutil
"""

from __future__ import annotations

import argparse
import functools
import json
import plistlib
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

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


class WindowError(Exception):
    """Base exception for window operations."""


class WindowNotFoundError(WindowError):
    """Window not found."""


class ActivationError(WindowError):
    """Failed to activate window."""


class ScreenshotError(WindowError):
    """Failed to take screenshot."""


@dataclass
class WindowInfo:
    """Information about a macOS window."""

    app_name: str
    window_title: str
    window_id: int
    pid: int
    layer: int
    on_screen: bool | None
    alpha: float
    bounds_x: float
    bounds_y: float
    bounds_width: float
    bounds_height: float
    space_index: int | None = None
    exe_path: str | None = None
    cmdline: list[str] = field(default_factory=list)

    @property
    def bounds(self) -> dict:
        """Window bounds as dict."""
        return {
            "x": self.bounds_x,
            "y": self.bounds_y,
            "width": self.bounds_width,
            "height": self.bounds_height,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["bounds"] = self.bounds
        del data["bounds_x"]
        del data["bounds_y"]
        del data["bounds_width"]
        del data["bounds_height"]
        return data


@dataclass
class WindowFilter:
    """Filter criteria for window search."""

    app_name: str | None = None
    title_pattern: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None
    main_window_only: bool = True


def get_spaces_plist() -> dict:
    """Read the spaces plist file."""
    result = subprocess.run(
        ["plutil", "-convert", "xml1", "-o", "-", str(SPACES_PLIST_PATH)],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return {}

    try:
        return plistlib.loads(result.stdout)
    except plistlib.InvalidFileException:
        return {}


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

    plist_data = get_spaces_plist()
    window_space_map = get_window_space_mapping(plist_data)
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


def _sanitize_app_name(app_name: str) -> str:
    """Sanitize application name for AppleScript."""
    if not re.match(r"^[\w\s.\-()]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")
    return app_name.replace('"', '\\"')


def activate_window(f: WindowFilter, wait_time: float = 0.5) -> WindowInfo:
    """Activate a window (switches to its Space)."""
    window = find_window(f)
    if not window:
        raise WindowNotFoundError("No window found matching filter")

    try:
        sanitized_name = _sanitize_app_name(window.app_name)
        result = subprocess.run(
            ["osascript", "-e", f'tell application "{sanitized_name}" to activate'],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise ActivationError(f"Failed to activate {window.app_name}: {stderr}")
        if wait_time > 0:
            time.sleep(wait_time)
        return window
    except ValueError as e:
        raise ActivationError(str(e)) from e


def take_screenshot(
    f: WindowFilter,
    output_path: str | Path | None = None,
    activate_first: bool = True,
    settle_ms: int = 1000,
) -> Path:
    """Take a screenshot of a window."""
    Q = _get_quartz()

    window = find_window(f)
    if not window:
        raise WindowNotFoundError("No window found matching filter")

    if activate_first:
        activate_window(f, wait_time=settle_ms / 1000.0)

    if output_path is None:
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^\w\-]", "_", window.app_name.lower())
        output_path = screenshots_dir / f"{safe_name}_{timestamp}.png"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Q.CGWindowListCreateImage(
        Q.CGRectNull,
        Q.kCGWindowListOptionIncludingWindow,
        window.window_id,
        Q.kCGWindowImageDefault,
    )
    if image is None:
        raise ScreenshotError(f"Failed to capture window {window.window_id}")

    url = Q.CFURLCreateWithFileSystemPath(
        None, str(output_path.absolute()), Q.kCFURLPOSIXPathStyle, False
    )
    dest = Q.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    if dest is None:
        raise ScreenshotError(f"Failed to create destination: {output_path}")

    Q.CGImageDestinationAddImage(dest, image, None)
    if not Q.CGImageDestinationFinalize(dest):
        raise ScreenshotError(f"Failed to finalize image: {output_path}")

    return output_path


def list_all_windows(main_only: bool = True) -> None:
    """Print all windows in a formatted table."""
    windows = get_all_windows()
    if main_only:
        windows = [w for w in windows if w.layer == 0 and w.window_title]

    if not windows:
        print("No windows found.")
        print("\nTip: Make sure Screen Recording permission is granted.")
        return

    print(f"{'App':<20} {'Title':<40} {'Space':<6} {'PID':<8}")
    print("-" * 80)
    for w in windows:
        space = str(w.space_index) if w.space_index else "-"
        title = w.window_title[:38] if w.window_title else "-"
        print(f"{w.app_name[:18]:<20} {title:<40} {space:<6} {w.pid:<8}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="macOS Window Controller - Find, activate, and screenshot windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                              List all windows
  %(prog)s --find "GoLand"                     Find GoLand window
  %(prog)s --find "GoLand" --path-contains ".gradle"  Find sandbox GoLand
  %(prog)s --activate "GoLand"                 Activate GoLand
  %(prog)s --screenshot "GoLand" -o shot.png   Take screenshot

Filtering:
  --title PATTERN       Regex match on window title
  --pid PID             Match specific process ID
  --path-contains STR   Executable path must contain STR
  --path-excludes STR   Executable path must not contain STR
  --args-contains STR   Command line must contain STR
        """,
    )

    actions = parser.add_argument_group("actions")
    actions.add_argument("--list", "-l", action="store_true", help="List all windows")
    actions.add_argument(
        "--find", "-f", metavar="APP", nargs="?", const="", help="Find window by app name"
    )
    actions.add_argument("--activate", "-a", metavar="APP", help="Activate window")
    actions.add_argument("--screenshot", "-s", metavar="APP", help="Take screenshot of window")

    output_format = parser.add_argument_group("output format")
    output_format.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    filters = parser.add_argument_group("filters")
    filters.add_argument("--title", "-t", metavar="PATTERN", help="Regex for window title")
    filters.add_argument("--pid", type=int, metavar="PID", help="Filter by process ID")
    filters.add_argument("--path-contains", metavar="STR", help="Exe path must contain STR")
    filters.add_argument("--path-excludes", metavar="STR", help="Exe path must NOT contain STR")
    filters.add_argument("--args-contains", metavar="STR", help="Command line must contain STR")
    filters.add_argument("--all-windows", action="store_true", help="Include non-main windows")

    screenshot_opts = parser.add_argument_group("screenshot options")
    screenshot_opts.add_argument("--output", "-o", metavar="PATH", help="Output path")
    screenshot_opts.add_argument("--no-activate", action="store_true", help="Don't activate first")
    screenshot_opts.add_argument(
        "--settle-ms", type=int, default=1000, metavar="MS", help="Wait time (default: 1000ms)"
    )

    return parser


def build_filter(args) -> WindowFilter:
    """Build WindowFilter from parsed arguments."""
    app_name = args.find if args.find is not None else (args.activate or args.screenshot)
    return WindowFilter(
        app_name=app_name if app_name else None,
        title_pattern=args.title,
        pid=args.pid,
        path_contains=args.path_contains,
        path_excludes=args.path_excludes,
        args_contains=args.args_contains,
        main_window_only=not args.all_windows,
    )


def _handle_list(args) -> int:
    """Handle --list action."""
    windows = get_all_windows()
    if not args.all_windows:
        windows = [w for w in windows if w.layer == 0 and w.window_title]
    if args.json:
        print(json.dumps([w.to_dict() for w in windows], indent=2))
    else:
        list_all_windows(main_only=not args.all_windows)
    return 0


def _handle_find(args, f: WindowFilter) -> int:
    """Handle --find action."""
    windows = find_windows(f)
    if not windows:
        msg = {"error": "No windows found matching filter"}
        print(json.dumps(msg) if args.json else "No windows found matching filter.")
        return 1

    if args.json:
        data = windows[0].to_dict() if len(windows) == 1 else [w.to_dict() for w in windows]
        print(json.dumps(data, indent=2))
    else:
        for w in windows:
            print(f"Found: {w.app_name}\n  Title: {w.window_title}")
            print(f"  Window ID: {w.window_id}\n  PID: {w.pid}")
            if w.exe_path:
                print(f"  Path: {w.exe_path}")
            if w.cmdline:
                print(f"  Args: {' '.join(w.cmdline[:3])}...")
            print(f"  Space: {w.space_index or 'unknown'}")
            print(f"  Bounds: {int(w.bounds_width)}x{int(w.bounds_height)}\n")
    return 0


def _handle_activate(args, f: WindowFilter) -> int:
    """Handle --activate action."""
    window = activate_window(f)
    if args.json:
        print(json.dumps({"activated": window.to_dict()}))
    else:
        print(f"Activated: {window.app_name}\n  Title: {window.window_title}")
    return 0


def _handle_screenshot(args, f: WindowFilter) -> int:
    """Handle --screenshot action."""
    path = take_screenshot(f, args.output, not args.no_activate, args.settle_ms)
    if args.json:
        print(json.dumps({"screenshot": str(path)}))
    else:
        print(f"Screenshot saved: {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not any([args.list, args.find is not None, args.activate, args.screenshot]):
        parser.print_help()
        return 1

    try:
        if args.list:
            return _handle_list(args)

        f = build_filter(args)
        if args.find is not None:
            return _handle_find(args, f)
        if args.activate:
            return _handle_activate(args, f)
        if args.screenshot:
            return _handle_screenshot(args, f)

    except WindowError as e:
        print(json.dumps({"error": str(e)}) if args.json else f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
