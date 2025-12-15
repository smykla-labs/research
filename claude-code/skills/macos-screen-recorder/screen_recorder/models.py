"""Data models and exceptions for macOS Screen Recorder."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class OutputFormat(Enum):
    """Supported output formats."""

    MOV = "mov"  # Native macOS format
    GIF = "gif"  # Animated GIF (palette optimized)
    WEBP = "webp"  # Animated WebP (lossy)
    MP4 = "mp4"  # H.264 video


class PlatformPreset(Enum):
    """Pre-configured platform optimization presets."""

    DISCORD = "discord"  # Max 10MB, webp/gif, 10fps, 720px
    GITHUB = "github"  # Target 5MB, gif, 10fps, 600px
    JETBRAINS = "jetbrains"  # 1280x800, gif, 15fps
    RAW = "raw"  # No conversion, mov only
    CUSTOM = "custom"  # User-specified settings


class VerificationStrategy(Enum):
    """Verification strategies for recordings."""

    BASIC = "basic"  # File exists, size > 0
    DURATION = "duration"  # Duration matches requested
    FRAMES = "frames"  # Frame count > expected minimum
    MOTION = "motion"  # First/last frames differ (content changed)
    ALL = "all"  # All strategies combined


class RetryStrategy(Enum):
    """Retry strategies on recording failure."""

    FIXED = "fixed"  # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    REACTIVATE = "reactivate"  # Re-activate window before retry


class CaptureBackend(Enum):
    """Backend for screen capture.

    Note: Video recording currently only supports QUARTZ backend (screencapture -v).
    ScreenCaptureKit streaming for video is not yet implemented.
    """

    QUARTZ = "quartz"  # screencapture CLI (requires activation for video)
    SCREENCAPTUREKIT = "screencapturekit"  # ScreenCaptureKit (screenshots only for now)
    AUTO = "auto"  # Auto-select best available backend


# Platform preset configurations
PRESET_CONFIGS: dict[PlatformPreset, dict] = {
    PlatformPreset.DISCORD: {
        "format": OutputFormat.WEBP,
        "max_size_mb": 10,
        "fps": 10,
        "max_width": 720,
        "quality": 70,
        "description": "Discord (no Nitro): webp, 10MB max, 10fps, 720px",
    },
    PlatformPreset.GITHUB: {
        "format": OutputFormat.GIF,
        "max_size_mb": 5,
        "fps": 10,
        "max_width": 600,
        "quality": None,  # GIF uses palette optimization
        "description": "GitHub README: gif, ~5MB, 10fps, 600px",
    },
    PlatformPreset.JETBRAINS: {
        "format": OutputFormat.GIF,
        "max_size_mb": 20,
        "fps": 15,
        "max_width": 1280,
        "max_height": 800,
        "quality": None,
        "description": "JetBrains Marketplace: gif, 1280x800, 15fps",
    },
    PlatformPreset.RAW: {
        "format": OutputFormat.MOV,
        "max_size_mb": None,
        "fps": None,  # Native fps
        "max_width": None,
        "quality": None,
        "description": "Raw MOV: no conversion, native quality",
    },
}

# Default settings
DEFAULT_DURATION_SECONDS = 10
DEFAULT_MAX_DURATION_SECONDS = 60
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_DELAY_MS = 500
DEFAULT_SETTLE_MS = 500
DEFAULT_FPS = 15
DEFAULT_QUALITY = 75  # For lossy formats
MIN_DURATION_FOR_MOTION_CHECK = 0.5  # Minimum video duration for motion verification


class RecordingError(Exception):
    """Base exception for recording operations."""


class CaptureError(RecordingError):
    """Failed to capture screen recording."""


class ConversionError(RecordingError):
    """Failed to convert recording to target format."""


class VerificationError(RecordingError):
    """Recording verification failed."""


class WindowNotFoundError(RecordingError):
    """Target window not found."""


class MaxRetriesError(RecordingError):
    """Max retries exceeded without successful verification."""


class DurationLimitError(RecordingError):
    """Requested duration exceeds safety limit."""


class DependencyError(RecordingError):
    """Required dependency (ffmpeg/ffprobe) not available."""


@dataclass(frozen=True)
class WindowBounds:
    """Window bounds for region recording."""

    x: float
    y: float
    width: float
    height: float

    @property
    def as_region(self) -> str:
        """Format as screencapture -R argument: x,y,width,height."""
        return f"{int(self.x)},{int(self.y)},{int(self.width)},{int(self.height)}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class VideoInfo:
    """Video file metadata from ffprobe."""

    path: Path
    duration_seconds: float
    frame_count: int
    fps: float
    width: int
    height: int
    file_size_bytes: int
    format_name: str

    @property
    def file_size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": str(self.path),
            "duration_seconds": self.duration_seconds,
            "frame_count": self.frame_count,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "file_size_bytes": self.file_size_bytes,
            "file_size_mb": round(self.file_size_mb, 2),
            "format_name": self.format_name,
        }


@dataclass(frozen=True)
class VerificationResult:
    """Result of a single verification check."""

    strategy: VerificationStrategy
    passed: bool
    message: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "strategy": self.strategy.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class RecordingResult:
    """Result of a screen recording operation."""

    # Output paths
    raw_path: Path
    final_path: Path

    # Recording details
    attempt: int
    duration_requested: float
    duration_actual: float

    # Window info (if window-targeted)
    window_id: int | None
    app_name: str | None
    window_title: str | None
    bounds: WindowBounds | None

    # Output info
    output_format: OutputFormat
    preset: PlatformPreset | None
    video_info: VideoInfo | None

    # Verification
    verifications: tuple[VerificationResult, ...] = field(default_factory=tuple)
    verified: bool = False

    @property
    def all_passed(self) -> bool:
        """True if all verifications passed."""
        return all(v.passed for v in self.verifications)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "raw_path": str(self.raw_path),
            "final_path": str(self.final_path),
            "attempt": self.attempt,
            "duration_requested": self.duration_requested,
            "duration_actual": self.duration_actual,
            "window_id": self.window_id,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "output_format": self.output_format.value,
            "preset": self.preset.value if self.preset else None,
            "video_info": self.video_info.to_dict() if self.video_info else None,
            "verifications": [v.to_dict() for v in self.verifications],
            "verified": self.verified,
        }


@dataclass(frozen=True)
class RecordingConfig:
    """Configuration for screen recording with verification."""

    # Target specification (window-based)
    app_name: str | None = None
    title_pattern: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None

    # Or direct region specification
    region: WindowBounds | None = None
    window_relative_region: WindowBounds | None = None  # Offset from window origin
    full_screen: bool = False

    # Recording settings
    duration_seconds: float = DEFAULT_DURATION_SECONDS
    max_duration_seconds: float = DEFAULT_MAX_DURATION_SECONDS
    show_clicks: bool = True

    # Output settings
    output_path: str | None = None
    output_format: OutputFormat = OutputFormat.GIF
    preset: PlatformPreset | None = None

    # Format-specific settings (override preset)
    fps: int | None = None
    max_width: int | None = None
    max_height: int | None = None
    quality: int | None = None  # For lossy formats (webp, mp4)
    max_size_mb: float | None = None

    # Behavior
    activate_first: bool = True
    settle_ms: int = DEFAULT_SETTLE_MS
    keep_raw: bool = False  # Keep original .mov file

    # Verification
    verification_strategies: tuple[VerificationStrategy, ...] = (VerificationStrategy.BASIC,)

    # Retry
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay_ms: int = DEFAULT_RETRY_DELAY_MS
    retry_strategy: RetryStrategy = RetryStrategy.FIXED

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "app_name": self.app_name,
            "title_pattern": self.title_pattern,
            "pid": self.pid,
            "path_contains": self.path_contains,
            "path_excludes": self.path_excludes,
            "args_contains": self.args_contains,
            "region": self.region.to_dict() if self.region else None,
            "window_relative_region": (
                self.window_relative_region.to_dict() if self.window_relative_region else None
            ),
            "full_screen": self.full_screen,
            "duration_seconds": self.duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "show_clicks": self.show_clicks,
            "output_path": self.output_path,
            "output_format": self.output_format.value,
            "preset": self.preset.value if self.preset else None,
            "fps": self.fps,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "quality": self.quality,
            "max_size_mb": self.max_size_mb,
            "activate_first": self.activate_first,
            "settle_ms": self.settle_ms,
            "keep_raw": self.keep_raw,
            "verification_strategies": [s.value for s in self.verification_strategies],
            "max_retries": self.max_retries,
            "retry_delay_ms": self.retry_delay_ms,
            "retry_strategy": self.retry_strategy.value,
        }


@dataclass(frozen=True)
class WindowTarget:
    """Target window information for recording."""

    window_id: int
    app_name: str
    window_title: str
    pid: int
    bounds: WindowBounds
    space_index: int | None = None
    exe_path: str | None = None
    cmdline: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "window_id": self.window_id,
            "app_name": self.app_name,
            "window_title": self.window_title,
            "pid": self.pid,
            "bounds": self.bounds.to_dict(),
            "space_index": self.space_index,
            "exe_path": self.exe_path,
            "cmdline": list(self.cmdline),
        }


@dataclass(frozen=True)
class VideoEncodingSettings:
    """Settings for video encoding/conversion."""

    fps: int = DEFAULT_FPS
    max_width: int | None = None
    max_height: int | None = None
    quality: int = DEFAULT_QUALITY
    loop: bool = True
    crf: int = 23  # For MP4 encoding

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "fps": self.fps,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "quality": self.quality,
            "loop": self.loop,
            "crf": self.crf,
        }


@dataclass(frozen=True)
class ConversionConfig:
    """Configuration for video format conversion."""

    input_path: Path
    output_path: Path
    output_format: OutputFormat
    fps: int = DEFAULT_FPS
    max_width: int | None = None
    max_height: int | None = None
    quality: int = DEFAULT_QUALITY
    loop: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "output_format": self.output_format.value,
            "fps": self.fps,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "quality": self.quality,
            "loop": self.loop,
        }
