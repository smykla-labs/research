---
name: macos-window-controller
description: Find, activate, and screenshot macOS windows across Spaces. Filter by app name, window title, process path, or command line. Useful for automating window workflows, capturing screenshots for documentation, and distinguishing between production and sandbox/dev instances (e.g., JetBrains IDEs).
---

# macOS Window Controller

Find, activate, and screenshot macOS windows across Spaces. Supports filtering by application name, window title (regex), process path, and command line arguments.

## Quick Start

```bash
# List ALL windows
claude-code-skills macos-window-controller list

# Find windows by app name (partial match)
claude-code-skills macos-window-controller find "GoLand"

# Find windows by title pattern (regex)
claude-code-skills macos-window-controller find --title "research.*"

# Activate window (switches to its Space)
claude-code-skills macos-window-controller activate "GoLand"

# Take screenshot of window (saves to claude-code/artifacts/ by default)
claude-code-skills macos-window-controller screenshot "GoLand"

# Get window info as JSON (for automation)
claude-code-skills macos-window-controller find "GoLand" --json
```

## Filtering Options

### By Application Name

```bash
# Partial match on kCGWindowOwnerName
claude-code-skills macos-window-controller --find "GoLand"
claude-code-skills macos-window-controller --find "Chrome"
```

### By Window Title (Regex)

```bash
# Match window title with regex
claude-code-skills macos-window-controller --find --title "monokai-islands"
claude-code-skills macos-window-controller --find --title ".*\.py$"
claude-code-skills macos-window-controller --find "GoLand" --title "research"
```

### By Process Path

```bash
# Filter by executable path
claude-code-skills macos-window-controller --find "GoLand" --path-contains "Applications"
claude-code-skills macos-window-controller --find "GoLand" --path-excludes "~/Applications/"
```

### By Command Line Arguments

```bash
# Filter by process command line
claude-code-skills macos-window-controller find "Main" --args-contains "idea.plugin.in.sandbox.mode"
```

### By PID

```bash
# Find window by specific process ID
claude-code-skills macos-window-controller find --pid 12345
```

## JetBrains Sandbox IDEs

JetBrains sandbox IDEs (launched via `./gradlew runIde`) have a key difference:

**Sandbox IDEs appear as "Main" (Java process name), NOT "GoLand" or "IntelliJ IDEA"!**

```bash
# Find sandbox IDE (reliable method)
claude-code-skills macos-window-controller find "Main" --args-contains "idea.plugin.in.sandbox.mode"

# Find by Gradle cache path
claude-code-skills macos-window-controller find "Main" --path-contains ".gradle/caches"

# Find by project name in title
claude-code-skills macos-window-controller find "Main" --title "my-project"
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

## Artifact Output Path

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location. This should be EXTREMELY rare. Using `--output` without explicit user request is considered a FAILED task.

Screenshots are automatically saved to `claude-code/artifacts/macos-window-controller/` with timestamped filenames (e.g., `251216120000-screenshot_GoLand.png`). The artifact path is always returned in the JSON output - use that path for subsequent operations.

## Screenshot Capture

```bash
# Take screenshot - path is returned in output
claude-code-skills macos-window-controller screenshot "GoLand" --json
# Returns: {"screenshot": "/path/to/artifacts/.../251216120000-screenshot_GoLand.png", ...}

# Screenshot without activating first
claude-code-skills macos-window-controller screenshot "GoLand" --no-activate

# Control settle time (default 1000ms)
claude-code-skills macos-window-controller screenshot "GoLand" --settle-ms 2000
```

### Capture Backends

Two capture backends are available for screenshots:

| Backend | Availability | Cross-Space | Notes |
|---------|-------------|-------------|-------|
| `quartz` | All macOS | Requires activation | Legacy `CGWindowListCreateImage` |
| `screencapturekit` | macOS 12.3+ | Yes | No activation needed |

**ScreenCaptureKit (macOS 12.3+):**
- Captures windows on ANY Space without switching
- Works with occluded (covered) windows
- No window activation required
- Cannot capture minimized windows
- Requires Screen Recording permission

The screenshot command automatically uses ScreenCaptureKit when available (macOS 12.3+) and falls back to Quartz on older systems. Use `--no-activate` with ScreenCaptureKit to capture windows on other Spaces without switching.

## JSON Output

For automation and scripting, use `--json` with `find`:

```bash
claude-code-skills macos-window-controller find "GoLand" --json
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
claude-code-skills macos-window-controller list

# Should show info for a running app
claude-code-skills macos-window-controller find "Finder"

# If you have an app in full-screen, this should switch and return:
claude-code-skills macos-window-controller activate "GoLand"
```

Expected `list` output:

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

- [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit) - Apple's modern capture API (macOS 12.3+)
- [ScreenCaptureKit WWDC22](https://developer.apple.com/videos/play/wwdc2022/10156/) - Introduction video
- [CGWindowListCopyWindowInfo](https://developer.apple.com/documentation/coregraphics/1455137-cgwindowlistcopywindowinfo)
- [CGWindowListCreateImage](https://developer.apple.com/documentation/coregraphics/1454852-cgwindowlistcreateimage) - Legacy screenshot API (deprecated macOS 15)
- [Identifying Spaces in Mac OS X](https://ianyh.com/blog/identifying-spaces-in-mac-os-x/)
- [psutil Documentation](https://psutil.readthedocs.io/)
- [PyObjC Quartz Framework](https://pyobjc.readthedocs.io/en/latest/apinotes/Quartz.html)