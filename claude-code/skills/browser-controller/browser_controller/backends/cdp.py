"""Chrome DevTools Protocol (CDP) backend for Chrome browser control.

This module provides connection to Chrome/Chromium browsers running with
remote debugging enabled (--remote-debugging-port=9222).

Key capabilities:
- Tab listing and management
- Page navigation
- DOM element interaction (click, fill)
- JavaScript execution
- Screenshots

Requirements:
- Chrome started with --remote-debugging-port=9222
"""

from __future__ import annotations

import asyncio
import base64
import functools
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.request import urlopen

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

DEFAULT_CDP_PORT = 9222


def _create_js_wrapper(
    selector_json: str,
    action_code: str,
    return_props: str = "tagName: el.tagName",
) -> str:
    """Create a JavaScript wrapper for element operations with consistent error handling.

    Args:
        selector_json: JSON-encoded selector string.
        action_code: JavaScript code to execute on the element.
        return_props: Properties to return on success (default: tagName).

    Returns:
        Complete JavaScript function as a string.
    """
    return f"""
    (function() {{
        const el = document.querySelector({selector_json});
        if (!el) return {{success: false, error: 'Element not found'}};
        {action_code}
        return {{success: true, {return_props}}};
    }})()
    """


@functools.cache
def _get_websockets():
    """Lazy load websockets library (cached)."""
    import websockets

    return websockets


@dataclass
class CDPConnection:
    """WebSocket connection to a CDP target."""

    ws: Any  # websockets.WebSocketClientProtocol
    target_id: str
    _message_id: int = field(default=0, repr=False)

    def next_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id


