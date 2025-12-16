---
name: macos-screen-recorder
description: Record macOS screen with verification, retry logic, and format conversion for Discord, GitHub, JetBrains. Integrates with window-controller for window discovery.
---

# macOS Screen Recorder

Record macOS screen with automatic verification, retry logic, and optimized format conversion. This skill captures screen recordings of specific windows or regions, converts them to platform-optimized formats (GIF, WebP, MP4), and verifies the recording captured what you intended.

## Workspace Context

Use the unified `claude-code-skills` CLI wrapper:

```bash
# Recommended: Use CLI wrapper (works from anywhere when in PATH)
claude-code-skills macos-screen-recorder --help

# Alternative: Use PYTHONPATH from workspace root
PYTHONPATH=claude-code/skills/macos-screen-recorder python -m screen_recorder.cli --help
```

## Artifact Output Path

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location. This should be EXTREMELY rare. Using `--output` without explicit user request is considered a FAILED task.

Recordings are automatically saved to `claude-code/artifacts/macos-screen-recorder/` with timestamped filenames (e.g., `251216120000-recording_GoLand.gif`). The artifact path is always returned in the JSON output - use that path for subsequent operations.

## Quick Start

```bash
# Record a window for 5 seconds - path is returned in output
claude-code-skills macos-screen-recorder record "GoLand" -d 5 --json
# Returns: {"final_path": "/path/to/artifacts/.../251216120000-recording_GoLand.mov", ...}

# Record optimized for Discord upload (10MB max, WebP)
claude-code-skills macos-screen-recorder record "GoLand" -d 5 --preset discord

# Record optimized for GitHub README (GIF, ~5MB)
claude-code-skills macos-screen-recorder record "Code" -d 10 --preset github

# Record optimized for JetBrains Marketplace (1280x800 GIF)
claude-code-skills macos-screen-recorder record "IntelliJ" -d 8 --preset jetbrains

# Record full screen
claude-code-skills macos-screen-recorder full-screen -d 3

# Record sandbox IDE (JetBrains via Gradle runIde)
claude-code-skills macos-screen-recorder record "Main" --args "idea.plugin.in.sandbox.mode" --no-activate

# Record window on different Space (no activation, ScreenCaptureKit)
claude-code-skills macos-screen-recorder record "Terminal" -d 5 --backend screencapturekit

# Record absolute screen region (x=100, y=200, w=800, h=600)
claude-code-skills macos-screen-recorder region 100,200,800,600 -d 5

# Record window-relative region (terminal area at bottom of IDE)
claude-code-skills macos-screen-recorder record "GoLand" --window-region 0,800,1600,400 -d 5

# Preview region before recording (iterative coordinate refinement)
claude-code-skills macos-screen-recorder record "GoLand" --window-region 0,800,1600,400 --preview-region

# Check if ffmpeg is installed
claude-code-skills macos-screen-recorder check-deps
```

## How It Works

### Recording Pipeline

1. **Window Discovery**: Uses `CGWindowListCopyWindowInfo` to find target window by app name, title pattern, PID, executable path, or command-line arguments.

2. **Activation** (optional): Activates the target app via AppleScript, which switches to the window's Space. Configurable settle time for rendering.

3. **Space Detection**: Automatically detects if target window is on a different Space (macOS virtual desktop). If so, switches to that Space, re-finds window bounds (Space switch invalidates coordinates), records, then returns to original Space.

4. **Screen Recording**: Uses native macOS `screencapture -v -R x,y,w,h -V duration` for region-specific video capture to `.mov` format.

### Capture Backends

The recorder supports multiple capture backends with different capabilities:

| Feature | Backend | Cross-Space | Notes |
|---------|---------|-------------|-------|
| Video recording | ScreenCaptureKit | Yes | macOS 12.3+, no activation needed |
| Video recording | `screencapture -v` | Requires activation | Built-in macOS tool, fallback |
| Region preview | `screencapture` | Requires activation | Built-in macOS tool |

**Backend Selection** (`--backend`):

