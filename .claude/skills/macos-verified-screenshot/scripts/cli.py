"""Command-line interface for macOS Verified Screenshot."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from .actions import capture_verified
from .core import find_target_window
from .models import (
    CaptureConfig,
    RetryStrategy,
    ScreenshotError,
    VerificationStrategy,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Capture macOS screenshots with verification and retry logic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --capture "GoLand"                     Capture GoLand window
  %(prog)s --capture "GoLand" --verify all        Capture with full verification
  %(prog)s --capture "Main" --args "sandbox"      Capture sandbox IDE
  %(prog)s --capture "Chrome" --title "GitHub"    Capture Chrome with GitHub tab
  %(prog)s --find "GoLand" --json                 Find window info only
  %(prog)s --capture "Code" --retries 3 -o out.png

Verification strategies:
  basic       File exists, size > 0, valid image format
  dimensions  Image dimensions match window bounds
  content     Not blank, differs from previous (perceptual hash)
  text        OCR verification of expected text
  all         All strategies combined

Retry strategies:
  fixed       Fixed delay between retries (default)
  exponential Exponential backoff
  reactivate  Re-activate window before each retry
        """,
    )

    actions = parser.add_argument_group("actions")
    actions.add_argument(
        "--capture", "-c", metavar="APP", help="Capture screenshot of window"
    )
    actions.add_argument(
        "--find", "-f", metavar="APP", help="Find window without capturing"
    )

    filters = parser.add_argument_group("window filters")
    filters.add_argument("--title", "-t", metavar="PATTERN", help="Regex for window title")
    filters.add_argument("--pid", type=int, metavar="PID", help="Filter by process ID")
    filters.add_argument("--path-contains", metavar="STR", help="Exe path must contain STR")
    filters.add_argument("--path-excludes", metavar="STR", help="Exe path must NOT contain STR")
    filters.add_argument("--args", "--args-contains", metavar="STR", help="Command line contains")

    output_opts = parser.add_argument_group("output")
    output_opts.add_argument("--output", "-o", metavar="PATH", help="Output path for screenshot")
    output_opts.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    capture_opts = parser.add_argument_group("capture options")
    capture_opts.add_argument(
        "--no-activate", action="store_true", help="Don't activate window first"
    )
    capture_opts.add_argument(
        "--settle-ms", type=int, default=1000, metavar="MS", help="Wait time after activation"
    )
    capture_opts.add_argument(
        "--shadow", action="store_true", help="Include window shadow"
    )

    verify_opts = parser.add_argument_group("verification")
    verify_opts.add_argument(
        "--verify", "-v",
        nargs="+",
        choices=["basic", "dimensions", "content", "text", "all", "none"],
        default=["basic", "content"],
        help="Verification strategies (default: basic content)",
    )
    verify_opts.add_argument(
        "--expected-text",
        nargs="+",
        metavar="TEXT",
        help="Text to verify via OCR",
    )
    verify_opts.add_argument(
        "--hash-threshold",
        type=int,
        default=5,
        metavar="N",
        help="Hamming distance threshold (default: 5)",
    )

    retry_opts = parser.add_argument_group("retry")
    retry_opts.add_argument(
        "--retries", "-r",
        type=int,
        default=5,
        metavar="N",
        help="Maximum retry attempts (default: 5)",
    )
    retry_opts.add_argument(
        "--retry-delay",
        type=int,
        default=500,
        metavar="MS",
        help="Delay between retries in ms (default: 500)",
    )
    retry_opts.add_argument(
        "--retry-strategy",
        choices=["fixed", "exponential", "reactivate"],
        default="fixed",
        help="Retry strategy (default: fixed)",
    )

    return parser


def parse_verification_strategies(
    strategies: list[str],
) -> tuple[VerificationStrategy, ...]:
    """Parse verification strategy strings to enum values."""
    if "none" in strategies:
        return ()
    if "all" in strategies:
        return (VerificationStrategy.ALL,)

    mapping = {
        "basic": VerificationStrategy.BASIC,
        "dimensions": VerificationStrategy.DIMENSIONS,
        "content": VerificationStrategy.CONTENT,
        "text": VerificationStrategy.TEXT,
    }
    return tuple(mapping[s] for s in strategies if s in mapping)


def parse_retry_strategy(strategy: str) -> RetryStrategy:
    """Parse retry strategy string to enum value."""
    mapping = {
        "fixed": RetryStrategy.FIXED,
        "exponential": RetryStrategy.EXPONENTIAL,
        "reactivate": RetryStrategy.REACTIVATE,
    }
    return mapping.get(strategy, RetryStrategy.FIXED)


def build_config(args) -> CaptureConfig:
    """Build CaptureConfig from parsed arguments."""
    return CaptureConfig(
        app_name=args.capture or args.find,
        title_pattern=args.title,
        pid=args.pid,
        path_contains=args.path_contains,
        path_excludes=args.path_excludes,
        args_contains=args.args,
        output_path=args.output,
        activate_first=not args.no_activate,
        settle_ms=args.settle_ms,
        no_shadow=not args.shadow,
        verification_strategies=parse_verification_strategies(args.verify),
        expected_text=tuple(args.expected_text) if args.expected_text else (),
        hash_threshold=args.hash_threshold,
        max_retries=args.retries,
        retry_delay_ms=args.retry_delay,
        retry_strategy=parse_retry_strategy(args.retry_strategy),
    )


def _handle_find(args, config: CaptureConfig) -> int:
    """Handle --find action."""
    target = find_target_window(config)

    if args.json:
        print(json.dumps(target.to_dict(), indent=2))
    else:
        print(f"Found: {target.app_name}")
        print(f"  Title: {target.window_title}")
        print(f"  Window ID: {target.window_id}")
        print(f"  PID: {target.pid}")
        if target.exe_path:
            print(f"  Path: {target.exe_path}")
        if target.cmdline:
            print(f"  Args: {' '.join(target.cmdline[:3])}...")
        print(f"  Space: {target.space_index or 'unknown'}")
        print(f"  Bounds: {int(target.bounds_width)}x{int(target.bounds_height)}")

    return 0


def _handle_capture(args, config: CaptureConfig) -> int:
    """Handle --capture action."""
    result = capture_verified(config)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "verified" if result.verified else "unverified"
        print(f"Screenshot saved: {result.path} ({status})")
        print(f"  Window: {result.app_name} - {result.window_title}")
        print(f"  Attempt: {result.attempt}/{config.max_retries}")
        print(f"  Dimensions: {result.actual_width}x{result.actual_height}")

        if result.verifications:
            print("  Verifications:")
            for v in result.verifications:
                icon = "  " if v.passed else "  "
                print(f"    {icon} {v.strategy.value}: {v.message}")

    return 0 if result.verified else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not any([args.capture, args.find]):
        parser.print_help()
        return 1

    try:
        config = build_config(args)

        if args.find:
            return _handle_find(args, config)
        if args.capture:
            return _handle_capture(args, config)

    except ScreenshotError as e:
        output = {"error": str(e)} if args.json else f"Error: {e}"
        print(json.dumps(output) if args.json else output, file=sys.stderr)
        return 1

    return 0
