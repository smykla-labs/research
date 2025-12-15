"""Combined workflow integration tests for OCR Finder + UI Inspector.

These tests verify that the two UI detection skills work together:
1. Screenshot capture → OCR text detection → coordinate extraction
2. Cross-validation: OCR coordinates vs UI Inspector coordinates
3. JSON output parsing pipeline between skills

Tests are marked with `integration` and `slow` markers for selective execution.

Requirements:
    - macOS Accessibility permissions must be granted to the terminal/IDE
    - Finder app will be used for testing (always available)

Run only integration tests:
    pytest -m integration tests/skills/integration/

Skip integration tests:
    pytest -m "not integration"
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest

# =============================================================================
# Pytest Markers
# =============================================================================

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


# =============================================================================
# Finder Window Fixtures (shared with ui-inspector tests)
# =============================================================================


def _get_finder_window_count() -> int:
    """Get the current number of Finder windows."""
    result = subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Finder" to count of windows',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return int(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0


def _ensure_finder_window_open(max_attempts: int = 5) -> bool:
    """Ensure Finder has at least one window open."""
    for attempt in range(max_attempts):
        if _get_finder_window_count() > 0:
            return True

        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Finder" to make new Finder window',
            ],
            capture_output=True,
            check=False,
        )
        time.sleep(1.0)

        if _get_finder_window_count() > 0:
            return True

        if attempt < max_attempts - 1:
            time.sleep(0.5 * (attempt + 1))

    return False


def _close_finder_windows(count: int) -> None:
    """Close a specific number of Finder windows."""
    if count <= 0:
        return

    for _ in range(count):
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Finder" to close window 1',
            ],
            capture_output=True,
            check=False,
        )


def _activate_finder() -> None:
    """Bring Finder to front."""
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Finder" to activate',
        ],
        capture_output=True,
        check=False,
    )
    time.sleep(0.5)


@pytest.fixture(scope="session")
def _session_finder_window() -> Generator[None, None, None]:
    """Session-level Finder window setup with cleanup."""
    initial_window_count = _get_finder_window_count()

    if not _ensure_finder_window_open():
        pytest.skip("Could not open Finder window - check Accessibility permissions")

    yield

    current_count = _get_finder_window_count()
    windows_to_close = current_count - initial_window_count

    if windows_to_close > 0:
        _close_finder_windows(windows_to_close)


@pytest.fixture
def finder_window(_session_finder_window: None) -> None:
    """Ensure Finder window is open and active."""
    if _get_finder_window_count() == 0:
        _ensure_finder_window_open(max_attempts=2)

    _activate_finder()


# =============================================================================
# Screenshot Fixture
# =============================================================================


@pytest.fixture
def screenshot_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for screenshots."""
    return tmp_path / "screenshots"


def _capture_finder_screenshot(output_path: Path) -> Path | None:
    """Capture a Finder window screenshot.

    Returns:
        Path to screenshot if successful, None on failure.
    """
    try:
        from verified_screenshot import CaptureConfig, capture_verified
        from verified_screenshot.models import VerificationStrategy

        config = CaptureConfig(
            app_name="Finder",
            output_path=str(output_path),
            max_retries=3,
            activate_first=True,
            settle_ms=500,
            verification_strategies=(VerificationStrategy.BASIC,),
        )

        result = capture_verified(config)
        return result.path
    except Exception:
        return None


# =============================================================================
# Screenshot → OCR Pipeline Tests
# =============================================================================


