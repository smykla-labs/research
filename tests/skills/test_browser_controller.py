"""Comprehensive tests for Browser Controller skill."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from browser_controller import (
    ActionResult,
    BrowserConnection,
    BrowserConnectionError,
    BrowserError,
    BrowserNotFoundError,
    BrowserType,
    ConnectionStatus,
    ElementInfo,
    ElementNotFoundError,
    NavigationError,
    PageContent,
    ScriptExecutionError,
    TabInfo,
    TabNotFoundError,
    normalize_url,
    parse_selector,
    validate_url,
)
from browser_controller.cli import main
from browser_controller.core import (
    detect_running_browsers,
    find_available_browser,
    get_browser_launch_command,
    resolve_browser_type,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_tab_chrome() -> TabInfo:
    """Create a sample Chrome tab."""
    return TabInfo(
        tab_id="ABC123",
        url="https://example.com",
        title="Example Domain",
        browser_type=BrowserType.CHROME,
        active=True,
    )


@pytest.fixture
def sample_tab_firefox() -> TabInfo:
    """Create a sample Firefox tab."""
    return TabInfo(
        tab_id="firefox-handle-1",
        url="https://mozilla.org",
        title="Mozilla",
        browser_type=BrowserType.FIREFOX,
        active=False,
    )


@pytest.fixture
def sample_connection_chrome(sample_tab_chrome: TabInfo) -> BrowserConnection:
    """Create a sample Chrome connection."""
    return BrowserConnection(
        browser_type=BrowserType.CHROME,
        endpoint="http://localhost:9222",
        status=ConnectionStatus.CONNECTED,
        tabs=(sample_tab_chrome,),
        _handle=MagicMock(),
    )


@pytest.fixture
def sample_page_content() -> PageContent:
    """Create sample page content."""
    return PageContent(
        url="https://example.com",
        title="Example Domain",
        html="<html><body>Hello World</body></html>",
        text="Hello World",
    )


@pytest.fixture
def sample_element_info() -> ElementInfo:
    """Create sample element info."""
    return ElementInfo(
        selector="#submit",
        tag_name="button",
        text="Submit",
        attributes={"id": "submit", "class": "btn primary"},
    )


@pytest.fixture
def sample_action_result() -> ActionResult:
    """Create sample action result."""
    return ActionResult(
        success=True,
        action="click",
        details={"selector": "#submit"},
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestBrowserType:
    """Tests for BrowserType enum."""

    def test_browser_types(self) -> None:
        """Test browser type values."""
        assert BrowserType.CHROME.value == "chrome"
        assert BrowserType.FIREFOX.value == "firefox"
        assert BrowserType.AUTO.value == "auto"


class TestConnectionStatus:
    """Tests for ConnectionStatus enum."""

    def test_connection_statuses(self) -> None:
        """Test connection status values."""
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.ERROR.value == "error"


class TestTabInfo:
    """Tests for TabInfo dataclass."""

    def test_tab_info_creation(self) -> None:
        """Test TabInfo creation."""
        tab = TabInfo(
            tab_id="test-123",
            url="https://example.com",
            title="Test",
            browser_type=BrowserType.CHROME,
        )
        assert tab.tab_id == "test-123"
        assert tab.url == "https://example.com"
        assert tab.title == "Test"
        assert tab.browser_type == BrowserType.CHROME
        assert tab.active is False

    def test_tab_info_to_dict(self, sample_tab_chrome: TabInfo) -> None:
        """Test TabInfo to_dict conversion."""
        data = sample_tab_chrome.to_dict()
        assert data["tab_id"] == "ABC123"
        assert data["url"] == "https://example.com"
        assert data["title"] == "Example Domain"
        assert data["browser_type"] == "chrome"
        assert data["active"] is True


class TestBrowserConnection:
    """Tests for BrowserConnection dataclass."""

    def test_connection_to_dict(self, sample_connection_chrome: BrowserConnection) -> None:
        """Test BrowserConnection to_dict excludes handle."""
        data = sample_connection_chrome.to_dict()
        assert data["browser_type"] == "chrome"
        assert data["endpoint"] == "http://localhost:9222"
        assert data["status"] == "connected"
        assert len(data["tabs"]) == 1
        assert "_handle" not in data


class TestPageContent:
    """Tests for PageContent dataclass."""

    def test_page_content_to_dict(self, sample_page_content: PageContent) -> None:
        """Test PageContent to_dict conversion."""
        data = sample_page_content.to_dict()
        assert data["url"] == "https://example.com"
        assert data["title"] == "Example Domain"
        assert "Hello World" in data["html"]
        assert data["text"] == "Hello World"


class TestElementInfo:
    """Tests for ElementInfo dataclass."""

    def test_element_info_to_dict(self, sample_element_info: ElementInfo) -> None:
        """Test ElementInfo to_dict conversion."""
        data = sample_element_info.to_dict()
        assert data["selector"] == "#submit"
        assert data["tag_name"] == "button"
        assert data["text"] == "Submit"
        assert data["attributes"]["class"] == "btn primary"


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_action_result_success(self, sample_action_result: ActionResult) -> None:
        """Test successful ActionResult."""
        assert sample_action_result.success is True
        assert sample_action_result.error is None

    def test_action_result_failure(self) -> None:
        """Test failed ActionResult."""
        result = ActionResult(
            success=False,
            action="navigate",
            error="Connection refused",
        )
        assert result.success is False
        assert result.error == "Connection refused"

    def test_action_result_to_dict(self, sample_action_result: ActionResult) -> None:
        """Test ActionResult to_dict conversion."""
        data = sample_action_result.to_dict()
        assert data["success"] is True
        assert data["action"] == "click"
        assert data["details"]["selector"] == "#submit"


# =============================================================================
# Core Function Tests
# =============================================================================


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_urls(self) -> None:
        """Test valid URL formats."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:9222") is True
        assert validate_url("https://example.com/path?query=1") is True

    def test_invalid_urls(self) -> None:
        """Test invalid URL formats."""
        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url("://missing-scheme.com") is False


