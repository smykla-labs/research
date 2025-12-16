"""Command-line interface for Browser Controller."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

import typer

# Skill name for artifact tracking
SKILL_NAME = "browser-controller"

try:
    from _shared.artifacts import (
        ArtifactError,
        get_default_artifact_path,
        save_artifact,
        validate_extension,
    )
    ARTIFACTS_AVAILABLE = True
except ImportError:
    ARTIFACTS_AVAILABLE = False
    from datetime import datetime

    class ArtifactError(Exception):  # type: ignore[no-redef]
        pass

    def get_default_artifact_path(
        _skill_name: str, description: str, ext: str
    ) -> Path:
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        return Path.cwd() / f"{timestamp}-{description}.{ext}"

    def save_artifact(
        source_path, skill_name, description, output_path=None, _allowed_extensions=None
    ):
        # Fallback: just return the source path
        import shutil
        from dataclasses import dataclass

        @dataclass
        class FallbackResult:
            primary_path: Path
            tracking_path: Path
            skill_name: str
            description: str
            timestamp: str
            def to_dict(self):
                return {"primary_path": str(self.primary_path)}

        if output_path:
            resolved = Path(output_path).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, resolved)
            return FallbackResult(resolved, resolved, skill_name, description, "")
        return FallbackResult(
            Path(source_path), Path(source_path), skill_name, description, ""
        )

    def validate_extension(path, _allowed=None):
        ext = Path(path).suffix.lstrip(".")
        if not ext:
            raise ArtifactError(f"Path must have extension: {path}")
        return ext

from .actions import (  # noqa: E402
    activate_tab,
    click,
    close_connection,
    close_tab,
    connect,
    fill,
    list_tabs,
    navigate,
    read_content,
    read_element,
    run_script,
    screenshot,
)
from .backends.cdp import DEFAULT_CDP_PORT  # noqa: E402
from .backends.marionette import DEFAULT_MARIONETTE_PORT  # noqa: E402
from .core import detect_running_browsers, get_browser_launch_command  # noqa: E402
from .models import BrowserError, BrowserType  # noqa: E402

app = typer.Typer(
    name="browser-controller",
    help="Browser Controller - Control Chrome and Firefox via CDP/Marionette.",
)

# Maximum length for displaying process command strings
MAX_COMMAND_DISPLAY_LENGTH = 100


# =============================================================================
# Common type aliases for Typer options
# =============================================================================


BrowserOpt = Annotated[
    str,
    typer.Option(
        "--browser",
        "-b",
        help="Browser type: chrome, firefox, or auto (default: auto)",
    ),
]

ChromePortOpt = Annotated[
    int,
    typer.Option("--chrome-port", help=f"Chrome CDP port (default: {DEFAULT_CDP_PORT})"),
]

FirefoxPortOpt = Annotated[
    int,
    typer.Option("--firefox-port", help=f"Firefox port (default: {DEFAULT_MARIONETTE_PORT})"),
]

TabOpt = Annotated[
    str | None,
    typer.Option("--tab", "-t", help="Target tab ID (uses first tab if not specified)"),
]

JsonOpt = Annotated[
    bool,
    typer.Option("--json", "-j", help="Output as JSON"),
]


# =============================================================================
# Helper functions
# =============================================================================


def _parse_browser_type(browser: str) -> BrowserType:
    """Parse browser type string to enum."""
    browser_lower = browser.lower()

    if browser_lower == "chrome":
        return BrowserType.CHROME
    if browser_lower == "firefox":
        return BrowserType.FIREFOX

    return BrowserType.AUTO


def _print_error(message: str, json_output: bool) -> None:
    """Print error message to stderr."""
    if json_output:
        print(json.dumps({"error": message}), file=sys.stderr)
    else:
        print(f"Error: {message}", file=sys.stderr)


# =============================================================================
# CLI Commands
# =============================================================================


@app.command("check")
def check_cmd(
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    json_output: JsonOpt = False,
) -> None:
    """Check for running browsers with remote debugging."""
    browsers = detect_running_browsers(chrome_port, firefox_port)

    result = {
        "chrome": {
            "available": browsers[BrowserType.CHROME],
            "port": chrome_port,
            "launch_command": get_browser_launch_command(BrowserType.CHROME),
        },
        "firefox": {
            "available": browsers[BrowserType.FIREFOX],
            "port": firefox_port,
            "launch_command": get_browser_launch_command(BrowserType.FIREFOX),
        },
    }

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        print("Browser Status:")
        print("-" * 50)

        for name, info in result.items():
            status = "✅ Available" if info["available"] else "❌ Not running"
            print(f"{name.title()}: {status} (port {info['port']})")

            if not info["available"]:
                print(f"  Launch: {info['launch_command']}")

        print()


@app.command("tabs")
def tabs_cmd(
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    json_output: JsonOpt = False,
) -> None:
    """List all open browser tabs."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        tabs = list_tabs(conn)
        close_connection(conn)

        if json_output:
            print(json.dumps([tab.to_dict() for tab in tabs], indent=2))
        else:
            if not tabs:
                print("No tabs found.")
                return

            print(f"Browser: {conn.browser_type.value}")
            print(f"{'ID':<40} {'Title':<40}")
            print("-" * 80)

            for tab in tabs:
                tab_id = tab.tab_id[:38] if len(tab.tab_id) > 38 else tab.tab_id
                title = tab.title[:38] if len(tab.title) > 38 else tab.title
                print(f"{tab_id:<40} {title:<40}")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("navigate")
