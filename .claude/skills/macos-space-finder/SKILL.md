---
name: macos-space-finder
description: Find and switch to macOS Spaces/Desktops by application name. Use when asked to find which Space an app is on, switch to a Space containing a specific app (like GoLand, IntelliJ, VS Code), navigate between Mission Control Spaces, or detect full-screen application windows across desktops.
---

# macOS Space Finder

Find which macOS Space/Desktop contains a specific application and navigate to it.

## Quick Start

```bash
# List all spaces
./scripts/find_space.py --list

# Find space containing an app
./scripts/find_space.py "GoLand"

# Show current space
./scripts/find_space.py --current

# Go to app's space and return to original
./scripts/find_space.py --go "GoLand"
```

## How It Works

### Data Source

macOS stores Space configuration in `~/Library/Preferences/com.apple.spaces.plist`. This plist contains:

- List of all Spaces per monitor
- Current Space identifier (`ManagedSpaceID`)
- Full-screen app info (`TileLayoutManager.TileSpaces[].appName`)
- Window IDs associated with each Space

### Switching Spaces

Two methods work reliably:

1. **AppleScript app activation** (recommended):
   ```bash
   osascript -e 'tell application "GoLand" to activate'
   ```
   - macOS automatically switches to the Space containing the app
   - Works for full-screen apps and windowed apps

2. **Keyboard shortcuts** via computer-control MCP:
   ```python
   # Control+Right Arrow to move one space right
   press_keys([["ctrl", "right"]])

   # Control+Left Arrow to move one space left
   press_keys([["ctrl", "left"]])
   ```
   - Requires knowing relative position of target Space

### Limitations

- **No public API**: Apple provides no official API to query Space information
- **Plist caching**: The plist may not update immediately after Space changes
- **Control+Number**: Direct Space switching (Ctrl+1, Ctrl+2) only works if enabled in System Settings > Keyboard > Keyboard Shortcuts > Mission Control

## Script Reference

### `scripts/find_space.py`

| Flag | Description |
|------|-------------|
| `--list` | Show all Spaces with index, type, app name, window title |
| `--current` | Print current Space's app name (or "Desktop") |
| `--go <app>` | Switch to app's Space, wait 1s, return to original |
| `<app>` | Find Space containing app (case-insensitive partial match) |

### Space Types

| Type | Description |
|------|-------------|
| Normal (0) | Standard desktop |
| FullSc (4) | Full-screen app Space |
| Tile (5) | Tile within full-screen Space |
| Wall (6) | Wallpaper layer |

## Integration with MCP

When using `computer-control-mcp` to navigate Spaces:

```python
# 1. Get current space before operations
result = subprocess.run(["./scripts/find_space.py", "--current"], capture_output=True, text=True)
original_space = result.stdout.strip()

# 2. Activate target app (switches Space automatically)
subprocess.run(["osascript", "-e", f'tell application "{target_app}" to activate'])

# 3. Perform MCP operations (screenshots, clicks, etc.)
# ... mcp operations ...

# 4. Return to original Space
subprocess.run(["osascript", "-e", f'tell application "{original_space}" to activate'])
```

## Testing

Verify the skill works by running:

```bash
# Should list all your Spaces
./scripts/find_space.py --list

# Should show current app (e.g., "Ghostty" or "Desktop")
./scripts/find_space.py --current

# If you have GoLand in full-screen, this should work:
./scripts/find_space.py --go GoLand
```

Expected `--list` output:
```
Idx  Current  Type   App Name             Window Title
--------------------------------------------------------------------------------
1    *        Normal -                    -
2             FullSc Ghostty              terminal session title
3             FullSc GoLand               project – file.go
```

## Troubleshooting

### Script returns wrong current Space

The plist may be cached. Wait 1-2 seconds after Space changes before querying.

### "No space found for app"

- Check exact app name with `--list`
- App must have a window (minimized apps may not appear)
- Full-screen apps are most reliably detected

### AppleScript activation doesn't switch Spaces

- Ensure "When switching to an application, switch to a Space with open windows" is enabled in System Settings > Desktop & Dock > Mission Control

## Technical References

- [Identifying Spaces in Mac OS X](https://ianyh.com/blog/identifying-spaces-in-mac-os-x/) - Cross-referencing window lists with Space data
- [CGSInternal/CGSSpace.h](https://github.com/NUIKit/CGSInternal/blob/master/CGSSpace.h) - Private API documentation
- [yabai wiki](https://github.com/koekeishiya/yabai/wiki/Commands) - Advanced window management (requires SIP modification)