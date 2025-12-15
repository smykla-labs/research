"""Comprehensive tests for macOS Screen Recorder skill."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from screen_recorder import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_FPS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_QUALITY,
    PRESET_CONFIGS,
    OutputFormat,
    PlatformPreset,
    RecordingConfig,
    RecordingResult,
    RetryStrategy,
    VerificationResult,
    VerificationStrategy,
    VideoInfo,
    WindowBounds,
    WindowTarget,
)
from screen_recorder.cli import (
    FormatOptions,
    OutputOptions,
    RecordingOptions,
    RetryOptions,
    WindowFilterOptions,
    build_config,
    main,
    parse_output_format,
    parse_preset,
    parse_region,
    parse_retry_strategy,
    parse_verification_strategies,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_bounds() -> WindowBounds:
    """Create sample window bounds."""
    return WindowBounds(x=100.0, y=50.0, width=800.0, height=600.0)


@pytest.fixture
def sample_target(sample_bounds: WindowBounds) -> WindowTarget:
    """Create sample window target."""
    return WindowTarget(
        window_id=12345,
        app_name="TestApp",
        window_title="Test Window",
        pid=1234,
        bounds=sample_bounds,
        space_index=1,
        exe_path="/Applications/TestApp.app",
        cmdline=("TestApp", "--arg1", "value"),
    )


@pytest.fixture
def sample_video_info() -> VideoInfo:
    """Create sample video info."""
    return VideoInfo(
        path=Path("test.mov"),
        duration_seconds=5.0,
        frame_count=150,
        fps=30.0,
        width=1920,
        height=1080,
        file_size_bytes=5_000_000,
        format_name="mov",
    )


@pytest.fixture
def sample_verification_passed() -> VerificationResult:
    """Create passed verification result."""
    return VerificationResult(
        strategy=VerificationStrategy.BASIC,
        passed=True,
        message="Valid video file",
        details={"size": 5000000},
    )


@pytest.fixture
def sample_verification_failed() -> VerificationResult:
    """Create failed verification result."""
    return VerificationResult(
        strategy=VerificationStrategy.DURATION,
        passed=False,
        message="Duration mismatch",
        details={"expected": 5.0, "actual": 3.0},
    )


@pytest.fixture
def sample_config() -> RecordingConfig:
    """Create sample recording config."""
    return RecordingConfig(
        app_name="TestApp",
        duration_seconds=5.0,
        output_format=OutputFormat.GIF,
        preset=PlatformPreset.GITHUB,
    )


@pytest.fixture
def sample_result(
    sample_bounds: WindowBounds,
    sample_video_info: VideoInfo,
    sample_verification_passed: VerificationResult,
) -> RecordingResult:
    """Create sample recording result."""
    return RecordingResult(
        raw_path=Path("test_raw.mov"),
        final_path=Path("test.gif"),
        attempt=1,
        duration_requested=5.0,
        duration_actual=5.1,
        window_id=12345,
        app_name="TestApp",
        window_title="Test Window",
        bounds=sample_bounds,
        output_format=OutputFormat.GIF,
        preset=PlatformPreset.GITHUB,
        video_info=sample_video_info,
        verifications=(sample_verification_passed,),
        verified=True,
    )


# =============================================================================
# WindowBounds Tests
# =============================================================================


class TestWindowBounds:
    """Tests for WindowBounds dataclass."""

    def test_field_access(self, sample_bounds: WindowBounds) -> None:
        """Test field access."""
        assert sample_bounds.x == 100.0
        assert sample_bounds.y == 50.0
        assert sample_bounds.width == 800.0
        assert sample_bounds.height == 600.0

    def test_as_region(self, sample_bounds: WindowBounds) -> None:
        """Test as_region property for screencapture."""
        assert sample_bounds.as_region == "100,50,800,600"

    def test_to_dict(self, sample_bounds: WindowBounds) -> None:
        """Test to_dict method."""
        data = sample_bounds.to_dict()
        assert data["x"] == 100.0
        assert data["y"] == 50.0
        assert data["width"] == 800.0
        assert data["height"] == 600.0

    def test_frozen_immutable(self, sample_bounds: WindowBounds) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_bounds.x = 200.0  # type: ignore[misc]


# =============================================================================
# WindowTarget Tests
# =============================================================================


class TestWindowTarget:
    """Tests for WindowTarget dataclass."""

    def test_field_access(self, sample_target: WindowTarget) -> None:
        """Test field access."""
        assert sample_target.window_id == 12345
        assert sample_target.app_name == "TestApp"
        assert sample_target.pid == 1234

    def test_to_dict(self, sample_target: WindowTarget) -> None:
        """Test to_dict method."""
        data = sample_target.to_dict()
        assert data["window_id"] == 12345
        assert data["app_name"] == "TestApp"
        assert data["bounds"]["width"] == 800.0
        assert data["cmdline"] == ["TestApp", "--arg1", "value"]

    def test_frozen_immutable(self, sample_target: WindowTarget) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_target.window_id = 99999  # type: ignore[misc]


# =============================================================================
# VideoInfo Tests
# =============================================================================


class TestVideoInfo:
    """Tests for VideoInfo dataclass."""

    def test_field_access(self, sample_video_info: VideoInfo) -> None:
        """Test field access."""
        assert sample_video_info.duration_seconds == 5.0
        assert sample_video_info.frame_count == 150
        assert sample_video_info.fps == 30.0

    def test_file_size_mb_property(self, sample_video_info: VideoInfo) -> None:
        """Test file_size_mb calculated property."""
        assert abs(sample_video_info.file_size_mb - 4.77) < 0.1

    def test_to_dict(self, sample_video_info: VideoInfo) -> None:
        """Test to_dict method."""
        data = sample_video_info.to_dict()
        assert data["duration_seconds"] == 5.0
        assert data["frame_count"] == 150
        assert "file_size_mb" in data

    def test_frozen_immutable(self, sample_video_info: VideoInfo) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_video_info.duration_seconds = 10.0  # type: ignore[misc]


# =============================================================================
# VerificationResult Tests
# =============================================================================


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_passed_result(self, sample_verification_passed: VerificationResult) -> None:
        """Test passed verification result."""
        assert sample_verification_passed.passed is True
        assert sample_verification_passed.strategy == VerificationStrategy.BASIC

    def test_failed_result(self, sample_verification_failed: VerificationResult) -> None:
        """Test failed verification result."""
        assert sample_verification_failed.passed is False
        assert "mismatch" in sample_verification_failed.message.lower()

    def test_to_dict(self, sample_verification_passed: VerificationResult) -> None:
        """Test to_dict method."""
        data = sample_verification_passed.to_dict()
        assert data["strategy"] == "basic"
        assert data["passed"] is True


# =============================================================================
# RecordingConfig Tests
# =============================================================================


class TestRecordingConfig:
    """Tests for RecordingConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RecordingConfig()
        assert config.duration_seconds == DEFAULT_DURATION_SECONDS
        assert config.max_retries == DEFAULT_MAX_RETRIES
        assert config.output_format == OutputFormat.GIF

    def test_custom_values(self, sample_config: RecordingConfig) -> None:
        """Test custom configuration values."""
        assert sample_config.app_name == "TestApp"
        assert sample_config.duration_seconds == 5.0
        assert sample_config.preset == PlatformPreset.GITHUB

    def test_to_dict(self, sample_config: RecordingConfig) -> None:
        """Test to_dict method."""
        data = sample_config.to_dict()
        assert data["app_name"] == "TestApp"
        assert data["output_format"] == "gif"
        assert data["preset"] == "github"

    def test_frozen_immutable(self, sample_config: RecordingConfig) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_config.duration_seconds = 10.0  # type: ignore[misc]


