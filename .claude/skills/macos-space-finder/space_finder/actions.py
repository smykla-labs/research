"""Actions for activating apps and navigating Spaces."""

from __future__ import annotations

import re
import subprocess
import time
from typing import TYPE_CHECKING

from .core import find_space_by_app, get_current_space
from .models import DEFAULT_RETURN_DELAY, ActivationError, SpaceInfo

if TYPE_CHECKING:
    from collections.abc import Sequence


def sanitize_app_name(app_name: str) -> str:
    """
    Sanitize application name for safe use in AppleScript.

    Args:
        app_name: Raw application name.

    Returns:
        Sanitized application name safe for AppleScript.

    Raises:
        ValueError: If the app name contains invalid characters.
    """
    # Allow only alphanumeric, spaces, hyphens, underscores, periods, and parentheses
    if not re.match(r"^[\w\s.\-()]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")

    # Escape any remaining quotes (shouldn't exist after regex, but defense in depth)
    return app_name.replace('"', '\\"')


def activate_app(app_name: str) -> None:
    """
    Activate an application via AppleScript.

    Args:
        app_name: Name of the application to activate.

    Raises:
        ActivationError: If the application cannot be activated.
        ValueError: If the app name contains invalid characters.
    """
    sanitized_name = sanitize_app_name(app_name)
    script = f'tell application "{sanitized_name}" to activate'

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ActivationError(f"Failed to activate {app_name}: {stderr}")


def switch_to_space(
    spaces: Sequence[SpaceInfo],
    app_query: str,
    settle_delay: float = DEFAULT_RETURN_DELAY,
) -> tuple[SpaceInfo | None, SpaceInfo | None, bool]:
    """
    Switch to space containing app and stay there.

    Args:
        spaces: List of SpaceInfo objects.
        app_query: Search query for target application.
        settle_delay: Seconds to wait after switching for animation to complete.

    Returns:
        Tuple of (target_space, original_space, success).
        Use original_space with return_to_space() to go back.
    """
    original = get_current_space(spaces)
    matches = find_space_by_app(spaces, app_query)

    if not matches:
        return None, original, False

    target = matches[0]

    if target.is_current:
        return target, original, True

    # Activate target app to switch to its space
    if target.app_name:
        activate_app(target.app_name)
        time.sleep(settle_delay)

    return target, original, True


def return_to_space(
    original: SpaceInfo | None,
    settle_delay: float = DEFAULT_RETURN_DELAY,
) -> bool:
    """
    Return to the original space.

    Args:
        original: SpaceInfo of the original space (from switch_to_space).
        settle_delay: Seconds to wait after switching for animation to complete.

    Returns:
        True if successfully returned, False if no original space provided.
    """
    if not original:
        return False

    if original.app_name:
        activate_app(original.app_name)
    else:
        # For normal desktop (no fullscreen app), activate Finder
        activate_app("Finder")

    time.sleep(settle_delay)
    return True


def go_to_space(
    spaces: Sequence[SpaceInfo],
    app_query: str,
    return_delay: float = DEFAULT_RETURN_DELAY,
) -> tuple[SpaceInfo | None, SpaceInfo | None, bool]:
    """
    Switch to space containing app, wait, then return to original space.

    Args:
        spaces: List of SpaceInfo objects.
        app_query: Search query for target application.
        return_delay: Seconds to wait before returning to original space.

    Returns:
        Tuple of (target_space, original_space, success).
    """
    target, original, success = switch_to_space(spaces, app_query, return_delay)

    if not success or not target or target.is_current:
        return target, original, success

    # Return to original space
    return_to_space(original, 0)  # No extra delay needed here

    return target, original, True
