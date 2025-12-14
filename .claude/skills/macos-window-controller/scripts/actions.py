"""Window actions: activation and screenshots for macOS Window Controller."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from .core import _get_quartz, find_window
from .models import (
    ActivationError,
    ScreenshotError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
)


def sanitize_app_name(app_name: str) -> str:
    """Sanitize application name for AppleScript."""
    if not re.match(r"^[\w\s.\-()]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")
    return app_name.replace('"', '\\"')


def _activate_by_app_name(app_name: str, wait_time: float = 0.5) -> None:
    """Activate app by name (internal helper).

    Args:
        app_name: Application name to activate.
        wait_time: Seconds to wait after activation.

    Raises:
        ActivationError: If activation fails.
    """
    try:
        sanitized = sanitize_app_name(app_name)
    except ValueError as e:
        raise ActivationError(str(e)) from e

    result = subprocess.run(
        ["osascript", "-e", f'tell application "{sanitized}" to activate'],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ActivationError(f"Failed to activate {app_name}: {stderr}")

    if wait_time > 0:
        time.sleep(wait_time)


def activate_window(f: WindowFilter, wait_time: float = 0.5) -> WindowInfo:
    """Activate a window (switches to its Space)."""
    window = find_window(f)
    if not window:
        raise WindowNotFoundError("No window found matching filter")

    _activate_by_app_name(window.app_name, wait_time)
    return window


def take_screenshot(
    f: WindowFilter,
    output_path: str | Path | None = None,
    activate_first: bool = True,
    settle_ms: int = 1000,
) -> Path:
    """Take a screenshot of a window."""
    Q = _get_quartz()

    window = find_window(f)
    if not window:
        raise WindowNotFoundError("No window found matching filter")

    if activate_first:
        # Use the found window's app name directly to avoid race condition
        _activate_by_app_name(window.app_name, settle_ms / 1000.0)

    if output_path is None:
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^\w\-]", "_", window.app_name.lower())
        output_path = screenshots_dir / f"{safe_name}_{timestamp}.png"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Q.CGWindowListCreateImage(
        Q.CGRectNull,
        Q.kCGWindowListOptionIncludingWindow,
        window.window_id,
        Q.kCGWindowImageDefault,
    )
    if image is None:
        raise ScreenshotError(f"Failed to capture window {window.window_id}")

    url = Q.CFURLCreateWithFileSystemPath(
        None, str(output_path.absolute()), Q.kCFURLPOSIXPathStyle, False
    )
    dest = Q.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    if dest is None:
        raise ScreenshotError(f"Failed to create destination: {output_path}")

    Q.CGImageDestinationAddImage(dest, image, None)
    if not Q.CGImageDestinationFinalize(dest):
        raise ScreenshotError(f"Failed to finalize image: {output_path}")

    return output_path
