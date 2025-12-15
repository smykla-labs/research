"""Action functions for UI element inspection."""

from ui_inspector.core import (
    find_elements_in_window,
    get_app_ref,
    get_frontmost_window,
)
from ui_inspector.models import ElementFilter, ElementNotFoundError, UIElement


def find_element(
    app_name: str,
    *,
    role: str | None = None,
    title: str | None = None,
    identifier: str | None = None,
) -> UIElement | None:
    """Find first matching UI element in application.

    Args:
        app_name: Application name or bundle ID
        role: Filter by element role (e.g., "AXButton")
        title: Filter by element title
        identifier: Filter by element identifier

    Returns:
        First matching UIElement or None if not found
    """
    app_ref = get_app_ref(app_name)
    window = get_frontmost_window(app_ref)
    filter_ = ElementFilter(role=role, title=title, identifier=identifier)
    elements = find_elements_in_window(window, filter_)
    return elements[0] if elements else None


def list_elements(
    app_name: str,
    *,
    role: str | None = None,
) -> tuple[UIElement, ...]:
    """List all UI elements in application, optionally filtered by role.

    Args:
        app_name: Application name or bundle ID
        role: Filter by element role (e.g., "AXButton", "AXTextField")

    Returns:
        Tuple of UIElement objects
    """
    app_ref = get_app_ref(app_name)
    window = get_frontmost_window(app_ref)
    filter_ = ElementFilter(role=role) if role else None
    return find_elements_in_window(window, filter_)


def get_click_target(
    app_name: str,
    *,
    role: str | None = None,
    title: str | None = None,
) -> tuple[int, int]:
    """Get click coordinates for UI element.

    Args:
        app_name: Application name or bundle ID
        role: Filter by element role (e.g., "AXButton")
        title: Filter by element title

    Returns:
        Tuple of (x, y) coordinates for center of element

    Raises:
        ElementNotFoundError: If no matching element is found
    """
    element = find_element(app_name, role=role, title=title)
    if not element:
        criteria = []
        if role:
            criteria.append(f"role={role}")
        if title:
            criteria.append(f"title={title}")
        raise ElementNotFoundError(f"Element not found: {', '.join(criteria) or 'no criteria'}")
    return element.center
