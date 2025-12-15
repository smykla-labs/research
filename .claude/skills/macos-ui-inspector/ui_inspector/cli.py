"""CLI interface for ui-inspector."""

import argparse
import json
import sys

from ui_inspector.actions import find_element, get_click_target, list_elements
from ui_inspector.models import UiInspectorError

# Text column width for table display
TEXT_COLUMN_WIDTH = 25


def _truncate(text: str | None, width: int) -> str:
    """Truncate text to width, adding ellipsis if needed."""
    if text is None:
        return ""
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def _handle_list(args: argparse.Namespace) -> int:
    """Handle --list action."""
    elements = list_elements(args.app, role=args.role)

    if args.json:
        output = [e.to_dict() for e in elements]
        print(json.dumps(output, indent=2))
        return 0

    if not elements:
        print("No elements found")
        return 0

    print(
        f"{'Role':<{TEXT_COLUMN_WIDTH}} {'Title':<{TEXT_COLUMN_WIDTH}} "
        f"{'Center (x,y)':<15} {'Enabled':<8}"
    )
    print("-" * 80)

    for elem in elements:
        role = _truncate(elem.role, TEXT_COLUMN_WIDTH)
        title = _truncate(elem.title, TEXT_COLUMN_WIDTH)
        x, y = elem.center
        enabled = "Yes" if elem.enabled else "No"
        print(
            f"{role:<{TEXT_COLUMN_WIDTH}} {title:<{TEXT_COLUMN_WIDTH}} "
            f"({x:>5}, {y:<5}) {enabled:<8}"
        )

    return 0


def _handle_find(args: argparse.Namespace) -> int:
    """Handle --find action."""
    element = find_element(
        args.app,
        role=args.role,
        title=args.title,
        identifier=args.identifier,
    )

    if args.json:
        if element:
            print(json.dumps(element.to_dict(), indent=2))
        else:
            print(json.dumps(None))
        return 0

    if not element:
        print("No matching element found")
        return 1

    print(f"Role:       {element.role}")
    print(f"Title:      {element.title or '(none)'}")
    print(f"Value:      {element.value or '(none)'}")
    print(f"Identifier: {element.identifier or '(none)'}")
    print(f"Position:   ({element.position[0]}, {element.position[1]})")
    print(f"Size:       {element.size[0]} x {element.size[1]}")
    print(f"Center:     ({element.center[0]}, {element.center[1]})")
    print(f"Enabled:    {'Yes' if element.enabled else 'No'}")
    print(f"Focused:    {'Yes' if element.focused else 'No'}")

    return 0


def _handle_click(args: argparse.Namespace) -> int:
    """Handle --click action."""
    x, y = get_click_target(args.app, role=args.role, title=args.title)

    if args.json:
        print(json.dumps({"x": x, "y": y}))
    else:
        print(f"{x},{y}")

    return 0


def _dispatch_action(args: argparse.Namespace) -> int:
    """Dispatch to appropriate action handler."""
    if args.list:
        return _handle_list(args)
    if args.find:
        return _handle_find(args)
    if args.click:
        return _handle_click(args)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ui-inspector CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = argparse.ArgumentParser(
        prog="ui-inspector",
        description="Inspect macOS UI elements via Accessibility API",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    # Required: application name
    parser.add_argument(
        "-a",
        "--app",
        required=True,
        help="Application name or bundle ID",
    )

    # Mutually exclusive actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all UI elements",
    )
    action_group.add_argument(
        "--find",
        action="store_true",
        help="Find specific element",
    )
    action_group.add_argument(
        "--click",
        action="store_true",
        help="Get click coordinates for element",
    )

    # Filter options
    parser.add_argument("--role", help="Filter by element role (e.g., AXButton)")
    parser.add_argument("--title", help="Filter by element title")
    parser.add_argument("--identifier", help="Filter by element identifier")

    # Output options
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args(argv)

    try:
        return _dispatch_action(args)
    except UiInspectorError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
