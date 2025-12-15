"""Command-line interface for macOS Space Finder."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from .actions import go_to_space
from .core import find_space_by_app, get_current_space, get_spaces_plist, parse_spaces
from .models import ActivationError, PlistReadError, SpaceInfo

if TYPE_CHECKING:
    from collections.abc import Sequence


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
        "-l",
        action="store_true",
        help="List all spaces with their details",
    )

    parser.add_argument(
        "--current",
        "-c",
        action="store_true",
        help="Print the current space's application name",
    )

    parser.add_argument(
        "--go",
        "-g",
        metavar="APP",
        help="Switch to the space containing APP, then return to original",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    parser.add_argument(
        "app_query",
        nargs="?",
        metavar="APP",
        help="Find space containing this application (partial match)",
    )

    return parser


def _handle_list(spaces: Sequence[SpaceInfo], *, json_output: bool = False) -> int:
    """Handle --list command."""
    if json_output:
        print(json.dumps([s.to_dict() for s in spaces], indent=2))
    else:
        list_spaces(spaces)
    return 0


def _handle_current(spaces: Sequence[SpaceInfo], *, json_output: bool = False) -> int:
    """Handle --current command."""
    current = get_current_space(spaces)
    if json_output:
        if current:
            print(json.dumps(current.to_dict(), indent=2))
        else:
            print(json.dumps(None))
    elif current:
        print(current.app_name or "Desktop")
    else:
        print("Unknown")
    return 0


def _handle_go(spaces: Sequence[SpaceInfo], app_query: str, *, json_output: bool = False) -> int:
    """Handle --go command."""
    try:
        target, original, success = go_to_space(spaces, app_query)
    except (ActivationError, ValueError) as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    if not success:
        if json_output:
            print(json.dumps({"error": f"No space found for app: {app_query}"}))
        else:
            print(f"No space found for app: {app_query}")
        return 1

    if json_output:
        print(
            json.dumps(
                {
                    "target": target.to_dict() if target else None,
                    "original": original.to_dict() if original else None,
                },
                indent=2,
            )
        )
    else:
        orig_name = original.app_name if original else "Desktop"
        target_name = target.app_name if target else "Unknown"
        print(f"Switched to: {target_name}")
        print(f"Returned to: {orig_name}")
    return 0


def _handle_find(spaces: Sequence[SpaceInfo], app_query: str, *, json_output: bool = False) -> int:
    """Handle find (positional argument) command."""
    matches = find_space_by_app(spaces, app_query)

    if not matches:
        if json_output:
            print(json.dumps({"error": f"No space found for app: {app_query}"}))
        else:
            print(f"No space found for app: {app_query}")
            print("\nAvailable spaces:")
            list_spaces(spaces)
        return 1

    if json_output:
        print(json.dumps([m.to_dict() for m in matches], indent=2))
    else:
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
    json_output = args.json

    if args.list:
        return _handle_list(spaces, json_output=json_output)

    if args.current:
        return _handle_current(spaces, json_output=json_output)

    if args.go:
        return _handle_go(spaces, args.go, json_output=json_output)

    if args.app_query:
        return _handle_find(spaces, args.app_query, json_output=json_output)

    return 0
