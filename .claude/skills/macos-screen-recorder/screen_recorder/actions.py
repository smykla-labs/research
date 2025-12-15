"""Actions for screen recording, conversion, and verification."""

from __future__ import annotations

import contextlib
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .core import (
    find_target_window,
    get_current_space_index,
    get_space_app_name,
    get_video_info,
    require_ffmpeg,
    verify_basic,
    verify_duration,
    verify_frames,
    verify_motion,
)
from .models import (
    DEFAULT_FPS,
    DEFAULT_QUALITY,
    PRESET_CONFIGS,
    CaptureError,
    ConversionError,
    DurationLimitError,
    MaxRetriesError,
    OutputFormat,
    PlatformPreset,
    RecordingConfig,
    RecordingResult,
    RetryStrategy,
    VerificationResult,
    VerificationStrategy,
    VideoEncodingSettings,
    VideoInfo,
    WindowBounds,
    WindowTarget,
)

if TYPE_CHECKING:
    pass


@dataclass
class _RecordingContext:
    """Internal context for recording operations."""

    config: RecordingConfig
    target: WindowTarget | None
    region: WindowBounds | None
    raw_path: Path
    final_path: Path
    settings: dict


def sanitize_app_name(app_name: str) -> str:
    """Sanitize application name for AppleScript.

    Args:
        app_name: Raw application name.

    Returns:
        Sanitized name safe for AppleScript.

    Raises:
        ValueError: If app name contains invalid characters.
    """
    if not re.match(r"^[\w\s.\-()]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")
    return app_name.replace('"', '\\"')


