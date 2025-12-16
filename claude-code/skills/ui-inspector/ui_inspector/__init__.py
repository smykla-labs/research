"""macOS UI element inspector via Accessibility API."""

from ui_inspector.actions import find_element, get_click_target, list_elements, press_element
from ui_inspector.models import (
    ActionError,
    AppNotFoundError,
    ElementFilter,
    ElementNotFoundError,
    UIElement,
    UiInspectorError,
    WindowNotFoundError,
)

__all__ = [
    "ActionError",
    "AppNotFoundError",
    "ElementFilter",
    "ElementNotFoundError",
    "UIElement",
    "UiInspectorError",
    "WindowNotFoundError",
    "find_element",
    "get_click_target",
    "list_elements",
    "press_element",
]
