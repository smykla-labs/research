---
name: macos-window-controller
description: Find, activate, and screenshot macOS windows across Spaces. Filter by app name, window title, process path, or command line. Useful for automating window workflows, capturing screenshots for documentation, and distinguishing between production and sandbox/dev instances (e.g., JetBrains IDEs).
---

# macOS Window Controller

Find, activate, and screenshot macOS windows across Spaces. Supports filtering by application name, window title (regex), process path, and command line arguments.

## Quick Start

```bash
# List ALL windows
uv run python -m scripts --list

# Find windows by app name (partial match)
uv run python -m scripts --find "GoLand"

# Find windows by title pattern (regex)
uv run python -m scripts --find --title "research.*"

# Activate window (switches to its Space)
uv run python -m scripts --activate "GoLand"

# Take screenshot of window
uv run python -m scripts --screenshot "GoLand" --output ~/shot.png

# Get window info as JSON (for automation)
uv run python -m scripts --find "GoLand" --json
```

## Filtering Options

### By Application Name

```bash
# Partial match on kCGWindowOwnerName
uv run python -m scripts --find "GoLand"
uv run python -m scripts --find "Chrome"
```

### By Window Title (Regex)

```bash
# Match window title with regex
uv run python -m scripts --find --title "monokai-islands"
uv run python -m scripts --find --title ".*\.py$"
uv run python -m scripts --find "GoLand" --title "research"
```

### By Process Path

```bash
# Filter by executable path
uv run python -m scripts --find "GoLand" --path-contains "Applications"
uv run python -m scripts --find "GoLand" --path-excludes "~/Applications/"
```

### By Command Line Arguments

```bash
# Filter by process command line
uv run python -m scripts --find "Main" --args-contains "idea.plugin.in.sandbox.mode"
```

### By PID

```bash
# Find window by specific process ID
uv run python -m scripts --find --pid 12345
```

## JetBrains Sandbox IDEs

JetBrains sandbox IDEs (launched via `./gradlew runIde`) have a key difference:

**Sandbox IDEs appear as "Main" (Java process name), NOT "GoLand" or "IntelliJ IDEA"!**

```bash
# Find sandbox IDE (reliable method)
uv run python -m scripts --find "Main" --args-contains "idea.plugin.in.sandbox.mode"

# Find by Gradle cache path
uv run python -m scripts --find "Main" --path-contains ".gradle/caches"

# Find by project name in title
uv run python -m scripts --find "Main" --title "my-project"
```

## How It Works

### Window Detection

Uses `CGWindowListCopyWindowInfo` with `kCGWindowListOptionAll` to list ALL windows including:

- Off-screen windows
- Windows on other Spaces
- Hidden/minimized windows

### Process Information

Uses `psutil` to get detailed process information:

- Executable path (`exe()`)
- Command line arguments (`cmdline()`)

### Space Detection

Parses `~/Library/Preferences/com.apple.spaces.plist` to map windows to Space indexes and identify which Space is currently active.

### Window Activation

Uses AppleScript to activate applications:

```bash
osascript -e 'tell application "GoLand" to activate'
```

macOS automatically switches to the Space containing the activated window (when enabled in System Settings).

## Screenshot Capture

```bash
# Take screenshot of specific window
uv run python -m scripts --screenshot "GoLand" --output ~/shot.png

# Screenshot without activating first
uv run python -m scripts --screenshot "GoLand" --no-activate

# Control settle time (default 1000ms)
uv run python -m scripts --screenshot "GoLand" --settle-ms 2000
```

## JSON Output

For automation and scripting, use `--json` with `--find`:

```bash
uv run python -m scripts --find "GoLand" --json
```

Output:

```json
{
  "app_name": "GoLand",
  "window_title": "research – models.py",
  "window_id": 190027,
  "pid": 57878,
  "exe_path": "/Users/.../Applications/GoLand.app/Contents/MacOS/goland",
  "cmdline": ["goland", "."],
  "layer": 0,
  "on_screen": null,
  "bounds": {"x": 0, "y": 39, "width": 2056, "height": 1290},
  "space_index": 3
}
```

## Permissions Required

### Screen Recording (required for window names on macOS 10.15+)

System Settings → Privacy & Security → Screen Recording → Add Terminal/Python

### Accessibility (required for AppleScript activation)

System Settings → Privacy & Security → Accessibility → Add Terminal/Python

## Testing

Verify the skill works by running:

```bash
# Should list all windows with titles
uv run python -m scripts --list

# Should show info for a running app
uv run python -m scripts --find "Finder"

# If you have an app in full-screen, this should switch and return:
uv run python -m scripts --activate "GoLand"
```

Expected `--list` output:

```
App                  Title                                    Space  PID
--------------------------------------------------------------------------------
GoLand               research – window_controller.py          3      57878
Ghostty              ~ - fish                                 2      12345
Finder               Documents                                1      456
```

## Troubleshooting

### "No windows found"

1. Check if app is running: `ps aux | grep -i goland`
2. Grant Screen Recording permission
3. Try without filters first: `--find "GoLand"`

### Window names are empty

Grant Screen Recording permission to the terminal/Python process.

### Activation doesn't switch Spaces

Enable "When switching to an application, switch to a Space with open windows" in System Settings → Desktop & Dock → Mission Control.

### Can't find sandbox IDE

1. Ensure `./gradlew runIde` is running
2. Sandbox IDEs appear as **"Main"**, not "GoLand"!
3. Use: `--find "Main" --args-contains "idea.plugin.in.sandbox.mode"`
4. List all windows: `--list | grep -i main`

## Technical References

- [CGWindowListCopyWindowInfo](https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo)
- [Identifying Spaces in Mac OS X](https://ianyh.com/blog/identifying-spaces-in-mac-os-x/)
- [psutil Documentation](https://psutil.readthedocs.io/)
- [PyObjC Quartz Framework](https://pyobjc.readthedocs.io/en/latest/apinotes/Quartz.html)