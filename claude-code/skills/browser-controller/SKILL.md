---
name: browser-controller
description: Programmatic control of Chrome and Firefox browsers via CDP (Chrome DevTools Protocol) and Marionette. Connect to running browser instances for tab management, navigation, DOM interaction, form filling, JavaScript execution, and screenshots. Useful for browser automation, web scraping, and testing.
---

# Browser Controller

Programmatic control of Chrome and Firefox browsers via CDP (Chrome DevTools Protocol) and Marionette protocols. Connect to already-running browser instances with remote debugging enabled.

## Quick Start

### Prerequisites

Start your browser with remote debugging enabled.

**CRITICAL: Chrome REQUIRES `--user-data-dir`**

When starting Chrome for automation, you MUST always use `--user-data-dir`:

```bash
open -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug"
```

This flag is **mandatory** because:

1. Chrome may fail to accept `--remote-debugging-port` without a separate profile
2. It prevents interference with your normal Chrome session
3. It ensures a clean, predictable automation environment

**IMPORTANT (macOS):** Use `open -a` instead of direct binary paths. This ensures screen recording permissions are attributed to Chrome/Firefox rather than your terminal app, avoiding the persistent "Currently Sharing" indicator.

**Chrome:**

```bash
# macOS - REQUIRED: Always use --user-data-dir with remote debugging
open -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug"

# Alternative: Direct binary (NOT recommended - causes screen sharing indicator)
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-debug"
```

**Firefox:**

```bash
# macOS - RECOMMENDED: Launch via LaunchServices
open -a Firefox --args --marionette

# Alternative: Direct binary (NOT recommended)
# /Applications/Firefox.app/Contents/MacOS/firefox --marionette
```

### Basic Commands

```bash
# Check for running browsers
claude-code-skills browser-controller check

# List all open tabs
claude-code-skills browser-controller tabs

# Navigate to URL
claude-code-skills browser-controller navigate "https://example.com"

# Click an element
claude-code-skills browser-controller click "#submit-btn"

# Fill a form field
claude-code-skills browser-controller fill "#email" "test@example.com"

# Read page content
claude-code-skills browser-controller read

# Execute JavaScript
claude-code-skills browser-controller run "document.title"

# Take screenshot (saves to claude-code/artifacts/ by default)
claude-code-skills browser-controller screenshot
```

## Command Reference

### check

Check for browsers running with remote debugging:

```bash
browser-controller check
browser-controller check --json
```

Output shows which browsers are available and how to launch them.

### tabs

List all open tabs:

```bash
browser-controller tabs
browser-controller tabs --browser chrome
browser-controller tabs --json
```

### navigate

Navigate to a URL:

```bash
browser-controller navigate "https://example.com"
browser-controller navigate "example.com"  # https:// added automatically
browser-controller navigate "https://example.com" --tab TAB_ID
```

### click

Click an element by CSS selector:

```bash
browser-controller click "#submit-btn"
browser-controller click ".my-class button"
browser-controller click "[data-testid='login']"
```

### fill

Fill a form field:

```bash
browser-controller fill "#email" "test@example.com"
browser-controller fill "input[name='password']" "secret123"
```

### read

Read page content:

```bash
browser-controller read                  # Show URL, title, and text
browser-controller read --text-only      # Text content only
browser-controller read --json           # Full content as JSON
```

### element

Get information about an element:

```bash
browser-controller element "#submit"
browser-controller element "input[name='email']" --json
```

### run

Execute JavaScript:

```bash
browser-controller run "document.title"
browser-controller run "document.querySelectorAll('a').length"
browser-controller run "window.scrollTo(0, document.body.scrollHeight)"
```

### screenshot

Take a screenshot:

```bash
browser-controller screenshot -o screenshot.png
browser-controller screenshot -o fullpage.png --full-page  # Chrome only
```

### activate

Activate (bring to front) a tab:

```bash
browser-controller activate TAB_ID
```

### close

Close a tab:

```bash
browser-controller close TAB_ID
```

### cleanup

Kill orphaned browser processes with remote debugging:

```bash
claude-code-skills browser-controller cleanup              # With confirmation
claude-code-skills browser-controller cleanup --dry-run    # Show without killing
claude-code-skills browser-controller cleanup --force      # No confirmation
```

### start

Start Chrome with remote debugging (always uses `--user-data-dir`):

```bash
# Basic start (port 9222, ~/.chrome-debug profile)
claude-code-skills browser-controller start

# Custom port
claude-code-skills browser-controller start --port 9223

# Auto-dismiss startup popups (uses ui-inspector AXPress)
claude-code-skills browser-controller start --dismiss-popups

# JSON output
claude-code-skills browser-controller start --json
```

The `start` command always includes `--user-data-dir` to ensure a clean automation environment.

## Common Options

| Option | Description |
|--------|-------------|
| `--browser`, `-b` | Browser type: `chrome`, `firefox`, or `auto` (default) |
| `--chrome-port` | Chrome CDP port (default: 9222) |
| `--firefox-port` | Firefox Marionette port (default: 2828) |
| `--tab`, `-t` | Target tab ID (uses first tab if not specified) |
| `--json`, `-j` | Output as JSON |

## Resource Cleanup

**IMPORTANT:** Always clean up browser resources after use unless the user explicitly requests otherwise.

### cleanup Command