- `auto` (default): Uses ScreenCaptureKit for window recording on macOS 12.3+, falls back to `screencapture` for full-screen or when unavailable
- `screencapturekit`: Force ScreenCaptureKit (requires macOS 12.3+)
- `quartz`: Force traditional `screencapture` command

**ScreenCaptureKit Video** (default for window recording):
- Uses SCStream + AVAssetWriter for video recording
- Records windows across Spaces without activation or Space switching
- Works with occluded/covered windows (captures window content directly)
- Requires macOS 12.3+ and Screen Recording permission
- Note: macOS 15 may have stability issues (PyObjC #647)

**Traditional screencapture** (default for full-screen):
- Uses macOS built-in `screencapture -v` command
- Requires window activation to record windows on other Spaces
- Space-aware recording automatically switches Spaces when needed
- Always used for full-screen recording (`--full-screen`)

**Region Preview** (`--preview-region`):
- Uses macOS built-in `screencapture` command for screenshot preview
- Requires window activation to capture windows on other Spaces
- Space-aware preview automatically switches Spaces when needed

5. **Format Conversion**: Converts to target format using ffmpeg:
   - **GIF**: Two-pass palette optimization with sierra2_4a dithering
   - **WebP**: Lossy animated WebP with configurable quality
   - **MP4**: H.264 with yuv420p pixel format for compatibility

6. **Verification**: Runs configured verification strategies:
   - **basic**: File exists, size > 0
   - **duration**: Duration matches requested (±0.5s)
   - **frames**: Minimum frame count based on duration × fps
   - **motion**: First/last frames differ (perceptual hash)

7. **Retry Loop**: On failure, retries up to N times with configurable delay strategy.

### Platform Presets

| Preset      | Format | Max Size | FPS    | Max Width | Use Case           |
|-------------|--------|----------|--------|-----------|--------------------|
| `discord`   | WebP   | 10 MB    | 10     | 720px     | Discord (no Nitro) |
| `github`    | GIF    | 5 MB     | 10     | 600px     | README files       |
| `jetbrains` | GIF    | 20 MB    | 15     | 1280×800  | Plugin marketplace |
| `raw`       | MOV    | -        | native | -         | No conversion      |

### Region Recording

Two region modes for capturing specific screen areas:

**Absolute Region** (`--region`, `-R`):
- Captures a fixed screen area regardless of window position
- Coordinates are absolute screen pixels: `x,y,width,height`
- Example: `-R 100,200,800,600` captures 800×600 area at screen position (100,200)

**Window-Relative Region** (`--window-region`):
- Captures a region relative to a window's top-left corner
- Requires `--record` to specify the target window
- Coordinates are offsets from window origin: `x,y,width,height`
- Example: `--record "GoLand" --window-region 0,800,1600,400`
  - Finds GoLand window (e.g., at screen position 50,25)
  - Adds offset: (50+0, 25+800) = captures at (50, 825)
  - Records 1600×400 area (captures terminal panel at bottom)

Use `find` to discover window bounds before recording:

```bash
claude-code-skills macos-screen-recorder find "GoLand" --json | jq '.bounds'
# {"x": 50, "y": 25, "width": 2056, "height": 1290}
```

**Iterative Coordinate Refinement** (`--preview-region`):

When capturing specific UI elements, use `--preview-region` to test coordinates:

```bash
# Step 1: Find window bounds
claude-code-skills macos-screen-recorder find "GoLand" --json

# Step 2: Preview estimated region
claude-code-skills macos-screen-recorder record "GoLand" --window-region 0,890,2056,400 --preview-region
# Preview saved: recordings/goland_preview_20241215_120000.png

# Step 3: View preview, adjust coordinates
open recordings/goland_preview_*.png

# Step 4: Record when satisfied
claude-code-skills macos-screen-recorder record "GoLand" --window-region 0,890,2056,400 -d 5
```

### Space-Aware Recording

When recording windows on different macOS Spaces (virtual desktops), the recorder automatically:

1. **Detects** if the target window is on a different Space
2. **Switches** to that Space using Mission Control integration
3. **Re-finds** the window (Space switches invalidate coordinates)
4. **Records** the window with correct bounds
5. **Returns** to the original Space after recording completes

This happens transparently—no special flags required:

```bash
# Record Terminal on Space 2 while you're on Space 1
claude-code-skills macos-screen-recorder record "Terminal" -d 5

# Record fullscreen Safari (which is its own Space)
claude-code-skills macos-screen-recorder record "Safari" -d 10
```

**Requirements:**

- Accessibility permissions (System Settings > Privacy & Security > Accessibility)
- Target window must be discoverable via `CGWindowListCopyWindowInfo`

**Behavior:**

- If Space switch fails, recording continues on current Space (may capture wrong window)
- Original Space is always restored, even if recording fails
- Use `--no-activate` to skip activation and Space switching entirely

### Verification Strategies

| Strategy   | Purpose           | Details                        |
|------------|-------------------|--------------------------------|
| `basic`    | Sanity check      | File exists, >0 bytes          |
| `duration` | Correct length    | Duration ±0.5s of requested    |
| `frames`   | Enough content    | ≥80% of expected frames        |
| `motion`   | Content changed   | First/last frame hashes differ |
| `all`      | Full verification | All above strategies           |
| `none`     | Skip verification | Record only                    |

## Command Reference

### Actions

| Flag              | Short | Description                          |
|-------------------|-------|--------------------------------------|
| `--record`        | `-r`  | Record window of specified app       |
| `--find`          | `-f`  | Find window without recording        |
| `--full-screen`   | `-F`  | Record entire screen                 |
| `--preview-region`|       | Screenshot region for coord testing  |
| `--check-deps`    |       | Check ffmpeg availability            |

### Window Filters

| Flag              | Short | Description                      |
|-------------------|-------|----------------------------------|
| `--title`         | `-t`  | Regex pattern for window title   |
| `--pid`           |       | Filter by process ID             |
| `--path-contains` |       | Executable path must contain     |
| `--path-excludes` |       | Executable path must NOT contain |
| `--args`          |       | Command line must contain        |

### Recording Options

| Flag               | Short | Description                                          |
|--------------------|-------|------------------------------------------------------|
| `--duration`       | `-d`  | Recording duration in seconds (default: 10)          |
| `--max-duration`   |       | Maximum allowed duration (default: 60)               |
| `--region`         | `-R`  | Absolute screen region: x,y,width,height             |
| `--window-region`  |       | Window-relative region (requires --record): x,y,w,h  |
| `--no-clicks`      |       | Don't show mouse clicks                              |
| `--no-activate`    |       | Don't activate window first                          |
| `--settle-ms`      |       | Wait time after activation (default: 500)            |
| `--backend`        |       | Capture backend: auto, quartz, screencapturekit      |

### Output Options

| Flag         | Short | Description                                      |
|--------------|-------|--------------------------------------------------|
| `--output`   | `-o`  | Output file path                                 |
| `--format`   |       | Output format: gif, webp, mp4, mov               |
| `--preset`   | `-p`  | Platform preset: discord, github, jetbrains, raw |
| `--keep-raw` |       | Keep original .mov after conversion              |
| `--json`     | `-j`  | Output result as JSON                            |

### Format Settings (Override Preset)

| Flag              | Description                       |
|-------------------|-----------------------------------|
| `--fps`           | Target frame rate                 |
| `--max-width`     | Maximum width in pixels           |
| `--max-height`    | Maximum height in pixels          |
| `--quality`, `-q` | Quality for lossy formats (0-100) |
| `--max-size`      | Target maximum file size in MB    |

### Verification Options

| Flag       | Short | Description                                            |
|------------|-------|--------------------------------------------------------|
| `--verify` | `-v`  | Strategies: basic, duration, frames, motion, all, none |

### Retry Options

| Flag               | Description                                |
|--------------------|--------------------------------------------|
| `--retries`        | Maximum retry attempts (default: 5)        |
| `--retry-delay`    | Delay between retries in ms (default: 500) |
| `--retry-strategy` | fixed, exponential, or reactivate          |

## Integration Examples

### Programmatic Use

```python
from screen_recorder import (
    record_verified,
    record_simple,
    RecordingConfig,
    PlatformPreset,
    VerificationStrategy,
)

# Simple recording
result = record_simple(
    app_name="GoLand",
    duration=5,
    preset=PlatformPreset.GITHUB,
)
print(f"Saved: {result.final_path}")
print(f"Size: {result.video_info.file_size_mb:.2f} MB")

# Full configuration
config = RecordingConfig(
    app_name="Chrome",
    title_pattern="GitHub",
    duration_seconds=10,
    preset=PlatformPreset.DISCORD,
    output_path="demo.webp",
    max_retries=3,
    verification_strategies=(
        VerificationStrategy.BASIC,
        VerificationStrategy.DURATION,
        VerificationStrategy.MOTION,
    ),
)
result = record_verified(config)

if result.verified:
    print(f"Recording saved: {result.final_path}")
    print(f"Duration: {result.duration_actual:.1f}s")
    print(f"Size: {result.video_info.file_size_mb:.2f} MB")
else:
    print("Recording failed verification:")
    for v in result.verifications:
        print(f"  {v.strategy.value}: {v.message}")
```

### JSON Output

```bash
claude-code-skills macos-screen-recorder record "GoLand" -d 5 --preset github --json
```

```json
{
  "raw_path": "recordings/goland_20241214_153045_raw.mov",
  "final_path": "recordings/goland_20241214_153045.gif",
  "attempt": 1,
  "duration_requested": 5.0,
  "duration_actual": 5.1,
  "window_id": 190027,
  "app_name": "GoLand",
  "window_title": "research – models.py",
  "bounds": {"x": 0, "y": 25, "width": 2056, "height": 1290},
  "output_format": "gif",
  "preset": "github",
  "video_info": {
    "path": "recordings/goland_20241214_153045.gif",
    "duration_seconds": 5.1,
    "frame_count": 51,
    "fps": 10.0,
    "width": 600,
    "height": 376,
    "file_size_mb": 2.34
  },
  "verifications": [
    {"strategy": "basic", "passed": true, "message": "Valid video file"},
    {"strategy": "duration", "passed": true, "message": "Duration matches"}
  ],
  "verified": true
}
```

### Claude Code Integration

```bash
# Load the skill context
Skill tool: macos-screen-recorder

# Record with platform preset - use the returned path
claude-code-skills macos-screen-recorder record "GoLand" -d 5 --preset discord --json
# Use the "final_path" field from JSON output for subsequent operations

# Verify dependencies first
claude-code-skills macos-screen-recorder check-deps
```

## Testing

```bash
# From workspace root
uv run pytest tests/skills/test_screen_recorder*.py -v

# Run with coverage
uv run pytest tests/skills/test_screen_recorder*.py -v --cov=screen_recorder

# Run specific test file
uv run pytest tests/skills/test_screen_recorder_core.py -v
```

## Troubleshooting

### "ffmpeg not found"

Install ffmpeg using Homebrew:

```bash
brew install ffmpeg
```

Verify installation:

```bash
claude-code-skills macos-screen-recorder check-deps
```

### "No window found matching filter"

1. Check if the app is running: `ps aux | grep -i appname`
2. Use `find` to see what windows are available
3. For sandbox IDEs, use `record "Main" --args "sandbox"`
4. Try without filters first

### Recording is wrong size or window

1. Grant Screen Recording permission: System Settings > Privacy & Security > Screen Recording
2. Window might be on another Space - use default activation
3. Increase `--settle-ms` if app is slow to render
4. Use `--verify motion` to detect static recordings

### File size too large for platform

1. Reduce `--duration`
2. Lower `--fps` (10 is usually sufficient)
3. Reduce `--max-width`
4. For WebP: lower `--quality` (try 50-60)
5. Use appropriate `--preset` for target platform

### Discord: "File too large" (no Nitro)

```bash
# Discord free limit is 10MB
claude-code-skills macos-screen-recorder record "App" -d 5 --preset discord
```

If still too large:
- Reduce duration
- Lower quality: `--quality 50`
- Reduce resolution: `--max-width 480`

### GitHub: GIF not animating

Ensure the GIF URL is direct (ends with `.gif`). If embedding in Markdown:

```markdown
![Demo](./demo.gif)
```

For large GIFs, drag-drop into GitHub issue/PR to upload to GitHub's CDN instead of committing to repo.

### Sandbox IDEs (JetBrains runIde)

JetBrains sandbox IDEs appear as "Main" and AppleScript cannot activate them:

```bash
claude-code-skills macos-screen-recorder --record "Main" --args "idea.plugin.in.sandbox.mode" --no-activate -d 10
```

With `--no-activate`, you must manually switch to the sandbox window's Space before recording. Alternatively, if the sandbox IDE is on a different Space, the Space-aware recording will switch to it automatically (activation via AppleScript still won't work, but the correct Space will be selected).

