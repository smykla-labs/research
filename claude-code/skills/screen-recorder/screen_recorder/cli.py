"""Command-line interface for macOS Screen Recorder."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Annotated

import typer

# Skill name for artifact tracking
SKILL_NAME = "screen-recorder"

try:
    from _shared.artifacts import get_default_artifact_path
except ImportError:
    # Fallback if shared module not available
    from datetime import datetime
    from pathlib import Path

    def get_default_artifact_path(
        _skill_name: str, description: str, ext: str
    ) -> Path:
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        return Path.cwd() / f"{timestamp}-{description}.{ext}"

from .actions import preview_region, record_verified  # noqa: E402
from .core import check_dependencies, find_target_window  # noqa: E402
from .models import (  # noqa: E402
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

EPILOG = """
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
"""

app = typer.Typer(
    name="screen-recorder",
    help="Record macOS screen with verification, retry logic, and format conversion.",
    epilog=EPILOG,
)


# =============================================================================
# Option dataclasses for grouping related CLI options
# =============================================================================


@dataclass(frozen=True)
class WindowFilterOptions:
    """Window filter options for finding target windows."""

    app_name: str | None = None
    title: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None


@dataclass(frozen=True)
class RecordingOptions:
    """Recording options for capture settings."""

    duration: float = DEFAULT_DURATION_SECONDS
    max_duration: float = DEFAULT_MAX_DURATION_SECONDS
    region: str | None = None
    window_region: str | None = None
    no_clicks: bool = False
    no_activate: bool = False
    settle_ms: int = DEFAULT_SETTLE_MS
    backend: str | None = None
    full_screen: bool = False


@dataclass(frozen=True)
class OutputOptions:
    """Output options for file and format settings."""

    output: str | None = None
    format_str: str = "gif"
    preset: str | None = None
    keep_raw: bool = False


@dataclass(frozen=True)
class FormatOptions:
    """Format options for video encoding settings."""

    fps: int | None = None
    max_width: int | None = None
    max_height: int | None = None
    quality: int | None = None
    max_size: float | None = None


@dataclass(frozen=True)
class RetryOptions:
    """Retry and verification options."""

    verify: list[str] | None = None
    retries: int = DEFAULT_MAX_RETRIES
    retry_delay: int = DEFAULT_RETRY_DELAY_MS
    retry_strategy: str = "fixed"


# =============================================================================
# Common type aliases for Typer options
# =============================================================================

# Window filter options
TitleOpt = Annotated[
    str | None, typer.Option("--title", "-t", help="Regex pattern for window title")
]
PidOpt = Annotated[int | None, typer.Option("--pid", help="Filter by process ID")]
PathContainsOpt = Annotated[
    str | None, typer.Option("--path-contains", help="Exe path must contain STR")
]
PathExcludesOpt = Annotated[
    str | None, typer.Option("--path-excludes", help="Exe path must NOT contain STR")
]
ArgsContainsOpt = Annotated[
    str | None, typer.Option("--args", "--args-contains", help="Command line contains STR")
]

# Recording options
DurationOpt = Annotated[
    float,
    typer.Option(
        "--duration",
        "-d",
        help=f"Recording duration in seconds (default: {DEFAULT_DURATION_SECONDS})",
    ),
]
MaxDurationOpt = Annotated[
    float,
    typer.Option(
        "--max-duration", help=f"Maximum allowed duration (default: {DEFAULT_MAX_DURATION_SECONDS})"
    ),
]
RegionOpt = Annotated[
    str | None, typer.Option("--region", "-R", help="Absolute screen region: x,y,width,height")
]
WindowRegionOpt = Annotated[
    str | None,
    typer.Option("--window-region", help="Window-relative region: x,y,w,h offset from window"),
]
NoClicksOpt = Annotated[
    bool, typer.Option("--no-clicks", help="Don't show mouse clicks in recording")
]
NoActivateOpt = Annotated[
    bool, typer.Option("--no-activate", help="Don't activate window before recording")
]
SettleMsOpt = Annotated[
    int,
    typer.Option("--settle-ms", help=f"Wait time after activation (default: {DEFAULT_SETTLE_MS})"),
]
BackendOpt = Annotated[
    str | None,
    typer.Option(
        "--backend", help="Capture backend: auto, quartz, screencapturekit (default: auto)"
    ),
]

# Output options
OutputOpt = Annotated[str | None, typer.Option("--output", "-o", help="Output path for recording")]
FormatOpt = Annotated[
    str, typer.Option("--format", help="Output format: gif, webp, mp4, mov (default: gif)")
]
PresetOpt = Annotated[
    str | None,
    typer.Option("--preset", "-p", help="Platform preset: discord, github, jetbrains, raw, custom"),
]
KeepRawOpt = Annotated[
    bool, typer.Option("--keep-raw", help="Keep original .mov file after conversion")
]
JsonOpt = Annotated[bool, typer.Option("--json", "-j", help="Output result as JSON")]

# Format options
FpsOpt = Annotated[
    int | None, typer.Option("--fps", help=f"Target frame rate (default: preset or {DEFAULT_FPS})")
]
MaxWidthOpt = Annotated[int | None, typer.Option("--max-width", help="Maximum width in pixels")]
MaxHeightOpt = Annotated[int | None, typer.Option("--max-height", help="Maximum height in pixels")]
QualityOpt = Annotated[
    int | None,
    typer.Option(
        "--quality", "-q", help=f"Quality for lossy formats 0-100 (default: {DEFAULT_QUALITY})"
    ),
]
MaxSizeOpt = Annotated[
    float | None, typer.Option("--max-size", help="Target maximum file size in MB")
]

# Retry options
VerifyOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--verify",
        "-v",
        help="Verification strategies: basic, duration, frames, motion, all, none",
    ),
]
RetriesOpt = Annotated[
    int, typer.Option("--retries", help=f"Maximum retry attempts (default: {DEFAULT_MAX_RETRIES})")
]
RetryDelayOpt = Annotated[
    int,
    typer.Option(
        "--retry-delay", help=f"Delay between retries in ms (default: {DEFAULT_RETRY_DELAY_MS})"
    ),
]
RetryStrategyOpt = Annotated[
    str,
    typer.Option("--retry-strategy", help="Retry strategy: fixed, exponential, reactivate"),
]


# =============================================================================
# Parsing helpers
# =============================================================================


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


def parse_capture_backend(backend_str: str | None):
    """Parse capture backend string to enum."""
    from .models import CaptureBackend

    if not backend_str:
        return CaptureBackend.AUTO
    mapping = {
        "auto": CaptureBackend.AUTO,
        "quartz": CaptureBackend.QUARTZ,
        "screencapturekit": CaptureBackend.SCREENCAPTUREKIT,
    }
    return mapping.get(backend_str, CaptureBackend.AUTO)


def parse_verification_strategies(strategies: list[str] | None) -> tuple[VerificationStrategy, ...]:
    """Parse verification strategy strings to enum values."""
    if strategies is None:
        strategies = ["basic", "duration"]

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
        typer.BadParameter: If format is invalid.
    """
    if not region_str:
        return None

    parts = region_str.split(",")
    if len(parts) != REGION_PARTS_COUNT:
        raise typer.BadParameter(f"Region must be x,y,width,height: {region_str}")

    try:
        x, y, w, h = (float(p.strip()) for p in parts)
    except ValueError as e:
        raise typer.BadParameter(f"Invalid region values: {region_str}") from e

    if w <= 0 or h <= 0:
        raise typer.BadParameter(f"Region width and height must be positive: {region_str}")

    return WindowBounds(x=x, y=y, width=w, height=h)


