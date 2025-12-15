"""CLI interface for ocr-finder."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from ocr_finder.actions import find_text, get_click_target, list_all_text
from ocr_finder.models import SearchOptions, TextNotFoundError

# Text column width for table display (truncate at 40 chars, show "..." for longer)
TEXT_COLUMN_WIDTH = 40

app = typer.Typer(
    name="ocr-finder",
    help="Find text in images using EasyOCR",
)

# Common type aliases to reduce argument count
ImagePath = Annotated[Path, typer.Option("--image", "-i", help="Path to image file", exists=True)]
JsonOutput = Annotated[bool, typer.Option("--json", help="Output as JSON")]
MinConfidence = Annotated[
    float, typer.Option("--min-confidence", help="Minimum OCR confidence (0.0-1.0)")
]
ExactMatch = Annotated[bool, typer.Option("--exact", help="Require exact match (not substring)")]
CaseSensitive = Annotated[bool, typer.Option("--case-sensitive", help="Case-sensitive matching")]


def _truncate(text: str, width: int) -> str:
    """Truncate text to width, adding ellipsis if needed."""
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def _build_options(
    exact: bool, case_sensitive: bool, min_confidence: float
) -> SearchOptions:
    """Build SearchOptions from CLI flags."""
    return SearchOptions(
        exact=exact,
        case_sensitive=case_sensitive,
        min_confidence=min_confidence,
    )


@app.command("list")
def list_cmd(
    image: ImagePath,
    min_confidence: MinConfidence = 0.5,
    json_output: JsonOutput = False,
) -> None:
    """List all text regions in an image."""
    try:
        regions = list_all_text(image, min_confidence=min_confidence)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if json_output:
        output = [r.to_dict() for r in regions]
        print(json.dumps(output, indent=2))
        return

    if not regions:
        print("No text found in image")
        return

    print(f"{'Text':<{TEXT_COLUMN_WIDTH}} {'Confidence':>10} {'Click (x,y)':<15}")
    print("-" * 70)

    for region in regions:
        text = _truncate(region.text, TEXT_COLUMN_WIDTH)
        x, y = region.click_coords
        print(f"{text:<{TEXT_COLUMN_WIDTH}} {region.confidence:>10.2f} ({x}, {y})")


@app.command("find")
def find_cmd(
    text: Annotated[str, typer.Argument(help="Text to search for")],
    image: ImagePath,
    exact: ExactMatch = False,
    case_sensitive: CaseSensitive = False,
    min_confidence: MinConfidence = 0.5,
    json_output: JsonOutput = False,
) -> None:
    """Find text in an image."""
    options = _build_options(exact, case_sensitive, min_confidence)

    try:
        matches = find_text(image, text, options)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except TextNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if json_output:
        output = [m.to_dict() for m in matches]
        print(json.dumps(output, indent=2))
        return

    if not matches:
        print(f"No matches found for '{text}'")
        raise typer.Exit(1)

    print(f"Found {len(matches)} match(es) for '{text}':")
    print(f"{'#':<3} {'Text':<{TEXT_COLUMN_WIDTH}} {'Confidence':>10} {'Click (x,y)':<15}")
    print("-" * 73)

    for i, match in enumerate(matches):
        truncated = _truncate(match.text, TEXT_COLUMN_WIDTH)
        x, y = match.click_coords
        print(f"{i:<3} {truncated:<{TEXT_COLUMN_WIDTH}} {match.confidence:>10.2f} ({x}, {y})")


@app.command("click")
def click_cmd(
    text: Annotated[str, typer.Argument(help="Text to search for")],
    image: ImagePath,
    exact: ExactMatch = False,
    case_sensitive: CaseSensitive = False,
    min_confidence: MinConfidence = 0.5,
    index: Annotated[int, typer.Option("--index", help="Match index")] = 0,
    json_output: JsonOutput = False,
) -> None:
    """Get click coordinates for text in an image."""
    options = _build_options(exact, case_sensitive, min_confidence)

    try:
        x, y = get_click_target(image, text, options, index)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
    except TextNotFoundError as e:
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
    """Main entry point for ocr-finder CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["ocr-finder", *list(argv)]
    try:
        app(prog_name="ocr-finder")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