### Permission errors

Grant these permissions in System Settings > Privacy & Security:

- **Screen Recording**: Required for screencapture
- **Accessibility**: Required for AppleScript window activation

## Dependencies

Required:
- `pyobjc-framework-Quartz>=10.0` - macOS Quartz framework bindings
- `pyobjc-framework-ScreenCaptureKit>=10.0` - ScreenCaptureKit bindings (macOS 12.3+)
- `pyobjc-framework-AVFoundation>=10.0` - AVFoundation for SCK video recording
- `psutil>=5.9` - Process information
- `pillow>=10.0` - Image processing (frame extraction)
- `imagehash>=4.3` - Perceptual hashing (motion detection)

External tools:
- `screencapture` - Built into macOS (fallback video recording)
- `ffmpeg` - Video conversion (`brew install ffmpeg`)
- `ffprobe` - Video metadata (included with ffmpeg)

## Technical References

### macOS screencapture

- [SS64 screencapture Manual](https://ss64.com/mac/screencapture.html)
- `-v` Video mode
- `-V seconds` Timed recording
- `-R x,y,w,h` Region capture
- `-k` Show clicks

### ffmpeg Conversion

- [FFmpeg MP4 to GIF Guide](https://shotstack.io/learn/convert-video-gif-ffmpeg/)
- [High Quality GIF with FFmpeg](https://blog.pkh.me/p/21-high-quality-gif-with-ffmpeg.html)
- [FFmpeg WebP Animation](https://www.ramstad.io/2022/01/22/Encoding-WebP-animations-with-FFmpeg/)

### Platform Limits

- [Discord File Upload Limits](https://support.discord.com/hc/en-us/articles/115000435108) - 10MB free, 50MB Basic, 500MB Nitro
- [GitHub File Size Limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) - 10MB warning, 100MB hard limit
- [JetBrains Marketplace Media](https://plugins.jetbrains.com/docs/marketplace/best-practices-for-listing.html) - 1280x800 recommended

### ScreenCaptureKit Video Recording

- [Recording to disk with ScreenCaptureKit (Nonstrict)](https://nonstrict.eu/blog/2023/recording-to-disk-with-screencapturekit/)
- [ScreenCaptureKit-Recording-example](https://github.com/nonstrict-hq/ScreenCaptureKit-Recording-example)
- [PyObjC Issue 590 - SCK usage](https://github.com/ronaldoussoren/pyobjc/issues/590)
- [PyObjC Issue 647 - macOS 15 issues](https://github.com/ronaldoussoren/pyobjc/issues/647)

## Sources (Research)

- [Apple AVCaptureScreenInput](https://developer.apple.com/documentation/avfoundation/avcapturescreeninput)
- [ScreenCaptureKit WWDC22](https://developer.apple.com/videos/play/wwdc2022/10156/)
- [PyObjC ScreenCaptureKit](https://pyobjc.readthedocs.io/en/latest/apinotes/ScreenCaptureKit.html)
- [ffprobe JSON Output](https://ffmpeg.org/ffprobe.html)
- [imagehash Library](https://github.com/JohannesBuchner/imagehash)