# =============================================================================
# Option builders
# =============================================================================


def _build_output_options(
    output: str | None,
    format_str: str,
    preset: str | None,
    keep_raw: bool,
) -> OutputOptions:
    """Build OutputOptions from CLI args."""
    # Use artifacts directory if no output path specified
    if output is None:
        output = str(get_default_artifact_path(SKILL_NAME, "recording", format_str))
    return OutputOptions(
        output=output,
        format_str=format_str,
        preset=preset,
        keep_raw=keep_raw,
    )


def _build_format_options(
    fps: int | None,
    max_width: int | None,
    max_height: int | None,
    quality: int | None,
    max_size: float | None,
) -> FormatOptions:
    """Build FormatOptions from CLI args."""
    return FormatOptions(
        fps=fps,
        max_width=max_width,
        max_height=max_height,
        quality=quality,
        max_size=max_size,
    )


def _build_retry_options(
    verify: list[str] | None,
    retries: int,
    retry_delay: int,
    retry_strategy: str,
) -> RetryOptions:
    """Build RetryOptions from CLI args."""
    return RetryOptions(
        verify=verify,
        retries=retries,
        retry_delay=retry_delay,
        retry_strategy=retry_strategy,
    )


def build_config(
    filter_opts: WindowFilterOptions,
    recording_opts: RecordingOptions,
    output_opts: OutputOptions,
    format_opts: FormatOptions,
    retry_opts: RetryOptions,
) -> RecordingConfig:
    """Build RecordingConfig from grouped option objects."""
    # Parse region arguments
    parsed_region = parse_region(recording_opts.region)
    window_relative_region = parse_region(recording_opts.window_region)

    # Validate: window-region requires a window target
    if window_relative_region and not filter_opts.app_name:
        msg = "--window-region requires an app name to specify the target window"
        raise typer.BadParameter(msg)

    return RecordingConfig(
        app_name=filter_opts.app_name,
        title_pattern=filter_opts.title,
        pid=filter_opts.pid,
        path_contains=filter_opts.path_contains,
        path_excludes=filter_opts.path_excludes,
        args_contains=filter_opts.args_contains,
        region=parsed_region,
        window_relative_region=window_relative_region,
        full_screen=recording_opts.full_screen,
        duration_seconds=recording_opts.duration,
        max_duration_seconds=recording_opts.max_duration,
        show_clicks=not recording_opts.no_clicks,
        capture_backend=parse_capture_backend(recording_opts.backend),
        output_path=output_opts.output,
        output_format=parse_output_format(output_opts.format_str),
        preset=parse_preset(output_opts.preset),
        fps=format_opts.fps,
        max_width=format_opts.max_width,
        max_height=format_opts.max_height,
        quality=format_opts.quality,
        max_size_mb=format_opts.max_size,
        activate_first=not recording_opts.no_activate,
        settle_ms=recording_opts.settle_ms,
        keep_raw=output_opts.keep_raw,
        verification_strategies=parse_verification_strategies(retry_opts.verify),
        max_retries=retry_opts.retries,
        retry_delay_ms=retry_opts.retry_delay,
        retry_strategy=parse_retry_strategy(retry_opts.retry_strategy),
    )


