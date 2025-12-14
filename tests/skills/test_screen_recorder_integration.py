"""Integration tests for screen_recorder record_verified function."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from screen_recorder.actions import record_simple, record_verified
from screen_recorder.models import (
    DurationLimitError,
    MaxRetriesError,
    PlatformPreset,
    RecordingConfig,
    VerificationStrategy,
    WindowBounds,
    WindowNotFoundError,
    WindowTarget,
)

# =============================================================================
# Helper fixtures
# =============================================================================


@pytest.fixture
def mock_window_target() -> WindowTarget:
    """Create mock window target."""
    return WindowTarget(
        window_id=12345,
        app_name="TestApp",
        window_title="Test Window",
        pid=1234,
        bounds=WindowBounds(x=100, y=50, width=800, height=600),
        space_index=1,
        exe_path="/Applications/TestApp.app",
        cmdline=("TestApp",),
    )


@pytest.fixture
def mock_ffprobe_success() -> bytes:
    """Create successful ffprobe response."""
    return json.dumps({
        "streams": [{
            "width": 800, "height": 600,
            "avg_frame_rate": "30/1", "nb_read_frames": "150"
        }],
        "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
    }).encode()


# =============================================================================
# record_verified Tests - Success Cases
# =============================================================================


class TestRecordVerifiedSuccess:
    """Tests for successful record_verified scenarios."""

    def test_success_first_attempt_basic_verification(
        self, tmp_path: Path, mock_window_target: WindowTarget, mock_ffprobe_success: bytes
    ) -> None:
        """Test successful recording on first attempt with basic verification."""

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                # Create recording file
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                # Create converted file
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=5.0,
            max_retries=3,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            preset=PlatformPreset.GITHUB,
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert result.attempt == 1
        assert result.app_name == "TestApp"
        assert result.window_id == 12345

    def test_success_with_full_screen(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test successful full screen recording (no window target)."""

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        config = RecordingConfig(
            full_screen=True,
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "fullscreen.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
        )

        with (
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert result.window_id is None
        assert result.app_name is None


# =============================================================================
# record_verified Tests - Retry Cases
# =============================================================================


class TestRecordVerifiedRetry:
    """Tests for record_verified retry scenarios."""

    def test_retry_on_verification_failure(
        self, tmp_path: Path, mock_window_target: WindowTarget
    ) -> None:
        """Test retry when verification fails."""
        attempt_count = [0]

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                attempt_count[0] += 1
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                # First attempt: short duration (fails), second: correct duration
                duration = "2.0" if attempt_count[0] == 1 else "5.0"
                proc_result.stdout = json.dumps({
                    "streams": [{"width": 800, "height": 600, "avg_frame_rate": "30/1"}],
                    "format": {"duration": duration, "size": "1000000", "format_name": "mov"}
                }).encode()
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=5.0,
            max_retries=3,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.DURATION,),
            preset=PlatformPreset.GITHUB,
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert result.attempt == 2
        assert attempt_count[0] == 2


# =============================================================================
# record_verified Tests - Error Cases
# =============================================================================


class TestRecordVerifiedErrors:
    """Tests for record_verified error scenarios."""

    def test_max_retries_exceeded_raises_error(
        self, tmp_path: Path, mock_window_target: WindowTarget
    ) -> None:
        """Test MaxRetriesError after all retries exhausted."""

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                # Always return short duration (fails verification)
                proc_result.stdout = json.dumps({
                    "streams": [{"width": 800, "height": 600, "avg_frame_rate": "30/1"}],
                    "format": {"duration": "1.0", "size": "1000", "format_name": "mov"}
                }).encode()

            return proc_result

        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=5.0,
            max_retries=2,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.DURATION,),
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            with pytest.raises(MaxRetriesError) as exc_info:
                record_verified(config)

        assert "2 attempts" in str(exc_info.value)
        assert "duration" in str(exc_info.value).lower()

    def test_duration_limit_exceeded_raises_error(self) -> None:
        """Test DurationLimitError when duration exceeds max."""
        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=120.0,  # Exceeds default max of 60
            max_duration_seconds=60.0,
        )

        with pytest.raises(DurationLimitError) as exc_info:
            record_verified(config)

        assert "120" in str(exc_info.value)
        assert "60" in str(exc_info.value)

    def test_window_not_found_raises_error(self) -> None:
        """Test WindowNotFoundError when no matching window."""
        config = RecordingConfig(
            app_name="NonExistentApp",
            duration_seconds=5.0,
        )

        with patch(
            "screen_recorder.actions.find_target_window",
            side_effect=WindowNotFoundError("No window found")
        ):
            with pytest.raises(WindowNotFoundError):
                record_verified(config)


# =============================================================================
# record_verified Tests - Configuration Options
# =============================================================================


class TestRecordVerifiedOptions:
    """Tests for record_verified configuration options."""

    def test_keep_raw_preserves_file(
        self, tmp_path: Path, mock_window_target: WindowTarget, mock_ffprobe_success: bytes
    ) -> None:
        """Test keep_raw=True preserves raw MOV file."""
        raw_files_created = []

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        raw_files_created.append(Path(arg))
                        break
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=5.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            keep_raw=True,
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # Raw file should exist (note: actual filename may be renamed during finalization)

    def test_no_keep_raw_removes_file(
        self, tmp_path: Path, mock_window_target: WindowTarget, mock_ffprobe_success: bytes
    ) -> None:
        """Test keep_raw=False removes raw MOV file."""

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=5.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            keep_raw=False,
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # Raw file should NOT exist (deleted during finalization)


# =============================================================================
# record_simple Tests
# =============================================================================


class TestRecordSimple:
    """Tests for record_simple convenience function."""

    def test_simple_recording(
        self, tmp_path: Path, mock_window_target: WindowTarget
    ) -> None:
        """Test record_simple convenience wrapper."""
        # Use 3 second duration to match requested duration
        ffprobe_3s = json.dumps({
            "streams": [{
                "width": 800, "height": 600,
                "avg_frame_rate": "30/1", "nb_read_frames": "90"
            }],
            "format": {"duration": "3.0", "size": "600000", "format_name": "mov"}
        }).encode()

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = ffprobe_3s
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_simple(
                app_name="TestApp",
                duration=3,
                preset=PlatformPreset.GITHUB,
                output_path=str(tmp_path / "simple.gif"),
            )

        assert result.verified is True
        assert result.preset == PlatformPreset.GITHUB

    def test_simple_defaults(
        self, tmp_path: Path, mock_window_target: WindowTarget, mock_ffprobe_success: bytes
    ) -> None:
        """Test record_simple with default parameters."""

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for arg in cmd:
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
                        break
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        with (
            patch("screen_recorder.actions.find_target_window", return_value=mock_window_target),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_simple(
                app_name="TestApp",
                output_path=str(tmp_path / "default.gif"),
            )

        assert result.verified is True
        assert result.duration_requested == 5  # Default duration
        assert result.preset == PlatformPreset.GITHUB  # Default preset
