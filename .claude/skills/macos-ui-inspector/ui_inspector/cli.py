"""CLI interface for ui-inspector."""

import argparse
import sys


def main() -> int:
    """Main entry point for ui-inspector CLI."""
    parser = argparse.ArgumentParser(
        prog="ui-inspector",
        description="Inspect macOS UI elements via Accessibility API",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    # Stub: Phase 4 will add full CLI implementation
    parser.add_argument("-a", "--app", help="Application name or bundle ID")
    parser.add_argument("-l", "--list", action="store_true", help="List all elements")
    parser.add_argument("--find", action="store_true", help="Find specific element")
    parser.add_argument("--click", action="store_true", help="Get click coordinates")
    parser.add_argument("--role", help="Filter by element role (e.g., AXButton)")
    parser.add_argument("--title", help="Filter by element title")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    _args = parser.parse_args()

    print("ui-inspector: CLI not yet implemented (Phase 4)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
