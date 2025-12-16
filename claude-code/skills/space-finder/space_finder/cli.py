"""Command-line interface for macOS Space Finder."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Annotated

import typer

from .actions import go_to_space
from .core import find_space_by_app, get_current_space, get_spaces_plist, parse_spaces
from .models import ActivationError, PlistReadError, SpaceInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

app = typer.Typer(
    name="space-finder",
    help="Find and switch to macOS Spaces by application name.",
)

# Common type aliases
JsonOutput = Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")]


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


def _load_spaces() -> list[SpaceInfo]:
    """Load and parse spaces data from plist."""
    plist_data = get_spaces_plist()
    return parse_spaces(plist_data)


def _handle_list(spaces: Sequence[SpaceInfo], *, json_output: bool = False) -> int:
    """Handle list command."""
    if json_output:
        print(json.dumps([s.to_dict() for s in spaces], indent=2))
    else:
        list_spaces(spaces)
    return 0


def _handle_current(spaces: Sequence[SpaceInfo], *, json_output: bool = False) -> int:
    """Handle current command."""
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
    """Handle go command."""
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
    """Handle find command."""
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


@app.command("list")
def list_cmd(
    json_output: JsonOutput = False,
) -> None:
    """List all spaces with their details."""
    try:
        spaces = _load_spaces()
    except PlistReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    result = _handle_list(spaces, json_output=json_output)
    if result != 0:
        raise typer.Exit(result)


@app.command("current")
def current_cmd(
    json_output: JsonOutput = False,
) -> None:
    """Print the current space's application name."""
    try:
        spaces = _load_spaces()
    except PlistReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    result = _handle_current(spaces, json_output=json_output)
    if result != 0:
        raise typer.Exit(result)


@app.command("go")
def go_cmd(
    app_name: Annotated[str, typer.Argument(help="Application to switch to")],
    json_output: JsonOutput = False,
) -> None:
    """Switch to the space containing APP, then return to original."""
    try:
        spaces = _load_spaces()
    except PlistReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    result = _handle_go(spaces, app_name, json_output=json_output)
    if result != 0:
        raise typer.Exit(result)


@app.command("find")
def find_cmd(
    app_name: Annotated[str, typer.Argument(help="Application to search for (partial match)")],
    json_output: JsonOutput = False,
) -> None:
    """Find space containing an application."""
    try:
        spaces = _load_spaces()
    except PlistReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    result = _handle_find(spaces, app_name, json_output=json_output)
    if result != 0:
        raise typer.Exit(result)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for space-finder CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["space-finder", *list(argv)]
    try:
        app(prog_name="space-finder")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
