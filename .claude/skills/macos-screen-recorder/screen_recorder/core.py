"""Core functionality for window detection and video verification."""

from __future__ import annotations

import functools
import json
import plistlib
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .models import (
    DEFAULT_FPS,
    MIN_DURATION_FOR_MOTION_CHECK,
    DependencyError,
    RecordingConfig,
    VerificationResult,
    VerificationStrategy,
    VideoInfo,
    WindowBounds,
    WindowNotFoundError,
    WindowTarget,
)

if TYPE_CHECKING:
    pass

# Spaces plist path
SPACES_PLIST_PATH = Path.home() / "Library/Preferences/com.apple.spaces.plist"


@functools.cache
def _get_quartz():
    """Lazy load Quartz framework (cached)."""
    import Quartz

    return Quartz


@functools.cache
def _get_psutil():
    """Lazy load psutil (cached)."""
    import psutil

    return psutil


@functools.cache
def _get_pil():
    """Lazy load PIL (cached)."""
    from PIL import Image as PILImage

    return PILImage


@functools.cache
def _get_imagehash():
    """Lazy load imagehash (cached)."""
    import imagehash

    return imagehash


def check_dependencies() -> dict[str, bool]:
    """Check availability of required external tools.

    Returns:
        Dict mapping tool name to availability status.
    """
    tools = {
        "screencapture": shutil.which("screencapture") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
    }
    return tools


def require_ffmpeg() -> None:
    """Ensure ffmpeg is available.

    Raises:
        DependencyError: If ffmpeg is not found.
    """
    if not shutil.which("ffmpeg"):
        raise DependencyError(
            "ffmpeg not found. Install with: brew install ffmpeg"
        )


def require_ffprobe() -> None:
    """Ensure ffprobe is available.

    Raises:
        DependencyError: If ffprobe is not found.
    """
    if not shutil.which("ffprobe"):
        raise DependencyError(
            "ffprobe not found. Install with: brew install ffmpeg"
        )


def get_spaces_plist() -> dict:
    """Read the spaces plist file."""
    result = subprocess.run(
        ["plutil", "-convert", "xml1", "-o", "-", str(SPACES_PLIST_PATH)],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return {}

    try:
        return plistlib.loads(result.stdout)
    except plistlib.InvalidFileException:
        return {}


def get_window_space_mapping(plist_data: dict) -> dict[int, int]:
    """Map window IDs to Space indexes (1-based)."""
    window_to_space: dict[int, int] = {}

    config = plist_data.get("SpacesDisplayConfiguration", {})
    mgmt_data = config.get("Management Data", {})
    monitors = mgmt_data.get("Monitors", [])

    for monitor in monitors:
        monitor_spaces = monitor.get("Spaces", [])
        for idx, space in enumerate(monitor_spaces, start=1):
            tile_mgr = space.get("TileLayoutManager", {})
            for tile in tile_mgr.get("TileSpaces", []):
                window_id = tile.get("TileWindowID")
                if window_id:
                    window_to_space[window_id] = idx

    return window_to_space


def get_process_info(pid: int) -> tuple[str | None, list[str]]:
    """Get process executable path and command line."""
    psutil = _get_psutil()

    try:
        proc = psutil.Process(pid)
        return proc.exe(), proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None, []


def _matches_config_filters(
    config: RecordingConfig,
    window: dict,
    process_info: tuple[str | None, list[str]],
) -> bool:
    """Check if window matches all config filters.

    Args:
        config: Recording configuration with filters.
        window: Window info dict from CGWindowListCopyWindowInfo.
        process_info: Tuple of (exe_path, cmdline) from get_process_info.

    Returns:
        True if window matches all filters, False otherwise.
    """
    app_name = window.get("kCGWindowOwnerName", "") or ""
    window_title = window.get("kCGWindowName", "") or ""
    pid = window.get("kCGWindowOwnerPID", 0)
    exe_path, cmdline = process_info

    if config.app_name and config.app_name.lower() not in app_name.lower():
        return False
    if config.title_pattern and not re.search(config.title_pattern, window_title, re.IGNORECASE):
        return False
    if config.pid and pid != config.pid:
        return False
    if config.path_contains and (not exe_path or config.path_contains not in exe_path):
        return False
    if config.path_excludes and exe_path and config.path_excludes in exe_path:
        return False
    return not config.args_contains or config.args_contains in " ".join(cmdline)


def _describe_filters(config: RecordingConfig) -> str:
    """Build human-readable description of active filters.

    Args:
        config: Recording configuration with filters.

    Returns:
        Comma-separated filter descriptions or 'no filters'.
    """
    filters = []
    if config.app_name:
        filters.append(f"app_name={config.app_name}")
    if config.title_pattern:
        filters.append(f"title_pattern={config.title_pattern}")
    if config.pid:
        filters.append(f"pid={config.pid}")
    if config.args_contains:
        filters.append(f"args_contains={config.args_contains}")
    return ", ".join(filters) or "no filters"


def find_target_window(config: RecordingConfig) -> WindowTarget:
    """Find the target window based on configuration.

    Args:
        config: Recording configuration with window filters.

    Returns:
        WindowTarget with window information.

    Raises:
        WindowNotFoundError: If no matching window found.
    """
    Q = _get_quartz()

    all_windows = Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionAll, Q.kCGNullWindowID)
    if not all_windows:
        raise WindowNotFoundError("No windows available")

    # Get space mapping
    plist_data = get_spaces_plist()
    window_space_map = get_window_space_mapping(plist_data)

    process_cache: dict[int, tuple[str | None, list[str]]] = {}

    for window in all_windows:
        # Skip non-main windows (layer != 0) and titleless windows
        if window.get("kCGWindowLayer", 0) != 0:
            continue
        if not window.get("kCGWindowName"):
            continue

        pid = window.get("kCGWindowOwnerPID", 0)

        # Get process info for path/args filtering
        if pid not in process_cache:
            process_cache[pid] = get_process_info(pid)
        process_info = process_cache[pid]

        # Apply all config filters
        if not _matches_config_filters(config, window, process_info):
            continue

        # Found a match
        app_name = window.get("kCGWindowOwnerName", "") or ""
        window_title = window.get("kCGWindowName", "") or ""
        exe_path, cmdline = process_info
        bounds = window.get("kCGWindowBounds", {})

        return WindowTarget(
            window_id=window.get("kCGWindowNumber", 0),
            app_name=app_name,
            window_title=window_title,
            pid=pid,
            bounds=WindowBounds(
                x=bounds.get("X", 0.0),
                y=bounds.get("Y", 0.0),
                width=bounds.get("Width", 0.0),
                height=bounds.get("Height", 0.0),
            ),
            space_index=window_space_map.get(window.get("kCGWindowNumber", 0)),
            exe_path=exe_path,
            cmdline=tuple(cmdline),
        )

    # No match found
    raise WindowNotFoundError(f"No window found matching: {_describe_filters(config)}")


