"""Tests for screen_recorder.actions module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from screen_recorder.actions import (
    activate_window,
    calculate_retry_delay,
    generate_output_path,
    get_effective_settings,
    run_verifications,
    sanitize_app_name,
)
from screen_recorder.models import (
    DEFAULT_FPS,
    DEFAULT_QUALITY,
    CaptureError,
    OutputFormat,
    PlatformPreset,
    RecordingConfig,
    RetryStrategy,
    VerificationStrategy,
    WindowBounds,
    WindowTarget,
)

# =============================================================================
# sanitize_app_name Tests
# =============================================================================


class TestSanitizeAppName:
    """Tests for sanitize_app_name function."""

    def test_valid_names_unchanged(self) -> None:
        """Test valid app names pass through."""
        assert sanitize_app_name("Safari") == "Safari"
        assert sanitize_app_name("Visual Studio Code") == "Visual Studio Code"
        assert sanitize_app_name("GoLand (2024.1)") == "GoLand (2024.1)"
        assert sanitize_app_name("App-Name.2") == "App-Name.2"

    def test_quotes_rejected(self) -> None:
        """Test double quotes are rejected (not in allowed character set)."""
        with pytest.raises(ValueError):
            sanitize_app_name('App"Name')

    def test_invalid_characters_raise_value_error(self) -> None:
        """Test invalid characters raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sanitize_app_name("App;rm -rf /")
        assert "invalid characters" in str(exc_info.value).lower()

        with pytest.raises(ValueError):
            sanitize_app_name("App`whoami`")

        with pytest.raises(ValueError):
            sanitize_app_name("App$HOME")


# =============================================================================
# activate_window Tests
# =============================================================================


class TestActivateWindow:
    """Tests for activate_window function."""

    @pytest.fixture
    def sample_target(self) -> WindowTarget:
        """Create sample window target."""
        return WindowTarget(
            window_id=12345,
            app_name="Safari",
            window_title="Test",
            pid=1234,
            bounds=WindowBounds(x=0, y=0, width=800, height=600),
        )

    def test_successful_activation(self, sample_target: WindowTarget) -> None:
        """Test successful window activation."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            activate_window(sample_target, wait_time=0)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "osascript" in cmd
        assert "Safari" in cmd[-1]

    def test_invalid_app_name_raises_capture_error(self) -> None:
        """Test CaptureError for invalid app name."""
        target = WindowTarget(
            window_id=12345,
            app_name="App;rm -rf /",  # Invalid
            window_title="Test",
            pid=1234,
            bounds=WindowBounds(x=0, y=0, width=800, height=600),
        )

        with pytest.raises(CaptureError) as exc_info:
            activate_window(target)

        assert "cannot activate" in str(exc_info.value).lower()

    def test_osascript_failure_raises_capture_error(self, sample_target: WindowTarget) -> None:
        """Test CaptureError on osascript failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(CaptureError) as exc_info:
                activate_window(sample_target, wait_time=0)

        assert "failed to activate" in str(exc_info.value).lower()


# =============================================================================
# get_effective_settings Tests
# =============================================================================