def navigate_cmd(  # noqa: PLR0913
    url: Annotated[str, typer.Argument(help="URL to navigate to")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Navigate to URL in browser tab."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        result = navigate(conn, url, tab)
        close_connection(conn)

        if json_output:
            print(json.dumps(result.to_dict(), indent=2))
        elif result.success:
            print(f"Navigated to: {url}")
        else:
            print(f"Navigation failed: {result.error}")
            raise typer.Exit(1)

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("click")
def click_cmd(  # noqa: PLR0913
    selector: Annotated[str, typer.Argument(help="CSS selector for element")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Click an element by CSS selector."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        result = click(conn, selector, tab)
        close_connection(conn)

        if json_output:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Clicked: {selector}")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("fill")
def fill_cmd(  # noqa: PLR0913
    selector: Annotated[str, typer.Argument(help="CSS selector for input element")],
    value: Annotated[str, typer.Argument(help="Value to fill")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Fill a form field with value."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        result = fill(conn, selector, value, tab)
        close_connection(conn)

        if json_output:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Filled {selector} with value")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("read")
def read_cmd(  # noqa: PLR0913
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    text_only: Annotated[bool, typer.Option("--text-only", help="Text only")] = False,
    json_output: JsonOpt = False,
) -> None:
    """Read page content."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        content = read_content(conn, tab)
        close_connection(conn)

        if json_output:
            print(json.dumps(content.to_dict(), indent=2))
        elif text_only:
            print(content.text)
        else:
            print(f"URL: {content.url}")
            print(f"Title: {content.title}")
            print("-" * 50)
            print(content.text[:2000])
            if len(content.text) > 2000:
                print(f"\n... (truncated, {len(content.text)} chars total)")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("element")
def element_cmd(  # noqa: PLR0913
    selector: Annotated[str, typer.Argument(help="CSS selector for element")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Get information about an element."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        element = read_element(conn, selector, tab)
        close_connection(conn)

        if json_output:
            print(json.dumps(element.to_dict(), indent=2))
        else:
            print(f"Tag: {element.tag_name}")
            print(f"Text: {element.text}")
            if element.attributes:
                print("Attributes:")
                for key, val in element.attributes.items():
                    print(f"  {key}: {val}")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("run")
def run_cmd(  # noqa: PLR0913
    script: Annotated[str, typer.Argument(help="JavaScript code to execute")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Execute JavaScript in page context."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        result = run_script(conn, script, tab)
        close_connection(conn)

        if json_output:
            print(json.dumps({"result": result}, indent=2))
        else:
            print(result)

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("screenshot")
def screenshot_cmd(  # noqa: PLR0913
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output path (must have .png extension)"),
    ] = None,
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    full_page: Annotated[bool, typer.Option("--full-page", help="Full page (Chrome)")] = False,
    json_output: JsonOpt = False,
) -> None:
    """Take screenshot of page."""
    try:
        # Validate output extension if provided
        if output is not None:
            try:
                validate_extension(output, ["png"])
            except ArtifactError as e:
                _print_error(str(e), json_output)
                raise typer.Exit(1) from e

        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)

        # Get tab info for description
        tabs = list_tabs(conn)
        target_tab = None
        if tab:
            target_tab = next((t for t in tabs if t.tab_id == tab), None)
        elif tabs:
            target_tab = tabs[0]

        # Generate description from tab info
        if target_tab:
            # Use URL domain or title for description
            url_part = target_tab.url.split("//")[-1].split("/")[0] if target_tab.url else "unknown"
            description = f"screenshot_{url_part}"
        else:
            description = "screenshot_browser"

        # Take screenshot to temp file first
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        screenshot(conn, tmp_path, tab, full_page)
        close_connection(conn)

        # Save artifact with proper tracking
        result = save_artifact(
            source_path=tmp_path,
            skill_name=SKILL_NAME,
            description=description,
            output_path=output,
            allowed_extensions=["png"],
        )

        # Clean up temp file
        tmp_path.unlink(missing_ok=True)

        if json_output:
            output_data = {
                "screenshot": str(result.primary_path),
                "tracking_copy": str(result.tracking_path),
            }
            if target_tab:
                output_data["url"] = target_tab.url
                output_data["title"] = target_tab.title
            print(json.dumps(output_data, indent=2))
        else:
            print(f"Screenshot saved: {result.primary_path}")
            if result.primary_path != result.tracking_path:
                print(f"Tracking copy: {result.tracking_path}")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e
    except ArtifactError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("activate")
def activate_cmd(
    tab_id: Annotated[str, typer.Argument(help="Tab ID to activate")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    json_output: JsonOpt = False,
) -> None:
    """Activate (bring to front) a tab."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        result = activate_tab(conn, tab_id)
        close_connection(conn)

        if json_output:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Activated tab: {tab_id}")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


@app.command("close")
def close_cmd(
    tab_id: Annotated[str, typer.Argument(help="Tab ID to close")],
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    json_output: JsonOpt = False,
) -> None:
    """Close a tab."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        result = close_tab(conn, tab_id)
        close_connection(conn)

        if json_output:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Closed tab: {tab_id}")

    except BrowserError as e:
        _print_error(str(e), json_output)
        raise typer.Exit(1) from e


def _find_debug_browser_processes() -> list[dict]:
    """Find browser processes running with remote debugging enabled.

    Returns:
        List of process info dicts with pid, name, and command.
    """
    processes = []

    # Patterns to match debug-enabled browsers
    patterns = [
        ("Chrome", "remote-debugging-port"),
        ("Chrome", "chrome-debug"),
        ("Chrome", "puppeteer"),
        ("Firefox", "marionette"),
    ]

    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=False,
        )

        for line in result.stdout.splitlines()[1:]:  # Skip header
            try:
                parts = line.split(None, 10)
                if len(parts) < 11:
                    continue

                pid = parts[1]
                command = parts[10]
                command_lower = command.lower()

                for browser_name, pattern in patterns:
                    if pattern in command_lower:
                        # Skip grep itself
                        if "grep" in command:
                            continue

                        # Truncate long commands for display
                        cmd_display = (
                            command[:MAX_COMMAND_DISPLAY_LENGTH] + "..."
                            if len(command) > MAX_COMMAND_DISPLAY_LENGTH
                            else command
                        )
                        processes.append({
                            "pid": int(pid),
                            "browser": browser_name,
                            "pattern": pattern,
                            "command": cmd_display,
                        })
                        break
            except (ValueError, IndexError):
                # Skip lines that don't match expected ps aux format
                continue

    except (subprocess.SubprocessError, OSError):
        pass

    return processes


def _kill_processes(processes: list[dict], verbose: bool = True) -> int:
    """Kill a list of processes by PID.

    Returns:
        Number of successfully killed processes.
    """
    killed = 0

    for proc in processes:
        try:
            subprocess.run(["kill", str(proc["pid"])], check=True, capture_output=True)
            if verbose:
                print(f"Killed PID {proc['pid']}")
            killed += 1
        except subprocess.SubprocessError as e:
            if verbose:
                print(f"Failed to kill PID {proc['pid']}: {e}")

    return killed


def _print_processes(processes: list[dict]) -> None:
    """Print process list in human-readable format."""
    print(f"Found {len(processes)} debug-enabled browser process(es):")
    print("-" * 60)

    for proc in processes:
        print(f"  PID {proc['pid']}: {proc['browser']} ({proc['pattern']})")
        print(f"      {proc['command']}")

    print()


@app.command("cleanup")
def cleanup_cmd(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be killed without killing"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Kill without confirmation"),
    ] = False,
    json_output: JsonOpt = False,
) -> None:
    """Kill orphaned browser processes with remote debugging enabled."""
    processes = _find_debug_browser_processes()

    if not processes:
        if json_output:
            print(json.dumps({"processes": [], "killed": 0}))
        else:
            print("No debug-enabled browser processes found.")
        return

    if json_output:
        if dry_run:
            print(json.dumps({"processes": processes, "dry_run": True}))
            return

        killed = _kill_processes(processes, verbose=False)
        print(json.dumps({"processes": processes, "killed": killed}))
        return

    _print_processes(processes)

    if dry_run:
        print("Dry run - no processes killed.")
        return

    if not force:
        confirm = typer.confirm("Kill these processes?")
        if not confirm:
            print("Aborted.")
            raise typer.Exit(0)

    killed = _kill_processes(processes)

    print(f"\nKilled {killed}/{len(processes)} process(es).")


# Default user data directory for Chrome automation
DEFAULT_CHROME_USER_DATA_DIR = "$HOME/.chrome-debug"
# Startup wait time in seconds
DEFAULT_STARTUP_WAIT = 3


def _wait_for_chrome_startup(port: int, timeout: float = 10.0) -> bool:
    """Wait for Chrome to accept CDP connections.

    Args:
        port: Chrome CDP port to check.
        timeout: Maximum time to wait in seconds.

    Returns:
        True if Chrome is ready, False if timeout reached.
    """
    import time
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/json/version", method="GET")
            urllib.request.urlopen(req, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def _dismiss_chrome_popups() -> list[str]:
    """Dismiss Chrome startup popups using ui-inspector AXPress.

    Attempts to:
    1. Uncheck "Make Google Chrome the default browser" checkbox
    2. Click "Not now" or similar dismiss buttons

    Returns:
        List of actions taken (for logging/display).
    """
    actions_taken = []

    try:
        # Try importing ui-inspector for AXPress
        from ui_inspector.actions import press_element  # type: ignore[import-not-found]
        from ui_inspector.models import ElementNotFoundError  # type: ignore[import-not-found]
    except ImportError:
        return ["ui-inspector not available - skipping popup dismissal"]

    # Known popup elements to dismiss
    dismiss_patterns = [
        # Default browser checkbox
        {"role": "AXCheckBox", "title": "Make Google Chrome the default browser"},
        {"role": "AXCheckBox", "title": "Make Google Chrome your default browser"},
        # Dismiss buttons
        {"role": "AXButton", "title": "Not now"},
        {"role": "AXButton", "title": "Skip"},
        {"role": "AXButton", "title": "No thanks"},
        {"role": "AXButton", "title": "Close"},
    ]

    for pattern in dismiss_patterns:
        try:
            press_element("Google Chrome", **pattern)
            actions_taken.append(f"Pressed: {pattern.get('role')} '{pattern.get('title')}'")
        except (ElementNotFoundError, Exception):
            # Element not present, that's okay
            pass

    return actions_taken


def _print_start_result(result: dict, json_output: bool) -> None:
    """Print start command result in appropriate format."""
    if json_output:
        print(json.dumps(result, indent=2))
        return

    if result.get("success"):
        print(f"Chrome started successfully on port {result['port']}")
        print(f"  User data dir: {result['user_data_dir']}")
        if result.get("popups_dismissed"):
            print("  Popups dismissed:")
            for action in result["popups_dismissed"]:
                print(f"    - {action}")
    elif result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
    else:
        print(f"Warning: Chrome started but not accepting CDP on port {result['port']}")


@app.command("start")
def start_cmd(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help=f"CDP port (default: {DEFAULT_CDP_PORT})"),
    ] = DEFAULT_CDP_PORT,
    user_data_dir: Annotated[
        str,
        typer.Option("--user-data-dir", help="Chrome profile directory"),
    ] = DEFAULT_CHROME_USER_DATA_DIR,
    dismiss_popups: Annotated[
        bool,
        typer.Option("--dismiss-popups", help="Auto-dismiss startup popups"),
    ] = False,
    wait: Annotated[
        float,
        typer.Option("--wait", help="Seconds to wait for startup"),
    ] = DEFAULT_STARTUP_WAIT,
    json_output: JsonOpt = False,
) -> None:
    """Start Chrome with remote debugging (ALWAYS uses --user-data-dir)."""
    import os
    import time

    expanded_user_data_dir = os.path.expandvars(user_data_dir)
    launch_cmd = [
        "open", "-a", "Google Chrome", "--args",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={expanded_user_data_dir}",
    ]

    result: dict = {
        "action": "start",
        "port": port,
        "user_data_dir": expanded_user_data_dir,
        "success": False,
        "popups_dismissed": [],
    }

    try:
        subprocess.run(launch_cmd, capture_output=True, text=True, check=True)
        if not json_output:
            print(f"Launching Chrome on port {port}...")
        time.sleep(wait)

        if _wait_for_chrome_startup(port):
            result["success"] = True
            if dismiss_popups:
                time.sleep(1)
                result["popups_dismissed"] = _dismiss_chrome_popups()
        else:
            result["error"] = "Chrome failed to accept CDP connections"

        _print_start_result(result, json_output)
        if not result["success"]:
            raise typer.Exit(1)

    except subprocess.CalledProcessError as e:
        result["error"] = str(e)
        _print_start_result(result, json_output)
        raise typer.Exit(1) from e


def main(argv: list[str] | None = None) -> int:
    """Main entry point for browser-controller CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["browser-controller", *list(argv)]

    try:
        app(prog_name="browser-controller")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