# =============================================================================
# Action handlers
# =============================================================================


def _handle_check_deps(*, json_output: bool = False) -> int:
    """Handle check-deps action."""
    deps = check_dependencies()

    if json_output:
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


def _handle_find(config: RecordingConfig, *, json_output: bool = False) -> int:
    """Handle find action."""
    target = find_target_window(config)

    if json_output:
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


def _handle_preview_region(config: RecordingConfig, *, json_output: bool = False) -> int:
    """Handle preview-region action."""
    result = preview_region(config)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Preview saved: {result.screenshot_path}")
        print(f"  Region: {result.region.as_region}")

        if result.app_name:
            print(f"  Window: {result.app_name} - {result.window_title}")
            print(f"  Window bounds: {result.window_bounds.as_region}")

        print("\nUse these coordinates with:")
        print(f"  screen-recorder record -R {result.region.as_region} -d 5")

        if result.app_name and result.window_bounds:
            print("\nOr use window-relative coordinates:")
            rel_x = int(result.region.x - result.window_bounds.x)
            rel_y = int(result.region.y - result.window_bounds.y)
            w = int(result.region.width)
            h = int(result.region.height)
            rel_region = f"{rel_x},{rel_y},{w},{h}"
            app_name = result.app_name
            print(f'  screen-recorder record "{app_name}" --window-region {rel_region} -d 5')

    return 0


def _handle_record(config: RecordingConfig, *, json_output: bool = False) -> int:
    """Handle record or full-screen action."""
    result = record_verified(config)

    if json_output:
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


# =============================================================================
# CLI commands
# =============================================================================


@app.command("check-deps")
def check_deps_cmd(
    json_output: JsonOpt = False,
) -> None:
    """Check availability of required tools (ffmpeg, screencapture)."""
    result = _handle_check_deps(json_output=json_output)
    if result != 0:
        raise typer.Exit(result)


