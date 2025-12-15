"""ScreenCaptureKit backend for macOS 12.3+ screen capture.

This module provides cross-Space capture without activation using Apple's
ScreenCaptureKit framework.

Support:
- Screenshots: Full support via SCScreenshotManager (no activation needed)
- Video recording: Full support via SCStream + AVAssetWriter (no activation needed)

Limitations:
- Requires macOS 12.3+
- Cannot capture minimized windows
- Requires Screen Recording permission
- macOS 15 may have stability issues (PyObjC #647)
"""

from __future__ import annotations

import functools
import platform
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from .models import CaptureError, WindowBounds

if TYPE_CHECKING:
    pass

# ScreenCaptureKit minimum version requirements
_SCK_MIN_MAJOR = 12
_SCK_MIN_MINOR = 3


def _check_macos_version() -> tuple[int, int]:
    """Get macOS version as (major, minor) tuple."""
    version = platform.mac_ver()[0]
    if not version:
        return (0, 0)
    parts = version.split(".")
    major = int(parts[0]) if parts else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    return (major, minor)


def is_screencapturekit_available() -> bool:
    """Check if ScreenCaptureKit is available on this system.

    Returns:
        True if ScreenCaptureKit is available (macOS 12.3+).
    """
    major, minor = _check_macos_version()
    if major < _SCK_MIN_MAJOR:
        return False
    return not (major == _SCK_MIN_MAJOR and minor < _SCK_MIN_MINOR)


def is_video_streaming_supported() -> bool:
    """Check if ScreenCaptureKit video streaming is supported.

    Returns:
        True if ScreenCaptureKit video streaming is available (macOS 12.3+).
    """
    return is_screencapturekit_available()


@functools.cache
def _get_screencapturekit():
    """Lazy load ScreenCaptureKit framework (cached)."""
    import ScreenCaptureKit

    return ScreenCaptureKit


@functools.cache
def _get_corefoundation():
    """Lazy load CoreFoundation for runloop (cached)."""
    import Foundation

    return Foundation


@functools.cache
def _get_quartz():
    """Lazy load Quartz framework (cached)."""
    import Quartz

    return Quartz


@functools.cache
def _get_avfoundation():
    """Lazy load AVFoundation framework (cached)."""
    import AVFoundation

    return AVFoundation


@functools.cache
def _get_coremedia():
    """Lazy load CoreMedia framework (cached)."""
    import CoreMedia

    return CoreMedia


class _CaptureContext:
    """Context for async screenshot capture."""

    def __init__(self) -> None:
        self.image = None
        self.error: str | None = None
        self.completed = threading.Event()


class _RecordingContext:
    """Context for async video recording."""

    def __init__(self, output_path: Path, duration: float) -> None:
        self.output_path = output_path
        self.target_duration = duration
        self.error: str | None = None
        self.completed = threading.Event()
        self.started = threading.Event()
        self.frame_count = 0
        self.first_timestamp: float | None = None
        self.last_timestamp: float | None = None


