"""Tests for ScreenCaptureKit video streaming."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from screen_recorder.models import CaptureBackend, CaptureError

# noinspection PyProtectedMember
from screen_recorder.screencapturekit import (
    _RecordingContext,
    _VideoWriter,
    is_video_streaming_supported,
    record_window_with_sck,
)

# =============================================================================
# _RecordingContext Tests
# =============================================================================


class TestRecordingContext:
    """Tests for _RecordingContext class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test context initialization with correct attributes."""
        output_path = tmp_path / "test.mov"
        duration = 5.0

        context = _RecordingContext(output_path, duration)

        assert context.output_path == output_path
        assert context.target_duration == duration
        assert context.error is None
        assert not context.completed.is_set()
        assert not context.started.is_set()
        assert context.frame_count == 0
        assert context.first_timestamp is None
        assert context.last_timestamp is None


# =============================================================================
# _VideoWriter Tests
# =============================================================================


class TestVideoWriter:
    """Tests for _VideoWriter class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test video writer initialization."""
        output_path = tmp_path / "test.mov"
        width = 1920
        height = 1080
        fps = 30.0

        writer = _VideoWriter(output_path, width, height, fps)

        assert writer.output_path == output_path
        assert writer.width == width
        assert writer.height == height
        assert writer.fps == fps
        assert writer.asset_writer is None
        assert writer.video_input is None
        assert not writer.is_writing

    @patch("screen_recorder.screencapturekit._get_avfoundation")
    @patch("screen_recorder.screencapturekit._get_corefoundation")
    def test_setup_creates_directories(
        self, mock_foundation: Mock, mock_av: Mock, tmp_path: Path
    ) -> None:
        """Test that setup creates parent directories if needed."""
        output_path = tmp_path / "subdir" / "test.mov"
        writer = _VideoWriter(output_path, 1920, 1080, 30.0)

        # Mock the foundation objects
        mock_url = Mock()
        mock_foundation.return_value.NSURL.fileURLWithPath_.return_value = mock_url

        mock_asset_writer = Mock()
        mock_av.return_value.AVAssetWriter.alloc().initWithURL_fileType_error_.return_value = (
            mock_asset_writer,
            None,
        )

        mock_video_input = Mock()
        mock_writer_input = (
            mock_av.return_value.AVAssetWriterInput.alloc()
            .initWithMediaType_outputSettings_
        )
        mock_writer_input.return_value = mock_video_input

        mock_asset_writer.canAddInput_.return_value = True
        mock_asset_writer.startWriting.return_value = True

        writer.setup()

        assert output_path.parent.exists()

    def test_finish_when_not_writing(self, tmp_path: Path) -> None:
        """Test finish() is safe to call when not writing."""
        writer = _VideoWriter(tmp_path / "test.mov", 1920, 1080, 30.0)

        # Should not raise
        writer.finish()

        assert not writer.is_writing


# =============================================================================
# is_video_streaming_supported Tests
# =============================================================================


class TestIsVideoStreamingSupported:
    """Tests for is_video_streaming_supported function."""

    @patch("screen_recorder.screencapturekit.is_screencapturekit_available")
    def test_returns_true_when_available(self, mock_available: Mock) -> None:
        """Test returns True when ScreenCaptureKit is available."""
        mock_available.return_value = True

        assert is_video_streaming_supported() is True

    @patch("screen_recorder.screencapturekit.is_screencapturekit_available")
    def test_returns_false_when_unavailable(self, mock_available: Mock) -> None:
        """Test returns False when ScreenCaptureKit is unavailable."""
        mock_available.return_value = False

        assert is_video_streaming_supported() is False


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(
    not is_video_streaming_supported(),
    reason="ScreenCaptureKit video not available on this system",
)
class TestSCKVideoIntegration:
    """Integration tests for ScreenCaptureKit video recording.

    These tests require macOS 12.3+ and Screen Recording permissions.
    """

    def test_record_window_requires_valid_window_id(self, tmp_path: Path) -> None:
        """Test that recording with invalid window ID fails gracefully."""
        output_path = tmp_path / "test.mov"

        with pytest.raises(CaptureError, match=r"Window .* not found"):
            record_window_with_sck(
                window_id=999999999,  # Invalid window ID
                output_path=output_path,
                duration_seconds=1.0,
            )


# =============================================================================
# Backend Selection Tests
# =============================================================================


class TestBackendSelection:
    """Tests for capture backend selection logic."""

    def test_capture_backend_enum_values(self) -> None:
        """Test CaptureBackend enum has expected values."""
        assert CaptureBackend.AUTO.value == "auto"
        assert CaptureBackend.QUARTZ.value == "quartz"
        assert CaptureBackend.SCREENCAPTUREKIT.value == "screencapturekit"
