"""Firefox Marionette backend for Firefox browser control.

This module provides connection to Firefox browsers running with
Marionette enabled (--marionette flag).

Key capabilities:
- Tab listing and management
- Page navigation
- DOM element interaction (click, fill)
- JavaScript execution
- Screenshots

Requirements:
- Firefox started with --marionette flag (default port: 2828)
"""

from __future__ import annotations

import functools
import socket
from pathlib import Path
from typing import Any

from ..models import (
    ActionResult,
    BrowserConnectionError,
    BrowserNotFoundError,
    BrowserType,
    ElementInfo,
    ElementNotFoundError,
    NavigationError,
    PageContent,
    ScriptExecutionError,
    TabInfo,
    TabNotFoundError,
)

DEFAULT_MARIONETTE_PORT = 2828


@functools.cache
def _get_marionette():
    """Lazy load marionette_driver library (cached)."""
    from marionette_driver import marionette

    return marionette


@functools.cache
def _get_by():
    """Lazy load marionette_driver By locator (cached)."""
    from marionette_driver import By

    return By


class MarionetteBackend:
    """Firefox Marionette backend.

    Provides operations for Firefox browser control via Marionette protocol.
    """

    def __init__(self, host: str = "localhost", port: int = DEFAULT_MARIONETTE_PORT) -> None:
        """Initialize Marionette backend.

        Args:
            host: Marionette host.
            port: Marionette port.
        """
        self.host = host
        self.port = port
        self._client: Any = None

    @property
    def endpoint(self) -> str:
        """Get Marionette endpoint string."""
        return f"{self.host}:{self.port}"

    def discover(self) -> bool:
        """Check if Firefox is running with Marionette enabled.

        Returns:
            True if Firefox with Marionette is accessible.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def connect(self) -> None:
        """Connect to Firefox via Marionette.

        Raises:
            BrowserNotFoundError: If Firefox is not accessible.
        """
        if self._client is not None:
            return

        marionette = _get_marionette()

        try:
            self._client = marionette.Marionette(host=self.host, port=self.port)
            self._client.start_session()
        except Exception as e:
            self._client = None
            raise BrowserNotFoundError(
                f"Firefox not found at {self.endpoint}. "
                f"Start Firefox with --marionette flag."
            ) from e

    def _ensure_connected(self) -> Any:
        """Ensure client is connected.

        Returns:
            Marionette client instance.

        Raises:
            BrowserConnectionError: If not connected.
        """
        if self._client is None:
            try:
                self.connect()
            except BrowserNotFoundError as e:
                raise BrowserConnectionError(str(e)) from e

        return self._client

    def get_tabs(self) -> list[TabInfo]:
        """Get all browser tabs.

        Returns:
            List of TabInfo for each open tab.

        Raises:
            BrowserConnectionError: If request fails.
        """
        client = self._ensure_connected()

        try:
            handles = client.window_handles
            current_handle = client.current_window_handle
            tabs = []

            for handle in handles:
                client.switch_to_window(handle)
                tabs.append(
                    TabInfo(
                        tab_id=handle,
                        url=client.get_url(),
                        title=client.title,
                        browser_type=BrowserType.FIREFOX,
                        active=(handle == current_handle),
                    )
                )

            # Switch back to original tab
            client.switch_to_window(current_handle)
            return tabs

        except Exception as e:
            raise BrowserConnectionError(f"Failed to get tabs: {e}") from e

    def _switch_to_tab(self, tab_id: str) -> None:
        """Switch to a specific tab.

        Args:
            tab_id: Tab handle ID.

        Raises:
            TabNotFoundError: If tab not found.
        """
        client = self._ensure_connected()

        try:
            client.switch_to_window(tab_id)
        except Exception as e:
            raise TabNotFoundError(f"Tab not found: {tab_id}") from e

    def navigate_to(self, url: str, tab_id: str | None = None) -> ActionResult:
        """Navigate to URL.

        Args:
            url: URL to navigate to.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            ActionResult indicating success.

        Raises:
            NavigationError: If navigation fails.
        """
        client = self._ensure_connected()

        if tab_id:
            self._switch_to_tab(tab_id)

        try:
            client.navigate(url)
            return ActionResult(
                success=True,
                action="navigate",
                details={"url": url, "tab_id": tab_id or client.current_window_handle},
            )
        except Exception as e:
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    def get_page_content(self, tab_id: str | None = None) -> PageContent:
        """Get page content (HTML and text).

        Args:
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            PageContent with HTML and text.
        """
        client = self._ensure_connected()

        if tab_id:
            self._switch_to_tab(tab_id)

        html = client.page_source
        title = client.title
        url = client.get_url()

        # Get body text via JavaScript
        text = client.execute_script("return document.body.innerText;") or ""

        return PageContent(url=url, title=title, html=html, text=text)

    def click_element(self, selector: str, tab_id: str | None = None) -> ActionResult:
        """Click an element by CSS selector.

        Args:
            selector: CSS selector for element.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            ActionResult indicating success.

        Raises:
            ElementNotFoundError: If element not found.
        """
        client = self._ensure_connected()
        By = _get_by()

        if tab_id:
            self._switch_to_tab(tab_id)

        try:
            element = client.find_element(By.CSS_SELECTOR, selector)
            tag_name = element.tag_name
            element.click()
            return ActionResult(
                success=True,
                action="click",
                details={"selector": selector, "tag_name": tag_name},
            )
        except Exception as e:
            if "Unable to locate" in str(e) or "NoSuchElement" in str(e):
                raise ElementNotFoundError(f"Element not found: {selector}") from e
            raise

    def fill_form(self, selector: str, value: str, tab_id: str | None = None) -> ActionResult:
        """Fill a form field with value.

        Args:
            selector: CSS selector for input element.
            value: Value to fill.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            ActionResult indicating success.

        Raises:
            ElementNotFoundError: If element not found.
        """
        client = self._ensure_connected()
        By = _get_by()

        if tab_id:
            self._switch_to_tab(tab_id)

        try:
            element = client.find_element(By.CSS_SELECTOR, selector)
            tag_name = element.tag_name
            element.clear()
            element.send_keys(value)
            return ActionResult(
                success=True,
                action="fill",
                details={"selector": selector, "value": value, "tag_name": tag_name},
            )
        except Exception as e:
            if "Unable to locate" in str(e) or "NoSuchElement" in str(e):
                raise ElementNotFoundError(f"Element not found: {selector}") from e
            raise

    def get_element_info(self, selector: str, tab_id: str | None = None) -> ElementInfo:
        """Get information about an element.

        Args:
            selector: CSS selector for element.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            ElementInfo with tag, text, and attributes.

        Raises:
            ElementNotFoundError: If element not found.
        """
        client = self._ensure_connected()
        By = _get_by()

        if tab_id:
            self._switch_to_tab(tab_id)

        try:
            element = client.find_element(By.CSS_SELECTOR, selector)

            # Get attributes via JavaScript
            attrs_script = """
            const el = arguments[0];
            const attrs = {};
            for (let i = 0; i < el.attributes.length; i++) {
                attrs[el.attributes[i].name] = el.attributes[i].value;
            }
            return attrs;
            """
            attributes = client.execute_script(attrs_script, [element]) or {}

            return ElementInfo(
                selector=selector,
                tag_name=element.tag_name.lower(),
                text=element.text,
                attributes=attributes,
            )
        except Exception as e:
            if "Unable to locate" in str(e) or "NoSuchElement" in str(e):
                raise ElementNotFoundError(f"Element not found: {selector}") from e
            raise

    def execute_script(self, script: str, tab_id: str | None = None) -> Any:
        """Execute JavaScript in page context.

        Args:
            script: JavaScript code to execute.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            Script result value.

        Raises:
            ScriptExecutionError: If script fails.
        """
        client = self._ensure_connected()

        if tab_id:
            self._switch_to_tab(tab_id)

        try:
            return client.execute_script(f"return {script};")
        except Exception as e:
            raise ScriptExecutionError(f"Script execution failed: {e}") from e

    def activate_tab(self, tab_id: str) -> ActionResult:
        """Activate (switch to) a tab.

        Args:
            tab_id: Tab handle ID.

        Returns:
            ActionResult indicating success.

        Raises:
            TabNotFoundError: If tab not found.
        """
        try:
            self._switch_to_tab(tab_id)
            return ActionResult(
                success=True,
                action="activate",
                details={"tab_id": tab_id},
            )
        except TabNotFoundError:
            raise
        except Exception as e:
            raise TabNotFoundError(f"Failed to activate tab {tab_id}: {e}") from e

    def close_tab(self, tab_id: str) -> ActionResult:
        """Close a tab.

        Args:
            tab_id: Tab handle ID.

        Returns:
            ActionResult indicating success.

        Raises:
            TabNotFoundError: If tab not found.
        """
        client = self._ensure_connected()

        try:
            self._switch_to_tab(tab_id)
            client.close()
            return ActionResult(
                success=True,
                action="close",
                details={"tab_id": tab_id},
            )
        except TabNotFoundError:
            raise
        except Exception as e:
            raise TabNotFoundError(f"Failed to close tab {tab_id}: {e}") from e

    def take_screenshot(self, output_path: Path, tab_id: str | None = None) -> Path:
        """Take screenshot of page.

        Args:
            output_path: Path to save screenshot.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            Path to saved screenshot.
        """
        client = self._ensure_connected()

        if tab_id:
            self._switch_to_tab(tab_id)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Marionette screenshot returns base64 string
        screenshot_data = client.screenshot()

        import base64

        with output_path.open("wb") as f:
            f.write(base64.b64decode(screenshot_data))

        return output_path

    def wait_for_element(
        self,
        selector: str,
        timeout: float = 10.0,
        tab_id: str | None = None,
    ) -> ElementInfo:
        """Wait for element to appear on page.

        Args:
            selector: CSS selector for element.
            timeout: Maximum wait time in seconds.
            tab_id: Optional tab ID (uses current tab if None).

        Returns:
            ElementInfo when element appears.

        Raises:
            ElementNotFoundError: If element not found within timeout.
        """
        import time

        if tab_id:
            self._switch_to_tab(tab_id)

        start = time.time()

        while time.time() - start < timeout:
            try:
                return self.get_element_info(selector, tab_id)
            except ElementNotFoundError:
                time.sleep(0.1)

        raise ElementNotFoundError(f"Element not found after {timeout}s: {selector}")

    def close(self) -> None:
        """Close Marionette connection."""
        if self._client is not None:
            try:
                self._client.delete_session()
            except Exception:
                pass
            self._client = None


# =============================================================================
# Synchronous wrapper functions for CLI
# =============================================================================


def discover_firefox(host: str = "localhost", port: int = DEFAULT_MARIONETTE_PORT) -> bool:
    """Check if Firefox is running with Marionette enabled (sync).

    Args:
        host: Marionette host.
        port: Marionette port.

    Returns:
        True if Firefox is accessible.
    """
    return MarionetteBackend(host, port).discover()


def get_firefox_tabs(host: str = "localhost", port: int = DEFAULT_MARIONETTE_PORT) -> list[TabInfo]:
    """Get Firefox tabs (sync).

    Args:
        host: Marionette host.
        port: Marionette port.

    Returns:
        List of TabInfo for each tab.
    """
    backend = MarionetteBackend(host, port)
    try:
        return backend.get_tabs()
    finally:
        backend.close()
