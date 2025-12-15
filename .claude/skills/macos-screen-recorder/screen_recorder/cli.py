"""Command-line interface for macOS Screen Recorder."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from .actions import preview_region, record_verified
from .core import check_dependencies, find_target_window
from .models import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_FPS,
    DEFAULT_MAX_DURATION_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_QUALITY,
    DEFAULT_RETRY_DELAY_MS,
    DEFAULT_SETTLE_MS,
    PRESET_CONFIGS,
    OutputFormat,
    PlatformPreset,
    RecordingConfig,
    RecordingError,
    RetryStrategy,
    VerificationStrategy,
    WindowBounds,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Record macOS screen with verification, retry logic, and format conversion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --record "GoLand" -d 5                Record GoLand for 5 seconds
  %(prog)s --record "GoLand" --preset discord    Record optimized for Discord
  %(prog)s --record "Chrome" --title "GitHub"    Record Chrome with GitHub tab
  %(prog)s --record "Code" -d 10 -o demo.gif     Record VS Code to demo.gif
  %(prog)s --full-screen -d 3 -o screen.webp     Full screen for 3 seconds
  %(prog)s --find "GoLand" --json                Find window info only
  %(prog)s --check-deps                          Check ffmpeg availability
  %(prog)s -R 100,200,800,600 -d 5               Record absolute screen region
  %(prog)s --record "GoLand" --window-region 0,400,800,300  Record terminal area

Platform presets:
  discord     WebP, 10MB max, 10fps, 720px max (no Nitro)
  github      GIF, ~5MB, 10fps, 600px max (README optimized)
  jetbrains   GIF, 1280x800, 15fps (plugin marketplace)
  raw         MOV only, no conversion

Output formats:
  gif         Animated GIF with palette optimization
  webp        Animated WebP (lossy, smaller than GIF)
  mp4         H.264 video
  mov         Native macOS format (no conversion)

Verification strategies:
  basic       File exists, size > 0
  duration    Duration matches requested
  frames      Minimum frame count check
  motion      First/last frames differ (content changed)
  all         All strategies combined
        """,
    )

    # Actions
    actions = parser.add_argument_group("actions")
    actions.add_argument(
        "--record", "-r", metavar="APP", help="Record window of specified application"
    )
    actions.add_argument("--find", "-f", metavar="APP", help="Find window without recording")
    actions.add_argument(
        "--full-screen", "-F", action="store_true", help="Record full screen instead of window"
    )
    actions.add_argument(
        "--check-deps", action="store_true", help="Check availability of required tools"
    )
    actions.add_argument(
        "--preview-region",
        action="store_true",
        help="Take screenshot of region for coordinate verification",
    )

    # Window filters
    filters = parser.add_argument_group("window filters")
    filters.add_argument("--title", "-t", metavar="PATTERN", help="Regex pattern for window title")
    filters.add_argument("--pid", type=int, metavar="PID", help="Filter by process ID")
    filters.add_argument("--path-contains", metavar="STR", help="Executable path must contain STR")
    filters.add_argument(
        "--path-excludes", metavar="STR", help="Executable path must NOT contain STR"
    )
    filters.add_argument(
        "--args", "--args-contains", metavar="STR", help="Command line must contain STR"
    )

    # Recording settings
    rec_opts = parser.add_argument_group("recording options")
    rec_opts.add_argument(
        "--duration",
        "-d",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        metavar="SEC",
        help=f"Recording duration in seconds (default: {DEFAULT_DURATION_SECONDS})",
    )
    rec_opts.add_argument(
        "--max-duration",
        type=float,
        default=DEFAULT_MAX_DURATION_SECONDS,
        metavar="SEC",
        help=f"Maximum allowed duration (default: {DEFAULT_MAX_DURATION_SECONDS})",
    )
    rec_opts.add_argument(
        "--region", "-R", metavar="X,Y,W,H", help="Absolute screen region: x,y,width,height"
    )
    rec_opts.add_argument(
        "--window-region",
        metavar="X,Y,W,H",
        help="Window-relative region (requires --record): x,y,w,h offset from window",
    )
    rec_opts.add_argument(
        "--no-clicks", action="store_true", help="Don't show mouse clicks in recording"
    )
    rec_opts.add_argument(
        "--no-activate", action="store_true", help="Don't activate window before recording"
    )
    rec_opts.add_argument(
        "--settle-ms",
        type=int,
        default=DEFAULT_SETTLE_MS,
        metavar="MS",
        help=f"Wait time after activation (default: {DEFAULT_SETTLE_MS})",
    )

    # Output options
    output_opts = parser.add_argument_group("output options")
    output_opts.add_argument("--output", "-o", metavar="PATH", help="Output path for recording")
    output_opts.add_argument(
        "--format",
        choices=["gif", "webp", "mp4", "mov"],
        default="gif",
        help="Output format (default: gif)",
    )
    output_opts.add_argument(
        "--preset",
        "-p",
        choices=["discord", "github", "jetbrains", "raw", "custom"],
        help="Platform optimization preset",
    )
    output_opts.add_argument(
        "--keep-raw", action="store_true", help="Keep original .mov file after conversion"
    )
    output_opts.add_argument("--json", "-j", action="store_true", help="Output result as JSON")

    # Format settings
    fmt_opts = parser.add_argument_group("format settings (override preset)")
    fmt_opts.add_argument(
        "--fps", type=int, metavar="N", help=f"Target frame rate (default: preset or {DEFAULT_FPS})"
    )
    fmt_opts.add_argument("--max-width", type=int, metavar="PX", help="Maximum width in pixels")
    fmt_opts.add_argument("--max-height", type=int, metavar="PX", help="Maximum height in pixels")
    fmt_opts.add_argument(
        "--quality",
        "-q",
        type=int,
        metavar="N",
        help=f"Quality for lossy formats 0-100 (default: {DEFAULT_QUALITY})",
    )
    fmt_opts.add_argument(
        "--max-size", type=float, metavar="MB", help="Target maximum file size in MB"
    )

    # Verification
    verify_opts = parser.add_argument_group("verification")
    verify_opts.add_argument(
        "--verify",
        "-v",
        nargs="+",
        choices=["basic", "duration", "frames", "motion", "all", "none"],
        default=["basic", "duration"],
        help="Verification strategies (default: basic duration)",
    )

    # Retry options
    retry_opts = parser.add_argument_group("retry options")
    retry_opts.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        metavar="N",
        help=f"Maximum retry attempts (default: {DEFAULT_MAX_RETRIES})",
    )
    retry_opts.add_argument(
        "--retry-delay",
        type=int,
        default=DEFAULT_RETRY_DELAY_MS,
        metavar="MS",
        help=f"Delay between retries in ms (default: {DEFAULT_RETRY_DELAY_MS})",
    )
    retry_opts.add_argument(
        "--retry-strategy",
        choices=["fixed", "exponential", "reactivate"],
        default="fixed",
        help="Retry strategy (default: fixed)",
    )

    return parser