# =============================================================================
# RecordingResult Tests
# =============================================================================


class TestRecordingResult:
    """Tests for RecordingResult dataclass."""

    def test_field_access(self, sample_result: RecordingResult) -> None:
        """Test field access."""
        assert sample_result.attempt == 1
        assert sample_result.verified is True
        assert sample_result.output_format == OutputFormat.GIF

    def test_all_passed_property(self, sample_result: RecordingResult) -> None:
        """Test all_passed computed property."""
        assert sample_result.all_passed is True

    def test_all_passed_with_failure(
        self,
        sample_bounds: WindowBounds,
        sample_video_info: VideoInfo,
        sample_verification_failed: VerificationResult,
    ) -> None:
        """Test all_passed when verification failed."""
        result = RecordingResult(
            raw_path=Path("test.mov"),
            final_path=Path("test.gif"),
            attempt=1,
            duration_requested=5.0,
            duration_actual=3.0,
            window_id=None,
            app_name=None,
            window_title=None,
            bounds=sample_bounds,
            output_format=OutputFormat.GIF,
            preset=None,
            video_info=sample_video_info,
            verifications=(sample_verification_failed,),
            verified=False,
        )
        assert result.all_passed is False

    def test_to_dict(self, sample_result: RecordingResult) -> None:
        """Test to_dict method."""
        data = sample_result.to_dict()
        assert data["attempt"] == 1
        assert data["verified"] is True
        assert data["output_format"] == "gif"
        assert "video_info" in data
        assert "verifications" in data


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_output_format_values(self) -> None:
        """Test OutputFormat enum values."""
        assert OutputFormat.GIF.value == "gif"
        assert OutputFormat.WEBP.value == "webp"
        assert OutputFormat.MP4.value == "mp4"
        assert OutputFormat.MOV.value == "mov"

    def test_platform_preset_values(self) -> None:
        """Test PlatformPreset enum values."""
        assert PlatformPreset.DISCORD.value == "discord"
        assert PlatformPreset.GITHUB.value == "github"
        assert PlatformPreset.JETBRAINS.value == "jetbrains"
        assert PlatformPreset.RAW.value == "raw"

    def test_verification_strategy_values(self) -> None:
        """Test VerificationStrategy enum values."""
        assert VerificationStrategy.BASIC.value == "basic"
        assert VerificationStrategy.DURATION.value == "duration"
        assert VerificationStrategy.FRAMES.value == "frames"
        assert VerificationStrategy.MOTION.value == "motion"
        assert VerificationStrategy.ALL.value == "all"

    def test_retry_strategy_values(self) -> None:
        """Test RetryStrategy enum values."""
        assert RetryStrategy.FIXED.value == "fixed"
        assert RetryStrategy.EXPONENTIAL.value == "exponential"
        assert RetryStrategy.REACTIVATE.value == "reactivate"