class CDPBackend:
    """Chrome DevTools Protocol backend.

    Provides low-level CDP operations for Chrome browser control.
    """

    def __init__(self, host: str = "localhost", port: int = DEFAULT_CDP_PORT) -> None:
        """Initialize CDP backend.

        Args:
            host: Chrome remote debugging host.
            port: Chrome remote debugging port.
        """
        self.host = host
        self.port = port
        self._connections: dict[str, CDPConnection] = {}

    @property
    def endpoint(self) -> str:
        """Get CDP HTTP endpoint URL."""
        return f"http://{self.host}:{self.port}"

    def discover(self) -> bool:
        """Check if Chrome is running with remote debugging.

        Returns:
            True if Chrome with remote debugging is accessible.
        """
        try:
            with urlopen(f"{self.endpoint}/json/version", timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def get_version(self) -> dict[str, Any]:
        """Get Chrome version info.

        Returns:
            Version info dictionary.

        Raises:
            BrowserNotFoundError: If Chrome is not accessible.
        """
        try:
            with urlopen(f"{self.endpoint}/json/version", timeout=5) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            raise BrowserNotFoundError(
                f"Chrome not found at {self.endpoint}. "
                f"Start Chrome with --remote-debugging-port={self.port}"
            ) from e

    def get_targets(self) -> list[TabInfo]:
        """Get all browser targets (tabs).

        Returns:
            List of TabInfo for each open tab.

        Raises:
            BrowserConnectionError: If request fails.
        """
        try:
            with urlopen(f"{self.endpoint}/json/list", timeout=5) as response:
                targets = json.loads(response.read().decode())
        except Exception as e:
            raise BrowserConnectionError(f"Failed to get targets: {e}") from e

        tabs = []
        for target in targets:
            if target.get("type") == "page":
                tabs.append(
                    TabInfo(
                        tab_id=target["id"],
                        url=target.get("url", ""),
                        title=target.get("title", ""),
                        browser_type=BrowserType.CHROME,
                        active=False,
                    )
                )
        return tabs

    async def connect_to_target(self, target_id: str) -> CDPConnection:
        """Connect to a specific target via WebSocket.

        Args:
            target_id: CDP target ID.

        Returns:
            CDPConnection for the target.

        Raises:
            BrowserConnectionError: If connection fails.
        """
        if target_id in self._connections:
            return self._connections[target_id]

        websockets = _get_websockets()
        ws_url = f"ws://{self.host}:{self.port}/devtools/page/{target_id}"

        try:
            ws = await websockets.connect(ws_url)
            conn = CDPConnection(ws=ws, target_id=target_id)
            self._connections[target_id] = conn
            return conn
        except Exception as e:
            raise BrowserConnectionError(f"Failed to connect to target {target_id}: {e}") from e

    async def send_command(
        self,
        conn: CDPConnection,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a CDP command and wait for response.

        Args:
            conn: CDP connection.
            method: CDP method name.
            params: Method parameters.

        Returns:
            Command result.

        Raises:
            BrowserConnectionError: If command fails.
        """
        msg_id = conn.next_id()
        message: dict[str, Any] = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        await conn.ws.send(json.dumps(message))

        RESPONSE_TIMEOUT = 10
        iteration_count = 0
        MAX_ITERATIONS = 1000

        while iteration_count < MAX_ITERATIONS:
            try:
                response_text = await asyncio.wait_for(conn.ws.recv(), timeout=RESPONSE_TIMEOUT)
            except TimeoutError as e:
                raise BrowserConnectionError(
                    f"Timed out waiting for response to command '{method}' (id={msg_id}) "
                    f"after {RESPONSE_TIMEOUT} seconds"
                ) from e

            response = json.loads(response_text)
            if response.get("id") == msg_id:
                if "error" in response:
                    error_msg = response["error"].get("message", str(response["error"]))
                    raise BrowserConnectionError(f"CDP error: {error_msg}")
                return response.get("result", {})

            iteration_count += 1

        raise BrowserConnectionError(
            f"Exceeded maximum iterations ({MAX_ITERATIONS}) waiting for response to "
            f"command '{method}' (id={msg_id})"
        )

    async def navigate_to(self, target_id: str, url: str) -> ActionResult:
        """Navigate tab to URL.

        Args:
            target_id: Target tab ID.
            url: URL to navigate to.

        Returns:
            ActionResult indicating success/failure.

        Raises:
            NavigationError: If navigation fails.
        """
        conn = await self.connect_to_target(target_id)

        try:
            result = await self.send_command(conn, "Page.navigate", {"url": url})

            if "errorText" in result:
                return ActionResult(
                    success=False,
                    action="navigate",
                    error=result["errorText"],
                    details={"url": url, "target_id": target_id},
                )

            return ActionResult(
                success=True,
                action="navigate",
                details={"url": url, "target_id": target_id, "frame_id": result.get("frameId")},
            )
        except BrowserConnectionError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

    async def get_page_content(self, target_id: str) -> PageContent:
        """Get page content (HTML and text).

        Args:
            target_id: Target tab ID.

        Returns:
            PageContent with HTML and text.
        """
        conn = await self.connect_to_target(target_id)

        # Get document HTML
        html_result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": "document.documentElement.outerHTML", "returnByValue": True},
        )
        html = html_result.get("result", {}).get("value", "")

        # Get page text
        text_result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": "document.body.innerText", "returnByValue": True},
        )
        text = text_result.get("result", {}).get("value", "")

        # Get title
        title_result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": "document.title", "returnByValue": True},
        )
        title = title_result.get("result", {}).get("value", "")

        # Get URL
        url_result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": "window.location.href", "returnByValue": True},
        )
        url = url_result.get("result", {}).get("value", "")

        return PageContent(url=url, title=title, html=html, text=text)

    async def click_element(self, target_id: str, selector: str) -> ActionResult:
        """Click an element by CSS selector.

        Args:
            target_id: Target tab ID.
            selector: CSS selector for element.

        Returns:
            ActionResult indicating success.

        Raises:
            ElementNotFoundError: If element not found.
        """
        conn = await self.connect_to_target(target_id)

        script = _create_js_wrapper(json.dumps(selector), "el.click();")
        result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": script, "returnByValue": True},
        )
        value = result.get("result", {}).get("value", {})

        if not value.get("success"):
            raise ElementNotFoundError(f"Element not found: {selector}")

        return ActionResult(
            success=True,
            action="click",
            details={"selector": selector, "tag_name": value.get("tagName")},
        )

    async def fill_form(self, target_id: str, selector: str, value: str) -> ActionResult:
        """Fill a form field with value.

        Args:
            target_id: Target tab ID.
            selector: CSS selector for input element.
            value: Value to fill.

        Returns:
            ActionResult indicating success.

        Raises:
            ElementNotFoundError: If element not found.
        """
        conn = await self.connect_to_target(target_id)

        action_code = f"""el.focus();
            el.value = {json.dumps(value)};
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));"""
        script = _create_js_wrapper(json.dumps(selector), action_code)
        result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": script, "returnByValue": True},
        )
        result_value = result.get("result", {}).get("value", {})

        if not result_value.get("success"):
            raise ElementNotFoundError(f"Element not found: {selector}")

        return ActionResult(
            success=True,
            action="fill",
            details={"selector": selector, "value": value, "tag_name": result_value.get("tagName")},
        )

    async def get_element_info(self, target_id: str, selector: str) -> ElementInfo:
        """Get information about an element.

        Args:
            target_id: Target tab ID.
            selector: CSS selector for element.

        Returns:
            ElementInfo with tag, text, and attributes.

        Raises:
            ElementNotFoundError: If element not found.
        """
        conn = await self.connect_to_target(target_id)

        script = f"""
        (function() {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return null;
            const attrs = {{}};
            for (const attr of el.attributes) {{
                attrs[attr.name] = attr.value;
            }}
            return {{
                tagName: el.tagName.toLowerCase(),
                text: el.innerText || el.textContent,
                attributes: attrs
            }};
        }})()
        """
        result = await self.send_command(
            conn,
            "Runtime.evaluate",
            {"expression": script, "returnByValue": True},
        )
        value = result.get("result", {}).get("value")

        if not value:
            raise ElementNotFoundError(f"Element not found: {selector}")

        return ElementInfo(
            selector=selector,
            tag_name=value["tagName"],
            text=value.get("text"),
            attributes=value.get("attributes", {}),
        )

    async def execute_script(self, target_id: str, script: str) -> Any:
        """Execute JavaScript in page context.

        Args:
            target_id: Target tab ID.
            script: JavaScript code to execute.

        Returns:
            Script result value.

        Raises:
            ScriptExecutionError: If script fails.
        """
        conn = await self.connect_to_target(target_id)

        try:
            result = await self.send_command(
                conn,
                "Runtime.evaluate",
                {"expression": script, "returnByValue": True},
            )

            if "exceptionDetails" in result:
                exc = result["exceptionDetails"]
                error_text = exc.get("text", exc.get("exception", {}).get("description", str(exc)))
                raise ScriptExecutionError(f"Script error: {error_text}")

            return result.get("result", {}).get("value")
        except ScriptExecutionError:
            raise
        except Exception as e:
            raise ScriptExecutionError(f"Failed to execute script: {e}") from e

    async def activate_tab(self, target_id: str) -> ActionResult:
        """Activate (bring to front) a tab.

        Args:
            target_id: Target tab ID.

        Returns:
            ActionResult indicating success.

        Raises:
            TabNotFoundError: If tab not found.
        """
        try:
            with urlopen(f"{self.endpoint}/json/activate/{target_id}", timeout=5) as response:
                if response.status == 200:
                    return ActionResult(
                        success=True,
                        action="activate",
                        details={"target_id": target_id},
                    )
                return ActionResult(
                    success=False,
                    action="activate",
                    error=f"HTTP {response.status}",
                    details={"target_id": target_id},
                )
        except Exception as e:
            raise TabNotFoundError(f"Failed to activate tab {target_id}: {e}") from e

    async def close_tab(self, target_id: str) -> ActionResult:
        """Close a tab.

        Args:
            target_id: Target tab ID.

        Returns:
            ActionResult indicating success.

        Raises:
            TabNotFoundError: If tab not found.
        """
        try:
            with urlopen(f"{self.endpoint}/json/close/{target_id}", timeout=5) as response:
                if response.status == 200:
                    self._connections.pop(target_id, None)
                    return ActionResult(
                        success=True,
                        action="close",
                        details={"target_id": target_id},
                    )
                return ActionResult(
                    success=False,
                    action="close",
                    error=f"HTTP {response.status}",
                    details={"target_id": target_id},
                )
        except Exception as e:
            raise TabNotFoundError(f"Failed to close tab {target_id}: {e}") from e

    async def take_screenshot(self, target_id: str, *, full_page: bool = False) -> bytes:
        """Take screenshot of page.

        Args:
            target_id: Target tab ID.
            full_page: Capture full page (not just viewport).

        Returns:
            PNG image bytes.
        """
        conn = await self.connect_to_target(target_id)

        params: dict[str, Any] = {"format": "png"}

        if full_page:
            metrics = await self.send_command(conn, "Page.getLayoutMetrics")
            content_size = metrics.get("contentSize", {})
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": content_size.get("width", 1920),
                "height": content_size.get("height", 1080),
                "scale": 1,
            }
            params["captureBeyondViewport"] = True

        result = await self.send_command(conn, "Page.captureScreenshot", params)
        return base64.b64decode(result["data"])

    async def wait_for_element(
        self,
        target_id: str,
        selector: str,
        timeout: float = 10.0,
    ) -> ElementInfo:
        """Wait for element to appear on page.

        Args:
            target_id: Target tab ID.
            selector: CSS selector for element.
            timeout: Maximum wait time in seconds.

        Returns:
            ElementInfo when element appears.

        Raises:
            ElementNotFoundError: If element not found within timeout.
        """
        import time

        start = time.monotonic()

        while time.monotonic() - start < timeout:
            try:
                return await self.get_element_info(target_id, selector)
            except ElementNotFoundError:
                await asyncio.sleep(0.1)

        raise ElementNotFoundError(f"Element not found after {timeout}s: {selector}")

    async def close(self) -> None:
        """Close all WebSocket connections."""
        for conn in self._connections.values():
            try:
                await conn.ws.close()
            except Exception:
                pass
        self._connections.clear()


# =============================================================================
# Synchronous wrapper functions for CLI
# =============================================================================


def discover_chrome(host: str = "localhost", port: int = DEFAULT_CDP_PORT) -> bool:
    """Check if Chrome is running with remote debugging (sync).

    Args:
        host: Chrome remote debugging host.
        port: Chrome remote debugging port.

    Returns:
        True if Chrome is accessible.
    """
    return CDPBackend(host, port).discover()


def get_chrome_tabs(host: str = "localhost", port: int = DEFAULT_CDP_PORT) -> list[TabInfo]:
    """Get Chrome tabs (sync).

    Args:
        host: Chrome remote debugging host.
        port: Chrome remote debugging port.

    Returns:
        List of TabInfo for each tab.
    """
    return CDPBackend(host, port).get_targets()