class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_add_scheme(self) -> None:
        """Test adding https scheme to bare domains."""
        assert normalize_url("example.com") == "https://example.com"
        assert normalize_url("www.example.com") == "https://www.example.com"

    def test_preserve_existing_scheme(self) -> None:
        """Test preserving existing schemes."""
        assert normalize_url("https://example.com") == "https://example.com"
        assert normalize_url("http://localhost:8080") == "http://localhost:8080"

    def test_empty_url(self) -> None:
        """Test empty URL returns empty."""
        assert normalize_url("") == ""


class TestParseSelector:
    """Tests for parse_selector function."""

    def test_css_selector_default(self) -> None:
        """Test default CSS selector."""
        selector_type, value = parse_selector("#submit-btn")
        assert selector_type == "css"
        assert value == "#submit-btn"

    def test_css_selector_explicit(self) -> None:
        """Test explicit CSS selector prefix."""
        selector_type, value = parse_selector("css:.my-class")
        assert selector_type == "css"
        assert value == ".my-class"

    def test_xpath_selector(self) -> None:
        """Test XPath selector prefix."""
        selector_type, value = parse_selector("xpath://div[@class='foo']")
        assert selector_type == "xpath"
        assert value == "//div[@class='foo']"

    def test_id_shorthand(self) -> None:
        """Test ID shorthand prefix."""
        selector_type, value = parse_selector("id:element-id")
        assert selector_type == "css"
        assert value == "#element-id"

    def test_class_shorthand(self) -> None:
        """Test class shorthand prefix."""
        selector_type, value = parse_selector("class:my-class")
        assert selector_type == "css"
        assert value == ".my-class"


class TestDetectRunningBrowsers:
    """Tests for detect_running_browsers function."""

    @patch("browser_controller.core.discover_chrome")
    @patch("browser_controller.core.discover_firefox")
    def test_both_available(
        self,
        mock_firefox: MagicMock,
        mock_chrome: MagicMock,
    ) -> None:
        """Test when both browsers are available."""
        mock_chrome.return_value = True
        mock_firefox.return_value = True

        browsers = detect_running_browsers()
        assert browsers[BrowserType.CHROME] is True
        assert browsers[BrowserType.FIREFOX] is True

    @patch("browser_controller.core.discover_chrome")
    @patch("browser_controller.core.discover_firefox")
    def test_none_available(
        self,
        mock_firefox: MagicMock,
        mock_chrome: MagicMock,
    ) -> None:
        """Test when no browsers are available."""
        mock_chrome.return_value = False
        mock_firefox.return_value = False

        browsers = detect_running_browsers()
        assert browsers[BrowserType.CHROME] is False
        assert browsers[BrowserType.FIREFOX] is False


class TestFindAvailableBrowser:
    """Tests for find_available_browser function."""

    @patch("browser_controller.core.detect_running_browsers")
    def test_chrome_preferred(self, mock_detect: MagicMock) -> None:
        """Test Chrome is preferred when both available."""
        mock_detect.return_value = {
            BrowserType.CHROME: True,
            BrowserType.FIREFOX: True,
        }
        assert find_available_browser() == BrowserType.CHROME

    @patch("browser_controller.core.detect_running_browsers")
    def test_firefox_fallback(self, mock_detect: MagicMock) -> None:
        """Test Firefox when Chrome not available."""
        mock_detect.return_value = {
            BrowserType.CHROME: False,
            BrowserType.FIREFOX: True,
        }
        assert find_available_browser() == BrowserType.FIREFOX

    @patch("browser_controller.core.detect_running_browsers")
    def test_none_available_raises(self, mock_detect: MagicMock) -> None:
        """Test raises when no browser available."""
        mock_detect.return_value = {
            BrowserType.CHROME: False,
            BrowserType.FIREFOX: False,
        }
        with pytest.raises(BrowserNotFoundError):
            find_available_browser()