Use the built-in `cleanup` command to find and kill orphaned browser processes:

```bash
# Show what would be killed (dry run)
browser-controller cleanup --dry-run

# Kill with confirmation prompt
browser-controller cleanup

# Kill without confirmation
browser-controller cleanup --force

# JSON output for scripting
browser-controller cleanup --json
```

The cleanup command finds processes matching:

- Chrome with `--remote-debugging-port`
- Chrome with debug user-data-dir patterns (`chrome-debug`, `puppeteer`)
- Firefox with `--marionette`

### Connection Cleanup

The CLI automatically closes connections after each command. For Python API usage, always call `close_connection()`:

```python
from browser_controller import connect, navigate, close_connection

conn = connect()
try:
    navigate(conn, "https://example.com")
finally:
    close_connection(conn)
```

### Screen Sharing Indicator (macOS)

If you see "Currently Sharing" in the macOS menu bar after using this skill:

**Why it happens:** When launching Chrome/Firefox directly via the binary path from a terminal, macOS attributes screen recording permissions to the terminal app (Ghostty, iTerm, etc.) rather than the browser. The indicator persists even after the browser quits.

**Fix:** Always use `open -a` to launch browsers (see Prerequisites). This uses macOS LaunchServices which properly attributes permissions to the browser.

**If already stuck:**

1. Restart your terminal app (Ghostty, iTerm, etc.)
2. Or: System Settings → Privacy & Security → Screen Recording → Toggle off/on for terminal app
3. Run `cleanup --force` to ensure no debug browsers are running

## How It Works

### Chrome (CDP)

Chrome DevTools Protocol uses WebSocket communication:

1. **Discovery**: HTTP request to `http://localhost:9222/json/list` returns available targets
2. **Connection**: WebSocket connects to `ws://localhost:9222/devtools/page/{targetId}`
3. **Commands**: JSON-RPC messages for navigation, evaluation, etc.

Key CDP domains used:

- `Page`: Navigation, screenshots
- `Runtime`: JavaScript evaluation
- `DOM`: Element queries (via JavaScript)

### Firefox (Marionette)

Marionette is Firefox's remote control protocol:

1. **Discovery**: TCP connection to port 2828
2. **Session**: Create session to start controlling browser
3. **Commands**: Protocol-specific commands similar to WebDriver

## Selector Types

CSS selectors are supported by default:

```bash
browser-controller click "#id"
browser-controller click ".class"
browser-controller click "button[type='submit']"
browser-controller click "div.container > form input"
```

Shorthand prefixes:

```bash
browser-controller click "id:element-id"     # Same as #element-id
browser-controller click "class:my-class"    # Same as .my-class
browser-controller click "css:.explicit"     # Explicit CSS
```

## JSON Output

Use `--json` for machine-readable output:

```bash
browser-controller tabs --json
```

```json
[
  {
    "tab_id": "ABC123",
    "url": "https://example.com",
    "title": "Example Domain",
    "browser_type": "chrome",
    "active": true
  }
]
```

```bash
browser-controller read --json
```

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "html": "<html>...</html>",
  "text": "Example Domain..."
}
```

## Python API

For programmatic use:

```python
from browser_controller import connect, navigate, click, fill, read_content

# Connect to browser
conn = connect()  # Auto-detect browser
# conn = connect(BrowserType.CHROME)  # Specific browser

# Navigate
navigate(conn, "https://example.com")

# Interact with page
fill(conn, "#email", "test@example.com")
fill(conn, "#password", "secret")
click(conn, "#login-btn")

# Read content
content = read_content(conn)
print(content.title)
print(content.text)

# Clean up
close_connection(conn)
```

## Troubleshooting

### "No browser found"

1. Verify browser is running with remote debugging:

   ```bash
   # Check Chrome
   curl http://localhost:9222/json/version

   # Check Firefox (should connect)
   nc -z localhost 2828
   ```

2. Start browser with correct flags (see Prerequisites)

### "Connection refused"

Port might already be in use or browser not started correctly:

```bash
# Check what's using the port
lsof -i :9222
lsof -i :2828
```

### "Element not found"

1. Verify selector in browser DevTools (F12 → Console):

   ```javascript
   document.querySelector("#my-element")
   ```

2. Wait for page load:

   ```bash
   # Use wait_for_element in Python API
   wait_for_element(conn, "#my-element", timeout=10)
   ```

3. Check if element is in iframe (not supported yet)

### Chrome tabs not listing

Ensure Chrome was started with `--remote-debugging-port=9222` flag. Tabs opened before enabling remote debugging may not appear.

### Firefox session issues

Marionette creates a new session each time. If you see "Session already started" errors, restart Firefox.

## Limitations

- **Iframes**: Cross-origin iframes not directly accessible
- **File dialogs**: Native OS dialogs cannot be controlled
- **Browser extensions**: May interfere with automation
- **Firefox multi-tab**: Marionette operates on one window at a time
- **Authentication**: Basic auth popups not supported

## Technical References

- [Chrome DevTools Protocol Documentation](https://chromedevtools.github.io/devtools-protocol/)
- [CDP Getting Started Guide](https://github.com/nicholass/getting-started-with-cdp)
- [Marionette Introduction](https://firefox-source-docs.mozilla.org/testing/marionette/Intro.html)
- [WebSockets Library (Python)](https://websockets.readthedocs.io/)