def get_video_info(video_path: Path) -> VideoInfo:
    """Get video metadata using ffprobe.

    Args:
        video_path: Path to the video file.

    Returns:
        VideoInfo with video metadata.

    Raises:
        DependencyError: If ffprobe is not available.
        ValueError: If video cannot be parsed.
    """
    require_ffprobe()

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            "-select_streams", "v:0",
            "-count_frames",
            str(video_path),
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"ffprobe failed: {stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse ffprobe output: {e}") from e

    # Extract stream info
    streams = data.get("streams", [])
    video_stream = streams[0] if streams else {}

    # Parse frame rate (can be "30/1" or "29.97")
    fps_str = video_stream.get("avg_frame_rate", "0/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 0.0
    else:
        fps = float(fps_str) if fps_str else 0.0

    # Get frame count
    frame_count = int(video_stream.get("nb_read_frames", 0) or 0)
    if frame_count == 0:
        # Fallback: estimate from duration * fps
        duration = float(data.get("format", {}).get("duration", 0))
        frame_count = int(duration * fps) if fps > 0 else 0

    # Get format info
    format_info = data.get("format", {})

    return VideoInfo(
        path=video_path,
        duration_seconds=float(format_info.get("duration", 0)),
        frame_count=frame_count,
        fps=fps or DEFAULT_FPS,
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        file_size_bytes=int(format_info.get("size", 0) or video_path.stat().st_size),
        format_name=format_info.get("format_name", "unknown"),
    )


def extract_frame(video_path: Path, output_path: Path, time_seconds: float = 0) -> Path:
    """Extract a single frame from a video.

    Args:
        video_path: Path to the video file.
        output_path: Path to save the frame image.
        time_seconds: Time position to extract (default: 0 = first frame).

    Returns:
        Path to the extracted frame.

    Raises:
        DependencyError: If ffmpeg is not available.
        ValueError: If extraction fails.
    """
    require_ffmpeg()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",  # Overwrite
            "-ss", str(time_seconds),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",  # High quality
            str(output_path),
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0 or not output_path.exists():
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"Frame extraction failed: {stderr}")

    return output_path


def compute_image_hash(image_path: Path) -> str:
    """Compute perceptual hash of an image.

    Args:
        image_path: Path to the image file.

    Returns:
        Hex string of the perceptual hash.
    """
    PILImage = _get_pil()
    imagehash = _get_imagehash()

    img = PILImage.open(image_path)
    phash = imagehash.phash(img)
    return str(phash)


def compute_hash_distance(hash1: str, hash2: str) -> int:
    """Compute hamming distance between two hash strings.

    Args:
        hash1: First hash string.
        hash2: Second hash string.

    Returns:
        Hamming distance (number of differing bits).
    """
    imagehash = _get_imagehash()

    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    return h1 - h2