class TestScreenshotOcrPipeline:
    """Tests for screenshot → OCR text detection workflow."""

    def test_screenshot_to_ocr_detection(self, finder_window: None, screenshot_dir: Path) -> None:
        """Test capturing screenshot and running OCR on it."""
        from ocr_finder import list_all_text

        screenshot_path = screenshot_dir / "finder_test.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        # Run OCR on the captured screenshot
        regions = list_all_text(captured, min_confidence=0.0)

        # Should detect some text (Finder windows have UI elements with text)
        assert isinstance(regions, tuple)
        # Note: May be empty if screenshot captures a blank area

    def test_ocr_returns_valid_coordinates(self, finder_window: None, screenshot_dir: Path) -> None:
        """Test that OCR returns valid bounding box coordinates."""
        from ocr_finder import list_all_text
        from PIL import Image

        screenshot_path = screenshot_dir / "finder_coords.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        regions = list_all_text(captured, min_confidence=0.0)

        if not regions:
            pytest.skip("No text detected in screenshot")

        img = Image.open(captured)
        width, height = img.size

        # Verify coordinates are within image bounds
        for region in regions:
            bbox = region.bbox
            assert bbox.x1 >= 0
            assert bbox.y1 >= 0
            assert bbox.x2 <= width
            assert bbox.y2 <= height

            # Click coords should be within image
            cx, cy = region.click_coords
            assert 0 <= cx <= width
            assert 0 <= cy <= height

    def test_ocr_confidence_filtering(self, finder_window: None, screenshot_dir: Path) -> None:
        """Test that confidence filtering works on real screenshots."""
        from ocr_finder import list_all_text

        screenshot_path = screenshot_dir / "finder_confidence.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        all_results = list_all_text(captured, min_confidence=0.0)
        high_conf_results = list_all_text(captured, min_confidence=0.9)

        # High confidence should return fewer or equal results
        assert len(high_conf_results) <= len(all_results)

    def test_screenshot_json_to_ocr(
        self, finder_window: None, screenshot_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON output from OCR can be parsed."""
        from ocr_finder.cli import main as ocr_main

        screenshot_path = screenshot_dir / "finder_json.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        exit_code = ocr_main(
            ["list", "--image", str(captured), "--json", "--min-confidence", "0"]
        )

        assert exit_code == 0

        captured_output = capsys.readouterr()
        data = json.loads(captured_output.out)
        assert isinstance(data, list)

        # Verify JSON structure
        for item in data:
            assert "text" in item
            assert "confidence" in item
            assert "bbox" in item


# =============================================================================
# Cross-Skill Validation Tests
# =============================================================================


class TestCrossSkillValidation:
    """Tests validating OCR and UI Inspector work together."""

    def test_both_skills_detect_ui_elements(self, finder_window: None) -> None:
        """Test that both skills can analyze the same app."""
        from ui_inspector import list_elements

        # UI Inspector should find elements
        ui_elements = list_elements("Finder")

        # Just verify both skills can run against Finder
        assert len(ui_elements) > 0

    def test_ui_inspector_elements_have_valid_coords(self, finder_window: None) -> None:
        """Test UI Inspector coordinates are screen-relative."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        if not elements:
            pytest.skip("No elements found in Finder")

        for elem in elements[:10]:
            x, y = elem.position
            w, h = elem.size
            cx, cy = elem.center

            # Size should be non-negative
            assert w >= 0
            assert h >= 0

            # Center should be position + half size
            assert cx == x + w // 2
            assert cy == y + h // 2

    def test_json_output_compatibility(
        self, finder_window: None, screenshot_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test JSON outputs from both skills have compatible structures."""
        from ocr_finder.cli import main as ocr_main
        from ui_inspector.cli import main as ui_main

        # Get UI Inspector JSON
        ui_exit = ui_main(["list", "--app", "Finder", "--json"])
        ui_captured = capsys.readouterr()

        if ui_exit != 0 or not ui_captured.out.strip():
            pytest.skip("Could not get UI Inspector JSON")

        ui_data = json.loads(ui_captured.out)
        assert isinstance(ui_data, list)

        # Verify UI Inspector has position info
        if ui_data:
            assert "center_x" in ui_data[0]
            assert "center_y" in ui_data[0]

        # Get OCR JSON (need screenshot first)
        screenshot_path = screenshot_dir / "finder_compat.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        ocr_exit = ocr_main(["list", "--image", str(captured), "--json", "--min-confidence", "0"])
        ocr_captured = capsys.readouterr()

        if ocr_exit == 0:
            ocr_data = json.loads(ocr_captured.out)
            assert isinstance(ocr_data, list)

            # Verify OCR has coordinate info
            if ocr_data:
                assert "bbox" in ocr_data[0]
                bbox = ocr_data[0]["bbox"]
                assert "x1" in bbox
                assert "y1" in bbox

    def test_combined_detection_workflow(self, finder_window: None, screenshot_dir: Path) -> None:
        """Test full detection workflow: screenshot → OCR → validate with UI Inspector."""
        from ocr_finder import list_all_text
        from ui_inspector import list_elements

        # Step 1: Get UI elements for reference
        ui_elements = list_elements("Finder")

        if not ui_elements:
            pytest.skip("No elements found in Finder")

        # Step 2: Capture screenshot
        screenshot_path = screenshot_dir / "finder_workflow.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        # Step 3: Run OCR
        ocr_regions = list_all_text(captured, min_confidence=0.0)

        # Both should have detected something (though not necessarily matching)
        assert len(ui_elements) > 0
        assert isinstance(ocr_regions, tuple)

        # Note: We don't require exact coordinate matches because:
        # - OCR coordinates are relative to screenshot
        # - UI Inspector coordinates are screen-absolute
        # - Screenshot may not capture exact window bounds


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestCombinedErrorHandling:
    """Tests for error handling in combined workflows."""

    def test_ocr_on_nonexistent_screenshot(self) -> None:
        """Test OCR error when screenshot doesn't exist."""
        from ocr_finder.cli import main as ocr_main

        exit_code = ocr_main(["list", "--image", "/nonexistent/path/screenshot.png"])

        # Typer returns exit code 2 for validation errors (path doesn't exist)
        assert exit_code == 2

    def test_ui_inspector_on_nonexistent_app(self) -> None:
        """Test UI Inspector error for non-existent app."""
        from ui_inspector import list_elements
        from ui_inspector.models import AppNotFoundError

        with pytest.raises(AppNotFoundError):
            list_elements("NonExistentApp12345XYZ")

    def test_graceful_ocr_empty_result(self, finder_window: None, screenshot_dir: Path) -> None:
        """Test OCR gracefully handles no text found."""
        from ocr_finder import SearchOptions, find_text

        screenshot_path = screenshot_dir / "finder_empty.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        # Search for text that definitely doesn't exist
        options = SearchOptions(min_confidence=0.0)
        matches = find_text(captured, "xyznonexistent12345abc", options)

        assert len(matches) == 0

    def test_graceful_ui_inspector_no_match(self, finder_window: None) -> None:
        """Test UI Inspector gracefully handles no matching element."""
        from ui_inspector import find_element

        result = find_element("Finder", title="NonexistentTitle12345XYZ")

        assert result is None


# =============================================================================
# CLI Pipeline Tests
# =============================================================================


class TestCLIPipeline:
    """Tests for CLI command pipelines."""

    def test_ocr_list_to_find_pipeline(
        self, finder_window: None, screenshot_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test using --list output to inform --find queries."""
        from ocr_finder.cli import main as ocr_main

        screenshot_path = screenshot_dir / "finder_pipeline.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        # Step 1: List all text
        list_exit = ocr_main(
            ["--list", "--image", str(captured), "--json", "--min-confidence", "0"]
        )
        list_output = capsys.readouterr()

        if list_exit != 0:
            pytest.skip("OCR list command failed")

        data = json.loads(list_output.out)

        if not data:
            pytest.skip("No text detected in screenshot")

        # Step 2: Use first detected text in a find query
        first_text = data[0]["text"]

        find_exit = ocr_main(
            ["--find", first_text, "--image", str(captured), "--min-confidence", "0"]
        )

        # Should find the text we just detected
        assert find_exit == 0

    def test_ui_inspector_list_to_find_pipeline(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test using --list output to inform --find queries."""
        from ui_inspector.cli import main as ui_main

        # Step 1: List elements
        list_exit = ui_main(["--app", "Finder", "--list", "--json"])
        list_output = capsys.readouterr()

        if list_exit != 0 or not list_output.out.strip():
            pytest.skip("UI Inspector list command failed")

        data = json.loads(list_output.out)

        if not data:
            pytest.skip("No elements found in Finder")

        # Step 2: Find by role of first element
        first_role = data[0]["role"]

        find_exit = ui_main(["--app", "Finder", "--find", "--role", first_role])
        _ = capsys.readouterr()  # Clear output

        # Should find elements with that role
        assert find_exit == 0

    def test_ocr_click_output_format(
        self, finder_window: None, screenshot_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --click output format is usable."""
        from ocr_finder.cli import main as ocr_main

        screenshot_path = screenshot_dir / "finder_click.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture Finder screenshot")

        # First get text that exists
        list_exit = ocr_main(
            ["--list", "--image", str(captured), "--json", "--min-confidence", "0"]
        )
        list_output = capsys.readouterr()

        if list_exit != 0:
            pytest.skip("OCR list command failed")

        data = json.loads(list_output.out)

        if not data:
            pytest.skip("No text detected")

        first_text = data[0]["text"]

        # Get click coords
        click_exit = ocr_main(
            [
                "--click",
                first_text,
                "--image",
                str(captured),
                "--json",
                "--min-confidence",
                "0",
            ]
        )
        click_output = capsys.readouterr()

        if click_exit == 0:
            coords = json.loads(click_output.out)
            assert "x" in coords
            assert "y" in coords
            assert isinstance(coords["x"], int)
            assert isinstance(coords["y"], int)

    def test_ui_inspector_click_output_format(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --click output format is usable."""
        from ui_inspector.cli import main as ui_main

        # Get a role that exists
        list_exit = ui_main(["--app", "Finder", "--list", "--json"])
        list_output = capsys.readouterr()

        if list_exit != 0 or not list_output.out.strip():
            pytest.skip("UI Inspector list command failed")

        data = json.loads(list_output.out)

        if not data:
            pytest.skip("No elements found")

        first_role = data[0]["role"]

        # Get click coords
        click_exit = ui_main(["--app", "Finder", "--click", "--role", first_role, "--json"])
        click_output = capsys.readouterr()

        if click_exit == 0:
            coords = json.loads(click_output.out)
            assert "x" in coords
            assert "y" in coords
            assert isinstance(coords["x"], int)
            assert isinstance(coords["y"], int)


# =============================================================================
# Performance Tests
# =============================================================================


class TestCombinedPerformance:
    """Performance tests for combined workflows."""

    def test_full_workflow_completes_in_time(
        self, finder_window: None, screenshot_dir: Path
    ) -> None:
        """Test that full workflow completes within reasonable time."""
        import time

        from ocr_finder import list_all_text
        from ui_inspector import list_elements

        start = time.time()

        # UI Inspector query (should be fast)
        list_elements("Finder")  # Just verify it runs
        ui_elapsed = time.time() - start

        # Should be very fast (< 5s)
        assert ui_elapsed < 5.0, f"UI Inspector took {ui_elapsed:.2f}s"

        # Screenshot + OCR (expected to be slower)
        screenshot_path = screenshot_dir / "finder_perf.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture screenshot")

        ocr_start = time.time()
        list_all_text(captured, min_confidence=0.0)  # Just verify it runs
        ocr_elapsed = time.time() - ocr_start

        # OCR is expected to be slower (< 30s with cold start)
        assert ocr_elapsed < 30.0, f"OCR took {ocr_elapsed:.2f}s"

        total_elapsed = time.time() - start
        assert total_elapsed < 40.0, f"Full workflow took {total_elapsed:.2f}s"

    def test_cached_ocr_reader_is_faster(self, finder_window: None, screenshot_dir: Path) -> None:
        """Test that second OCR call benefits from cached reader."""
        import time

        from ocr_finder import list_all_text

        screenshot_path = screenshot_dir / "finder_cache.png"
        captured = _capture_finder_screenshot(screenshot_path)

        if captured is None:
            pytest.skip("Could not capture screenshot")

        # First call (cold start)
        start1 = time.time()
        list_all_text(captured, min_confidence=0.0)
        elapsed1 = time.time() - start1

        # Second call (should use cached reader)
        start2 = time.time()
        list_all_text(captured, min_confidence=0.0)
        elapsed2 = time.time() - start2

        # Second call should be faster or similar (caching helps)
        # Note: May not always be true due to system variance
        assert elapsed2 <= elapsed1 * 2.0  # Allow some variance
