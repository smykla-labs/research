"""Command-line interface for Browser Controller."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Annotated

import typer

from .actions import (
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
from .backends.cdp import DEFAULT_CDP_PORT
from .backends.marionette import DEFAULT_MARIONETTE_PORT
from .core import detect_running_browsers, get_browser_launch_command
from .models import BrowserError, BrowserType

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
    output: Annotated[str, typer.Option("--output", "-o", help="Output path")] = "screenshot.png",
    browser: BrowserOpt = "auto",
    chrome_port: ChromePortOpt = DEFAULT_CDP_PORT,
    firefox_port: FirefoxPortOpt = DEFAULT_MARIONETTE_PORT,
    tab: TabOpt = None,
    full_page: Annotated[bool, typer.Option("--full-page", help="Full page (Chrome)")] = False,
    json_output: JsonOpt = False,
) -> None:
    """Take screenshot of page."""
    try:
        browser_type = _parse_browser_type(browser)
        conn = connect(browser_type, chrome_port=chrome_port, firefox_port=firefox_port)
        path = screenshot(conn, output, tab, full_page)
        close_connection(conn)

        if json_output:
            print(json.dumps({"screenshot": str(path)}, indent=2))
        else:
            print(f"Screenshot saved: {path}")

    except BrowserError as e:
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
