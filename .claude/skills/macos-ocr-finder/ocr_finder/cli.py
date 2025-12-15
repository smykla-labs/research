"""CLI interface for ocr-finder."""

import argparse
import sys


def main() -> int:
    """Main entry point for ocr-finder CLI."""
    parser = argparse.ArgumentParser(
        prog="ocr-finder",
        description="Find text in images using EasyOCR",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    # Stub: Phase 2 will add full CLI implementation
    parser.add_argument("-i", "--image", help="Path to image file")
    parser.add_argument("-f", "--find", help="Text to find")
    parser.add_argument("--click", help="Get click coordinates for text")
    parser.add_argument("-l", "--list", action="store_true", help="List all text regions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    _args = parser.parse_args()

    print("ocr-finder: CLI not yet implemented (Phase 2)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
