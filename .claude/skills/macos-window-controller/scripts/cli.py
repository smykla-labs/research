"""Command-line interface for macOS Window Controller."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from .actions import activate_window, take_screenshot
from .core import find_windows, get_all_windows
from .models import WindowError, WindowFilter

if TYPE_CHECKING:
    from collections.abc import Sequence


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


def _list_windows_table(main_only: bool = True) -> None:
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


def _handle_list(args) -> int:
    """Handle --list action."""
    windows = get_all_windows()
    if not args.all_windows:
        windows = [w for w in windows if w.layer == 0 and w.window_title]
    if args.json:
        print(json.dumps([w.to_dict() for w in windows], indent=2))
    else:
        _list_windows_table(main_only=not args.all_windows)
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
