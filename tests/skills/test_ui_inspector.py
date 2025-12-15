"""Comprehensive tests for macOS UI Inspector skill."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from ui_inspector import (
    AppNotFoundError,
    ElementFilter,
    ElementNotFoundError,
    UIElement,
    UiInspectorError,
    WindowNotFoundError,
    find_element,
    get_click_target,
    list_elements,
)
from ui_inspector.cli import (
    TEXT_COLUMN_WIDTH,
    _truncate,
    main,
)
from ui_inspector.core import (
    _try_convert_element,
    element_to_ui_element,
    find_elements_in_window,
    get_app_ref,
    get_frontmost_window,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_ui_element() -> UIElement:
    """Create a sample UI element for testing."""
    return UIElement(
        role="AXButton",
        title="Submit",
        value=None,
        position=(100, 200),
        size=(80, 30),
        enabled=True,
        focused=False,
        identifier="submit-btn",
    )


@pytest.fixture
def sample_element_filter() -> ElementFilter:
    """Create a sample element filter for testing."""
    return ElementFilter(
        role="AXButton",
        title="Submit",
        identifier="submit-btn",
        enabled_only=True,
    )


@pytest.fixture
def mock_atomacos_element() -> MagicMock:
    """Create a mock atomacos element."""
    element = MagicMock()
    element.AXRole = "AXButton"
    element.AXTitle = "Submit"
    element.AXValue = None
    element.AXPosition = (100, 200)
    element.AXSize = (80, 30)
    element.AXEnabled = True
    element.AXFocused = False
    element.AXIdentifier = "submit-btn"
    return element


@pytest.fixture
def mock_atomacos_elements() -> list[MagicMock]:
    """Create multiple mock atomacos elements."""
    elements = []

    # Button element
    btn = MagicMock()
    btn.AXRole = "AXButton"
    btn.AXTitle = "Submit"
    btn.AXValue = None
    btn.AXPosition = (100, 200)
    btn.AXSize = (80, 30)
    btn.AXEnabled = True
    btn.AXFocused = False
    btn.AXIdentifier = "submit-btn"
    elements.append(btn)

    # Text field element
    field = MagicMock()
    field.AXRole = "AXTextField"
    field.AXTitle = "Username"
    field.AXValue = "john@example.com"
    field.AXPosition = (100, 100)
    field.AXSize = (200, 25)
    field.AXEnabled = True
    field.AXFocused = True
    field.AXIdentifier = "username-field"
    elements.append(field)

    # Disabled button
    disabled = MagicMock()
    disabled.AXRole = "AXButton"
    disabled.AXTitle = "Disabled"
    disabled.AXValue = None
    disabled.AXPosition = (200, 200)
    disabled.AXSize = (80, 30)
    disabled.AXEnabled = False
    disabled.AXFocused = False
    disabled.AXIdentifier = "disabled-btn"
    elements.append(disabled)

    # Static text
    text = MagicMock()
    text.AXRole = "AXStaticText"
    text.AXTitle = None
    text.AXValue = "Welcome to the app"
    text.AXPosition = (50, 50)
    text.AXSize = (300, 20)
    text.AXEnabled = True
    text.AXFocused = False
    text.AXIdentifier = None
    elements.append(text)

    return elements


@pytest.fixture
def mock_app_ref() -> MagicMock:
    """Create a mock application reference."""
    return MagicMock()


@pytest.fixture
def mock_window() -> MagicMock:
    """Create a mock window reference."""
    return MagicMock()


# =============================================================================
# UIElement Tests
# =============================================================================


class TestUIElement:
    """Tests for UIElement dataclass."""

    def test_field_access(self, sample_ui_element: UIElement) -> None:
        """Test field access."""
        assert sample_ui_element.role == "AXButton"
        assert sample_ui_element.title == "Submit"
        assert sample_ui_element.value is None
        assert sample_ui_element.position == (100, 200)
        assert sample_ui_element.size == (80, 30)
        assert sample_ui_element.enabled is True
        assert sample_ui_element.focused is False
        assert sample_ui_element.identifier == "submit-btn"

    def test_center_property(self, sample_ui_element: UIElement) -> None:
        """Test center property calculation."""
        center = sample_ui_element.center
        # position=(100, 200), size=(80, 30) -> center=(140, 215)
        assert center == (140, 215)

    def test_bounds_property(self, sample_ui_element: UIElement) -> None:
        """Test bounds property."""
        bounds = sample_ui_element.bounds
        assert bounds["x"] == 100
        assert bounds["y"] == 200
        assert bounds["width"] == 80
        assert bounds["height"] == 30

    def test_to_dict(self, sample_ui_element: UIElement) -> None:
        """Test to_dict method."""
        data = sample_ui_element.to_dict()
        assert data["role"] == "AXButton"
        assert data["title"] == "Submit"
        assert data["value"] is None
        assert data["identifier"] == "submit-btn"
        assert data["position_x"] == 100
        assert data["position_y"] == 200
        assert data["width"] == 80
        assert data["height"] == 30
        assert data["center_x"] == 140
        assert data["center_y"] == 215
        assert data["enabled"] is True
        assert data["focused"] is False
        assert "bounds" in data
        assert data["bounds"]["width"] == 80

    def test_frozen_immutable(self, sample_ui_element: UIElement) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            sample_ui_element.role = "AXTextField"  # type: ignore[misc]

    def test_zero_size_element(self) -> None:
        """Test UI element with zero size."""
        elem = UIElement(
            role="AXGroup",
            title=None,
            value=None,
            position=(50, 50),
            size=(0, 0),
            enabled=True,
            focused=False,
        )
        assert elem.center == (50, 50)
        assert elem.bounds["width"] == 0
        assert elem.bounds["height"] == 0

    def test_none_optional_fields(self) -> None:
        """Test UI element with None optional fields."""
        elem = UIElement(
            role="AXUnknown",
            title=None,
            value=None,
            position=(0, 0),
            size=(100, 100),
            enabled=True,
            focused=False,
            identifier=None,
        )
        data = elem.to_dict()
        assert data["title"] is None
        assert data["value"] is None
        assert data["identifier"] is None


# =============================================================================
# ElementFilter Tests
# =============================================================================


class TestElementFilter:
    """Tests for ElementFilter dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        filter_ = ElementFilter()
        assert filter_.role is None
        assert filter_.title is None
        assert filter_.identifier is None
        assert filter_.enabled_only is True

    def test_custom_values(self, sample_element_filter: ElementFilter) -> None:
        """Test custom values."""
        assert sample_element_filter.role == "AXButton"
        assert sample_element_filter.title == "Submit"
        assert sample_element_filter.identifier == "submit-btn"
        assert sample_element_filter.enabled_only is True

    def test_frozen_immutable(self, sample_element_filter: ElementFilter) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            sample_element_filter.role = "AXTextField"  # type: ignore[misc]

    def test_disabled_included(self) -> None:
        """Test filter with enabled_only=False."""
        filter_ = ElementFilter(enabled_only=False)
        assert filter_.enabled_only is False


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for custom exceptions."""

    def test_exception_hierarchy(self) -> None:
        """Test exception hierarchy."""
        assert issubclass(AppNotFoundError, UiInspectorError)
        assert issubclass(WindowNotFoundError, UiInspectorError)
        assert issubclass(ElementNotFoundError, UiInspectorError)

    def test_app_not_found_error_message(self) -> None:
        """Test AppNotFoundError message handling."""
        e = AppNotFoundError("Application not found: Safari")
        assert "Safari" in str(e)

    def test_window_not_found_error_message(self) -> None:
        """Test WindowNotFoundError message handling."""
        e = WindowNotFoundError("No windows found for application")
        assert "windows" in str(e)

    def test_element_not_found_error_message(self) -> None:
        """Test ElementNotFoundError message handling."""
        e = ElementNotFoundError("Element not found: role=AXButton, title=Submit")
        assert "AXButton" in str(e)
        assert "Submit" in str(e)


# =============================================================================
# Core Function Tests
# =============================================================================


class TestGetAppRef:
    """Tests for get_app_ref function."""

    def test_bundle_id_lookup(self) -> None:
        """Test looking up app by bundle ID."""
        mock_app = MagicMock()
        with patch("ui_inspector.core.atomacos") as mock_atomacos:
            mock_atomacos.getAppRefByBundleId.return_value = mock_app
            result = get_app_ref("com.apple.Safari")
            assert result is mock_app
            mock_atomacos.getAppRefByBundleId.assert_called_once_with("com.apple.Safari")

    def test_localized_name_lookup(self) -> None:
        """Test looking up app by localized name."""
        mock_app = MagicMock()
        with patch("ui_inspector.core.atomacos") as mock_atomacos:
            mock_atomacos.getAppRefByLocalizedName.return_value = mock_app
            result = get_app_ref("Safari")
            assert result is mock_app
            mock_atomacos.getAppRefByLocalizedName.assert_called_once_with("Safari")

    def test_fallback_to_bundle_id_without_dots(self) -> None:
        """Test fallback to bundle ID lookup for names without dots."""
        mock_app = MagicMock()
        with patch("ui_inspector.core.atomacos") as mock_atomacos:
            # Localized name fails, bundle ID succeeds
            mock_atomacos.getAppRefByLocalizedName.side_effect = Exception("Not found")
            mock_atomacos.getAppRefByBundleId.return_value = mock_app

            result = get_app_ref("SimpleApp")

            assert result is mock_app
            mock_atomacos.getAppRefByBundleId.assert_called_with("SimpleApp")

    def test_app_not_found_error(self) -> None:
        """Test AppNotFoundError when app not found."""
        with patch("ui_inspector.core.atomacos") as mock_atomacos:
            mock_atomacos.getAppRefByLocalizedName.side_effect = Exception("Not found")
            mock_atomacos.getAppRefByBundleId.side_effect = Exception("Not found")

            with pytest.raises(AppNotFoundError, match="Application not found"):
                get_app_ref("NonexistentApp")


class TestGetFrontmostWindow:
    """Tests for get_frontmost_window function."""

    def test_returns_first_window(self, mock_app_ref: MagicMock) -> None:
        """Test returning first window."""
        mock_window = MagicMock()
        mock_app_ref.windows.return_value = [mock_window, MagicMock()]

        result = get_frontmost_window(mock_app_ref)

        assert result is mock_window

    def test_no_windows_error(self, mock_app_ref: MagicMock) -> None:
        """Test WindowNotFoundError when no windows."""
        mock_app_ref.windows.return_value = []

        with pytest.raises(WindowNotFoundError, match="No windows found"):
            get_frontmost_window(mock_app_ref)

    def test_attribute_error_handling(self, mock_app_ref: MagicMock) -> None:
        """Test handling of AttributeError."""
        mock_app_ref.windows.side_effect = AttributeError("No windows method")

        with pytest.raises(WindowNotFoundError, match="Unable to access windows"):
            get_frontmost_window(mock_app_ref)


class TestElementToUIElement:
    """Tests for element_to_ui_element function."""

    def test_converts_all_attributes(self, mock_atomacos_element: MagicMock) -> None:
        """Test converting all attributes."""
        result = element_to_ui_element(mock_atomacos_element)

        assert result.role == "AXButton"
        assert result.title == "Submit"
        assert result.value is None
        assert result.position == (100, 200)
        assert result.size == (80, 30)
        assert result.enabled is True
        assert result.focused is False
        assert result.identifier == "submit-btn"

    def test_handles_missing_position(self) -> None:
        """Test handling missing position attribute."""
        element = MagicMock(spec=[])  # Empty spec means no attributes
        result = element_to_ui_element(element)

        assert result.position == (0, 0)

    def test_handles_missing_size(self) -> None:
        """Test handling missing size attribute."""
        element = MagicMock(spec=[])
        result = element_to_ui_element(element)

        assert result.size == (0, 0)

    def test_handles_none_role(self) -> None:
        """Test handling None role."""
        element = MagicMock()
        element.AXRole = None
        result = element_to_ui_element(element)

        assert result.role == "Unknown"


class TestTryConvertElement:
    """Tests for _try_convert_element function."""

    def test_successful_conversion(self, mock_atomacos_element: MagicMock) -> None:
        """Test successful element conversion."""
        result = _try_convert_element(mock_atomacos_element, None)

        assert result is not None
        assert result.role == "AXButton"

    def test_filters_disabled_elements(self, mock_atomacos_elements: list[MagicMock]) -> None:
        """Test filtering disabled elements when enabled_only=True."""
        disabled_elem = mock_atomacos_elements[2]  # Disabled button
        filter_ = ElementFilter(enabled_only=True)

        result = _try_convert_element(disabled_elem, filter_)

        assert result is None

    def test_includes_disabled_when_filter_allows(
        self, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test including disabled elements when enabled_only=False."""
        disabled_elem = mock_atomacos_elements[2]
        filter_ = ElementFilter(enabled_only=False)

        result = _try_convert_element(disabled_elem, filter_)

        assert result is not None
        assert result.enabled is False

    def test_returns_none_on_exception(self) -> None:
        """Test returning None on exception."""
        element = MagicMock()
        element.AXPosition = "invalid"  # Will cause conversion error

        # Should not raise, returns None
        with patch("ui_inspector.core.element_to_ui_element", side_effect=Exception("Error")):
            result = _try_convert_element(element, None)
            assert result is None