def parse_output_format(format_str: str) -> OutputFormat:
    """Parse output format string to enum."""
    mapping = {
        "gif": OutputFormat.GIF,
        "webp": OutputFormat.WEBP,
        "mp4": OutputFormat.MP4,
        "mov": OutputFormat.MOV,
    }
    return mapping.get(format_str, OutputFormat.GIF)


def parse_preset(preset_str: str | None) -> PlatformPreset | None:
    """Parse preset string to enum."""
    if not preset_str:
        return None
    mapping = {
        "discord": PlatformPreset.DISCORD,
        "github": PlatformPreset.GITHUB,
        "jetbrains": PlatformPreset.JETBRAINS,
        "raw": PlatformPreset.RAW,
        "custom": PlatformPreset.CUSTOM,
    }
    return mapping.get(preset_str)


def parse_verification_strategies(strategies: list[str]) -> tuple[VerificationStrategy, ...]:
    """Parse verification strategy strings to enum values."""
    if "none" in strategies:
        return ()
    if "all" in strategies:
        return (VerificationStrategy.ALL,)

    mapping = {
        "basic": VerificationStrategy.BASIC,
        "duration": VerificationStrategy.DURATION,
        "frames": VerificationStrategy.FRAMES,
        "motion": VerificationStrategy.MOTION,
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


REGION_PARTS_COUNT = 4  # x, y, width, height


def parse_region(region_str: str | None) -> WindowBounds | None:
    """Parse region string to WindowBounds.

    Args:
        region_str: Region in format "x,y,width,height".

    Returns:
        WindowBounds or None if not provided.

    Raises:
        argparse.ArgumentTypeError: If format is invalid.
    """
    if not region_str:
        return None

    parts = region_str.split(",")
    if len(parts) != REGION_PARTS_COUNT:
        raise argparse.ArgumentTypeError(f"Region must be x,y,width,height: {region_str}")

    try:
        x, y, w, h = (float(p.strip()) for p in parts)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid region values: {region_str}") from e

    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError(f"Region width and height must be positive: {region_str}")

    return WindowBounds(x=x, y=y, width=w, height=h)


def build_config(args) -> RecordingConfig:
    """Build RecordingConfig from parsed arguments."""
    # Parse region arguments
    region = parse_region(args.region)
    window_relative_region = parse_region(args.window_region)

    # Validate: window-region requires a window target
    if window_relative_region and not args.record:
        raise argparse.ArgumentTypeError(
            "--window-region requires --record to specify the target window"
        )

    return RecordingConfig(
        app_name=args.record or args.find,
        title_pattern=args.title,
        pid=args.pid,
        path_contains=args.path_contains,
        path_excludes=args.path_excludes,
        args_contains=args.args,
        region=region,
        window_relative_region=window_relative_region,
        full_screen=args.full_screen,
        duration_seconds=args.duration,
        max_duration_seconds=args.max_duration,
        show_clicks=not args.no_clicks,
        output_path=args.output,
        output_format=parse_output_format(args.format),
        preset=parse_preset(args.preset),
        fps=args.fps,
        max_width=args.max_width,
        max_height=args.max_height,
        quality=args.quality,
        max_size_mb=args.max_size,
        activate_first=not args.no_activate,
        settle_ms=args.settle_ms,
        keep_raw=args.keep_raw,
        verification_strategies=parse_verification_strategies(args.verify),
        max_retries=args.retries,
        retry_delay_ms=args.retry_delay,
        retry_strategy=parse_retry_strategy(args.retry_strategy),
    )


def _handle_check_deps(args) -> int:
    """Handle --check-deps action."""
    deps = check_dependencies()

    if args.json:
        print(json.dumps(deps, indent=2))
    else:
        print("Dependency check:")
        for tool, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {tool}")

        if not all(deps.values()):
            print("\nInstall missing dependencies:")
            if not deps.get("ffmpeg") or not deps.get("ffprobe"):
                print("  brew install ffmpeg")

    return 0 if all(deps.values()) else 1


def _handle_find(args, config: RecordingConfig) -> int:
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
        print(f"  Bounds: {int(target.bounds.width)}x{int(target.bounds.height)}")
        print(f"  Region: {target.bounds.as_region}")

    return 0


def _handle_preview_region(args, config: RecordingConfig) -> int:
    """Handle --preview-region action."""
    result = preview_region(config)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Preview saved: {result.screenshot_path}")
        print(f"  Region: {result.region.as_region}")

        if result.app_name:
            print(f"  Window: {result.app_name} - {result.window_title}")
            print(f"  Window bounds: {result.window_bounds.as_region}")

        print("\nUse these coordinates with:")
        print(f"  screen-recorder -R {result.region.as_region} -d 5")

        if result.app_name and result.window_bounds:
            print("\nOr use window-relative coordinates:")
            rel_x = int(result.region.x - result.window_bounds.x)
            rel_y = int(result.region.y - result.window_bounds.y)
            w = int(result.region.width)
            h = int(result.region.height)
            rel_region = f"{rel_x},{rel_y},{w},{h}"
            app = result.app_name
            print(f'  screen-recorder --record "{app}" --window-region {rel_region} -d 5')

    return 0


def _handle_record(args, config: RecordingConfig) -> int:
    """Handle --record or --full-screen action."""
    result = record_verified(config)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "✅ verified" if result.verified else "❌ unverified"
        print(f"Recording saved: {result.final_path} ({status})")

        if result.app_name:
            print(f"  Window: {result.app_name} - {result.window_title}")

        print(f"  Attempt: {result.attempt}/{config.max_retries}")
        actual = result.duration_actual
        requested = result.duration_requested
        print(f"  Duration: {actual:.1f}s (requested: {requested:.1f}s)")
        print(f"  Format: {result.output_format.value}")

        if result.video_info:
            print(f"  Size: {result.video_info.file_size_mb:.2f} MB")
            print(f"  Resolution: {result.video_info.width}x{result.video_info.height}")
            print(f"  FPS: {result.video_info.fps:.1f}")

        if result.verifications:
            print("  Verifications:")
            for v in result.verifications:
                icon = "✅" if v.passed else "❌"
                print(f"    {icon} {v.strategy.value}: {v.message}")

        if config.preset:
            preset_info = PRESET_CONFIGS.get(config.preset, {})
            if preset_info.get("description"):
                print(f"  Preset: {preset_info['description']}")

    return 0 if result.verified else 1


def _dispatch_action(args, config: RecordingConfig) -> int:
    """Dispatch to the appropriate action handler."""
    if args.preview_region:
        return _handle_preview_region(args, config)

    if args.find:
        return _handle_find(args, config)

    if args.record or args.full_screen:
        return _handle_record(args, config)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle special actions
    if args.check_deps:
        return _handle_check_deps(args)

    # Preview region requires region or record (for window bounds)
    has_region_target = any([args.region, args.window_region, args.record])
    if args.preview_region and not has_region_target:
        print(
            "Error: --preview-region requires --region, --window-region, or --record",
            file=sys.stderr,
        )
        return 1

    # Validate: need an action
    if not any([args.record, args.find, args.full_screen, args.preview_region]):
        parser.print_help()
        return 1

    try:
        config = build_config(args)
        return _dispatch_action(args, config)
    except (RecordingError, ValueError) as e:
        output = {"error": str(e)} if args.json else f"Error: {e}"
        print(json.dumps(output) if args.json else output, file=sys.stderr)
        return 1
