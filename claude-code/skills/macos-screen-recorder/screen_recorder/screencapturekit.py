"""ScreenCaptureKit backend for macOS 12.3+ screen capture.

This module provides cross-Space capture without activation using Apple's
ScreenCaptureKit framework.

Current support:
- Screenshots: Full support via SCScreenshotManager (no activation needed)
- Video recording: NOT YET IMPLEMENTED (requires SCStream + AVAssetWriter)

For video recording, the screen recorder still uses `screencapture -v` which
requires window activation. ScreenCaptureKit streaming is planned for future.

Limitations:
- Requires macOS 12.3+
- Cannot capture minimized windows
- Requires Screen Recording permission
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
        False - video streaming is not yet implemented.
    """
    # Video streaming via SCStream is not implemented yet
    # This would require AVAssetWriter integration
    return False


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


class _CaptureContext:
    """Context for async screenshot capture."""

    def __init__(self) -> None:
        self.image = None
        self.error: str | None = None
        self.completed = threading.Event()


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