# =============================================================================
# Preset Config Tests
# =============================================================================


class TestPresetConfigs:
    """Tests for preset configurations."""

    def test_discord_preset(self) -> None:
        """Test Discord preset configuration."""
        config = PRESET_CONFIGS[PlatformPreset.DISCORD]
        assert config["format"] == OutputFormat.WEBP
        assert config["max_size_mb"] == 10
        assert config["fps"] == 10
        assert config["max_width"] == 720

    def test_github_preset(self) -> None:
        """Test GitHub preset configuration."""
        config = PRESET_CONFIGS[PlatformPreset.GITHUB]
        assert config["format"] == OutputFormat.GIF
        assert config["max_size_mb"] == 5
        assert config["fps"] == 10
        assert config["max_width"] == 600

    def test_jetbrains_preset(self) -> None:
        """Test JetBrains preset configuration."""
        config = PRESET_CONFIGS[PlatformPreset.JETBRAINS]
        assert config["format"] == OutputFormat.GIF
        assert config["fps"] == 15
        assert config["max_width"] == 1280
        assert config["max_height"] == 800

    def test_raw_preset(self) -> None:
        """Test raw preset configuration."""
        config = PRESET_CONFIGS[PlatformPreset.RAW]
        assert config["format"] == OutputFormat.MOV
        assert config["max_size_mb"] is None


