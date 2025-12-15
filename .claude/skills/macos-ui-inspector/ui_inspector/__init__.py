"""macOS UI element inspector via Accessibility API."""

from ui_inspector.actions import find_element, get_click_target, list_elements
from ui_inspector.models import (
    AppNotFoundError,
    ElementFilter,
    ElementNotFoundError,
    UIElement,
    UiInspectorError,
    WindowNotFoundError,
)

__all__ = [
    "AppNotFoundError",
    "ElementFilter",
    "ElementNotFoundError",
    "UIElement",
    "UiInspectorError",
    "WindowNotFoundError",
    "find_element",
    "get_click_target",
    "list_elements",
]