class _VideoWriter:
    """AVAssetWriter wrapper for CMSampleBuffer writing."""

    def __init__(
        self, output_path: Path, width: int, height: int, fps: float = 30.0
    ) -> None:
        """Initialize video writer.

        Args:
            output_path: Path to save the video file.
            width: Video width in pixels.
            height: Video height in pixels.
            fps: Frames per second (default: 30.0).
        """
        self.output_path = output_path
        self.width = width
        self.height = height
        self.fps = fps
        self.asset_writer = None
        self.video_input = None
        self.is_writing = False

    def setup(self) -> None:
        """Initialize AVAssetWriter with H.264 video track.

        Raises:
            CaptureError: If setup fails.
        """
        AV = _get_avfoundation()
        Foundation = _get_corefoundation()

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        url = Foundation.NSURL.fileURLWithPath_(str(self.output_path.absolute()))

        self.asset_writer = AV.AVAssetWriter.alloc().initWithURL_fileType_error_(
            url, AV.AVFileTypeQuickTimeMovie, None
        )[0]

        if self.asset_writer is None:
            raise CaptureError(f"Failed to create AVAssetWriter: {self.output_path}")

        video_settings = {
            AV.AVVideoCodecKey: AV.AVVideoCodecTypeH264,
            AV.AVVideoWidthKey: self.width,
            AV.AVVideoHeightKey: self.height,
        }

        self.video_input = AV.AVAssetWriterInput.alloc().initWithMediaType_outputSettings_(
            AV.AVMediaTypeVideo, video_settings
        )

        if self.video_input is None:
            raise CaptureError("Failed to create AVAssetWriterInput")

        self.video_input.setExpectsMediaDataInRealTime_(True)

        if not self.asset_writer.canAddInput_(self.video_input):
            raise CaptureError("Cannot add video input to asset writer")

        self.asset_writer.addInput_(self.video_input)

        if not self.asset_writer.startWriting():
            error = self.asset_writer.error()
            raise CaptureError(f"Failed to start writing: {error}")

        self.is_writing = True

    def append_sample_buffer(self, sample_buffer) -> bool:
        """Append a CMSampleBuffer to the video.

        Args:
            sample_buffer: CMSampleBuffer to append.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_writing:
            return False

        if not self.video_input.isReadyForMoreMediaData():
            return False

        return self.video_input.appendSampleBuffer_(sample_buffer)

    def finish(self) -> None:
        """Finalize and close video file."""
        if not self.is_writing:
            return

        self.is_writing = False

        if self.video_input:
            self.video_input.markAsFinished()

        if self.asset_writer:
            completion_event = threading.Event()

            def completion_handler():
                completion_event.set()

            self.asset_writer.finishWritingWithCompletionHandler_(completion_handler)

            completion_event.wait(timeout=5.0)


class _SCStreamOutputHandler:
    """SCStreamOutput protocol - receives CMSampleBuffer frames."""

    def __init__(self, context: _RecordingContext, video_writer: _VideoWriter) -> None:
        """Initialize handler with recording context and video writer.

        Args:
            context: Recording context for tracking state.
            video_writer: Video writer for writing frames.
        """
        import objc

        Foundation = _get_corefoundation()

        self.context = context
        self.video_writer = video_writer
        self.start_time: float | None = None

        NSObject = Foundation.NSObject

        class Handler(NSObject):
            """PyObjC protocol implementation."""

            def initWithContext_videoWriter_(self_, ctx, writer):
                """Initialize with context and writer."""
                self_ = objc.super(Handler, self_).init()
                if self_ is None:
                    return None
                self_.ctx = ctx
                self_.writer = writer
                self_.start_time = None
                return self_

            def stream_didOutputSampleBuffer_ofType_(
                self_, _stream, sample_buffer, output_type
            ):
                """Receive and write frames to AVAssetWriter."""
                CM = _get_coremedia()
                SC = _get_screencapturekit()

                if output_type != SC.SCStreamOutputTypeScreen:
                    return

                if not self_.ctx.started.is_set():
                    self_.ctx.started.set()

                try:
                    presentation_time = CM.CMSampleBufferGetPresentationTimeStamp(
                        sample_buffer
                    )
                    timestamp = CM.CMTimeGetSeconds(presentation_time)

                    if self_.start_time is None:
                        self_.start_time = timestamp
                        self_.writer.asset_writer.startSessionAtSourceTime_(
                            presentation_time
                        )

                    elapsed = timestamp - self_.start_time

                    if self_.ctx.first_timestamp is None:
                        self_.ctx.first_timestamp = timestamp
                    self_.ctx.last_timestamp = timestamp
                    self_.ctx.frame_count += 1

                    if elapsed >= self_.ctx.target_duration:
                        self_.ctx.completed.set()
                        return

                    success = self_.writer.append_sample_buffer(sample_buffer)
                    if not success and not self_.ctx.completed.is_set():
                        self_.ctx.error = "Failed to append sample buffer"
                        self_.ctx.completed.set()

                except Exception as e:
                    if not self_.ctx.completed.is_set():
                        self_.ctx.error = f"Frame processing error: {e}"
                        self_.ctx.completed.set()

        self.handler_class = Handler

    def create_handler(self):
        """Create and return the protocol handler instance."""
        return self.handler_class.alloc().initWithContext_videoWriter_(
            self.context, self.video_writer
        )


def _find_sc_window(window_id: int, timeout: float = 5.0):
    """Find SCWindow matching the given window ID.

    Args:
        window_id: CGWindowID to find.
        timeout: Timeout in seconds for async operation.

    Returns:
        SCWindow object or None if not found.

    Raises:
        CaptureError: If shareable content fetch fails.
    """
    SC = _get_screencapturekit()
    Foundation = _get_corefoundation()

    context = _CaptureContext()
    result_window = [None]

    def completion_handler(shareable_content, error):
        if error:
            context.error = str(error)
            context.completed.set()
            return

        if shareable_content is None:
            context.error = "No shareable content available"
            context.completed.set()
            return

        windows = shareable_content.windows()
        for window in windows:
            if window.windowID() == window_id:
                result_window[0] = window
                break

        context.completed.set()

    SC.SCShareableContent.getShareableContentWithCompletionHandler_(completion_handler)

    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = Foundation.NSDate.dateWithTimeIntervalSinceNow_(timeout)

    while not context.completed.is_set():
        run_loop.runMode_beforeDate_(Foundation.NSDefaultRunLoopMode, deadline)
        if Foundation.NSDate.date().compare_(deadline) == Foundation.NSOrderedDescending:
            break

    if context.error:
        raise CaptureError(f"Failed to get shareable content: {context.error}")

    return result_window[0]


def _setup_stream_configuration(sc_window, fps: int):
    """Setup SCStreamConfiguration for recording.

    Args:
        sc_window: SCWindow to record.
        fps: Frames per second.

    Returns:
        Configured SCStreamConfiguration.
    """
    SC = _get_screencapturekit()
    CM = _get_coremedia()

    config = SC.SCStreamConfiguration.alloc().init()
    config.setWidth_(int(sc_window.frame().size.width * 2))
    config.setHeight_(int(sc_window.frame().size.height * 2))
    config.setMinimumFrameInterval_(CM.CMTimeMake(1, fps))
    config.setQueueDepth_(5)
    config.setShowsCursor_(False)
    config.setPixelFormat_(1111970369)

    return config


def _start_stream_capture(stream, handler, recording_context: _RecordingContext) -> None:
    """Start SCStream capture and wait for recording to begin.

    Args:
        stream: SCStream to start.
        handler: Stream output handler.
        recording_context: Recording context.

    Raises:
        CaptureError: If stream fails to start or add handler.
    """
    SC = _get_screencapturekit()

    error = stream.addStreamOutput_type_sampleHandlerQueue_error_(
        handler, SC.SCStreamOutputTypeScreen, None, None
    )[1]

    if error:
        raise CaptureError(f"Failed to add stream output: {error}")

    start_error = [None]

    def start_handler(err):
        start_error[0] = err

    stream.startCaptureWithCompletionHandler_(start_handler)

    # Wait for start completion
    import time

    time.sleep(0.5)

    if start_error[0]:
        raise CaptureError(f"Failed to start capture: {start_error[0]}")

    if not recording_context.started.wait(timeout=5.0):
        raise CaptureError("Recording did not start within timeout")


def _wait_for_recording_completion(
    recording_context: _RecordingContext, timeout: float
) -> None:
    """Wait for recording to complete using NSRunLoop.

    Args:
        recording_context: Recording context.
        timeout: Timeout in seconds.
    """
    Foundation = _get_corefoundation()

    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = Foundation.NSDate.dateWithTimeIntervalSinceNow_(timeout)

    while not recording_context.completed.is_set():
        run_loop.runMode_beforeDate_(Foundation.NSDefaultRunLoopMode, deadline)
        if Foundation.NSDate.date().compare_(deadline) == Foundation.NSOrderedDescending:
            break


def record_window_with_sck(
    window_id: int,
    output_path: Path,
    duration_seconds: float,
    fps: int = 30,
    timeout: float | None = None,
) -> Path:
    """Record window using ScreenCaptureKit - works across Spaces.

    Args:
        window_id: CGWindowID to record.
        output_path: Path to save the video file.
        duration_seconds: Duration of recording in seconds.
        fps: Frames per second (default: 30).
        timeout: Optional timeout for the entire operation.

    Returns:
        Path to the saved video file.

    Raises:
        CaptureError: If recording fails or ScreenCaptureKit unavailable.
    """
    if not is_screencapturekit_available():
        raise CaptureError("ScreenCaptureKit requires macOS 12.3 or later")

    SC = _get_screencapturekit()

    if timeout is None:
        timeout = duration_seconds + 10.0

    sc_window = _find_sc_window(window_id)
    if sc_window is None:
        raise CaptureError(f"Window {window_id} not found")

    content_filter = SC.SCContentFilter.alloc().initWithDesktopIndependentWindow_(
        sc_window
    )
    config = _setup_stream_configuration(sc_window, fps)

    recording_context = _RecordingContext(output_path, duration_seconds)
    video_writer = _VideoWriter(
        output_path,
        int(sc_window.frame().size.width * 2),
        int(sc_window.frame().size.height * 2),
        float(fps),
    )

    try:
        video_writer.setup()

        handler_wrapper = _SCStreamOutputHandler(recording_context, video_writer)
        handler = handler_wrapper.create_handler()

        stream = SC.SCStream.alloc().initWithFilter_configuration_delegate_(
            content_filter, config, None
        )

        if stream is None:
            raise CaptureError("Failed to create SCStream")

        _start_stream_capture(stream, handler, recording_context)
        _wait_for_recording_completion(recording_context, timeout)

        stream.stopCaptureWithCompletionHandler_(lambda _err: None)

        if recording_context.error:
            raise CaptureError(f"Recording failed: {recording_context.error}")

    finally:
        video_writer.finish()

    if not output_path.exists():
        raise CaptureError(f"Video file was not created: {output_path}")

    return output_path


def _save_cgimage_as_png(image, output_path: Path) -> Path:
    """Save a CGImage to a PNG file.

    Args:
        image: CGImage to save.
        output_path: Path to save the PNG file.

    Returns:
        Path to the saved file.

    Raises:
        CaptureError: If save fails.
    """
    Q = _get_quartz()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    url = Q.CFURLCreateWithFileSystemPath(
        None, str(output_path.absolute()), Q.kCFURLPOSIXPathStyle, False
    )
    dest = Q.CGImageDestinationCreateWithURL(url, "public.png", 1, None)

    if dest is None:
        raise CaptureError(f"Failed to create image destination: {output_path}")

    Q.CGImageDestinationAddImage(dest, image, None)

    if not Q.CGImageDestinationFinalize(dest):
        raise CaptureError(f"Failed to finalize image: {output_path}")

    return output_path


def _wait_for_completion(context: _CaptureContext, timeout: float) -> None:
    """Wait for capture completion using NSRunLoop.

    Args:
        context: Capture context with completion event.
        timeout: Timeout in seconds.
    """
    Foundation = _get_corefoundation()
    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = Foundation.NSDate.dateWithTimeIntervalSinceNow_(timeout)

    while not context.completed.is_set():
        run_loop.runMode_beforeDate_(Foundation.NSDefaultRunLoopMode, deadline)
        if Foundation.NSDate.date().compare_(deadline) == Foundation.NSOrderedDescending:
            break


def capture_region_screenshot_sck(
    output_path: Path,
    region: WindowBounds | None = None,
    timeout: float = 10.0,
) -> Path:
    """Capture a screenshot of a screen region using ScreenCaptureKit.

    This method captures the screen without requiring window activation.
    Works across Spaces without switching.

    Args:
        output_path: Path to save the screenshot.
        region: Optional bounds for region capture (captures full display if None).
        timeout: Timeout in seconds for async operations.

    Returns:
        Path to the saved screenshot.

    Raises:
        CaptureError: If capture fails or ScreenCaptureKit unavailable.
    """
    if not is_screencapturekit_available():
        raise CaptureError("ScreenCaptureKit requires macOS 12.3 or later")

    SC = _get_screencapturekit()
    Q = _get_quartz()

    context = _CaptureContext()

    def content_handler(shareable_content, error):
        if error:
            context.error = str(error)
            context.completed.set()
            return

        if shareable_content is None:
            context.error = "No shareable content available"
            context.completed.set()
            return

        displays = shareable_content.displays()
        if not displays:
            context.error = "No displays found"
            context.completed.set()
            return

        display = displays[0]
        content_filter = SC.SCContentFilter.alloc().initWithDisplay_excludingWindows_(
            display, []
        )

        config = SC.SCStreamConfiguration.alloc().init()
        if region:
            source_rect = Q.CGRectMake(region.x, region.y, region.width, region.height)
            config.setSourceRect_(source_rect)
            config.setWidth_(int(region.width * 2))
            config.setHeight_(int(region.height * 2))
        else:
            config.setWidth_(int(display.width() * 2))
            config.setHeight_(int(display.height() * 2))

        config.setShowsCursor_(False)

        def screenshot_handler(image, error2):
            if error2:
                context.error = str(error2)
            else:
                context.image = image
            context.completed.set()

        SC.SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(
            content_filter, config, screenshot_handler
        )

    SC.SCShareableContent.getShareableContentWithCompletionHandler_(content_handler)
    _wait_for_completion(context, timeout)

    if context.error:
        raise CaptureError(f"Screenshot capture failed: {context.error}")

    if context.image is None:
        raise CaptureError("Screenshot capture timed out or returned no image")

    return _save_cgimage_as_png(context.image, output_path)