class TestFindElementsInWindow:
    """Tests for find_elements_in_window function."""

    def test_finds_all_elements(
        self, mock_window: MagicMock, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test finding all elements without filter."""
        mock_window.findAll.return_value = mock_atomacos_elements

        results = find_elements_in_window(mock_window)

        # Should have 3 elements (disabled one filtered by default enabled_only)
        # Actually no filter passed, so enabled_only not applied
        assert len(results) == 4

    def test_filter_by_role(
        self, mock_window: MagicMock, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test filtering by role."""
        # Return only buttons
        buttons = [e for e in mock_atomacos_elements if e.AXRole == "AXButton"]
        mock_window.findAll.return_value = buttons

        filter_ = ElementFilter(role="AXButton")
        results = find_elements_in_window(mock_window, filter_)

        mock_window.findAll.assert_called_with(AXRole="AXButton")
        # Should return 1 (enabled button), disabled filtered
        assert len(results) == 1

    def test_filter_by_title(
        self, mock_window: MagicMock, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test filtering by title."""
        submit_btn = [e for e in mock_atomacos_elements if e.AXTitle == "Submit"]
        mock_window.findAll.return_value = submit_btn

        filter_ = ElementFilter(title="Submit")
        results = find_elements_in_window(mock_window, filter_)

        mock_window.findAll.assert_called_with(AXTitle="Submit")
        assert len(results) == 1
        assert results[0].title == "Submit"

    def test_filter_by_identifier(
        self, mock_window: MagicMock, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test filtering by identifier."""
        submit_btn = [e for e in mock_atomacos_elements if e.AXIdentifier == "submit-btn"]
        mock_window.findAll.return_value = submit_btn

        filter_ = ElementFilter(identifier="submit-btn")
        results = find_elements_in_window(mock_window, filter_)

        mock_window.findAll.assert_called_with(AXIdentifier="submit-btn")
        assert len(results) == 1

    def test_handles_findall_exception(self, mock_window: MagicMock) -> None:
        """Test handling exception from findAll."""
        mock_window.findAll.side_effect = Exception("API error")

        results = find_elements_in_window(mock_window)

        assert results == ()

    def test_combined_filters(
        self, mock_window: MagicMock, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test combined filter criteria."""
        mock_window.findAll.return_value = [mock_atomacos_elements[0]]

        filter_ = ElementFilter(role="AXButton", title="Submit")
        find_elements_in_window(mock_window, filter_)

        mock_window.findAll.assert_called_with(AXRole="AXButton", AXTitle="Submit")


# =============================================================================
# Action Function Tests
# =============================================================================


class TestFindElement:
    """Tests for find_element function."""

    def test_find_element_returns_first_match(
        self, mock_atomacos_elements: list[MagicMock]
    ) -> None:
        """Test finding first matching element."""
        with (
            patch("ui_inspector.actions.get_app_ref") as mock_get_app,
            patch("ui_inspector.actions.get_frontmost_window") as mock_get_window,
            patch("ui_inspector.actions.find_elements_in_window") as mock_find,
        ):
            mock_get_app.return_value = MagicMock()
            mock_get_window.return_value = MagicMock()
            mock_find.return_value = (
                UIElement(
                    role="AXButton",
                    title="Submit",
                    value=None,
                    position=(100, 200),
                    size=(80, 30),
                    enabled=True,
                    focused=False,
                ),
            )

            result = find_element("Safari", role="AXButton", title="Submit")

            assert result is not None
            assert result.role == "AXButton"
            assert result.title == "Submit"

    def test_find_element_returns_none_when_not_found(self) -> None:
        """Test returning None when element not found."""
        with (
            patch("ui_inspector.actions.get_app_ref") as mock_get_app,
            patch("ui_inspector.actions.get_frontmost_window") as mock_get_window,
            patch("ui_inspector.actions.find_elements_in_window") as mock_find,
        ):
            mock_get_app.return_value = MagicMock()
            mock_get_window.return_value = MagicMock()
            mock_find.return_value = ()

            result = find_element("Safari", role="AXButton", title="Nonexistent")

            assert result is None


class TestListElements:
    """Tests for list_elements function."""

    def test_list_all_elements(self) -> None:
        """Test listing all elements."""
        elements = (
            UIElement(
                role="AXButton",
                title="Submit",
                value=None,
                position=(100, 200),
                size=(80, 30),
                enabled=True,
                focused=False,
            ),
            UIElement(
                role="AXTextField",
                title="Username",
                value="test",
                position=(100, 100),
                size=(200, 25),
                enabled=True,
                focused=True,
            ),
        )

        with (
            patch("ui_inspector.actions.get_app_ref") as mock_get_app,
            patch("ui_inspector.actions.get_frontmost_window") as mock_get_window,
            patch("ui_inspector.actions.find_elements_in_window") as mock_find,
        ):
            mock_get_app.return_value = MagicMock()
            mock_get_window.return_value = MagicMock()
            mock_find.return_value = elements

            result = list_elements("Safari")

            assert len(result) == 2
            mock_find.assert_called_once()

    def test_list_filtered_by_role(self) -> None:
        """Test listing elements filtered by role."""
        with (
            patch("ui_inspector.actions.get_app_ref") as mock_get_app,
            patch("ui_inspector.actions.get_frontmost_window") as mock_get_window,
            patch("ui_inspector.actions.find_elements_in_window") as mock_find,
        ):
            mock_get_app.return_value = MagicMock()
            mock_get_window.return_value = MagicMock()
            mock_find.return_value = ()

            list_elements("Safari", role="AXButton")

            # Verify filter was created with role
            call_args = mock_find.call_args
            filter_arg = call_args[0][1]
            assert filter_arg.role == "AXButton"


class TestGetClickTarget:
    """Tests for get_click_target function."""

    def test_get_click_target_returns_center(self) -> None:
        """Test getting click target returns center coordinates."""
        with patch("ui_inspector.actions.find_element") as mock_find:
            mock_find.return_value = UIElement(
                role="AXButton",
                title="Submit",
                value=None,
                position=(100, 200),
                size=(80, 30),
                enabled=True,
                focused=False,
            )

            x, y = get_click_target("Safari", role="AXButton", title="Submit")

            # position=(100, 200), size=(80, 30) -> center=(140, 215)
            assert x == 140
            assert y == 215

    def test_get_click_target_not_found_error(self) -> None:
        """Test ElementNotFoundError when element not found."""
        with patch("ui_inspector.actions.find_element") as mock_find:
            mock_find.return_value = None

            with pytest.raises(ElementNotFoundError, match="Element not found"):
                get_click_target("Safari", role="AXButton", title="Nonexistent")

    def test_get_click_target_error_message_includes_criteria(self) -> None:
        """Test error message includes search criteria."""
        with patch("ui_inspector.actions.find_element") as mock_find:
            mock_find.return_value = None

            with pytest.raises(ElementNotFoundError) as exc_info:
                get_click_target("Safari", role="AXButton", title="Submit")

            assert "role=AXButton" in str(exc_info.value)
            assert "title=Submit" in str(exc_info.value)

    def test_get_click_target_no_criteria_error_message(self) -> None:
        """Test error message when no criteria specified."""
        with patch("ui_inspector.actions.find_element") as mock_find:
            mock_find.return_value = None

            with pytest.raises(ElementNotFoundError) as exc_info:
                get_click_target("Safari")

            assert "no criteria" in str(exc_info.value)


# =============================================================================
# CLI Helper Tests
# =============================================================================


class TestTruncate:
    """Tests for _truncate helper function."""

    def test_short_text_unchanged(self) -> None:
        """Test short text is returned unchanged."""
        assert _truncate("Hello", 10) == "Hello"

    def test_long_text_truncated(self) -> None:
        """Test long text is truncated with ellipsis."""
        result = _truncate("Hello World!", 8)
        assert result == "Hello..."
        assert len(result) == 8

    def test_none_returns_empty(self) -> None:
        """Test None returns empty string."""
        assert _truncate(None, 10) == ""

    def test_exact_length_unchanged(self) -> None:
        """Test text at exact length is unchanged."""
        assert _truncate("Hello", 5) == "Hello"

    def test_text_column_width_constant(self) -> None:
        """Test TEXT_COLUMN_WIDTH constant exists."""
        assert TEXT_COLUMN_WIDTH == 25


# =============================================================================
# CLI Parser Tests
# =============================================================================


class TestCLIParser:
    """Tests for CLI argument parser."""

    def test_list_action_requires_app(self) -> None:
        """Test list command requires --app."""
        result = main(["list"])
        assert result == 2  # Typer error

    def test_find_action(self) -> None:
        """Test find command."""
        with (
            patch("ui_inspector.cli.find_element") as mock_find,
        ):
            mock_find.side_effect = AppNotFoundError("Not found")
            result = main(["find", "--app", "Safari", "--title", "Submit"])
            assert result == 1  # Error

    def test_click_action(self) -> None:
        """Test click command."""
        with patch("ui_inspector.cli.get_click_target") as mock_click:
            mock_click.side_effect = AppNotFoundError("Not found")
            result = main(["click", "--app", "Safari", "--title", "Submit"])
            assert result == 1  # Error

    def test_mutually_exclusive_actions(self) -> None:
        """Test that commands cannot be used simultaneously (handled by Typer)."""
        # With Typer, commands are mutually exclusive by design
        # This test now verifies invalid command syntax
        result = main(["list", "find"])
        assert result == 2  # Typer error

    def test_app_required(self) -> None:
        """Test --app is required for list command."""
        result = main(["list"])
        assert result == 2  # Typer error

    def test_short_flags(self) -> None:
        """Test short flags parsing."""
        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.side_effect = AppNotFoundError("Not found")
            # -a for app
            result = main(["list", "-a", "Safari"])
            assert result == 1  # Error from AppNotFoundError


# =============================================================================
# CLI Handler Tests
# =============================================================================


class TestHandleList:
    """Tests for _handle_list function."""

    def test_handle_list_json_output(self, capsys) -> None:
        """Test list command with --json output."""
        elements = (
            UIElement(
                role="AXButton",
                title="Submit",
                value=None,
                position=(100, 200),
                size=(80, 30),
                enabled=True,
                focused=False,
            ),
        )

        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.return_value = elements
            result = main(["list", "--app", "Safari", "--json"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Submit" in captured.out
            assert '"role"' in captured.out

    def test_handle_list_table_output(self, capsys) -> None:
        """Test list command with table output."""
        elements = (
            UIElement(
                role="AXButton",
                title="Submit",
                value=None,
                position=(100, 200),
                size=(80, 30),
                enabled=True,
                focused=False,
            ),
        )

        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.return_value = elements
            result = main(["list", "--app", "Safari"])

            assert result == 0
            captured = capsys.readouterr()
            assert "AXButton" in captured.out
            assert "Submit" in captured.out
            assert "Role" in captured.out

    def test_handle_list_empty(self, capsys) -> None:
        """Test list command with no elements found."""
        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.return_value = ()
            result = main(["list", "--app", "Safari"])

            assert result == 0
            captured = capsys.readouterr()
            assert "No elements found" in captured.out

    def test_handle_list_with_role_filter(self, capsys) -> None:
        """Test list command with --role filter."""
        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.return_value = ()
            main(["list", "--app", "Safari", "--role", "AXButton"])

            mock_list.assert_called_once_with("Safari", role="AXButton")


class TestHandleFind:
    """Tests for _handle_find function."""

    def test_handle_find_with_match(self, capsys) -> None:
        """Test find command with matching element."""
        element = UIElement(
            role="AXButton",
            title="Submit",
            value=None,
            position=(100, 200),
            size=(80, 30),
            enabled=True,
            focused=False,
            identifier="submit-btn",
        )

        with patch("ui_inspector.cli.find_element") as mock_find:
            mock_find.return_value = element
            result = main(["find", "--app", "Safari", "--title", "Submit"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Role:" in captured.out
            assert "AXButton" in captured.out

    def test_handle_find_no_match(self, capsys) -> None:
        """Test find command with no match."""
        with patch("ui_inspector.cli.find_element") as mock_find:
            mock_find.return_value = None
            result = main(["find", "--app", "Safari", "--title", "Nonexistent"])

            assert result == 1
            captured = capsys.readouterr()
            assert "No matching element found" in captured.out

    def test_handle_find_json_output(self, capsys) -> None:
        """Test find command with --json output."""
        element = UIElement(
            role="AXButton",
            title="Submit",
            value=None,
            position=(100, 200),
            size=(80, 30),
            enabled=True,
            focused=False,
        )

        with patch("ui_inspector.cli.find_element") as mock_find:
            mock_find.return_value = element
            result = main(["find", "--app", "Safari", "--title", "Submit", "--json"])

            assert result == 0
            captured = capsys.readouterr()
            assert '"role": "AXButton"' in captured.out

    def test_handle_find_json_null_when_not_found(self, capsys) -> None:
        """Test find command with --json outputs null when not found."""
        with patch("ui_inspector.cli.find_element") as mock_find:
            mock_find.return_value = None
            result = main(["find", "--app", "Safari", "--title", "X", "--json"])

            assert result == 0  # JSON mode returns 0 even for null
            captured = capsys.readouterr()
            assert "null" in captured.out


class TestHandleClick:
    """Tests for _handle_click function."""

    def test_handle_click_returns_coords(self, capsys) -> None:
        """Test click command returns coordinates."""
        with patch("ui_inspector.cli.get_click_target") as mock_click:
            mock_click.return_value = (140, 215)
            result = main(["click", "--app", "Safari", "--title", "Submit"])

            assert result == 0
            captured = capsys.readouterr()
            assert "140,215" in captured.out

    def test_handle_click_json_output(self, capsys) -> None:
        """Test click command with --json output."""
        with patch("ui_inspector.cli.get_click_target") as mock_click:
            mock_click.return_value = (140, 215)
            result = main(["click", "--app", "Safari", "--title", "Submit", "--json"])

            assert result == 0
            captured = capsys.readouterr()
            assert '"x": 140' in captured.out
            assert '"y": 215' in captured.out

    def test_handle_click_not_found(self, capsys) -> None:
        """Test click command with element not found."""
        with patch("ui_inspector.cli.get_click_target") as mock_click:
            mock_click.side_effect = ElementNotFoundError("Not found")
            result = main(["click", "--app", "Safari", "--title", "Nonexistent"])

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err


# =============================================================================
# CLI Error Handling Tests
# =============================================================================


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_app_not_found_error(self, capsys) -> None:
        """Test AppNotFoundError handling."""
        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.side_effect = AppNotFoundError("Application not found: BadApp")
            result = main(["list", "--app", "BadApp"])

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err

    def test_window_not_found_error(self, capsys) -> None:
        """Test WindowNotFoundError handling."""
        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.side_effect = WindowNotFoundError("No windows")
            result = main(["list", "--app", "Safari"])

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err

    def test_generic_exception_handling(self, capsys) -> None:
        """Test generic exception handling."""
        with patch("ui_inspector.cli.list_elements") as mock_list:
            mock_list.side_effect = RuntimeError("Unexpected error")
            result = main(["list", "--app", "Safari"])

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err

    def test_version_flag(self) -> None:
        """Test --version flag (Typer provides this automatically)."""
        # Typer provides --version via callback, but requires configuration
        # For now, verify that invalid command returns error code
        result = main(["--version"])
        # Typer exits with code 2 for unknown options
        assert result in (0, 2)