class TestResolveBrowserType:
    """Tests for resolve_browser_type function."""

    @patch("browser_controller.core.find_available_browser")
    def test_auto_resolved(self, mock_find: MagicMock) -> None:
        """Test AUTO is resolved to actual type."""
        mock_find.return_value = BrowserType.CHROME
        result = resolve_browser_type(BrowserType.AUTO)
        assert result == BrowserType.CHROME
        mock_find.assert_called_once()

    def test_explicit_chrome(self) -> None:
        """Test explicit Chrome is not changed."""
        result = resolve_browser_type(BrowserType.CHROME)
        assert result == BrowserType.CHROME

    def test_explicit_firefox(self) -> None:
        """Test explicit Firefox is not changed."""
        result = resolve_browser_type(BrowserType.FIREFOX)
        assert result == BrowserType.FIREFOX


class TestGetBrowserLaunchCommand:
    """Tests for get_browser_launch_command function."""

    def test_chrome_command(self) -> None:
        """Test Chrome launch command."""
        cmd = get_browser_launch_command(BrowserType.CHROME)
        assert "Chrome" in cmd
        assert "--remote-debugging-port" in cmd

    def test_firefox_command(self) -> None:
        """Test Firefox launch command."""
        cmd = get_browser_launch_command(BrowserType.FIREFOX)
        assert "firefox" in cmd
        assert "--marionette" in cmd

    def test_auto_returns_empty(self) -> None:
        """Test AUTO returns empty string."""
        cmd = get_browser_launch_command(BrowserType.AUTO)
        assert cmd == ""


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for custom exceptions."""

    def test_browser_error_base(self) -> None:
        """Test BrowserError is base for all browser exceptions."""
        assert issubclass(BrowserConnectionError, BrowserError)
        assert issubclass(BrowserNotFoundError, BrowserError)
        assert issubclass(ElementNotFoundError, BrowserError)
        assert issubclass(NavigationError, BrowserError)
        assert issubclass(ScriptExecutionError, BrowserError)
        assert issubclass(TabNotFoundError, BrowserError)

    def test_browser_not_found_error(self) -> None:
        """Test BrowserNotFoundError message."""
        error = BrowserNotFoundError("Chrome not found")
        assert str(error) == "Chrome not found"

    def test_element_not_found_error(self) -> None:
        """Test ElementNotFoundError message."""
        error = ElementNotFoundError("Element #submit not found")
        assert str(error) == "Element #submit not found"

    def test_navigation_error(self) -> None:
        """Test NavigationError message."""
        error = NavigationError("Failed to navigate")
        assert str(error) == "Failed to navigate"


# =============================================================================
# CLI Tests
# =============================================================================


class TestCLI:
    """Tests for CLI commands."""

    def test_no_command_shows_help(self) -> None:
        """Test no command returns non-zero."""
        result = main([])
        assert result != 0

    @patch("browser_controller.cli.detect_running_browsers")
    def test_check_command(self, mock_detect: MagicMock, capsys) -> None:
        """Test check subcommand."""
        mock_detect.return_value = {
            BrowserType.CHROME: True,
            BrowserType.FIREFOX: False,
        }
        result = main(["check"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Chrome" in captured.out
        assert "Firefox" in captured.out

    @patch("browser_controller.cli.detect_running_browsers")
    def test_check_command_json(self, mock_detect: MagicMock, capsys) -> None:
        """Test check subcommand with --json."""
        mock_detect.return_value = {
            BrowserType.CHROME: True,
            BrowserType.FIREFOX: False,
        }
        result = main(["check", "--json"])
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["chrome"]["available"] is True
        assert data["firefox"]["available"] is False

    @patch("browser_controller.cli.connect")
    @patch("browser_controller.cli.list_tabs")
    @patch("browser_controller.cli.close_connection")
    def test_tabs_command(
        self,
        mock_close: MagicMock,
        mock_tabs: MagicMock,
        mock_connect: MagicMock,
        sample_tab_chrome: TabInfo,
        capsys,
    ) -> None:
        """Test tabs subcommand."""
        mock_connect.return_value = BrowserConnection(
            browser_type=BrowserType.CHROME,
            endpoint="http://localhost:9222",
            status=ConnectionStatus.CONNECTED,
            tabs=(sample_tab_chrome,),
        )
        mock_tabs.return_value = (sample_tab_chrome,)

        result = main(["tabs"])
        assert result == 0
        mock_close.assert_called_once()

    @patch("browser_controller.cli.connect")
    @patch("browser_controller.cli.navigate")
    @patch("browser_controller.cli.close_connection")
    def test_navigate_command(
        self,
        mock_close: MagicMock,
        mock_navigate: MagicMock,
        mock_connect: MagicMock,
        sample_connection_chrome: BrowserConnection,
        capsys,
    ) -> None:
        """Test navigate subcommand."""
        mock_connect.return_value = sample_connection_chrome
        mock_navigate.return_value = ActionResult(
            success=True,
            action="navigate",
            details={"url": "https://example.com"},
        )

        result = main(["navigate", "https://example.com"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Navigated to" in captured.out

    @patch("browser_controller.cli.connect")
    @patch("browser_controller.cli.click")
    @patch("browser_controller.cli.close_connection")
    def test_click_command(
        self,
        mock_close: MagicMock,
        mock_click: MagicMock,
        mock_connect: MagicMock,
        sample_connection_chrome: BrowserConnection,
        capsys,
    ) -> None:
        """Test click subcommand."""
        mock_connect.return_value = sample_connection_chrome
        mock_click.return_value = ActionResult(
            success=True,
            action="click",
            details={"selector": "#submit"},
        )

        result = main(["click", "#submit"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Clicked" in captured.out

    @patch("browser_controller.cli.connect")
    @patch("browser_controller.cli.fill")
    @patch("browser_controller.cli.close_connection")
    def test_fill_command(
        self,
        mock_close: MagicMock,
        mock_fill: MagicMock,
        mock_connect: MagicMock,
        sample_connection_chrome: BrowserConnection,
        capsys,
    ) -> None:
        """Test fill subcommand."""
        mock_connect.return_value = sample_connection_chrome
        mock_fill.return_value = ActionResult(
            success=True,
            action="fill",
            details={"selector": "#email", "value": "test@example.com"},
        )

        result = main(["fill", "#email", "test@example.com"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Filled" in captured.out

    def test_read_command(
        self,
        sample_connection_chrome: BrowserConnection,
        sample_page_content: PageContent,
        capsys,
    ) -> None:
        """Test read subcommand."""
        with (
            patch("browser_controller.cli.connect") as mock_connect,
            patch("browser_controller.cli.read_content") as mock_read,
            patch("browser_controller.cli.close_connection"),
        ):
            mock_connect.return_value = sample_connection_chrome
            mock_read.return_value = sample_page_content

            result = main(["read"])
            assert result == 0

        captured = capsys.readouterr()
        assert "Example Domain" in captured.out

    def test_read_command_text_only(
        self,
        sample_connection_chrome: BrowserConnection,
        sample_page_content: PageContent,
        capsys,
    ) -> None:
        """Test read subcommand with --text-only."""
        with (
            patch("browser_controller.cli.connect") as mock_connect,
            patch("browser_controller.cli.read_content") as mock_read,
            patch("browser_controller.cli.close_connection"),
        ):
            mock_connect.return_value = sample_connection_chrome
            mock_read.return_value = sample_page_content

            result = main(["read", "--text-only"])
            assert result == 0

        captured = capsys.readouterr()
        assert captured.out.strip() == "Hello World"

    @patch("browser_controller.cli.connect")
    @patch("browser_controller.cli.run_script")
    @patch("browser_controller.cli.close_connection")
    def test_run_command(
        self,
        mock_close: MagicMock,
        mock_run: MagicMock,
        mock_connect: MagicMock,
        sample_connection_chrome: BrowserConnection,
        capsys,
    ) -> None:
        """Test run subcommand."""
        mock_connect.return_value = sample_connection_chrome
        mock_run.return_value = "Example Domain"

        result = main(["run", "document.title"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Example Domain" in captured.out

    def test_screenshot_command(
        self,
        sample_connection_chrome: BrowserConnection,
        capsys,
        tmp_path,
    ) -> None:
        """Test screenshot subcommand."""
        with (
            patch("browser_controller.cli.connect") as mock_connect,
            patch("browser_controller.cli.screenshot") as mock_screenshot,
            patch("browser_controller.cli.close_connection"),
        ):
            mock_connect.return_value = sample_connection_chrome
            output_path = tmp_path / "screenshot.png"
            mock_screenshot.return_value = output_path

            result = main(["screenshot", "-o", str(output_path)])
            assert result == 0

        captured = capsys.readouterr()
        assert "Screenshot saved" in captured.out

    @patch("browser_controller.cli.connect")
    def test_tabs_error_handling(
        self,
        mock_connect: MagicMock,
        capsys,
    ) -> None:
        """Test error handling in tabs command."""
        mock_connect.side_effect = BrowserNotFoundError("Chrome not found")

        result = main(["tabs"])
        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err or "error" in captured.err.lower()
