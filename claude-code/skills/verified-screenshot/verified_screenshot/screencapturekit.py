"""ScreenCaptureKit backend for macOS 12.3+ window capture.

This module provides cross-Space window capture without activation using Apple's
ScreenCaptureKit framework. Key advantages over CGWindowListCreateImage:

- Captures windows on ANY Space without switching
- Works with occluded (covered) windows
- Works with off-screen windows
- Future-proof (CGWindowListCreateImage deprecated in macOS 15)

Limitations:
- Requires macOS 12.3+
- Cannot capture minimized windows (stream pauses)
- Requires Screen Recording permission
"""

from __future__ import annotations

import functools
import platform
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from .models import CaptureError, WindowTarget

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
    # ScreenCaptureKit requires macOS 12.3+
    if major < _SCK_MIN_MAJOR:
        return False
    return not (major == _SCK_MIN_MAJOR and minor < _SCK_MIN_MINOR)


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
    result_window = [None]  # Use list to allow modification in callback

    def completion_handler(shareable_content, error):
        if error:
            context.error = str(error)
            context.completed.set()
            return

        if shareable_content is None:
            context.error = "No shareable content available"
            context.completed.set()
            return

        # Find window by ID
        windows = shareable_content.windows()
        for window in windows:
            if window.windowID() == window_id:
                result_window[0] = window
                break

        context.completed.set()

    # Request shareable content (includes windows from all Spaces)
    SC.SCShareableContent.getShareableContentWithCompletionHandler_(completion_handler)

    # Run the runloop until completion or timeout
    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = Foundation.NSDate.dateWithTimeIntervalSinceNow_(timeout)

    while not context.completed.is_set():
        run_loop.runMode_beforeDate_(Foundation.NSDefaultRunLoopMode, deadline)
        if Foundation.NSDate.date().compare_(deadline) == Foundation.NSOrderedDescending:
            break

    if context.error:
        raise CaptureError(f"Failed to get shareable content: {context.error}")

    return result_window[0]


def capture_with_screencapturekit(
    target: WindowTarget,
    output_path: Path,
    no_shadow: bool = True,
    timeout: float = 10.0,
) -> Path:
    """Capture a window using ScreenCaptureKit.

    This method captures windows without requiring activation or Space switching.
    Windows can be on any Space, occluded, or off-screen.

    Args:
        target: Window target information (must include window_id).
        output_path: Path to save the screenshot.
        no_shadow: Whether to exclude the window shadow from the screenshot.
        timeout: Timeout in seconds for async operations.

    Returns:
        Path to the saved screenshot.

    Raises:
        CaptureError: If capture fails or window not found.
    """
    if not is_screencapturekit_available():
        raise CaptureError("ScreenCaptureKit requires macOS 12.3 or later")

    SC = _get_screencapturekit()
    Q = _get_quartz()
    Foundation = _get_corefoundation()

    # Find the SCWindow for the target
    sc_window = _find_sc_window(target.window_id, timeout=timeout)
    if sc_window is None:
        raise CaptureError(
            f"Window {target.window_id} not found in ScreenCaptureKit. "
            "Window may be minimized or on a different user session."
        )

    # Create desktop-independent filter (works across Spaces)
    content_filter = SC.SCContentFilter.alloc().initWithDesktopIndependentWindow_(sc_window)

    # Configure stream
    config = SC.SCStreamConfiguration.alloc().init()

    # Set dimensions from content rect (accounts for scaling)
    content_rect = content_filter.contentRect()
    pixel_scale = content_filter.pointPixelScale()

    width = int(content_rect.size.width * pixel_scale)
    height = int(content_rect.size.height * pixel_scale)

    config.setWidth_(width)
    config.setHeight_(height)
    config.setShowsCursor_(False)
    config.setIgnoreShadowsSingleWindow_(no_shadow)

    # Capture screenshot
    context = _CaptureContext()

    def screenshot_handler(image, error):
        if error:
            context.error = str(error)
        else:
            context.image = image
        context.completed.set()

    SC.SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(
        content_filter, config, screenshot_handler
    )

    # Run the runloop until completion or timeout
    run_loop = Foundation.NSRunLoop.currentRunLoop()
    deadline = Foundation.NSDate.dateWithTimeIntervalSinceNow_(timeout)

    while not context.completed.is_set():
        run_loop.runMode_beforeDate_(Foundation.NSDefaultRunLoopMode, deadline)
        if Foundation.NSDate.date().compare_(deadline) == Foundation.NSOrderedDescending:
            break

    if context.error:
        raise CaptureError(f"Screenshot capture failed: {context.error}")

    if context.image is None:
        raise CaptureError("Screenshot capture timed out or returned no image")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as PNG using Quartz
    url = Q.CFURLCreateWithFileSystemPath(
        None, str(output_path.absolute()), Q.kCFURLPOSIXPathStyle, False
    )
    dest = Q.CGImageDestinationCreateWithURL(url, "public.png", 1, None)

    if dest is None:
        raise CaptureError(f"Failed to create image destination: {output_path}")

    Q.CGImageDestinationAddImage(dest, context.image, None)

    if not Q.CGImageDestinationFinalize(dest):
        raise CaptureError(f"Failed to finalize image: {output_path}")

    return output_path
