"""Window actions: activation and screenshots for macOS Window Controller."""

from __future__ import annotations

import contextlib
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .core import _get_quartz, find_window
from .models import (
    ActivationError,
    CaptureBackend,
    ScreenshotError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
)
from .screencapturekit import capture_with_screencapturekit, is_screencapturekit_available

# =============================================================================
# Space Detection and Switching
# =============================================================================


def get_current_space_index() -> int:
    """Get the current Space index (1-based).

    Uses Mission Control's bundle to determine current Space.

    Returns:
        Current Space index (1-based), or 0 if detection fails.
    """
    script = """
    tell application "System Events"
        set mcBundle to bundle identifier of application "Mission Control"
    end tell
    tell application id mcBundle
        set spaceCount to count of spaces
        repeat with i from 1 to spaceCount
            if space i is active then
                return i
            end if
        end repeat
    end tell
    return 0
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        try:
            return int(result.stdout.decode().strip())
        except ValueError:
            pass
    return 0


def get_space_app_name() -> str | None:
    """Get the app name of a fullscreen Space, if applicable.

    For regular desktop Spaces, returns None.
    For fullscreen app Spaces, returns the app name.

    Returns:
        App name if on a fullscreen Space, None otherwise.
    """
    script = """
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        return name of frontApp
    end tell
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        app_name = result.stdout.decode().strip()
        # Finder is the frontmost app on regular desktop Spaces
        if app_name and app_name != "Finder":
            return app_name
    return None


@dataclass
class _SpaceContext:
    """Context for Space switching operations."""

    original_space_index: int
    original_space_app: str | None
    target_space_index: int | None
    switched: bool = False


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


def _return_to_original_space(ctx: _SpaceContext, settle_time: float = 0.5) -> None:
    """Return to the original Space after an operation.

    Args:
        ctx: Space context with original Space info.
        settle_time: Time to wait after switching.
    """
    if not ctx.switched:
        return

    # Use original app name if available (for fullscreen Spaces)
    # Otherwise use Finder to return to desktop Space
    return_app = ctx.original_space_app or "Finder"

    try:
        _activate_by_app_name(return_app, settle_time)
    except ActivationError:
        # If return fails, try Finder as fallback
        if return_app != "Finder":
            with contextlib.suppress(ActivationError):
                _activate_by_app_name("Finder", settle_time)


def resolve_backend(backend: CaptureBackend) -> CaptureBackend:
    """Resolve AUTO backend to actual backend.

    Args:
        backend: Requested backend (may be AUTO).

    Returns:
        Resolved backend (SCREENCAPTUREKIT or QUARTZ).
    """
    if backend == CaptureBackend.AUTO:
        if is_screencapturekit_available():
            return CaptureBackend.SCREENCAPTUREKIT
        return CaptureBackend.QUARTZ
    return backend


def _capture_with_quartz(window: WindowInfo, output_path: Path) -> Path:
    """Capture window using legacy Quartz/CGWindowListCreateImage.

    Args:
        window: Window to capture.
        output_path: Path to save screenshot.

    Returns:
        Path to saved screenshot.

    Raises:
        ScreenshotError: If capture fails.
    """
    Q = _get_quartz()

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


def take_screenshot(
    f: WindowFilter,
    output_path: str | Path | None = None,
    activate_first: bool = True,
    settle_ms: int = 1000,
    backend: CaptureBackend = CaptureBackend.AUTO,
) -> Path:
    """Take a screenshot of a window.

    When using ScreenCaptureKit backend (macOS 12.3+), activation is skipped
    because SCK can capture windows across Spaces without switching.

    Automatically returns to original Space after capturing if activation
    caused a Space switch (Quartz backend only).

    Args:
        f: Window filter to find the target window.
        output_path: Path to save screenshot (auto-generated if None).
        activate_first: Whether to activate window before capture (ignored for SCK).
        settle_ms: Milliseconds to wait after activation.
        backend: Capture backend to use (AUTO, QUARTZ, or SCREENCAPTUREKIT).

    Returns:
        Path to the saved screenshot.

    Raises:
        WindowNotFoundError: If no matching window found.
        ScreenshotError: If capture fails.
    """
    window = find_window(f)
    if not window:
        raise WindowNotFoundError("No window found matching filter")

    # Resolve backend once
    resolved_backend = resolve_backend(backend)

    # ScreenCaptureKit doesn't require activation - it captures across Spaces
    skip_activation = resolved_backend == CaptureBackend.SCREENCAPTUREKIT

    # Detect current Space before any activation
    space_ctx = _SpaceContext(
        original_space_index=get_current_space_index(),
        original_space_app=get_space_app_name(),
        target_space_index=window.space_index,
        switched=False,
    )

    # Check if we need to switch Spaces (only relevant for Quartz backend)
    needs_space_switch = (
        activate_first
        and not skip_activation
        and window.space_index is not None
        and space_ctx.original_space_index != window.space_index
    )

    try:
        # Only activate for Quartz backend when requested
        if activate_first and not skip_activation:
            _activate_by_app_name(window.app_name, settle_ms / 1000.0)
            if needs_space_switch:
                space_ctx.switched = True

        # Generate output path if not provided
        if output_path is None:
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r"[^\w\-]", "_", window.app_name.lower())
            output_path = screenshots_dir / f"{safe_name}_{timestamp}.png"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Capture using selected backend
        if resolved_backend == CaptureBackend.SCREENCAPTUREKIT:
            return capture_with_screencapturekit(window, output_path)

        return _capture_with_quartz(window, output_path)

    finally:
        # Return to original Space after screenshot (Quartz backend only)
        if space_ctx.switched:
            _return_to_original_space(space_ctx, settle_time=0.5)
