"""atomacos wrapper for UI element discovery."""

from ui_inspector.models import ElementFilter, UIElement


def get_app_ref(app_name: str):  # type: ignore[no-untyped-def]
    """Get application reference by name or bundle ID."""
    raise NotImplementedError("Phase 4: Implement get_app_ref")


def get_frontmost_window(app_ref):  # type: ignore[no-untyped-def]
    """Get the frontmost window of an application."""
    raise NotImplementedError("Phase 4: Implement get_frontmost_window")


def element_to_ui_element(element) -> UIElement:  # type: ignore[no-untyped-def]
    """Convert atomacos element to UIElement dataclass."""
    raise NotImplementedError("Phase 4: Implement element_to_ui_element")


def find_elements_in_window(
    window,  # type: ignore[no-untyped-def]
    filter_: ElementFilter | None = None,
) -> tuple[UIElement, ...]:
    """Find all elements matching filter in window."""
    raise NotImplementedError("Phase 4: Implement find_elements_in_window")
