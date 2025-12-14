"""Actions for activating apps and navigating Spaces."""

from __future__ import annotations

import re
import subprocess
import time
from typing import TYPE_CHECKING

from .core import find_space_by_app, get_current_space
from .models import DEFAULT_RETURN_DELAY, AppActivationError, SpaceInfo

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
        AppActivationError: If the application cannot be activated.
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
        raise AppActivationError(f"Failed to activate {app_name}: {stderr}")


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
    original = get_current_space(spaces)
    matches = find_space_by_app(spaces, app_query)

    if not matches:
        return None, original, False

    target = matches[0]

    if target.is_current:
        return target, original, True

    # Activate target app
    if target.app_name:
        activate_app(target.app_name)
        time.sleep(return_delay)

        # Return to original space
        if original and original.app_name:
            activate_app(original.app_name)
        elif original:
            # For normal desktop, activate Finder
            activate_app("Finder")

    return target, original, True