def verify_basic(video_path: Path) -> VerificationResult:
    """Basic verification: file exists, size > 0.

    Args:
        video_path: Path to the video file.

    Returns:
        VerificationResult with pass/fail status.
    """
    if not video_path.exists():
        return VerificationResult(
            strategy=VerificationStrategy.BASIC,
            passed=False,
            message="File does not exist",
            details={"path": str(video_path)},
        )

    file_size = video_path.stat().st_size
    if file_size == 0:
        return VerificationResult(
            strategy=VerificationStrategy.BASIC,
            passed=False,
            message="File is empty",
            details={"path": str(video_path), "size": 0},
        )

    return VerificationResult(
        strategy=VerificationStrategy.BASIC,
        passed=True,
        message="Valid video file",
        details={"path": str(video_path), "size": file_size},
    )


def verify_duration(
    video_path: Path,
    expected_duration: float,
    tolerance: float = 0.5,
) -> VerificationResult:
    """Verify video duration matches expected (within tolerance).

    Args:
        video_path: Path to the video file.
        expected_duration: Expected duration in seconds.
        tolerance: Allowed variance in seconds (default 0.5s).

    Returns:
        VerificationResult with pass/fail status.
    """
    try:
        info = get_video_info(video_path)
    except (DependencyError, ValueError) as e:
        return VerificationResult(
            strategy=VerificationStrategy.DURATION,
            passed=False,
            message=f"Could not read video info: {e}",
            details={"error": str(e)},
        )

    actual = info.duration_seconds
    diff = abs(actual - expected_duration)
    passed = diff <= tolerance

    if passed:
        message = "Duration matches"
    else:
        message = f"Duration mismatch: {actual:.1f}s vs {expected_duration:.1f}s expected"

    return VerificationResult(
        strategy=VerificationStrategy.DURATION,
        passed=passed,
        message=message,
        details={
            "expected_seconds": expected_duration,
            "actual_seconds": actual,
            "difference_seconds": diff,
            "tolerance_seconds": tolerance,
        },
    )


def verify_frames(
    video_path: Path,
    min_frames: int | None = None,
    expected_duration: float | None = None,
    expected_fps: float = DEFAULT_FPS,
) -> VerificationResult:
    """Verify video has minimum expected frames.

    Args:
        video_path: Path to the video file.
        min_frames: Minimum frame count (overrides duration calculation).
        expected_duration: Expected duration to calculate min frames.
        expected_fps: Expected FPS for calculation.

    Returns:
        VerificationResult with pass/fail status.
    """
    try:
        info = get_video_info(video_path)
    except (DependencyError, ValueError) as e:
        return VerificationResult(
            strategy=VerificationStrategy.FRAMES,
            passed=False,
            message=f"Could not read video info: {e}",
            details={"error": str(e)},
        )

    # Calculate expected minimum frames
    if min_frames is None and expected_duration is not None:
        # Expect at least 80% of theoretical frames
        min_frames = int(expected_duration * expected_fps * 0.8)
    elif min_frames is None:
        min_frames = 1  # At least one frame

    passed = info.frame_count >= min_frames

    if passed:
        message = "Frame count OK"
    else:
        message = f"Insufficient frames: {info.frame_count} < {min_frames}"

    return VerificationResult(
        strategy=VerificationStrategy.FRAMES,
        passed=passed,
        message=message,
        details={
            "actual_frames": info.frame_count,
            "minimum_required": min_frames,
            "actual_fps": info.fps,
        },
    )


def verify_motion(
    video_path: Path,
    hash_threshold: int = 5,
) -> VerificationResult:
    """Verify video has motion (first and last frames differ).

    Args:
        video_path: Path to the video file.
        hash_threshold: Minimum hamming distance for "different".

    Returns:
        VerificationResult with pass/fail status.
    """
    import tempfile

    try:
        info = get_video_info(video_path)
    except (DependencyError, ValueError) as e:
        return VerificationResult(
            strategy=VerificationStrategy.MOTION,
            passed=False,
            message=f"Could not read video info: {e}",
            details={"error": str(e)},
        )

    # Need minimum duration for motion check
    if info.duration_seconds < MIN_DURATION_FOR_MOTION_CHECK:
        return VerificationResult(
            strategy=VerificationStrategy.MOTION,
            passed=True,
            message="Video too short for motion check, skipping",
            details={"duration_seconds": info.duration_seconds},
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        try:
            # Extract first frame
            first_frame = extract_frame(video_path, tmppath / "first.png", 0)
            first_hash = compute_image_hash(first_frame)

            # Extract last frame (slightly before end to avoid edge issues)
            last_time = max(0, info.duration_seconds - 0.1)
            last_frame = extract_frame(video_path, tmppath / "last.png", last_time)
            last_hash = compute_image_hash(last_frame)

        except ValueError as e:
            return VerificationResult(
                strategy=VerificationStrategy.MOTION,
                passed=False,
                message=f"Frame extraction failed: {e}",
                details={"error": str(e)},
            )

    distance = compute_hash_distance(first_hash, last_hash)
    passed = distance >= hash_threshold

    return VerificationResult(
        strategy=VerificationStrategy.MOTION,
        passed=passed,
        message="Motion detected" if passed else "No significant motion detected",
        details={
            "first_hash": first_hash,
            "last_hash": last_hash,
            "hamming_distance": distance,
            "threshold": hash_threshold,
        },
    )
