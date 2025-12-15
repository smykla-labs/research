"""atomacos wrapper for UI element discovery."""

import contextlib
from typing import Any

import atomacos

from ui_inspector.models import (
    AppNotFoundError,
    ElementFilter,
    UIElement,
    WindowNotFoundError,
)


def get_app_ref(app_name: str) -> Any:
    """Get application reference by name or bundle ID.

    Args:
        app_name: Application name (e.g., "Safari") or bundle ID (e.g., "com.apple.Safari")

    Returns:
        atomacos application reference

    Raises:
        AppNotFoundError: If application is not found
    """
    # Try bundle ID first (e.g., "com.apple.Safari")
    if "." in app_name:
        with contextlib.suppress(Exception):
            return atomacos.getAppRefByBundleId(app_name)

    # Fall back to localized name (e.g., "Safari")
    with contextlib.suppress(Exception):
        return atomacos.getAppRefByLocalizedName(app_name)

    # Try bundle ID even without dots (some bundle IDs are simple)
    with contextlib.suppress(Exception):
        return atomacos.getAppRefByBundleId(app_name)

    raise AppNotFoundError(f"Application not found: {app_name}")


def get_frontmost_window(app_ref: Any) -> Any:
    """Get the frontmost window of an application.

    Args:
        app_ref: atomacos application reference

    Returns:
        atomacos window reference

    Raises:
        WindowNotFoundError: If no windows found for application
    """
    try:
        windows = app_ref.windows()
        if not windows:
            raise WindowNotFoundError("No windows found for application")
        return windows[0]
    except AttributeError as err:
        raise WindowNotFoundError("Unable to access windows for application") from err


def element_to_ui_element(element: Any) -> UIElement:
    """Convert atomacos element to UIElement dataclass.

    Args:
        element: atomacos UI element

    Returns:
        UIElement dataclass with element properties
    """
    # Get position and size, defaulting to (0, 0) if not available
    position = getattr(element, "AXPosition", None) or (0, 0)
    size = getattr(element, "AXSize", None) or (0, 0)

    return UIElement(
        role=getattr(element, "AXRole", None) or "Unknown",
        title=getattr(element, "AXTitle", None),
        value=getattr(element, "AXValue", None),
        position=(int(position[0]), int(position[1])),
        size=(int(size[0]), int(size[1])),
        enabled=bool(getattr(element, "AXEnabled", True)),
        focused=bool(getattr(element, "AXFocused", False)),
        identifier=getattr(element, "AXIdentifier", None),
    )


def _try_convert_element(
    elem: Any,
    filter_: ElementFilter | None,
) -> UIElement | None:
    """Try to convert an element, returning None on failure."""
    with contextlib.suppress(Exception):
        ui_elem = element_to_ui_element(elem)
        if filter_ and filter_.enabled_only and not ui_elem.enabled:
            return None
        return ui_elem
    return None


def find_elements_in_window(
    window: Any,
    filter_: ElementFilter | None = None,
) -> tuple[UIElement, ...]:
    """Find all elements matching filter in window.

    Args:
        window: atomacos window reference
        filter_: Optional filter criteria for element search

    Returns:
        Tuple of UIElement objects matching the filter
    """
    criteria = {}
    if filter_:
        if filter_.role:
            criteria["AXRole"] = filter_.role
        if filter_.title:
            criteria["AXTitle"] = filter_.title
        if filter_.identifier:
            criteria["AXIdentifier"] = filter_.identifier

    try:
        elements = window.findAll(**criteria) if criteria else window.findAll()
    except Exception:
        return ()

    results = [
        ui_elem for elem in elements if (ui_elem := _try_convert_element(elem, filter_)) is not None
    ]

    return tuple(results)
