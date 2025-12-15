"""Core browser detection and utilities for Browser Controller."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .backends.cdp import DEFAULT_CDP_PORT, discover_chrome
from .backends.marionette import DEFAULT_MARIONETTE_PORT, discover_firefox
from .models import BrowserNotFoundError, BrowserType


def detect_running_browsers(
    chrome_port: int = DEFAULT_CDP_PORT,
    firefox_port: int = DEFAULT_MARIONETTE_PORT,
) -> dict[BrowserType, bool]:
    """Detect which browsers are running with remote debugging enabled.

    Args:
        chrome_port: Port to check for Chrome CDP.
        firefox_port: Port to check for Firefox Marionette.

    Returns:
        Dictionary mapping BrowserType to availability status.
    """
    return {
        BrowserType.CHROME: discover_chrome(port=chrome_port),
        BrowserType.FIREFOX: discover_firefox(port=firefox_port),
    }


def find_available_browser(
    chrome_port: int = DEFAULT_CDP_PORT,
    firefox_port: int = DEFAULT_MARIONETTE_PORT,
) -> BrowserType:
    """Find first available browser with remote debugging.

    Checks Chrome first, then Firefox.

    Args:
        chrome_port: Port to check for Chrome CDP.
        firefox_port: Port to check for Firefox Marionette.

    Returns:
        BrowserType of available browser.

    Raises:
        BrowserNotFoundError: If no browser is available.
    """
    browsers = detect_running_browsers(chrome_port, firefox_port)

    if browsers[BrowserType.CHROME]:
        return BrowserType.CHROME

    if browsers[BrowserType.FIREFOX]:
        return BrowserType.FIREFOX

    raise BrowserNotFoundError(
        "No browser found with remote debugging enabled.\n"
        f"Start Chrome with: --remote-debugging-port={chrome_port}\n"
        f"Start Firefox with: --marionette (port {firefox_port})"
    )


def resolve_browser_type(
    browser_type: BrowserType,
    chrome_port: int = DEFAULT_CDP_PORT,
    firefox_port: int = DEFAULT_MARIONETTE_PORT,
) -> BrowserType:
    """Resolve AUTO browser type to actual type.

    Args:
        browser_type: Requested browser type (may be AUTO).
        chrome_port: Port for Chrome CDP.
        firefox_port: Port for Firefox Marionette.

    Returns:
        Resolved BrowserType (CHROME or FIREFOX).

    Raises:
        BrowserNotFoundError: If AUTO and no browser available.
    """
    if browser_type == BrowserType.AUTO:
        return find_available_browser(chrome_port, firefox_port)
    return browser_type


def validate_url(url: str) -> bool:
    """Validate URL format.

    Args:
        url: URL to validate.

    Returns:
        True if URL is valid.
    """
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize URL by adding scheme if missing.

    Args:
        url: URL to normalize.

    Returns:
        Normalized URL with scheme.
    """
    if not url:
        return url

    # Check if scheme is present
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return f"https://{url}"

    return url


def parse_selector(selector: str) -> tuple[str, str]:
    """Parse selector string into type and value.

    Supports:
    - CSS selector (default): "div.class", "#id"
    - XPath: "xpath://div[@class='foo']"
    - ID shorthand: "id:element-id"
    - Class shorthand: "class:element-class"

    Args:
        selector: Selector string.

    Returns:
        Tuple of (selector_type, selector_value).
    """
    # Check for explicit type prefix
    if selector.startswith("xpath:"):
        return ("xpath", selector[6:])

    if selector.startswith("id:"):
        return ("css", f"#{selector[3:]}")

    if selector.startswith("class:"):
        return ("css", f".{selector[6:]}")

    if selector.startswith("css:"):
        return ("css", selector[4:])

    # Default to CSS selector
    return ("css", selector)


def get_browser_launch_command(browser_type: BrowserType) -> str:
    """Get command to launch browser with remote debugging.

    Args:
        browser_type: Browser type.

    Returns:
        Shell command to launch browser.
    """
    if browser_type == BrowserType.CHROME:
        return (
            "/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome "
            f"--remote-debugging-port={DEFAULT_CDP_PORT}"
        )

    if browser_type == BrowserType.FIREFOX:
        return "/Applications/Firefox.app/Contents/MacOS/firefox --marionette"

    return ""
