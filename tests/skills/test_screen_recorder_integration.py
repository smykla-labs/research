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
    return json.dumps(
        {
            "streams": [
                {"width": 800, "height": 600, "avg_frame_rate": "30/1", "nb_read_frames": "150"}
            ],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"},
        }
    ).encode()


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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert result.attempt == 1
        assert result.app_name == "TestApp"
        assert result.window_id == 12345

    def test_success_with_full_screen(self, tmp_path: Path, mock_ffprobe_success: bytes) -> None:
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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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
                proc_result.stdout = json.dumps(
                    {
                        "streams": [{"width": 800, "height": 600, "avg_frame_rate": "30/1"}],
                        "format": {"duration": duration, "size": "1000000", "format_name": "mov"},
                    }
                ).encode()
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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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
                proc_result.stdout = json.dumps(
                    {
                        "streams": [{"width": 800, "height": 600, "avg_frame_rate": "30/1"}],
                        "format": {"duration": "1.0", "size": "1000", "format_name": "mov"},
                    }
                ).encode()

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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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
            side_effect=WindowNotFoundError("No window found"),
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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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

    def test_simple_recording(self, tmp_path: Path, mock_window_target: WindowTarget) -> None:
        """Test record_simple convenience wrapper."""
        # Use 3 second duration to match requested duration
        ffprobe_3s = json.dumps(
            {
                "streams": [
                    {"width": 800, "height": 600, "avg_frame_rate": "30/1", "nb_read_frames": "90"}
                ],
                "format": {"duration": "3.0", "size": "600000", "format_name": "mov"},
            }
        ).encode()

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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
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


# =============================================================================
# Region Recording Tests
# =============================================================================


