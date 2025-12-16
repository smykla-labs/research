---
name: macos-ocr-finder
description: Find text in images using EasyOCR, returning click coordinates. Works on any image (screenshots, UI captures, etc.) without requiring accessibility permissions. Useful for UI automation, finding buttons/labels in screenshots, and extracting text positions.
---

# macOS OCR Finder

Find text in images using EasyOCR. Returns text locations with bounding boxes and click coordinates. Works with any image format (PNG, JPG, etc.) and doesn't require accessibility permissions.

## Quick Start

```bash
# List all text found in an image
claude-code-skills macos-ocr-finder list --image screenshot.png

# Find specific text (substring match, case-insensitive)
claude-code-skills macos-ocr-finder find "Accept" --image dialog.png

# Get click coordinates for text
claude-code-skills macos-ocr-finder click "Submit" --image form.png

# JSON output for automation
claude-code-skills macos-ocr-finder list --image screenshot.png --json
```

## Commands

### List All Text (`--list`)

Detect and list all text regions in an image.

```bash
# Basic listing
claude-code-skills macos-ocr-finder -l -i screenshot.png

# With low confidence threshold (detect more text)
claude-code-skills macos-ocr-finder -l -i screenshot.png --min-confidence 0.3

# JSON output
claude-code-skills macos-ocr-finder -l -i screenshot.png --json
```

Example output:

```
Text                                     Confidence Click (x,y)
----------------------------------------------------------------------
File                                           0.92 (45, 12)
Edit                                           0.89 (98, 12)
View                                           0.91 (152, 12)
Submit                                         0.95 (320, 450)
```

### Find Text (`--find`)

Search for specific text in an image.

```bash
# Substring match (default)
claude-code-skills macos-ocr-finder -f "Accept" -i dialog.png

# Exact match only
claude-code-skills macos-ocr-finder -f "OK" -i dialog.png --exact

# Case-sensitive match
claude-code-skills macos-ocr-finder -f "Submit" -i form.png --case-sensitive

# Low confidence threshold
claude-code-skills macos-ocr-finder -f "faded text" -i low-contrast.png --min-confidence 0.2
```

### Get Click Coordinates (`--click`)

Get the center coordinates of text for clicking.

```bash
# Get coords for first match
claude-code-skills macos-ocr-finder --click "Submit" -i form.png
# Output: 320,450

# Get coords for second match (index 1)
claude-code-skills macos-ocr-finder --click "Button" -i form.png --index 1

# JSON output
claude-code-skills macos-ocr-finder --click "OK" -i dialog.png --json
# Output: {"x": 420, "y": 380}
```

## Options

| Option | Short | Description |
|:-------|:------|:------------|
| `--image` | `-i` | Path to image file (required) |
| `--list` | `-l` | List all text regions |
| `--find` | `-f` | Find specific text |
| `--click` | | Get click coordinates |
| `--json` | | Output as JSON |
| `--exact` | | Require exact match |
| `--case-sensitive` | | Case-sensitive matching |
| `--min-confidence` | | Minimum OCR confidence (0.0-1.0, default: 0.5) |
| `--index` | | Match index for --click (default: 0) |

## JSON Output

### List Output

```json
[
  {
    "text": "Submit",
    "confidence": 0.95,
    "bbox": {
      "x1": 300,
      "y1": 440,
      "x2": 340,
      "y2": 460,
      "width": 40,
      "height": 20,
      "center_x": 320,
      "center_y": 450
    },
    "click_x": 320,
    "click_y": 450
  }
]
```

### Click Output

```json
{"x": 320, "y": 450}
```

## Use Cases

### UI Automation

```bash
# Find button and click it
coords=$(claude-code-skills macos-ocr-finder --click "Submit" -i screenshot.png)
# Use coords with your automation tool
```

### Finding UI Elements in Screenshots

```bash
# List all buttons visible in a dialog screenshot
claude-code-skills macos-ocr-finder -l -i dialog.png --json | jq '.[] | select(.text | test("OK|Cancel|Apply"))'
```

### Cross-Skill Workflow

Combine with `verified-screenshot` for end-to-end automation:

```bash
# Capture window → Find text → Get click coords
claude-code-skills macos-verified-screenshot --app "Safari" --output /tmp/safari.png
claude-code-skills macos-ocr-finder --click "Downloads" -i /tmp/safari.png --json
```

## How It Works

1. **EasyOCR Detection**: Uses EasyOCR (CPU mode) to detect text regions
2. **Bounding Boxes**: Each detected region has a bounding box (x1, y1, x2, y2)
3. **Click Coordinates**: Center of bounding box is returned as click target
4. **Confidence Filtering**: Low-confidence detections are filtered by default

### Reader Caching

The EasyOCR reader is cached after first use. First call may take 5-10 seconds (model loading), subsequent calls are faster.

## Dependencies

- **EasyOCR**: Text detection engine (installed via workspace dependencies)
- **PIL/Pillow**: Image loading
- No accessibility permissions required (works on any image)

## Limitations

- **OCR Accuracy**: May miss text in low-contrast images or unusual fonts
- **First Call Latency**: ~5-10 seconds on first call (model loading)
- **Image Coordinates**: Returns coordinates relative to image, not screen
- **CPU Only**: Uses CPU mode for broader compatibility (no GPU required)

## Troubleshooting

### "No text found in image"

1. Lower the confidence threshold: `--min-confidence 0.3`
2. Check if the image has text (view the image manually)
3. Ensure image format is supported (PNG, JPG)

### Text Not Matching

1. Use `--list` to see what text was detected
2. Try `--exact` for exact matches vs substring
3. Try `--case-sensitive` if case matters

### Slow First Run

EasyOCR loads its model on first use (~5-10 seconds). Subsequent calls use the cached reader and are much faster.

### Coordinates Off-Target

OCR bounding boxes may not be pixel-perfect. If clicking doesn't hit the target:

1. Use `--list --json` to inspect exact bounding boxes
2. Consider using `ui-inspector` for live UI elements (more accurate but requires permissions)

## Comparison with ui-inspector

| Feature | ocr-finder | ui-inspector |
|:--------|:-----------|:-------------|
| Works on | Any image | Live apps only |
| Permissions | None | Accessibility |
| Speed | Slower (~1-5s) | Instant |
| Coordinates | Image-relative | Screen-absolute |
| Element type | Text only | Any UI element |
| Best for | Screenshots, non-standard UIs | Automation, buttons/fields |

## Technical References

- [EasyOCR Documentation](https://github.com/JaidedAI/EasyOCR)
- [PIL/Pillow Documentation](https://pillow.readthedocs.io/)