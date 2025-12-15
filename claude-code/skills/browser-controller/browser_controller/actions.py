"""High-level browser actions for Browser Controller.

This module provides browser-agnostic operations that work with both
Chrome (CDP) and Firefox (Marionette) backends.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import Any

from .backends.cdp import DEFAULT_CDP_PORT, CDPBackend
from .backends.marionette import DEFAULT_MARIONETTE_PORT, MarionetteBackend
from .core import normalize_url, resolve_browser_type
from .models import (
    ActionResult,
    BrowserConnection,
    BrowserType,
    ConnectionStatus,
    ElementInfo,
    PageContent,
    TabInfo,
)


def connect(
    browser_type: BrowserType = BrowserType.AUTO,
    host: str = "localhost",
    chrome_port: int = DEFAULT_CDP_PORT,
    firefox_port: int = DEFAULT_MARIONETTE_PORT,
) -> BrowserConnection:
    """Connect to a browser with remote debugging enabled.

    Args:
        browser_type: Browser type (CHROME, FIREFOX, or AUTO).
        host: Remote debugging host.
        chrome_port: Chrome CDP port.
        firefox_port: Firefox Marionette port.

    Returns:
        BrowserConnection with tabs and backend handle.

    Raises:
        BrowserNotFoundError: If browser is not available.
    """
    resolved_type = resolve_browser_type(browser_type, chrome_port, firefox_port)

    if resolved_type == BrowserType.CHROME:
        backend = CDPBackend(host, chrome_port)
        tabs = backend.get_targets()
        return BrowserConnection(
            browser_type=BrowserType.CHROME,
            endpoint=backend.endpoint,
            status=ConnectionStatus.CONNECTED,
            tabs=tuple(tabs),
            _handle=backend,
        )

    # Firefox
    backend = MarionetteBackend(host, firefox_port)
    backend.connect()
    tabs = backend.get_tabs()
    return BrowserConnection(
        browser_type=BrowserType.FIREFOX,
        endpoint=backend.endpoint,
        status=ConnectionStatus.CONNECTED,
        tabs=tuple(tabs),
        _handle=backend,
    )


def refresh_tabs(connection: BrowserConnection) -> BrowserConnection:
    """Refresh the list of tabs for a connection.

    Args:
        connection: Browser connection.

    Returns:
        Updated BrowserConnection with current tabs.
    """
    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        tabs = backend.get_targets()
    else:
        backend_m: MarionetteBackend = connection._handle
        tabs = backend_m.get_tabs()

    return replace(connection, tabs=tuple(tabs))


def list_tabs(connection: BrowserConnection) -> tuple[TabInfo, ...]:
    """List all open tabs.

    Args:
        connection: Browser connection.

    Returns:
        Tuple of TabInfo for each tab.
    """
    return refresh_tabs(connection).tabs


def get_first_tab_id(connection: BrowserConnection) -> str:
    """Get the first tab ID from connection.

    Args:
        connection: Browser connection.

    Returns:
        First tab ID.

    Raises:
        ValueError: If no tabs available.
    """
    if not connection.tabs:
        raise ValueError("No tabs available in browser")
    return connection.tabs[0].tab_id


def navigate(
    connection: BrowserConnection,
    url: str,
    tab_id: str | None = None,
) -> ActionResult:
    """Navigate to URL in browser tab.

    Args:
        connection: Browser connection.
        url: URL to navigate to.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        ActionResult indicating success.
    """
    url = normalize_url(url)
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.navigate_to(tab_id, url))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.navigate_to(url, tab_id)


def click(
    connection: BrowserConnection,
    selector: str,
    tab_id: str | None = None,
) -> ActionResult:
    """Click an element.

    Args:
        connection: Browser connection.
        selector: CSS selector for element.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        ActionResult indicating success.
    """
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.click_element(tab_id, selector))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.click_element(selector, tab_id)


def fill(
    connection: BrowserConnection,
    selector: str,
    value: str,
    tab_id: str | None = None,
) -> ActionResult:
    """Fill a form field.

    Args:
        connection: Browser connection.
        selector: CSS selector for input element.
        value: Value to fill.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        ActionResult indicating success.
    """
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.fill_form(tab_id, selector, value))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.fill_form(selector, value, tab_id)


def read_content(
    connection: BrowserConnection,
    tab_id: str | None = None,
) -> PageContent:
    """Read page content (HTML and text).

    Args:
        connection: Browser connection.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        PageContent with URL, title, HTML, and text.
    """
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.get_page_content(tab_id))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.get_page_content(tab_id)


def read_element(
    connection: BrowserConnection,
    selector: str,
    tab_id: str | None = None,
) -> ElementInfo:
    """Read information about an element.

    Args:
        connection: Browser connection.
        selector: CSS selector for element.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        ElementInfo with tag, text, and attributes.
    """
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.get_element_info(tab_id, selector))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.get_element_info(selector, tab_id)


def run_script(
    connection: BrowserConnection,
    script: str,
    tab_id: str | None = None,
) -> Any:
    """Execute JavaScript in page context.

    Args:
        connection: Browser connection.
        script: JavaScript code to execute.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        Script result value.
    """
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.execute_script(tab_id, script))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.execute_script(script, tab_id)


def activate_tab(connection: BrowserConnection, tab_id: str) -> ActionResult:
    """Activate (bring to front) a tab.

    Args:
        connection: Browser connection.
        tab_id: Target tab ID.

    Returns:
        ActionResult indicating success.
    """
    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.activate_tab(tab_id))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.activate_tab(tab_id)


def close_tab(connection: BrowserConnection, tab_id: str) -> ActionResult:
    """Close a tab.

    Args:
        connection: Browser connection.
        tab_id: Target tab ID.

    Returns:
        ActionResult indicating success.
    """
    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.close_tab(tab_id))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.close_tab(tab_id)


def screenshot(
    connection: BrowserConnection,
    output_path: str | Path,
    tab_id: str | None = None,
    full_page: bool = False,
) -> Path:
    """Take screenshot of page.

    Args:
        connection: Browser connection.
        output_path: Path to save screenshot.
        tab_id: Target tab ID (uses first tab if None).
        full_page: Capture full page (Chrome only).

    Returns:
        Path to saved screenshot.
    """
    tab_id = tab_id or get_first_tab_id(connection)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        png_data = asyncio.run(backend.take_screenshot(tab_id, full_page=full_page))
        with output_path.open("wb") as f:
            f.write(png_data)
        return output_path

    backend_m: MarionetteBackend = connection._handle
    return backend_m.take_screenshot(output_path, tab_id)


def wait_for_element(
    connection: BrowserConnection,
    selector: str,
    timeout: float = 10.0,
    tab_id: str | None = None,
) -> ElementInfo:
    """Wait for element to appear on page.

    Args:
        connection: Browser connection.
        selector: CSS selector for element.
        timeout: Maximum wait time in seconds.
        tab_id: Target tab ID (uses first tab if None).

    Returns:
        ElementInfo when element appears.

    Raises:
        ElementNotFoundError: If element not found within timeout.
    """
    tab_id = tab_id or get_first_tab_id(connection)

    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        return asyncio.run(backend.wait_for_element(tab_id, selector, timeout))

    backend_m: MarionetteBackend = connection._handle
    return backend_m.wait_for_element(selector, timeout, tab_id)


def close_connection(connection: BrowserConnection) -> None:
    """Close browser connection.

    Args:
        connection: Browser connection to close.
    """
    if connection.browser_type == BrowserType.CHROME:
        backend: CDPBackend = connection._handle
        asyncio.run(backend.close())
    else:
        backend_m: MarionetteBackend = connection._handle
        backend_m.close()