@app.command("find")
def find_cmd(  # noqa: PLR0913
    app_name: Annotated[str, typer.Argument(help="Application name")],
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Find window without recording."""
    try:
        filter_opts = WindowFilterOptions(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
        )
        config = build_config(
            filter_opts,
            RecordingOptions(),
            OutputOptions(),
            FormatOptions(),
            RetryOptions(),
        )
        result = _handle_find(config, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)

    except RecordingError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("preview-region")
def preview_region_cmd(  # noqa: PLR0913
    app_name: Annotated[str | None, typer.Argument(help="Application name")] = None,
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    region: RegionOpt = None,
    window_region: WindowRegionOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Take screenshot of region for coordinate verification."""
    # Validate: need region or window target
    has_region_target = any([region, window_region, app_name])
    if not has_region_target:
        print(
            "Error: preview-region requires --region, --window-region, or an app name",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    try:
        filter_opts = WindowFilterOptions(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
        )
        recording_opts = RecordingOptions(region=region, window_region=window_region)
        config = build_config(
            filter_opts,
            recording_opts,
            OutputOptions(),
            FormatOptions(),
            RetryOptions(),
        )
        result = _handle_preview_region(config, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)

    except RecordingError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("record")
def record_cmd(  # noqa: PLR0913 - Typer CLI requires many options
    app_name: Annotated[str, typer.Argument(help="Application name")],
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    duration: DurationOpt = DEFAULT_DURATION_SECONDS,
    max_duration: MaxDurationOpt = DEFAULT_MAX_DURATION_SECONDS,
    region: RegionOpt = None,
    window_region: WindowRegionOpt = None,
    no_clicks: NoClicksOpt = False,
    no_activate: NoActivateOpt = False,
    settle_ms: SettleMsOpt = DEFAULT_SETTLE_MS,
    backend: BackendOpt = None,
    output: OutputOpt = None,
    format_str: FormatOpt = "gif",
    preset: PresetOpt = None,
    keep_raw: KeepRawOpt = False,
    fps: FpsOpt = None,
    max_width: MaxWidthOpt = None,
    max_height: MaxHeightOpt = None,
    quality: QualityOpt = None,
    max_size: MaxSizeOpt = None,
    verify: VerifyOpt = None,
    retries: RetriesOpt = DEFAULT_MAX_RETRIES,
    retry_delay: RetryDelayOpt = DEFAULT_RETRY_DELAY_MS,
    retry_strategy: RetryStrategyOpt = "fixed",
    json_output: JsonOpt = False,
) -> None:
    """Record window of specified application."""
    try:
        filter_opts = WindowFilterOptions(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
        )
        recording_opts = RecordingOptions(
            duration=duration,
            max_duration=max_duration,
            region=region,
            window_region=window_region,
            no_clicks=no_clicks,
            no_activate=no_activate,
            settle_ms=settle_ms,
            backend=backend,
        )
        output_opts = _build_output_options(output, format_str, preset, keep_raw)
        format_opts = _build_format_options(fps, max_width, max_height, quality, max_size)
        retry_opts = _build_retry_options(verify, retries, retry_delay, retry_strategy)

        config = build_config(
            filter_opts,
            recording_opts,
            output_opts,
            format_opts,
            retry_opts,
        )
        result = _handle_record(config, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)

    except RecordingError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("full-screen")
def full_screen_cmd(  # noqa: PLR0913 - Typer CLI requires many options
    duration: DurationOpt = DEFAULT_DURATION_SECONDS,
    max_duration: MaxDurationOpt = DEFAULT_MAX_DURATION_SECONDS,
    region: RegionOpt = None,
    no_clicks: NoClicksOpt = False,
    settle_ms: SettleMsOpt = DEFAULT_SETTLE_MS,
    output: OutputOpt = None,
    format_str: FormatOpt = "gif",
    preset: PresetOpt = None,
    keep_raw: KeepRawOpt = False,
    fps: FpsOpt = None,
    max_width: MaxWidthOpt = None,
    max_height: MaxHeightOpt = None,
    quality: QualityOpt = None,
    max_size: MaxSizeOpt = None,
    verify: VerifyOpt = None,
    retries: RetriesOpt = DEFAULT_MAX_RETRIES,
    retry_delay: RetryDelayOpt = DEFAULT_RETRY_DELAY_MS,
    retry_strategy: RetryStrategyOpt = "fixed",
    json_output: JsonOpt = False,
) -> None:
    """Record full screen instead of window."""
    try:
        recording_opts = RecordingOptions(
            duration=duration,
            max_duration=max_duration,
            region=region,
            no_clicks=no_clicks,
            settle_ms=settle_ms,
            full_screen=True,
        )
        output_opts = _build_output_options(output, format_str, preset, keep_raw)
        format_opts = _build_format_options(fps, max_width, max_height, quality, max_size)
        retry_opts = _build_retry_options(verify, retries, retry_delay, retry_strategy)

        config = build_config(
            WindowFilterOptions(),
            recording_opts,
            output_opts,
            format_opts,
            retry_opts,
        )
        result = _handle_record(config, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)

    except RecordingError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


def main(argv: list[str] | None = None) -> int:
    """Main entry point for screen-recorder CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["screen-recorder", *list(argv)]
    try:
        app(prog_name="screen-recorder")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
