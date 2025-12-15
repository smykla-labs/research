# Integration Tests for macOS Skills

This directory contains integration tests that use real system APIs and external services. Unlike unit tests that mock dependencies, these tests verify actual behavior.

## Requirements

### Accessibility Permissions

The `ui-inspector` tests require macOS Accessibility permissions:

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Add your terminal application (Terminal, iTerm2, VS Code, etc.)
3. Restart your terminal after granting permissions

### Test Application

Tests use **Finder** as the target application because:

- Always available on macOS
- Has consistent UI elements (buttons, toolbar, etc.)
- Doesn't require any setup

### Python Dependencies

Integration tests require the skill packages to be available:

```bash
# From project root
uv sync
```

## Running Tests

### Run All Integration Tests

```bash
pytest -m integration tests/skills/integration/
```

### Run Specific Test Files

```bash
# OCR Finder only
pytest tests/skills/integration/test_ocr_finder_integration.py

# UI Inspector only
pytest tests/skills/integration/test_ui_inspector_integration.py

# Combined workflow
pytest tests/skills/integration/test_combined_workflow.py
```

### Skip Integration Tests

```bash
# Run all tests EXCEPT integration tests
pytest -m "not integration"

# Run only fast unit tests
pytest -m "not slow"
```

### Verbose Output

```bash
pytest -v -m integration tests/skills/integration/
```

## Test Markers

| Marker        | Description                              |
|:--------------|:-----------------------------------------|
| `integration` | Tests using real APIs (not mocked)       |
| `slow`        | Tests that take > 1 second to complete   |

Both markers are applied to all tests in this directory.

## Test Structure

### OCR Finder Integration (`test_ocr_finder_integration.py`)

Tests real EasyOCR text detection:

- Generates test images with PIL
- Uses actual EasyOCR detection (no mocking)
- Validates bounding boxes, confidence scores, coordinates
- Tests CLI with real images

**Note:** First OCR call may take 5-10 seconds (model loading). Subsequent calls use cached reader.

### UI Inspector Integration (`test_ui_inspector_integration.py`)

Tests real Accessibility API:

- Uses `atomacos` to query live Finder windows
- Validates element roles, positions, sizes
- Tests finding elements by various criteria
- Tests CLI with live applications

**Note:** Tests will skip if Accessibility permissions are not granted.

### Combined Workflow (`test_combined_workflow.py`)

Tests both skills working together:

- Screenshot capture → OCR detection pipeline
- Cross-validation between OCR and UI Inspector
- JSON output compatibility between skills
- Error handling across skill boundaries

## Fixtures

### Finder Window Management

The tests use session-scoped fixtures to manage Finder windows:

```python
@pytest.fixture(scope="session")
def _session_finder_window():
    """Opens Finder window, cleans up test-created windows on teardown."""
    initial_count = _get_finder_window_count()  # Preserve user's windows
    _ensure_finder_window_open()
    yield
    # Only close windows we created
    windows_to_close = current_count - initial_count
    _close_finder_windows(windows_to_close)
```

This ensures:

- Pre-existing Finder windows are preserved
- Tests have a window to work with
- Only test-created windows are cleaned up

### Function-Scoped Fixtures

```python
@pytest.fixture
def finder_window(_session_finder_window):
    """Re-opens window if closed, activates Finder."""
    if not _check_finder_has_windows():
        _ensure_finder_window_open()
    _activate_finder()
```

## CLI Testing Pattern

Integration tests call CLI `main()` functions directly rather than using subprocess:

```python
from ocr_finder.cli import main

# Pass argv as a list
exit_code = main(["--list", "--image", str(image_path), "--json"])
```

This approach:

- Avoids subprocess overhead
- Works without installing packages as executables
- Allows proper pytest output capture

## Troubleshooting

### "Could not open Finder window"

- Check Accessibility permissions
- Ensure Finder.app is running
- Try manually opening a Finder window first

### "No elements found in Finder"

- Finder may be in a background Space
- Tests activate Finder but this may fail in some environments
- Try running tests with Finder already in foreground

### OCR Tests Are Slow

- First run loads EasyOCR model (~5-10s)
- Subsequent runs use cached reader
- Tests are marked `slow` for selective execution

### Flaky Tests

Some tests may be flaky due to:

- Window focus/activation timing
- Mission Control Space switching
- System resource contention

If a test fails intermittently, try:

```bash
pytest --lf  # Re-run last failed tests
```

## Adding New Tests

When adding integration tests:

1. Add both markers: `@pytest.mark.integration` and `@pytest.mark.slow`
2. Use graceful skips for environment issues:
   ```python
   if not condition:
       pytest.skip("Reason for skip")
   ```
3. Don't assume specific text/elements exist (UI can change)
4. Clean up any resources created during tests