# =============================================================================
# CLI Subcommand Tests
# =============================================================================


class TestCLISubcommands:
    """Tests for CLI subcommands (Typer-based)."""

    def test_main_no_args_shows_error(self, capsys) -> None:
        """Test that no args shows error and returns 2."""
        result = main([])
        # Typer returns 2 when missing required command
        assert result == 2
        captured = capsys.readouterr()
        assert "Missing command" in captured.err

    def test_check_deps_command(self, capsys) -> None:
        """Test check-deps subcommand."""
        with patch("screen_recorder.cli.check_dependencies") as mock_check:
            mock_check.return_value = {
                "screencapture": True,
                "ffmpeg": True,
                "ffprobe": True,
            }
            result = main(["check-deps"])

        assert result == 0
        captured = capsys.readouterr()
        assert "screencapture" in captured.out

    def test_check_deps_missing(self, capsys) -> None:
        """Test check-deps with missing dependency."""
        with patch("screen_recorder.cli.check_dependencies") as mock_check:
            mock_check.return_value = {
                "screencapture": True,
                "ffmpeg": False,
                "ffprobe": False,
            }
            result = main(["check-deps"])

        assert result == 1

    def test_find_command(self, capsys, sample_target: WindowTarget) -> None:
        """Test find subcommand."""
        with patch("screen_recorder.cli.find_target_window") as mock_find:
            mock_find.return_value = sample_target
            result = main(["find", "TestApp"])

        assert result == 0
        captured = capsys.readouterr()
        assert "TestApp" in captured.out

    def test_find_command_json(self, capsys, sample_target: WindowTarget) -> None:
        """Test find subcommand with --json output."""
        with patch("screen_recorder.cli.find_target_window") as mock_find:
            mock_find.return_value = sample_target
            result = main(["find", "TestApp", "--json"])

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["app_name"] == "TestApp"
        assert data["window_id"] == 12345


# =============================================================================
# CLI Parse Functions Tests
# =============================================================================


class TestCLIParseFunctions:
    """Tests for CLI parsing helper functions."""

    def test_parse_output_format(self) -> None:
        """Test output format parsing."""
        assert parse_output_format("gif") == OutputFormat.GIF
        assert parse_output_format("webp") == OutputFormat.WEBP
        assert parse_output_format("mp4") == OutputFormat.MP4
        assert parse_output_format("mov") == OutputFormat.MOV
        assert parse_output_format("unknown") == OutputFormat.GIF

    def test_parse_preset(self) -> None:
        """Test preset parsing."""
        assert parse_preset("discord") == PlatformPreset.DISCORD
        assert parse_preset("github") == PlatformPreset.GITHUB
        assert parse_preset("jetbrains") == PlatformPreset.JETBRAINS
        assert parse_preset("raw") == PlatformPreset.RAW
        assert parse_preset(None) is None

    def test_parse_verification_strategies_basic(self) -> None:
        """Test verification strategy parsing."""
        strategies = parse_verification_strategies(["basic", "duration"])
        assert VerificationStrategy.BASIC in strategies
        assert VerificationStrategy.DURATION in strategies

    def test_parse_verification_strategies_all(self) -> None:
        """Test 'all' verification strategy."""
        strategies = parse_verification_strategies(["all"])
        assert strategies == (VerificationStrategy.ALL,)

    def test_parse_verification_strategies_none(self) -> None:
        """Test 'none' verification strategy."""
        strategies = parse_verification_strategies(["none"])
        assert strategies == ()

    def test_parse_verification_strategies_default(self) -> None:
        """Test default verification strategies when None is passed."""
        strategies = parse_verification_strategies(None)
        assert VerificationStrategy.BASIC in strategies
        assert VerificationStrategy.DURATION in strategies

    def test_parse_retry_strategy(self) -> None:
        """Test retry strategy parsing."""
        assert parse_retry_strategy("fixed") == RetryStrategy.FIXED
        assert parse_retry_strategy("exponential") == RetryStrategy.EXPONENTIAL
        assert parse_retry_strategy("reactivate") == RetryStrategy.REACTIVATE
        assert parse_retry_strategy("unknown") == RetryStrategy.FIXED


