"""Tests for ScreenCaptureKit modules across all skills.

These tests cover the common ScreenCaptureKit functionality used by:
- macos-verified-screenshot
- macos-window-controller
- macos-screen-recorder
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# =============================================================================
# Verified Screenshot SCK Tests
# =============================================================================


class TestVerifiedScreenshotSCK:
    """Tests for verified_screenshot.screencapturekit module."""

    def test_is_screencapturekit_available_true(self) -> None:
        """Test SCK availability on macOS 12.3+."""
        from verified_screenshot import screencapturekit as sck

        with patch.object(sck, "_check_macos_version", return_value=(12, 3)):
            assert sck.is_screencapturekit_available() is True

        with patch.object(sck, "_check_macos_version", return_value=(13, 0)):
            assert sck.is_screencapturekit_available() is True

        with patch.object(sck, "_check_macos_version", return_value=(14, 5)):
            assert sck.is_screencapturekit_available() is True

    def test_is_screencapturekit_available_false(self) -> None:
        """Test SCK unavailability on older macOS versions."""
        from verified_screenshot import screencapturekit as sck

        with patch.object(sck, "_check_macos_version", return_value=(12, 2)):
            assert sck.is_screencapturekit_available() is False

        with patch.object(sck, "_check_macos_version", return_value=(11, 0)):
            assert sck.is_screencapturekit_available() is False

        with patch.object(sck, "_check_macos_version", return_value=(10, 15)):
            assert sck.is_screencapturekit_available() is False

    def test_check_macos_version_parsing(self) -> None:
        """Test macOS version string parsing."""
        from verified_screenshot import screencapturekit as sck

        with patch("platform.mac_ver", return_value=("14.5.0", ("", "", ""), "")):
            assert sck._check_macos_version() == (14, 5)

        with patch("platform.mac_ver", return_value=("12.3", ("", "", ""), "")):
            assert sck._check_macos_version() == (12, 3)

        with patch("platform.mac_ver", return_value=("", ("", "", ""), "")):
            assert sck._check_macos_version() == (0, 0)

    def test_capture_with_screencapturekit_requires_macos_12_3(self) -> None:
        """Test capture raises error on unsupported macOS."""
        from verified_screenshot import screencapturekit as sck
        from verified_screenshot.models import CaptureError, WindowTarget

        target = WindowTarget(
            window_id=12345,
            app_name="TestApp",
            window_title="Test Window",
            pid=9999,
            bounds_x=0.0,
            bounds_y=0.0,
            bounds_width=800.0,
            bounds_height=600.0,
        )

        with patch.object(sck, "is_screencapturekit_available", return_value=False):
            with pytest.raises(CaptureError, match=r"macOS 12\.3"):
                sck.capture_with_screencapturekit(target, Path("/tmp/test.png"))

    def test_capture_context_initialization(self) -> None:
        """Test _CaptureContext initializes correctly."""
        from verified_screenshot.screencapturekit import _CaptureContext

        ctx = _CaptureContext()
        assert ctx.image is None
        assert ctx.error is None
        assert ctx.completed.is_set() is False


# =============================================================================
# Window Controller SCK Tests
# =============================================================================


class TestWindowControllerSCK:
    """Tests for window_controller.screencapturekit module."""

    def test_is_screencapturekit_available_true(self) -> None:
        """Test SCK availability on macOS 12.3+."""
        from window_controller import screencapturekit as sck

        with patch.object(sck, "_check_macos_version", return_value=(12, 3)):
            assert sck.is_screencapturekit_available() is True

        with patch.object(sck, "_check_macos_version", return_value=(15, 0)):
            assert sck.is_screencapturekit_available() is True

    def test_is_screencapturekit_available_false(self) -> None:
        """Test SCK unavailability on older macOS versions."""
        from window_controller import screencapturekit as sck

        with patch.object(sck, "_check_macos_version", return_value=(12, 2)):
            assert sck.is_screencapturekit_available() is False

        with patch.object(sck, "_check_macos_version", return_value=(11, 6)):
            assert sck.is_screencapturekit_available() is False

    def test_check_macos_version_parsing(self) -> None:
        """Test macOS version string parsing."""
        from window_controller import screencapturekit as sck

        with patch("platform.mac_ver", return_value=("13.4.1", ("", "", ""), "")):
            assert sck._check_macos_version() == (13, 4)

        with patch("platform.mac_ver", return_value=("12.3.0", ("", "", ""), "")):
            assert sck._check_macos_version() == (12, 3)

    def test_capture_with_screencapturekit_requires_macos_12_3(self) -> None:
        """Test capture raises error on unsupported macOS."""
        from window_controller import screencapturekit as sck
        from window_controller.models import ScreenshotError, WindowInfo

        window = WindowInfo(
            app_name="TestApp",
            window_title="Test Window",
            window_id=12345,
            pid=9999,
            layer=0,
            on_screen=True,
            alpha=1.0,
            bounds_x=0.0,
            bounds_y=0.0,
            bounds_width=800.0,
            bounds_height=600.0,
        )

        with patch.object(sck, "is_screencapturekit_available", return_value=False):
            with pytest.raises(ScreenshotError, match=r"macOS 12\.3"):
                sck.capture_with_screencapturekit(window, Path("/tmp/test.png"))

    def test_capture_context_initialization(self) -> None:
        """Test _CaptureContext initializes correctly."""
        from window_controller.screencapturekit import _CaptureContext

        ctx = _CaptureContext()
        assert ctx.image is None
        assert ctx.error is None
        assert ctx.completed.is_set() is False


# =============================================================================
# Screen Recorder SCK Tests
# =============================================================================


class TestScreenRecorderSCK:
    """Tests for screen_recorder.screencapturekit module."""

    def test_is_screencapturekit_available_true(self) -> None:
        """Test SCK availability on macOS 12.3+."""
        from screen_recorder import screencapturekit as sck

        with patch.object(sck, "_check_macos_version", return_value=(12, 3)):
            assert sck.is_screencapturekit_available() is True

        with patch.object(sck, "_check_macos_version", return_value=(14, 0)):
            assert sck.is_screencapturekit_available() is True

    def test_is_screencapturekit_available_false(self) -> None:
        """Test SCK unavailability on older macOS versions."""
        from screen_recorder import screencapturekit as sck

        with patch.object(sck, "_check_macos_version", return_value=(12, 2)):
            assert sck.is_screencapturekit_available() is False

        with patch.object(sck, "_check_macos_version", return_value=(10, 14)):
            assert sck.is_screencapturekit_available() is False

    def test_is_video_streaming_supported_false(self) -> None:
        """Test video streaming is not yet supported."""
        from screen_recorder import screencapturekit as sck

        assert sck.is_video_streaming_supported() is False

    def test_check_macos_version_parsing(self) -> None:
        """Test macOS version string parsing."""
        from screen_recorder import screencapturekit as sck

        with patch("platform.mac_ver", return_value=("15.1.0", ("", "", ""), "")):
            assert sck._check_macos_version() == (15, 1)

        with patch("platform.mac_ver", return_value=("12.3", ("", "", ""), "")):
            assert sck._check_macos_version() == (12, 3)

    def test_capture_region_screenshot_sck_requires_macos_12_3(self) -> None:
        """Test capture raises error on unsupported macOS."""
        from screen_recorder import screencapturekit as sck
        from screen_recorder.models import CaptureError

        with patch.object(sck, "is_screencapturekit_available", return_value=False):
            with pytest.raises(CaptureError, match=r"macOS 12\.3"):
                sck.capture_region_screenshot_sck(Path("/tmp/test.png"))

    def test_capture_context_initialization(self) -> None:
        """Test _CaptureContext initializes correctly."""
        from screen_recorder.screencapturekit import _CaptureContext

        ctx = _CaptureContext()
        assert ctx.image is None
        assert ctx.error is None
        assert ctx.completed.is_set() is False

    def test_capture_backend_enum(self) -> None:
        """Test CaptureBackend enum values."""
        from screen_recorder.models import CaptureBackend

        assert CaptureBackend.QUARTZ.value == "quartz"
        assert CaptureBackend.SCREENCAPTUREKIT.value == "screencapturekit"
        assert CaptureBackend.AUTO.value == "auto"


# =============================================================================
# Cross-Module Consistency Tests
# =============================================================================


class TestSCKConsistency:
    """Tests for consistency across SCK implementations."""

    def test_all_modules_have_same_min_version(self) -> None:
        """Verify all modules require macOS 12.3."""
        from screen_recorder import screencapturekit as sr_sck
        from verified_screenshot import screencapturekit as vs_sck
        from window_controller import screencapturekit as wc_sck

        assert vs_sck._SCK_MIN_MAJOR == 12
        assert vs_sck._SCK_MIN_MINOR == 3

        assert wc_sck._SCK_MIN_MAJOR == 12
        assert wc_sck._SCK_MIN_MINOR == 3

        assert sr_sck._SCK_MIN_MAJOR == 12
        assert sr_sck._SCK_MIN_MINOR == 3

    def test_all_modules_export_availability_check(self) -> None:
        """Verify all modules export is_screencapturekit_available."""
        from screen_recorder import is_screencapturekit_available as sr_avail
        from verified_screenshot import is_screencapturekit_available as vs_avail
        from window_controller import is_screencapturekit_available as wc_avail

        # All should be callable
        assert callable(vs_avail)
        assert callable(wc_avail)
        assert callable(sr_avail)