class TestGetEffectiveSettings:
    """Tests for get_effective_settings function."""

    def test_no_preset_uses_defaults(self) -> None:
        """Test settings without preset use config values or defaults."""
        config = RecordingConfig()
        settings = get_effective_settings(config)

        assert settings["fps"] == DEFAULT_FPS
        assert settings["quality"] == DEFAULT_QUALITY
        assert settings["format"] == OutputFormat.GIF

    def test_preset_sets_defaults(self) -> None:
        """Test preset provides default settings."""
        config = RecordingConfig(preset=PlatformPreset.DISCORD)
        settings = get_effective_settings(config)

        assert settings["format"] == OutputFormat.WEBP
        assert settings["fps"] == 10
        assert settings["max_width"] == 720

    def test_config_overrides_preset(self) -> None:
        """Test config values override preset defaults."""
        config = RecordingConfig(
            preset=PlatformPreset.DISCORD,
            fps=15,  # Override preset's 10
            max_width=1280,  # Override preset's 720
        )
        settings = get_effective_settings(config)

        assert settings["fps"] == 15
        assert settings["max_width"] == 1280

    def test_github_preset_settings(self) -> None:
        """Test GitHub preset values."""
        config = RecordingConfig(preset=PlatformPreset.GITHUB)
        settings = get_effective_settings(config)

        assert settings["format"] == OutputFormat.GIF
        assert settings["max_width"] == 600
        assert settings["fps"] == 10
        assert settings["max_size_mb"] == 5

    def test_jetbrains_preset_settings(self) -> None:
        """Test JetBrains preset values."""
        config = RecordingConfig(preset=PlatformPreset.JETBRAINS)
        settings = get_effective_settings(config)

        assert settings["format"] == OutputFormat.GIF
        assert settings["max_width"] == 1280
        assert settings["max_height"] == 800
        assert settings["fps"] == 15

    def test_raw_preset_settings(self) -> None:
        """Test RAW preset values."""
        config = RecordingConfig(preset=PlatformPreset.RAW)
        settings = get_effective_settings(config)

        assert settings["format"] == OutputFormat.MOV
        assert settings["max_size_mb"] is None


# =============================================================================
# run_verifications Tests
# =============================================================================


