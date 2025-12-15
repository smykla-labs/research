"""Action functions for UI element inspection."""

from ui_inspector.models import UIElement


def find_element(
    app_name: str,
    *,
    role: str | None = None,
    title: str | None = None,
    identifier: str | None = None,
) -> UIElement | None:
    """Find first matching UI element in application."""
    raise NotImplementedError("Phase 4: Implement find_element")


def list_elements(
    app_name: str,
    *,
    role: str | None = None,
) -> tuple[UIElement, ...]:
    """List all UI elements in application, optionally filtered by role."""
    raise NotImplementedError("Phase 4: Implement list_elements")


def get_click_target(
    app_name: str,
    *,
    role: str | None = None,
    title: str | None = None,
) -> tuple[int, int]:
    """Get click coordinates for UI element."""
    raise NotImplementedError("Phase 4: Implement get_click_target")
