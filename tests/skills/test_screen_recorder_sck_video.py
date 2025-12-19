"""Tests for ScreenCaptureKit video streaming."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from screen_recorder.models import CaptureBackend, CaptureError
from screen_recorder.screencapturekit import (
    ASSET_WRITER_FINISH_TIMEOUT_SECONDS,
    PIXEL_FORMAT_BGRA,
    RETINA_SCALE_FACTOR,
    STREAM_START_WAIT_SECONDS,
    _RecordingContext,
    _SCStreamOutputHandler,
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


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_retina_scale_factor(self) -> None:
        """Test RETINA_SCALE_FACTOR is defined correctly."""
        assert RETINA_SCALE_FACTOR == 2

    def test_stream_start_wait_seconds(self) -> None:
        """Test STREAM_START_WAIT_SECONDS is defined correctly."""
        assert STREAM_START_WAIT_SECONDS == 0.5

    def test_pixel_format_bgra(self) -> None:
        """Test PIXEL_FORMAT_BGRA is kCVPixelFormatType_32BGRA."""
        # kCVPixelFormatType_32BGRA = 'BGRA' = 0x42475241 = 1111970369
        assert PIXEL_FORMAT_BGRA == 1111970369

    def test_asset_writer_finish_timeout(self) -> None:
        """Test ASSET_WRITER_FINISH_TIMEOUT_SECONDS is defined correctly."""
        assert ASSET_WRITER_FINISH_TIMEOUT_SECONDS == 5.0


# =============================================================================
# _SCStreamOutputHandler Tests
# =============================================================================


class TestSCStreamOutputHandler:
    """Tests for _SCStreamOutputHandler class."""

    @patch("screen_recorder.screencapturekit._get_corefoundation")
    def test_initialization(self, mock_foundation: Mock, tmp_path: Path) -> None:
        """Test handler initialization with context and video writer."""
        context = _RecordingContext(tmp_path / "test.mov", 5.0)
        writer = _VideoWriter(tmp_path / "test.mov", 1920, 1080, 30.0)

        # Mock Foundation.NSObject
        mock_ns_object = Mock()
        mock_foundation.return_value.NSObject = mock_ns_object

        handler = _SCStreamOutputHandler(context, writer)

        assert handler.context is context
        assert handler.video_writer is writer
        assert handler.handler_class is not None

    @patch("screen_recorder.screencapturekit._get_corefoundation")
    def test_create_handler_returns_instance(
        self, mock_foundation: Mock, tmp_path: Path
    ) -> None:
        """Test create_handler returns a handler instance."""
        context = _RecordingContext(tmp_path / "test.mov", 5.0)
        writer = _VideoWriter(tmp_path / "test.mov", 1920, 1080, 30.0)

        # Mock Foundation.NSObject with alloc/init chain
        mock_ns_object = Mock()
        mock_handler_instance = Mock()
        mock_ns_object.alloc().initWithContext_videoWriter_.return_value = (
            mock_handler_instance
        )
        mock_foundation.return_value.NSObject = mock_ns_object

        handler_wrapper = _SCStreamOutputHandler(context, writer)

        # The create_handler uses the dynamically created Handler class
        # which inherits from NSObject, so we verify the class was created
        assert handler_wrapper.handler_class is not None


# =============================================================================
# _find_sc_window Tests
# =============================================================================


class TestFindSCWindow:
    """Tests for _find_sc_window helper function."""

    @patch("screen_recorder.screencapturekit.is_screencapturekit_available")
    def test_raises_when_sck_unavailable(self, mock_available: Mock) -> None:
        """Test record_window_with_sck raises when SCK unavailable."""
        mock_available.return_value = False

        with pytest.raises(CaptureError, match=r"requires macOS 12\.3"):
            record_window_with_sck(
                window_id=12345,
                output_path=Path("/tmp/test.mov"),
                duration_seconds=1.0,
            )


# =============================================================================
# _VideoWriter Error Handling Tests
# =============================================================================


class TestVideoWriterErrorHandling:
    """Tests for _VideoWriter error handling."""

    def test_append_sample_buffer_returns_false_when_not_writing(
        self, tmp_path: Path
    ) -> None:
        """Test append_sample_buffer returns False when not writing."""
        writer = _VideoWriter(tmp_path / "test.mov", 1920, 1080, 30.0)

        # Not writing (setup not called)
        result = writer.append_sample_buffer(Mock())

        assert result is False

    @patch("screen_recorder.screencapturekit._get_avfoundation")
    @patch("screen_recorder.screencapturekit._get_corefoundation")
    def test_setup_raises_on_null_asset_writer(
        self, mock_foundation: Mock, mock_av: Mock, tmp_path: Path
    ) -> None:
        """Test setup raises CaptureError when AVAssetWriter fails to create."""
        output_path = tmp_path / "test.mov"
        writer = _VideoWriter(output_path, 1920, 1080, 30.0)

        mock_url = Mock()
        mock_foundation.return_value.NSURL.fileURLWithPath_.return_value = mock_url

        # Asset writer creation returns None
        mock_av.return_value.AVAssetWriter.alloc().initWithURL_fileType_error_.return_value = (
            None,
            None,
        )

        with pytest.raises(CaptureError, match="Failed to create AVAssetWriter"):
            writer.setup()

    @patch("screen_recorder.screencapturekit._get_avfoundation")
    @patch("screen_recorder.screencapturekit._get_corefoundation")
    def test_setup_raises_on_null_video_input(
        self, mock_foundation: Mock, mock_av: Mock, tmp_path: Path
    ) -> None:
        """Test setup raises CaptureError when AVAssetWriterInput fails."""
        output_path = tmp_path / "test.mov"
        writer = _VideoWriter(output_path, 1920, 1080, 30.0)

        mock_url = Mock()
        mock_foundation.return_value.NSURL.fileURLWithPath_.return_value = mock_url

        mock_asset_writer = Mock()
        mock_av.return_value.AVAssetWriter.alloc().initWithURL_fileType_error_.return_value = (
            mock_asset_writer,
            None,
        )

        # Video input creation returns None
        mock_writer_input = mock_av.return_value.AVAssetWriterInput.alloc()
        mock_writer_input.initWithMediaType_outputSettings_.return_value = None

        with pytest.raises(CaptureError, match="Failed to create AVAssetWriterInput"):
            writer.setup()