class TestRunVerifications:
    """Tests for run_verifications function."""

    def test_single_strategy(self, tmp_path: Path) -> None:
        """Test running single verification strategy."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake video content")

        config = RecordingConfig(verification_strategies=(VerificationStrategy.BASIC,))
        results = run_verifications(video_path, config)

        assert len(results) == 1
        assert results[0].strategy == VerificationStrategy.BASIC
        assert results[0].passed is True

    def test_multiple_strategies(self, tmp_path: Path) -> None:
        """Test running multiple verification strategies."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake video content")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "streams": [{"width": 1920, "height": 1080, "avg_frame_rate": "30/1"}],
                "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"},
            }
        ).encode()

        config = RecordingConfig(
            duration_seconds=5.0,
            verification_strategies=(
                VerificationStrategy.BASIC,
                VerificationStrategy.DURATION,
            ),
        )

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            results = run_verifications(video_path, config)

        assert len(results) == 2
        strategies = [r.strategy for r in results]
        assert VerificationStrategy.BASIC in strategies
        assert VerificationStrategy.DURATION in strategies

    def test_all_strategy_expands(self, tmp_path: Path) -> None:
        """Test ALL strategy expands to individual strategies."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake video content")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "streams": [
                    {
                        "width": 1920,
                        "height": 1080,
                        "avg_frame_rate": "30/1",
                        "nb_read_frames": "150",
                    }
                ],
                "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"},
            }
        ).encode()

        config = RecordingConfig(
            duration_seconds=5.0, verification_strategies=(VerificationStrategy.ALL,)
        )

        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run", return_value=mock_result),
            patch("screen_recorder.core.extract_frame") as mock_extract,
            patch("screen_recorder.core.compute_image_hash", return_value="hash"),
            patch("screen_recorder.core.compute_hash_distance", return_value=10),
        ):

            def create_frame(_video, output, _time_seconds=0):
                output.write_bytes(b"fake image")
                return output

            mock_extract.side_effect = create_frame

            results = run_verifications(video_path, config)

        assert len(results) == 4
        strategies = {r.strategy for r in results}
        assert strategies == {
            VerificationStrategy.BASIC,
            VerificationStrategy.DURATION,
            VerificationStrategy.FRAMES,
            VerificationStrategy.MOTION,
        }


# =============================================================================
# calculate_retry_delay Tests
# =============================================================================


class TestCalculateRetryDelay:
    """Tests for calculate_retry_delay function."""

    def test_fixed_strategy_constant_delay(self) -> None:
        """Test FIXED strategy returns constant delay."""
        config = RecordingConfig(
            retry_strategy=RetryStrategy.FIXED,
            retry_delay_ms=500,
        )

        assert calculate_retry_delay(1, config) == 0.5
        assert calculate_retry_delay(2, config) == 0.5
        assert calculate_retry_delay(3, config) == 0.5

    def test_exponential_strategy_doubles(self) -> None:
        """Test EXPONENTIAL strategy doubles delay each attempt."""
        config = RecordingConfig(
            retry_strategy=RetryStrategy.EXPONENTIAL,
            retry_delay_ms=500,
        )

        assert calculate_retry_delay(1, config) == 0.5  # 0.5 * 2^0 = 0.5
        assert calculate_retry_delay(2, config) == 1.0  # 0.5 * 2^1 = 1.0
        assert calculate_retry_delay(3, config) == 2.0  # 0.5 * 2^2 = 2.0
        assert calculate_retry_delay(4, config) == 4.0  # 0.5 * 2^3 = 4.0

    def test_reactivate_uses_fixed_delay(self) -> None:
        """Test REACTIVATE strategy uses fixed delay (activation happens separately)."""
        config = RecordingConfig(
            retry_strategy=RetryStrategy.REACTIVATE,
            retry_delay_ms=500,
        )

        # REACTIVATE doesn't use exponential, just fixed base delay
        assert calculate_retry_delay(1, config) == 0.5
        assert calculate_retry_delay(2, config) == 0.5


# =============================================================================
# generate_output_path Tests
# =============================================================================


class TestGenerateOutputPath:
    """Tests for generate_output_path function."""

    @pytest.fixture
    def sample_target(self) -> WindowTarget:
        """Create sample window target."""
        return WindowTarget(
            window_id=12345,
            app_name="Safari",
            window_title="Test",
            pid=1234,
            bounds=WindowBounds(x=0, y=0, width=800, height=600),
        )

    def test_generates_paths_from_target(self, sample_target: WindowTarget) -> None:
        """Test path generation from window target."""
        config = RecordingConfig()
        raw_path, final_path = generate_output_path(config, sample_target)

        assert "safari" in str(raw_path).lower()
        assert raw_path.suffix == ".mov"
        assert final_path.suffix == ".gif"

    def test_generates_paths_without_target(self) -> None:
        """Test path generation without target uses 'recording'."""
        config = RecordingConfig()
        raw_path, final_path = generate_output_path(config, None)

        assert "recording" in str(raw_path).lower()
        assert raw_path.suffix == ".mov"

    def test_output_path_as_file_used_directly(self) -> None:
        """Test output_path as filename is used directly."""
        config = RecordingConfig(output_path="/tmp/myrecording.gif")
        raw_path, final_path = generate_output_path(config, None)

        assert str(final_path) == "/tmp/myrecording.gif"
        assert raw_path.suffix == ".mov"

    def test_output_path_as_directory_appends_filename(self, sample_target: WindowTarget) -> None:
        """Test output_path as directory appends generated filename."""
        config = RecordingConfig(output_path="/tmp/recordings")
        raw_path, final_path = generate_output_path(config, sample_target)

        assert str(final_path).startswith("/tmp/recordings/")
        assert "safari" in str(final_path).lower()

    def test_preset_determines_extension(self) -> None:
        """Test preset determines output extension."""
        config = RecordingConfig(preset=PlatformPreset.DISCORD)
        raw_path, final_path = generate_output_path(config, None)

        assert final_path.suffix == ".webp"

    def test_mov_output_handles_raw_path_conflict(self) -> None:
        """Test MOV format creates distinct raw/final paths."""
        config = RecordingConfig(preset=PlatformPreset.RAW)
        raw_path, final_path = generate_output_path(config, None)

        # Both would be .mov, so raw should have _raw suffix
        assert "_raw" in raw_path.stem or raw_path != final_path