# =============================================================================
# CLI Build Config Tests
# =============================================================================


class TestCLIBuildConfig:
    """Tests for CLI config building with option dataclasses."""

    def test_build_config_basic(self) -> None:
        """Test building config from basic args."""
        filter_opts = WindowFilterOptions(app_name="TestApp")
        recording_opts = RecordingOptions(duration=5.0)
        output_opts = OutputOptions()
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.app_name == "TestApp"
        assert config.duration_seconds == 5.0

    def test_build_config_with_preset(self) -> None:
        """Test building config with preset."""
        filter_opts = WindowFilterOptions(app_name="App")
        recording_opts = RecordingOptions()
        output_opts = OutputOptions(preset="github")
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.preset == PlatformPreset.GITHUB

    def test_build_config_with_filters(self) -> None:
        """Test building config with window filters."""
        filter_opts = WindowFilterOptions(app_name="App", title="Test.*", args_contains="sandbox")
        recording_opts = RecordingOptions()
        output_opts = OutputOptions()
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.title_pattern == "Test.*"
        assert config.args_contains == "sandbox"

    def test_build_config_with_format(self) -> None:
        """Test building config with format."""
        filter_opts = WindowFilterOptions(app_name="App")
        recording_opts = RecordingOptions()
        output_opts = OutputOptions(format_str="webp")
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.output_format == OutputFormat.WEBP

    def test_build_config_full_screen(self) -> None:
        """Test building config for full screen."""
        filter_opts = WindowFilterOptions()
        recording_opts = RecordingOptions(duration=3.0, full_screen=True)
        output_opts = OutputOptions()
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.full_screen is True
        assert config.duration_seconds == 3.0


# =============================================================================
# Default Value Tests
# =============================================================================


class TestDefaultValues:
    """Tests for default constant values."""

    def test_default_duration(self) -> None:
        """Test default duration value."""
        assert DEFAULT_DURATION_SECONDS == 10

    def test_default_fps(self) -> None:
        """Test default FPS value."""
        assert DEFAULT_FPS == 15

    def test_default_max_retries(self) -> None:
        """Test default max retries value."""
        assert DEFAULT_MAX_RETRIES == 5

    def test_default_quality(self) -> None:
        """Test default quality value."""
        assert DEFAULT_QUALITY == 75


# =============================================================================
# Region Parsing Tests
# =============================================================================