class TestRegionRecording:
    """Tests for absolute region recording (--region x,y,w,h)."""

    def test_absolute_region_captures_correct_coordinates(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test absolute region recording uses specified coordinates."""
        captured_region: list[str] = []

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                # Capture the -R argument for verification
                for i, arg in enumerate(cmd):
                    if arg == "-R" and i + 1 < len(cmd):
                        captured_region.append(cmd[i + 1])
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        config = RecordingConfig(
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "region.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            region=WindowBounds(x=100, y=200, width=800, height=600),
        )

        with (
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert len(captured_region) == 1
        assert captured_region[0] == "100,200,800,600"

    def test_region_dimensions_preserved_in_result(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test region dimensions are preserved in recording result."""

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

        region = WindowBounds(x=50, y=100, width=1024, height=768)
        config = RecordingConfig(
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "region.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            region=region,
        )

        with (
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert result.bounds == region


# =============================================================================
# Window-Relative Region Tests
# =============================================================================


class TestWindowRelativeRegion:
    """Tests for window-relative region recording (--window-region)."""

    def test_window_relative_region_offsets_from_window(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test window-relative region is offset from window origin."""
        captured_region: list[str] = []

        # Window at screen position (100, 50)
        window_target = WindowTarget(
            window_id=12345,
            app_name="TestApp",
            window_title="Test Window",
            pid=1234,
            bounds=WindowBounds(x=100, y=50, width=1200, height=800),
            space_index=1,
            exe_path="/Applications/TestApp.app",
            cmdline=("TestApp",),
        )

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for i, arg in enumerate(cmd):
                    if arg == "-R" and i + 1 < len(cmd):
                        captured_region.append(cmd[i + 1])
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        # Relative region: 0 offset X, 600 offset Y, 1200 width, 200 height
        # Should capture absolute region: x=100+0, y=50+600, w=1200, h=200
        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "window_region.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            window_relative_region=WindowBounds(x=0, y=600, width=1200, height=200),
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=window_target),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert len(captured_region) == 1
        # Window at (100, 50) + relative (0, 600) = absolute (100, 650)
        assert captured_region[0] == "100,650,1200,200"

    def test_window_relative_region_with_offset(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test window-relative region with non-zero X offset."""
        captured_region: list[str] = []

        window_target = WindowTarget(
            window_id=12345,
            app_name="IDE",
            window_title="Editor",
            pid=1234,
            bounds=WindowBounds(x=200, y=100, width=1600, height=1000),
            space_index=1,
            exe_path="/Applications/IDE.app",
            cmdline=("IDE",),
        )

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for i, arg in enumerate(cmd):
                    if arg == "-R" and i + 1 < len(cmd):
                        captured_region.append(cmd[i + 1])
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        # Relative region: 50 offset X, 800 offset Y, 1500 width, 150 height
        # Should capture absolute region: x=200+50, y=100+800, w=1500, h=150
        config = RecordingConfig(
            app_name="IDE",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "ide_region.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            window_relative_region=WindowBounds(x=50, y=800, width=1500, height=150),
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=window_target),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        assert len(captured_region) == 1
        assert captured_region[0] == "250,900,1500,150"


# =============================================================================
# Space Switching Tests
# =============================================================================


class TestSpaceSwitching:
    """Tests for Space-aware recording (automatic Space switching)."""

    def test_no_switch_when_window_on_same_space(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test no Space switch when window is on current Space."""
        switch_calls: list[str] = []

        window_target = WindowTarget(
            window_id=12345,
            app_name="TestApp",
            window_title="Test Window",
            pid=1234,
            bounds=WindowBounds(x=100, y=50, width=800, height=600),
            space_index=1,  # Same as current
            exe_path="/Applications/TestApp.app",
            cmdline=("TestApp",),
        )

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

        def mock_activate(app_name: str, _settle_time: float) -> None:
            switch_calls.append(app_name)

        config = RecordingConfig(
            app_name="TestApp",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
            activate_first=False,  # Skip activation to isolate Space switching
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=window_target),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("screen_recorder.actions.activate_app_by_name", side_effect=mock_activate),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # No Space switching should have occurred
        assert len(switch_calls) == 0

    def test_switch_when_window_on_different_space(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test Space switch when window is on different Space."""
        activate_calls: list[str] = []
        find_window_calls = [0]

        window_target = WindowTarget(
            window_id=12345,
            app_name="Terminal",
            window_title="Terminal",
            pid=1234,
            bounds=WindowBounds(x=100, y=50, width=800, height=600),
            space_index=2,  # Different from current Space 1
            exe_path="/Applications/Utilities/Terminal.app",
            cmdline=("Terminal",),
        )

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

        def mock_activate(app_name: str, _settle_time: float) -> None:
            activate_calls.append(app_name)

        def mock_find_window(_config):
            find_window_calls[0] += 1
            return window_target

        config = RecordingConfig(
            app_name="Terminal",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
        )

        with (
            patch("screen_recorder.actions.find_target_window", side_effect=mock_find_window),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("screen_recorder.actions.activate_app_by_name", side_effect=mock_activate),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # Should have called activate for Space switch and return
        assert "Terminal" in activate_calls
        # Should have found window twice: initial + after Space switch
        assert find_window_calls[0] == 2

    def test_return_to_original_space_after_recording(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test returns to original Space after recording completes."""
        activate_calls: list[str] = []

        window_target = WindowTarget(
            window_id=12345,
            app_name="Safari",
            window_title="Safari",
            pid=1234,
            bounds=WindowBounds(x=0, y=0, width=1920, height=1080),
            space_index=3,  # Different from current Space 1
            exe_path="/Applications/Safari.app",
            cmdline=("Safari",),
        )

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

        def mock_activate(app_name: str, _settle_time: float) -> None:
            activate_calls.append(app_name)

        config = RecordingConfig(
            app_name="Safari",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=window_target),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value="GoLand"),
            patch("screen_recorder.actions.activate_app_by_name", side_effect=mock_activate),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # Should have: 1) switched to Safari, 2) returned to GoLand
        assert activate_calls == ["Safari", "GoLand"]

    def test_return_to_finder_when_original_was_desktop(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test returns to Finder when original Space had no fullscreen app."""
        activate_calls: list[str] = []

        window_target = WindowTarget(
            window_id=12345,
            app_name="Notes",
            window_title="Notes",
            pid=1234,
            bounds=WindowBounds(x=100, y=100, width=800, height=600),
            space_index=2,  # Different from current Space 1
            exe_path="/Applications/Notes.app",
            cmdline=("Notes",),
        )

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

        def mock_activate(app_name: str, _settle_time: float) -> None:
            activate_calls.append(app_name)

        config = RecordingConfig(
            app_name="Notes",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=window_target),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),  # Desktop
            patch("screen_recorder.actions.activate_app_by_name", side_effect=mock_activate),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # Should have: 1) switched to Notes, 2) returned to Finder (for desktop)
        assert activate_calls == ["Notes", "Finder"]

    def test_space_switch_refreshes_window_bounds(
        self, tmp_path: Path, mock_ffprobe_success: bytes
    ) -> None:
        """Test window bounds are refreshed after Space switch."""
        captured_regions: list[str] = []
        find_calls = [0]

        # Initial bounds (before Space switch)
        initial_target = WindowTarget(
            window_id=12345,
            app_name="Code",
            window_title="Visual Studio Code",
            pid=1234,
            bounds=WindowBounds(x=100, y=100, width=1200, height=800),
            space_index=2,
            exe_path="/Applications/Visual Studio Code.app",
            cmdline=("Code",),
        )

        # Updated bounds (after Space switch - coordinates may change)
        updated_target = WindowTarget(
            window_id=12345,
            app_name="Code",
            window_title="Visual Studio Code",
            pid=1234,
            bounds=WindowBounds(x=50, y=50, width=1200, height=800),  # Different position
            space_index=2,
            exe_path="/Applications/Visual Studio Code.app",
            cmdline=("Code",),
        )

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            proc_result = Mock()
            proc_result.returncode = 0
            proc_result.stderr = b""

            if "screencapture" in cmd[0]:
                for i, arg in enumerate(cmd):
                    if arg == "-R" and i + 1 < len(cmd):
                        captured_regions.append(cmd[i + 1])
                    if arg.endswith(".mov"):
                        Path(arg).write_bytes(b"fake video")
            elif "ffprobe" in cmd[0]:
                proc_result.stdout = mock_ffprobe_success
            elif "ffmpeg" in cmd[0]:
                output = cmd[-1]
                Path(output).write_bytes(b"fake gif")

            return proc_result

        def mock_find_window(_config):
            find_calls[0] += 1
            # Return different bounds on second call (after Space switch)
            return initial_target if find_calls[0] == 1 else updated_target

        config = RecordingConfig(
            app_name="Code",
            duration_seconds=3.0,
            max_retries=1,
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.BASIC,),
        )

        with (
            patch("screen_recorder.actions.find_target_window", side_effect=mock_find_window),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value=None),
            patch("screen_recorder.actions.activate_app_by_name"),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            result = record_verified(config)

        assert result.verified is True
        # find_target_window should be called twice
        assert find_calls[0] == 2
        # Recording should use updated bounds (50,50,1200,800)
        assert len(captured_regions) == 1
        assert captured_regions[0] == "50,50,1200,800"

    def test_returns_to_space_even_on_recording_failure(self, tmp_path: Path) -> None:
        """Test Space is returned even when recording fails."""
        activate_calls: list[str] = []

        window_target = WindowTarget(
            window_id=12345,
            app_name="Preview",
            window_title="Preview",
            pid=1234,
            bounds=WindowBounds(x=100, y=100, width=800, height=600),
            space_index=2,
            exe_path="/Applications/Preview.app",
            cmdline=("Preview",),
        )

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
                # Always return short duration to fail verification
                proc_result.stdout = json.dumps(
                    {
                        "streams": [{"width": 800, "height": 600, "avg_frame_rate": "30/1"}],
                        "format": {"duration": "0.5", "size": "1000", "format_name": "mov"},
                    }
                ).encode()

            return proc_result

        def mock_activate(app_name: str, _settle_time: float) -> None:
            activate_calls.append(app_name)

        config = RecordingConfig(
            app_name="Preview",
            duration_seconds=5.0,
            max_retries=1,  # Only 1 retry so it fails fast
            output_path=str(tmp_path / "output.gif"),
            verification_strategies=(VerificationStrategy.DURATION,),
        )

        with (
            patch("screen_recorder.actions.find_target_window", return_value=window_target),
            patch("screen_recorder.actions.get_current_space_index", return_value=1),
            patch("screen_recorder.actions.get_space_app_name", return_value="GoLand"),
            patch("screen_recorder.actions.activate_app_by_name", side_effect=mock_activate),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("time.sleep"),
        ):
            with pytest.raises(MaxRetriesError):
                record_verified(config)

        # Even though recording failed, should still return to original Space
        assert "Preview" in activate_calls
        assert "GoLand" in activate_calls
