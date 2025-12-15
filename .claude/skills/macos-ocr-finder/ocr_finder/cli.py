"""CLI interface for ocr-finder."""

import argparse
import json
import sys
from pathlib import Path

from ocr_finder.actions import find_text, get_click_target, list_all_text
from ocr_finder.models import SearchOptions, TextNotFoundError

# Text column width for table display (truncate at 40 chars, show "..." for longer)
TEXT_COLUMN_WIDTH = 40


def main() -> int:
    """Main entry point for ocr-finder CLI."""
    parser = argparse.ArgumentParser(
        prog="ocr-finder",
        description="Find text in images using EasyOCR",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    # Required: image path
    parser.add_argument(
        "-i",
        "--image",
        required=True,
        type=Path,
        help="Path to image file",
    )

    # Mutually exclusive actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("-f", "--find", metavar="TEXT", help="Find text in image")
    action_group.add_argument("--click", metavar="TEXT", help="Get click coordinates for text")
    action_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all text regions",
    )

    # Options
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--exact", action="store_true", help="Require exact match (not substring)")
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Case-sensitive matching",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum OCR confidence (0.0-1.0, default: 0.5)",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Match index for --click (default: 0)",
    )

    args = parser.parse_args()

    try:
        if args.list:
            return _handle_list(args)
        elif args.find:
            return _handle_find(args)
        elif args.click:
            return _handle_click(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except TextNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def _handle_list(args: argparse.Namespace) -> int:
    """Handle --list action."""
    regions = list_all_text(args.image, min_confidence=args.min_confidence)

    if args.json:
        output = [r.to_dict() for r in regions]
        print(json.dumps(output, indent=2))
    else:
        if not regions:
            print("No text found in image")
            return 0

        print(f"{'Text':<{TEXT_COLUMN_WIDTH}} {'Confidence':>10} {'Click (x,y)':<15}")
        print("-" * 70)

        for region in regions:
            truncate_at = TEXT_COLUMN_WIDTH - 3  # Leave room for "..."
            text = (
                region.text[:truncate_at] + "..."
                if len(region.text) > TEXT_COLUMN_WIDTH
                else region.text
            )
            x, y = region.click_coords
            print(f"{text:<{TEXT_COLUMN_WIDTH}} {region.confidence:>10.2f} ({x}, {y})")

    return 0


def _handle_find(args: argparse.Namespace) -> int:
    """Handle --find action."""
    options = SearchOptions(
        exact=args.exact,
        case_sensitive=args.case_sensitive,
        min_confidence=args.min_confidence,
    )
    matches = find_text(args.image, args.find, options)

    if args.json:
        output = [m.to_dict() for m in matches]
        print(json.dumps(output, indent=2))
    else:
        if not matches:
            print(f"No matches found for '{args.find}'")
            return 1

        print(f"Found {len(matches)} match(es) for '{args.find}':")
        print(f"{'#':<3} {'Text':<{TEXT_COLUMN_WIDTH}} {'Confidence':>10} {'Click (x,y)':<15}")
        print("-" * 73)

        for i, match in enumerate(matches):
            truncate_at = TEXT_COLUMN_WIDTH - 3  # Leave room for "..."
            text = (
                match.text[:truncate_at] + "..."
                if len(match.text) > TEXT_COLUMN_WIDTH
                else match.text
            )
            x, y = match.click_coords
            print(f"{i:<3} {text:<{TEXT_COLUMN_WIDTH}} {match.confidence:>10.2f} ({x}, {y})")

    return 0


def _handle_click(args: argparse.Namespace) -> int:
    """Handle --click action."""
    options = SearchOptions(
        exact=args.exact,
        case_sensitive=args.case_sensitive,
        min_confidence=args.min_confidence,
    )
    x, y = get_click_target(args.image, args.click, options, args.index)

    if args.json:
        print(json.dumps({"x": x, "y": y}))
    else:
        print(f"{x},{y}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