class TestParseRegion:
    """Tests for parse_region function."""

    def test_parse_region_valid(self) -> None:
        """Test parsing valid region string."""
        bounds = parse_region("100,200,800,600")
        assert bounds is not None
        assert bounds.x == 100.0
        assert bounds.y == 200.0
        assert bounds.width == 800.0
        assert bounds.height == 600.0

    def test_parse_region_with_spaces(self) -> None:
        """Test parsing region with spaces around values."""
        bounds = parse_region("100, 200, 800, 600")
        assert bounds is not None
        assert bounds.x == 100.0
        assert bounds.y == 200.0

    def test_parse_region_float_values(self) -> None:
        """Test parsing region with float values."""
        bounds = parse_region("100.5,200.5,800.5,600.5")
        assert bounds is not None
        assert bounds.x == 100.5
        assert bounds.y == 200.5

    def test_parse_region_none(self) -> None:
        """Test parsing None returns None."""
        assert parse_region(None) is None

    def test_parse_region_empty_string(self) -> None:
        """Test parsing empty string returns None."""
        assert parse_region("") is None

    def test_parse_region_invalid_format_too_few(self) -> None:
        """Test parsing region with too few parts raises error."""
        with pytest.raises(typer.BadParameter, match="x,y,width,height"):
            parse_region("100,200,800")

    def test_parse_region_invalid_format_too_many(self) -> None:
        """Test parsing region with too many parts raises error."""
        with pytest.raises(typer.BadParameter, match="x,y,width,height"):
            parse_region("100,200,800,600,extra")

    def test_parse_region_invalid_values(self) -> None:
        """Test parsing region with non-numeric values raises error."""
        with pytest.raises(typer.BadParameter, match="Invalid region"):
            parse_region("abc,200,800,600")

    def test_parse_region_zero_width(self) -> None:
        """Test parsing region with zero width raises error."""
        with pytest.raises(typer.BadParameter, match="must be positive"):
            parse_region("100,200,0,600")

    def test_parse_region_negative_height(self) -> None:
        """Test parsing region with negative height raises error."""
        with pytest.raises(typer.BadParameter, match="must be positive"):
            parse_region("100,200,800,-100")

    def test_parse_region_as_region_format(self) -> None:
        """Test that parsed region can be used for screencapture."""
        bounds = parse_region("100,200,800,600")
        assert bounds is not None
        assert bounds.as_region == "100,200,800,600"


class TestCLIRegionOptions:
    """Tests for CLI region options."""

    def test_build_config_with_region(self) -> None:
        """Test building config with --region."""
        filter_opts = WindowFilterOptions()
        recording_opts = RecordingOptions(region="100,200,800,600", full_screen=True)
        output_opts = OutputOptions()
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.region is not None
        assert config.region.x == 100.0
        assert config.region.y == 200.0
        assert config.region.width == 800.0
        assert config.region.height == 600.0

    def test_build_config_with_window_region(self) -> None:
        """Test building config with --window-region."""
        filter_opts = WindowFilterOptions(app_name="TestApp")
        recording_opts = RecordingOptions(window_region="0,400,800,300")
        output_opts = OutputOptions()
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        config = build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)

        assert config.window_relative_region is not None
        assert config.window_relative_region.x == 0.0
        assert config.window_relative_region.y == 400.0
        assert config.window_relative_region.width == 800.0
        assert config.window_relative_region.height == 300.0

    def test_window_region_requires_app_name(self) -> None:
        """Test --window-region requires app_name."""
        filter_opts = WindowFilterOptions()  # No app_name
        recording_opts = RecordingOptions(window_region="0,400,800,300", full_screen=True)
        output_opts = OutputOptions()
        format_opts = FormatOptions()
        retry_opts = RetryOptions()

        with pytest.raises(typer.BadParameter, match="requires an app name"):
            build_config(filter_opts, recording_opts, output_opts, format_opts, retry_opts)


class TestRecordingConfigWindowRelativeRegion:
    """Tests for RecordingConfig with window_relative_region."""

    def test_config_with_window_relative_region(self) -> None:
        """Test RecordingConfig stores window_relative_region."""
        region = WindowBounds(x=0, y=400, width=800, height=300)
        config = RecordingConfig(
            app_name="TestApp",
            window_relative_region=region,
        )
        assert config.window_relative_region == region

    def test_config_to_dict_includes_window_relative_region(self) -> None:
        """Test to_dict includes window_relative_region."""
        region = WindowBounds(x=0, y=400, width=800, height=300)
        config = RecordingConfig(
            app_name="TestApp",
            window_relative_region=region,
        )
        data = config.to_dict()

        assert "window_relative_region" in data
        assert data["window_relative_region"]["x"] == 0
        assert data["window_relative_region"]["y"] == 400

    def test_config_to_dict_null_window_relative_region(self) -> None:
        """Test to_dict with None window_relative_region."""
        config = RecordingConfig(app_name="TestApp")
        data = config.to_dict()

        assert data["window_relative_region"] is None