def activate_window(target: WindowTarget, wait_time: float = 0.5) -> None:
    """Activate a window (switches to its Space).

    Args:
        target: Window target information.
        wait_time: Seconds to wait after activation.

    Raises:
        CaptureError: If activation fails.
    """
    try:
        sanitized = sanitize_app_name(target.app_name)
    except ValueError as e:
        raise CaptureError(f"Cannot activate: {e}") from e

    result = subprocess.run(
        ["osascript", "-e", f'tell application "{sanitized}" to activate'],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise CaptureError(f"Failed to activate {target.app_name}: {stderr}")

    if wait_time > 0:
        time.sleep(wait_time)


def activate_app_by_name(app_name: str, wait_time: float = 0.5) -> None:
    """Activate an application by name (switches to its Space).

    Args:
        app_name: Application name to activate.
        wait_time: Seconds to wait after activation.

    Raises:
        CaptureError: If activation fails.
    """
    try:
        sanitized = sanitize_app_name(app_name)
    except ValueError as e:
        raise CaptureError(f"Cannot activate: {e}") from e

    result = subprocess.run(
        ["osascript", "-e", f'tell application "{sanitized}" to activate'],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise CaptureError(f"Failed to activate {app_name}: {stderr}")

    if wait_time > 0:
        time.sleep(wait_time)


@dataclass
class _SpaceContext:
    """Context for Space switching during recording."""

    original_space_index: int | None
    original_app_name: str | None
    target_space_index: int | None
    switched: bool


def _detect_space_switch_needed(
    target: WindowTarget | None,
) -> _SpaceContext:
    """Detect if we need to switch Spaces for recording.

    Args:
        target: Target window information.

    Returns:
        SpaceContext with current and target Space info.
    """
    current_space = get_current_space_index()
    current_app = get_space_app_name(current_space) if current_space else None

    if target is None or target.space_index is None:
        return _SpaceContext(
            original_space_index=current_space,
            original_app_name=current_app,
            target_space_index=None,
            switched=False,
        )

    return _SpaceContext(
        original_space_index=current_space,
        original_app_name=current_app,
        target_space_index=target.space_index,
        switched=False,
    )


def _switch_to_target_space(
    target: WindowTarget,
    space_ctx: _SpaceContext,
    settle_time: float = 1.0,
) -> None:
    """Switch to the target window's Space.

    Args:
        target: Target window with app name.
        space_ctx: Space context to update.
        settle_time: Seconds to wait after switching.
    """
    if target.app_name:
        activate_app_by_name(target.app_name, settle_time)
        space_ctx.switched = True


def _return_to_original_space(
    space_ctx: _SpaceContext,
    settle_time: float = 0.5,
) -> None:
    """Return to the original Space after recording.

    Args:
        space_ctx: Space context with original Space info.
        settle_time: Seconds to wait after switching.
    """
    if not space_ctx.switched:
        return

    # Best effort - don't fail recording if return fails
    if space_ctx.original_app_name:
        with contextlib.suppress(CaptureError):
            activate_app_by_name(space_ctx.original_app_name, settle_time)
    else:
        # For normal desktop (no fullscreen app), activate Finder
        with contextlib.suppress(CaptureError):
            activate_app_by_name("Finder", settle_time)


def record_screen_region(
    output_path: Path,
    duration_seconds: float,
    region: WindowBounds | None = None,
    show_clicks: bool = True,
) -> Path:
    """Record screen region using macOS screencapture.

    Args:
        output_path: Path to save the recording (must be .mov).
        duration_seconds: Duration in seconds.
        region: Optional window bounds for region capture.
        show_clicks: Show mouse clicks in recording.

    Returns:
        Path to the recorded video.

    Raises:
        CaptureError: If recording fails.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build screencapture command
    cmd = ["screencapture", "-v", "-V", str(int(duration_seconds))]

    if region:
        cmd.extend(["-R", region.as_region])

    if show_clicks:
        cmd.append("-k")

    # Disable sound effect
    cmd.append("-x")

    cmd.append(str(output_path))

    result = subprocess.run(
        cmd,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise CaptureError(f"Screen recording failed: {stderr}")

    if not output_path.exists():
        raise CaptureError(f"Recording file not created: {output_path}")

    return output_path


def capture_region_screenshot(
    output_path: Path,
    region: WindowBounds | None = None,
) -> Path:
    """Capture a screenshot of a screen region.

    Args:
        output_path: Path to save the screenshot (png format).
        region: Optional window bounds for region capture.

    Returns:
        Path to the captured screenshot.

    Raises:
        CaptureError: If screenshot fails.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build screencapture command for still image
    cmd = ["screencapture", "-x"]  # -x disables sound

    if region:
        cmd.extend(["-R", region.as_region])

    cmd.append(str(output_path))

    result = subprocess.run(
        cmd,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise CaptureError(f"Screenshot failed: {stderr}")

    if not output_path.exists():
        raise CaptureError(f"Screenshot file not created: {output_path}")

    return output_path


def _build_scale_filter(max_width: int | None, max_height: int | None) -> str:
    """Build ffmpeg scale filter string."""
    if max_width and max_height:
        return (
            f"scale='min({max_width},iw)':'min({max_height},ih)':"
            "force_original_aspect_ratio=decrease"
        )
    if max_width:
        return f"scale='min({max_width},iw)':-1"
    if max_height:
        return f"scale=-1:'min({max_height},ih)'"
    return ""


def convert_to_gif(
    input_path: Path,
    output_path: Path,
    settings: VideoEncodingSettings | None = None,
) -> Path:
    """Convert video to optimized GIF using two-pass palette generation.

    Args:
        input_path: Path to input video.
        output_path: Path for output GIF.
        settings: Video encoding settings (fps, max_width, max_height).

    Returns:
        Path to the created GIF.

    Raises:
        ConversionError: If conversion fails.
    """
    require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if settings is None:
        settings = VideoEncodingSettings(fps=10)

    # Build scale filter
    scale_filter = _build_scale_filter(settings.max_width, settings.max_height)
    scale_part = f"{scale_filter}," if scale_filter else ""

    # Two-pass palette optimization for high quality GIF
    # Using split filter for single-command approach
    filter_complex = (
        f"fps={settings.fps},{scale_part}split[a][b];"
        f"[a]palettegen=stats_mode=diff[palette];"
        f"[b][palette]paletteuse=dither=sierra2_4a"
    )

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-filter_complex", filter_complex,
            str(output_path),
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0 or not output_path.exists():
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ConversionError(f"GIF conversion failed: {stderr}")

    return output_path


def convert_to_webp(
    input_path: Path,
    output_path: Path,
    settings: VideoEncodingSettings | None = None,
) -> Path:
    """Convert video to animated WebP.

    Args:
        input_path: Path to input video.
        output_path: Path for output WebP.
        settings: Video encoding settings (fps, max_width, max_height, quality, loop).

    Returns:
        Path to the created WebP.

    Raises:
        ConversionError: If conversion fails.
    """
    require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if settings is None:
        settings = VideoEncodingSettings(fps=10)

    # Build video filter chain
    scale_filter = _build_scale_filter(settings.max_width, settings.max_height)
    filters = [f"fps={settings.fps}"]
    if scale_filter:
        filters.append(scale_filter)

    vf = ",".join(filters)

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-vf", vf,
            "-vcodec", "libwebp",
            "-lossless", "0",
            "-compression_level", "4",
            "-q:v", str(settings.quality),
            "-loop", "0" if settings.loop else "1",
            "-an",  # No audio
            str(output_path),
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0 or not output_path.exists():
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ConversionError(f"WebP conversion failed: {stderr}")

    return output_path


def convert_to_mp4(
    input_path: Path,
    output_path: Path,
    settings: VideoEncodingSettings | None = None,
) -> Path:
    """Convert video to H.264 MP4.

    Args:
        input_path: Path to input video.
        output_path: Path for output MP4.
        settings: Video encoding settings (fps, max_width, max_height, crf).

    Returns:
        Path to the created MP4.

    Raises:
        ConversionError: If conversion fails.
    """
    require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if settings is None:
        settings = VideoEncodingSettings()

    # Build video filter chain
    filters = []
    if settings.fps:
        filters.append(f"fps={settings.fps}")

    scale_filter = _build_scale_filter(settings.max_width, settings.max_height)
    if scale_filter:
        filters.append(scale_filter)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
    ]

    if filters:
        cmd.extend(["-vf", ",".join(filters)])

    cmd.extend([
        "-c:v", "libx264",
        "-crf", str(settings.crf),
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-an",  # No audio for screen recordings
        str(output_path),
    ])

    result = subprocess.run(cmd, capture_output=True, check=False)

    if result.returncode != 0 or not output_path.exists():
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ConversionError(f"MP4 conversion failed: {stderr}")

    return output_path


def convert_video(
    input_path: Path,
    output_format: OutputFormat,
    output_path: Path | None = None,
    settings: VideoEncodingSettings | None = None,
) -> Path:
    """Convert video to specified format.

    Args:
        input_path: Path to input video.
        output_format: Target format.
        output_path: Optional output path (auto-generated if None).
        settings: Video encoding settings.

    Returns:
        Path to the converted video.

    Raises:
        ConversionError: If conversion fails.
    """
    if output_path is None:
        output_path = input_path.with_suffix(f".{output_format.value}")

    if settings is None:
        settings = VideoEncodingSettings()

    if output_format == OutputFormat.MOV:
        # No conversion needed
        if input_path != output_path:
            import shutil
            shutil.copy2(input_path, output_path)
        return output_path

    if output_format == OutputFormat.GIF:
        gif_settings = VideoEncodingSettings(
            fps=settings.fps or 10,
            max_width=settings.max_width,
            max_height=settings.max_height,
        )
        return convert_to_gif(input_path, output_path, gif_settings)

    if output_format == OutputFormat.WEBP:
        webp_settings = VideoEncodingSettings(
            fps=settings.fps or 10,
            max_width=settings.max_width,
            max_height=settings.max_height,
            quality=settings.quality or DEFAULT_QUALITY,
            loop=settings.loop,
        )
        return convert_to_webp(input_path, output_path, webp_settings)

    if output_format == OutputFormat.MP4:
        return convert_to_mp4(input_path, output_path, settings)

    raise ConversionError(f"Unsupported output format: {output_format}")


def get_effective_settings(config: RecordingConfig) -> dict:
    """Get effective settings by merging preset with overrides.

    Args:
        config: Recording configuration.

    Returns:
        Dict with effective fps, max_width, max_height, quality, format.
    """
    settings = {
        "fps": config.fps or DEFAULT_FPS,
        "max_width": config.max_width,
        "max_height": config.max_height,
        "quality": config.quality or DEFAULT_QUALITY,
        "format": config.output_format,
        "max_size_mb": config.max_size_mb,
    }

    # Apply preset defaults
    if config.preset and config.preset != PlatformPreset.CUSTOM:
        preset_config = PRESET_CONFIGS.get(config.preset, {})

        if config.fps is None and preset_config.get("fps"):
            settings["fps"] = preset_config["fps"]

        if config.max_width is None and preset_config.get("max_width"):
            settings["max_width"] = preset_config["max_width"]

        if config.max_height is None and preset_config.get("max_height"):
            settings["max_height"] = preset_config["max_height"]

        if config.quality is None and preset_config.get("quality"):
            settings["quality"] = preset_config["quality"]

        if preset_config.get("format"):
            settings["format"] = preset_config["format"]

        if config.max_size_mb is None and preset_config.get("max_size_mb"):
            settings["max_size_mb"] = preset_config["max_size_mb"]

    return settings


def run_verifications(
    video_path: Path,
    config: RecordingConfig,
) -> tuple[VerificationResult, ...]:
    """Run all configured verification strategies.

    Args:
        video_path: Path to the video.
        config: Recording configuration.

    Returns:
        Tuple of verification results.
    """
    results: list[VerificationResult] = []
    strategies = config.verification_strategies

    # Expand ALL to individual strategies
    if VerificationStrategy.ALL in strategies:
        strategies = (
            VerificationStrategy.BASIC,
            VerificationStrategy.DURATION,
            VerificationStrategy.FRAMES,
            VerificationStrategy.MOTION,
        )

    settings = get_effective_settings(config)

    for strategy in strategies:
        if strategy == VerificationStrategy.BASIC:
            results.append(verify_basic(video_path))

        elif strategy == VerificationStrategy.DURATION:
            results.append(
                verify_duration(video_path, config.duration_seconds)
            )

        elif strategy == VerificationStrategy.FRAMES:
            results.append(
                verify_frames(
                    video_path,
                    expected_duration=config.duration_seconds,
                    expected_fps=settings["fps"],
                )
            )

        elif strategy == VerificationStrategy.MOTION:
            results.append(verify_motion(video_path))

    return tuple(results)


def calculate_retry_delay(attempt: int, config: RecordingConfig) -> float:
    """Calculate delay before next retry.

    Args:
        attempt: Current attempt number (1-based).
        config: Recording configuration.

    Returns:
        Delay in seconds.
    """
    base_delay = config.retry_delay_ms / 1000.0

    if config.retry_strategy == RetryStrategy.EXPONENTIAL:
        return base_delay * (2 ** (attempt - 1))

    return base_delay


def generate_output_path(
    config: RecordingConfig,
    target: WindowTarget | None = None,
) -> tuple[Path, Path]:
    """Generate output paths for raw recording and final output.

    Args:
        config: Recording configuration.
        target: Optional window target for naming.

    Returns:
        Tuple of (raw_mov_path, final_output_path).
    """
    settings = get_effective_settings(config)
    output_format = settings["format"]

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    safe_name = re.sub(r"[^\w\-]", "_", target.app_name.lower()) if target else "recording"

    if config.output_path:
        final_path = Path(config.output_path)
        if final_path.suffix.lower() not in (".mov", ".gif", ".webp", ".mp4"):
            # Treat as directory
            final_path = final_path / f"{safe_name}_{timestamp}.{output_format.value}"
    else:
        recordings_dir = Path("recordings")
        final_path = recordings_dir / f"{safe_name}_{timestamp}.{output_format.value}"

    # Raw recording is always .mov
    raw_path = final_path.with_suffix(".mov")
    if raw_path == final_path:
        raw_path = final_path.with_stem(f"{final_path.stem}_raw")

    return raw_path, final_path


@dataclass
class _AttemptPaths:
    """Paths for a single recording attempt."""

    raw: Path
    final: Path
    attempt_num: int


def _build_recording_result(
    ctx: _RecordingContext,
    paths: _AttemptPaths,
    video_info: VideoInfo | None,
    verifications: tuple[VerificationResult, ...],
    verified: bool,
) -> RecordingResult:
    """Build a RecordingResult with common parameters."""
    return RecordingResult(
        raw_path=paths.raw,
        final_path=paths.final,
        attempt=paths.attempt_num,
        duration_requested=ctx.config.duration_seconds,
        duration_actual=video_info.duration_seconds if video_info else 0,
        window_id=ctx.target.window_id if ctx.target else None,
        app_name=ctx.target.app_name if ctx.target else None,
        window_title=ctx.target.window_title if ctx.target else None,
        bounds=ctx.region,
        output_format=ctx.settings["format"],
        preset=ctx.config.preset,
        video_info=video_info,
        verifications=verifications,
        verified=verified,
    )


def _finalize_successful_recording(
    attempt_raw: Path,
    attempt_final: Path,
    raw_path: Path,
    final_path: Path,
    config: RecordingConfig,
) -> tuple[Path, Path]:
    """Rename attempt files to final paths and cleanup.

    Returns:
        Tuple of (final_raw_path, final_output_path).
    """
    actual_raw = raw_path
    actual_final = final_path

    # Rename raw file if needed
    if attempt_raw != raw_path and attempt_raw.exists():
        attempt_raw.rename(raw_path)
    else:
        actual_raw = attempt_raw

    # Rename final file if needed
    if attempt_final not in (raw_path, final_path) and attempt_final.exists():
        attempt_final.rename(final_path)
    elif attempt_final == attempt_raw:
        actual_final = actual_raw
    else:
        actual_final = attempt_final

    # Clean up raw if not keeping
    if not config.keep_raw and actual_raw.exists() and actual_raw != actual_final:
        actual_raw.unlink()

    return actual_raw, actual_final


def _cleanup_failed_attempt(attempt_raw: Path, attempt_final: Path) -> None:
    """Clean up files from a failed attempt."""
    if attempt_raw.exists():
        attempt_raw.unlink()
    if attempt_final.exists() and attempt_final != attempt_raw:
        attempt_final.unlink()


def _handle_window_activation(
    target: WindowTarget | None,
    config: RecordingConfig,
    attempt: int,
) -> None:
    """Handle window activation or retry delay."""
    should_activate = target and (
        config.activate_first or
        (attempt > 1 and config.retry_strategy == RetryStrategy.REACTIVATE)
    )

    if should_activate and target:
        settle_time = config.settle_ms / 1000.0
        if attempt > 1:
            settle_time *= attempt
        activate_window(target, settle_time)
    elif attempt > 1:
        delay = calculate_retry_delay(attempt, config)
        time.sleep(delay)


def _convert_recording(
    attempt_raw: Path,
    attempt_final: Path,
    settings: dict,
) -> tuple[VideoInfo | None, tuple[VerificationResult, ...], bool]:
    """Convert recording to target format if needed.

    Returns:
        Tuple of (video_info, additional_verifications, conversion_succeeded).
    """
    try:
        encoding_settings = VideoEncodingSettings(
            fps=settings["fps"],
            max_width=settings["max_width"],
            max_height=settings["max_height"],
            quality=settings["quality"],
        )
        convert_video(attempt_raw, settings["format"], attempt_final, encoding_settings)
        video_info = get_video_info(attempt_final)
        return video_info, (), True
    except (ConversionError, Exception) as e:
        failed_verification = VerificationResult(
            strategy=VerificationStrategy.BASIC,
            passed=False,
            message=f"Conversion failed: {e}",
            details={"error": str(e)},
        )
        return None, (failed_verification,), False


def record_verified(config: RecordingConfig) -> RecordingResult:
    """Record screen with verification and retry logic.

    This is the main entry point for the skill. It:
    1. Finds the target window (if specified)
    2. Switches to target Space if window is on different Space
    3. Refreshes window bounds after Space switch
    4. Optionally activates the window
    5. Records the screen region
    6. Converts to target format
    7. Runs verification checks
    8. Retries on failure up to max_retries times
    9. Returns to original Space after recording

    Args:
        config: Recording configuration.

    Returns:
        RecordingResult with recording details.

    Raises:
        WindowNotFoundError: If target window not found.
        DurationLimitError: If duration exceeds max.
        MaxRetriesError: If verification fails after all retries.
    """
    # Validate duration
    if config.duration_seconds > config.max_duration_seconds:
        raise DurationLimitError(
            f"Requested duration {config.duration_seconds}s exceeds "
            f"max {config.max_duration_seconds}s"
        )

    # Find target window if filtering configured
    target, region = _find_target_if_needed(config)

    # Detect if we need to switch Spaces
    space_ctx = _detect_space_switch_needed(target)
    needs_space_switch = (
        target is not None
        and space_ctx.target_space_index is not None
        and space_ctx.original_space_index != space_ctx.target_space_index
    )

    try:
        # Switch to target Space if needed
        if needs_space_switch and target:
            _switch_to_target_space(target, space_ctx, settle_time=1.0)

            # CRITICAL: Refresh window bounds after Space switch
            # Window coordinates may differ between Spaces
            target, region = _find_target_if_needed(config)

        # Generate output paths and create context
        raw_path, final_path = generate_output_path(config, target)
        ctx = _RecordingContext(
            config=config,
            target=target,
            region=region,
            raw_path=raw_path,
            final_path=final_path,
            settings=get_effective_settings(config),
        )
        last_result: RecordingResult | None = None

        for attempt in range(1, config.max_retries + 1):
            result = _execute_single_attempt(ctx, attempt)
            if result is None:
                continue  # Recording failed, retry

            last_result = result
            if result.verified:
                return _handle_successful_attempt(ctx, result)

            _cleanup_failed_attempt(result.raw_path, result.final_path)

        # All retries exhausted
        failed_strategies = [
            v.strategy.value for v in last_result.verifications if not v.passed
        ]
        raise MaxRetriesError(
            f"Verification failed after {config.max_retries} attempts. "
            f"Failed checks: {', '.join(failed_strategies)}"
        )

    finally:
        # Always return to original Space after recording
        if space_ctx.switched:
            _return_to_original_space(space_ctx, settle_time=0.5)


def _find_target_if_needed(
    config: RecordingConfig,
) -> tuple[WindowTarget | None, WindowBounds | None]:
    """Find target window if filtering is configured."""
    target: WindowTarget | None = None
    region: WindowBounds | None = config.region

    has_window_filters = any([
        config.app_name,
        config.title_pattern,
        config.pid,
        config.path_contains,
        config.args_contains,
    ])

    if has_window_filters:
        target = find_target_window(config)

        # Handle window-relative region (offset from window origin)
        if config.window_relative_region:
            rel = config.window_relative_region
            region = WindowBounds(
                x=target.bounds.x + rel.x,
                y=target.bounds.y + rel.y,
                width=rel.width,
                height=rel.height,
            )
        else:
            region = target.bounds

    return target, region


def _execute_single_attempt(
    ctx: _RecordingContext,
    attempt: int,
) -> RecordingResult | None:
    """Execute a single recording attempt.

    Returns:
        RecordingResult on success, None if recording failed and should retry.

    Raises:
        MaxRetriesError: If this was the last attempt and recording failed.
    """
    _handle_window_activation(ctx.target, ctx.config, attempt)

    attempt_raw = ctx.raw_path.with_stem(f"{ctx.raw_path.stem}_attempt{attempt}")

    # Record screen
    try:
        record_screen_region(
            attempt_raw,
            ctx.config.duration_seconds,
            region=ctx.region if not ctx.config.full_screen else None,
            show_clicks=ctx.config.show_clicks,
        )
    except CaptureError as e:
        if attempt == ctx.config.max_retries:
            raise MaxRetriesError(f"Recording failed after {attempt} attempts: {e}") from e
        return None

    # Get video info and run verifications
    video_info = _safe_get_video_info(attempt_raw)
    verifications = run_verifications(attempt_raw, ctx.config)
    all_passed = all(v.passed for v in verifications)

    # Convert to final format if needed
    attempt_final = ctx.final_path.with_stem(f"{ctx.final_path.stem}_attempt{attempt}")
    state: _VerificationState = (video_info, verifications, all_passed)
    video_info, verifications, all_passed = _maybe_convert(
        attempt_raw, attempt_final, ctx.settings, state
    )

    paths = _AttemptPaths(raw=attempt_raw, final=attempt_final, attempt_num=attempt)
    return _build_recording_result(ctx, paths, video_info, verifications, all_passed)


def _safe_get_video_info(path: Path) -> VideoInfo | None:
    """Get video info, returning None on any error."""
    try:
        return get_video_info(path)
    except Exception:
        return None


# Type alias for verification state
_VerificationState = tuple[VideoInfo | None, tuple[VerificationResult, ...], bool]


def _maybe_convert(
    attempt_raw: Path,
    attempt_final: Path,
    settings: dict,
    state: _VerificationState,
) -> _VerificationState:
    """Convert recording if verification passed and format requires it."""
    video_info, verifications, all_passed = state

    if not all_passed or settings["format"] == OutputFormat.MOV:
        return state

    converted_info, extra_verifications, success = _convert_recording(
        attempt_raw, attempt_final, settings
    )

    if success:
        return converted_info, verifications, True

    return video_info, (*verifications, *extra_verifications), False


def _handle_successful_attempt(
    ctx: _RecordingContext,
    result: RecordingResult,
) -> RecordingResult:
    """Handle file renaming and cleanup for successful recording."""
    actual_raw, actual_final = _finalize_successful_recording(
        result.raw_path, result.final_path, ctx.raw_path, ctx.final_path, ctx.config
    )

    paths = _AttemptPaths(raw=actual_raw, final=actual_final, attempt_num=result.attempt)
    return _build_recording_result(
        ctx, paths, result.video_info, result.verifications, True
    )


@dataclass(frozen=True)
class PreviewResult:
    """Result of a region preview screenshot."""

    screenshot_path: Path
    region: WindowBounds
    window_id: int | None = None
    app_name: str | None = None
    window_title: str | None = None
    window_bounds: WindowBounds | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "screenshot_path": str(self.screenshot_path),
            "region": self.region.to_dict(),
            "window_id": self.window_id,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "window_bounds": self.window_bounds.to_dict() if self.window_bounds else None,
        }


def preview_region(config: RecordingConfig) -> PreviewResult:
    """Take a screenshot of the configured region for coordinate verification.

    This helps users iteratively refine region coordinates before recording.
    Uses the same window discovery and region calculation as recording.

    Args:
        config: Recording configuration with region settings.

    Returns:
        PreviewResult with screenshot path and region details.

    Raises:
        WindowNotFoundError: If target window not found.
        CaptureError: If screenshot fails.
        ValueError: If no region specified.
    """
    # Find target window and calculate region
    target, region = _find_target_if_needed(config)

    if region is None:
        raise ValueError(
            "No region specified. Use --region or --window-region, "
            "or --record to capture a window's bounds."
        )

    # Optionally activate window first
    if target and config.activate_first:
        settle_time = config.settle_ms / 1000.0
        activate_window(target, settle_time)

    # Generate output path for preview
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    if config.output_path:
        output_path = Path(config.output_path)
        if output_path.suffix.lower() != ".png":
            output_path = output_path.with_suffix(".png")
    else:
        safe_name = (
            re.sub(r"[^\w\-]", "_", target.app_name.lower())
            if target else "preview"
        )
        output_path = Path("recordings") / f"{safe_name}_preview_{timestamp}.png"

    # Take screenshot
    capture_region_screenshot(output_path, region)

    return PreviewResult(
        screenshot_path=output_path,
        region=region,
        window_id=target.window_id if target else None,
        app_name=target.app_name if target else None,
        window_title=target.window_title if target else None,
        window_bounds=target.bounds if target else None,
    )


def record_simple(
    app_name: str | None = None,
    duration: float = 5,
    preset: PlatformPreset = PlatformPreset.GITHUB,
    output_path: str | None = None,
    max_retries: int = 5,
) -> RecordingResult:
    """Simple recording with sensible defaults.

    Convenience wrapper around record_verified for common use cases.

    Args:
        app_name: Application name to find.
        duration: Recording duration in seconds.
        preset: Platform preset for optimization.
        output_path: Output path for recording.
        max_retries: Maximum retry attempts.

    Returns:
        RecordingResult with recording details.
    """
    config = RecordingConfig(
        app_name=app_name,
        duration_seconds=duration,
        preset=preset,
        output_path=output_path,
        max_retries=max_retries,
        verification_strategies=(
            VerificationStrategy.BASIC,
            VerificationStrategy.DURATION,
        ),
    )
    return record_verified(config)
