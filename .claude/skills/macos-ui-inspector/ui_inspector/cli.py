"""CLI interface for ui-inspector."""

import json
import sys

import typer

from ui_inspector.actions import find_element, get_click_target, list_elements
from ui_inspector.models import UiInspectorError

# Text column width for table display
TEXT_COLUMN_WIDTH = 25

app = typer.Typer(
    name="ui-inspector",
    help="Inspect macOS UI elements via Accessibility API",
)


def _truncate(text: str | None, width: int) -> str:
    """Truncate text to width, adding ellipsis if needed."""
    if text is None:
        return ""
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


@app.command("list")
def list_cmd(
    app_name: str = typer.Option(
        ..., "--app", "-a", help="Application name or bundle ID"
    ),
    role: str | None = typer.Option(
        None, "--role", help="Filter by element role (e.g., AXButton)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all UI elements."""
    try:
        elements = list_elements(app_name, role=role)
    except UiInspectorError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if json_output:
        output = [e.to_dict() for e in elements]
        print(json.dumps(output, indent=2))
        return

    if not elements:
        print("No elements found")
        return

    print(
        f"{'Role':<{TEXT_COLUMN_WIDTH}} {'Title':<{TEXT_COLUMN_WIDTH}} "
        f"{'Center (x,y)':<15} {'Enabled':<8}"
    )
    print("-" * 80)

    for elem in elements:
        role_str = _truncate(elem.role, TEXT_COLUMN_WIDTH)
        title = _truncate(elem.title, TEXT_COLUMN_WIDTH)
        x, y = elem.center
        enabled = "Yes" if elem.enabled else "No"
        print(
            f"{role_str:<{TEXT_COLUMN_WIDTH}} {title:<{TEXT_COLUMN_WIDTH}} "
            f"({x:>5}, {y:<5}) {enabled:<8}"
        )


@app.command("find")
def find_cmd(
    app_name: str = typer.Option(
        ..., "--app", "-a", help="Application name or bundle ID"
    ),
    role: str | None = typer.Option(None, "--role", help="Filter by element role"),
    title: str | None = typer.Option(None, "--title", help="Filter by element title"),
    identifier: str | None = typer.Option(
        None, "--identifier", help="Filter by element identifier"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Find specific element."""
    try:
        element = find_element(
            app_name,
            role=role,
            title=title,
            identifier=identifier,
        )
    except UiInspectorError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if json_output:
        if element:
            print(json.dumps(element.to_dict(), indent=2))
        else:
            print(json.dumps(None))
        return

    if not element:
        print("No matching element found")
        raise typer.Exit(1)

    print(f"Role:       {element.role}")
    print(f"Title:      {element.title or '(none)'}")
    print(f"Value:      {element.value or '(none)'}")
    print(f"Identifier: {element.identifier or '(none)'}")
    print(f"Position:   ({element.position[0]}, {element.position[1]})")
    print(f"Size:       {element.size[0]} x {element.size[1]}")
    print(f"Center:     ({element.center[0]}, {element.center[1]})")
    print(f"Enabled:    {'Yes' if element.enabled else 'No'}")
    print(f"Focused:    {'Yes' if element.focused else 'No'}")


@app.command("click")
def click_cmd(
    app_name: str = typer.Option(
        ..., "--app", "-a", help="Application name or bundle ID"
    ),
    role: str | None = typer.Option(None, "--role", help="Filter by element role"),
    title: str | None = typer.Option(None, "--title", help="Filter by element title"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get click coordinates for element."""
    try:
        x, y = get_click_target(app_name, role=role, title=title)
    except UiInspectorError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if json_output:
        print(json.dumps({"x": x, "y": y}))
    else:
        print(f"{x},{y}")


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ui-inspector CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["ui-inspector", *list(argv)]
    try:
        app(prog_name="ui-inspector")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
