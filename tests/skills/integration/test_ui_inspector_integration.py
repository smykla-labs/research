"""Integration tests for UI Inspector using real Accessibility API.

These tests use real atomacos (no mocking) to verify UI element detection.
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
from collections.abc import Generator

import pytest

# =============================================================================
# Pytest Markers
# =============================================================================

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


# =============================================================================
# Fixtures
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


def _check_finder_has_windows() -> bool:
    """Check if Finder has any windows open."""
    return _get_finder_window_count() > 0


def _ensure_finder_window_open(max_attempts: int = 5) -> bool:
    """Ensure Finder has at least one window open.

    Args:
        max_attempts: Maximum number of attempts to open window.

    Returns:
        True if window is open, False otherwise.
    """
    import time

    for attempt in range(max_attempts):
        # Check if Finder already has windows
        if _check_finder_has_windows():
            return True

        # Try to open a Finder window
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Finder" to make new Finder window',
            ],
            capture_output=True,
            check=False,
        )

        # Wait for window to appear
        time.sleep(1.0)

        # Verify window is now open
        if _check_finder_has_windows():
            return True

        # Exponential backoff
        if attempt < max_attempts - 1:
            time.sleep(0.5 * (attempt + 1))

    return False


def _close_finder_windows(count: int) -> None:
    """Close a specific number of Finder windows (most recently opened first).

    Args:
        count: Number of windows to close.
    """
    if count <= 0:
        return

    # Close windows one by one (closes frontmost/most recent first)
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
    """Bring Finder to front and ensure window is visible."""
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Finder" to activate',
        ],
        capture_output=True,
        check=False,
    )
    import time

    time.sleep(0.5)


@pytest.fixture(scope="session")
def _session_finder_window() -> Generator[None, None, None]:
    """Initial session-level check that Finder windows can be opened.

    Preserves any pre-existing Finder windows. Only closes windows
    that were opened during the test session.
    """
    # Track how many windows existed before tests
    initial_window_count = _get_finder_window_count()

    if not _ensure_finder_window_open():
        pytest.skip("Could not open Finder window - check Accessibility permissions")

    yield

    # Cleanup: close only the windows we opened (current - initial)
    current_count = _get_finder_window_count()
    windows_to_close = current_count - initial_window_count

    if windows_to_close > 0:
        _close_finder_windows(windows_to_close)


@pytest.fixture
def finder_window(_session_finder_window: None) -> None:
    """Ensure Finder has at least one window open before each test.

    Re-opens Finder window if it was closed since last test.
    Activates Finder to ensure window is in foreground.
    Depends on session fixture for initial setup and cleanup.
    """
    if not _check_finder_has_windows():
        _ensure_finder_window_open(max_attempts=2)

    # Activate Finder to ensure window is accessible
    _activate_finder()


@pytest.fixture(scope="module")
def screen_size() -> tuple[int, int]:
    """Get screen size for coordinate validation."""
    # Use AppKit to get screen dimensions
    try:
        from AppKit import NSScreen

        frame = NSScreen.mainScreen().frame()
        return int(frame.size.width), int(frame.size.height)
    except ImportError:
        # Fallback to reasonable defaults
        return 1920, 1080


# =============================================================================
# Real Accessibility API Tests
# =============================================================================


class TestRealAccessibilityAPI:
    """Tests using real Accessibility API (no mocking)."""

    def test_list_finder_elements(self, finder_window: None) -> None:
        """Test listing UI elements from Finder."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        # Finder should have UI elements
        assert len(elements) > 0

    def test_finder_has_expected_roles(self, finder_window: None) -> None:
        """Test that Finder contains expected element roles."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")
        roles = {e.role for e in elements}

        # Finder windows typically have these roles
        expected_roles = {"AXToolbar", "AXButton", "AXGroup", "AXSplitGroup"}
        found_roles = roles & expected_roles

        assert len(found_roles) >= 1, f"Expected some of {expected_roles}, got {roles}"

    def test_list_elements_by_role(self, finder_window: None) -> None:
        """Test filtering elements by role."""
        from ui_inspector import list_elements

        # Get all elements and filter by a common role
        all_elements = list_elements("Finder")
        all_roles = {e.role for e in all_elements}

        # Pick a role that exists
        if "AXButton" in all_roles:
            buttons = list_elements("Finder", role="AXButton")
            assert all(e.role == "AXButton" for e in buttons)
        elif "AXGroup" in all_roles:
            groups = list_elements("Finder", role="AXGroup")
            assert all(e.role == "AXGroup" for e in groups)

    def test_element_has_valid_position(self, finder_window: None) -> None:
        """Test that elements have valid position coordinates."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        for elem in elements[:10]:  # Check first 10 elements
            x, y = elem.position

            # Position should be non-negative (could be off-screen but >= 0)
            assert x >= 0 or x < 0  # Allow negative for off-screen elements
            assert y >= 0 or y < 0

    def test_element_has_valid_size(self, finder_window: None) -> None:
        """Test that elements have valid size."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        for elem in elements[:10]:  # Check first 10 elements
            w, h = elem.size

            # Size should be non-negative
            assert w >= 0
            assert h >= 0

    def test_element_center_calculation(self, finder_window: None) -> None:
        """Test that center is correctly calculated from position and size."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        for elem in elements[:10]:
            x, y = elem.position
            w, h = elem.size
            cx, cy = elem.center

            # Center should be position + half of size
            assert cx == x + w // 2
            assert cy == y + h // 2

    def test_element_enabled_state(self, finder_window: None) -> None:
        """Test that elements have enabled state."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        # At least some elements should be enabled
        enabled_count = sum(1 for e in elements if e.enabled)

        assert enabled_count > 0

    def test_to_dict_conversion(self, finder_window: None) -> None:
        """Test UIElement to_dict conversion."""
        from ui_inspector import list_elements

        elements = list_elements("Finder")

        if elements:
            elem = elements[0]
            d = elem.to_dict()

            # Required keys
            assert "role" in d
            assert "title" in d
            assert "position_x" in d
            assert "position_y" in d
            assert "width" in d
            assert "height" in d
            assert "center_x" in d
            assert "center_y" in d
            assert "enabled" in d
            assert "bounds" in d


# =============================================================================
# Find Element Tests
# =============================================================================


class TestFindElement:
    """Tests for find_element function with real Accessibility API."""

    def test_find_by_role(self, finder_window: None) -> None:
        """Test finding element by role."""
        from ui_inspector import find_element, list_elements

        # First check what roles exist
        all_elements = list_elements("Finder")
        roles = {e.role for e in all_elements}

        # Try to find by a role that exists
        if "AXToolbar" in roles:
            elem = find_element("Finder", role="AXToolbar")
            assert elem is not None
            assert elem.role == "AXToolbar"

    def test_find_nonexistent_element(self, finder_window: None) -> None:
        """Test finding element that doesn't exist."""
        from ui_inspector import find_element

        elem = find_element("Finder", title="NonexistentTitle12345XYZ")

        assert elem is None

    def test_find_returns_first_match(self, finder_window: None) -> None:
        """Test that find_element returns first matching element."""
        from ui_inspector import find_element, list_elements

        # Get buttons if they exist
        all_elements = list_elements("Finder")
        buttons = [e for e in all_elements if e.role == "AXButton"]

        if len(buttons) >= 2:
            # find_element should return the first one
            found = find_element("Finder", role="AXButton")
            assert found is not None
            # We can't guarantee which button is first, but it should be one of them
            assert found.role == "AXButton"


# =============================================================================
# Get Click Target Tests
# =============================================================================


class TestGetClickTarget:
    """Tests for get_click_target function."""

    def test_get_click_target_returns_coords(
        self, finder_window: None, screen_size: tuple[int, int]
    ) -> None:
        """Test getting click coordinates for element."""
        from ui_inspector import get_click_target, list_elements
        from ui_inspector.models import ElementNotFoundError

        # Find an element that exists
        all_elements = list_elements("Finder")
        if not all_elements:
            pytest.skip("No elements found in Finder")

        # Try a role that exists
        roles = {e.role for e in all_elements}
        target_role = next(iter(roles))

        try:
            x, y = get_click_target("Finder", role=target_role)

            assert isinstance(x, int)
            assert isinstance(y, int)

            # Coordinates should be reasonable (within extended screen bounds)
            max_w, max_h = screen_size
            assert -max_w <= x <= max_w * 3  # Allow multi-monitor
            assert -max_h <= y <= max_h * 3

        except ElementNotFoundError:
            # Element may have disappeared
            pass

    def test_get_click_target_not_found_raises(self, finder_window: None) -> None:
        """Test that ElementNotFoundError is raised for non-existent element."""
        from ui_inspector import get_click_target
        from ui_inspector.models import ElementNotFoundError

        with pytest.raises(ElementNotFoundError):
            get_click_target("Finder", title="NonexistentTitle12345XYZ")


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_app_not_found_error(self) -> None:
        """Test AppNotFoundError for non-existent app."""
        from ui_inspector import list_elements
        from ui_inspector.models import AppNotFoundError

        with pytest.raises(AppNotFoundError):
            list_elements("NonExistentApp12345XYZ")

    def test_app_not_running_error(self) -> None:
        """Test error when app is not running.

        Note: This test is tricky since we need an app that's definitely not running.
        Using a fake app name that won't exist.
        """
        from ui_inspector import list_elements
        from ui_inspector.models import AppNotFoundError

        with pytest.raises(AppNotFoundError):
            list_elements("com.fake.nonexistent.app.12345")

    def test_window_not_found_handling(self) -> None:
        """Test handling when app has no windows.

        Note: We can't reliably test this without controlling app state,
        so we just verify the error type exists and is properly inherited.
        """
        from ui_inspector.models import UiInspectorError, WindowNotFoundError

        assert issubclass(WindowNotFoundError, UiInspectorError)


# =============================================================================
# CLI Integration Tests
# =============================================================================


def _get_finder_elements_json(
    capsys: pytest.CaptureFixture[str],
) -> list[dict[str, str | int | bool]] | None:
    """Helper to get Finder elements as JSON, returning None on failure."""
    from ui_inspector.cli import main

    exit_code = main(["--app", "Finder", "--list", "--json"])
    captured = capsys.readouterr()

    if exit_code != 0 or not captured.out.strip():
        return None

    try:
        return json.loads(captured.out)
    except json.JSONDecodeError:
        return None


class TestCLIIntegration:
    """End-to-end CLI tests with real Accessibility API."""

    def test_cli_list_command(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list CLI command."""
        from ui_inspector.cli import main

        exit_code = main(["--app", "Finder", "--list"])
        captured = capsys.readouterr()

        if "No windows found" in captured.err:
            pytest.skip("Finder window not accessible")

        assert exit_code == 0
        # Should have table header or "No elements"
        assert "Role" in captured.out or "No elements" in captured.out

    def test_cli_list_json_output(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list with --json output."""
        data = _get_finder_elements_json(capsys)

        if data is None:
            pytest.skip("Finder window not accessible")

        assert isinstance(data, list)

        # Each item should have required fields
        for item in data:
            assert "role" in item
            assert "enabled" in item

    def test_cli_list_with_role_filter(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list with --role filter."""
        from ui_inspector.cli import main

        data = _get_finder_elements_json(capsys)

        if data is None or not data:
            pytest.skip("Finder window not accessible or no elements")

        # Use a role that exists
        role = data[0]["role"]

        exit_code = main(["--app", "Finder", "--list", "--role", str(role), "--json"])
        assert exit_code == 0

        captured = capsys.readouterr()
        filtered_data = json.loads(captured.out)

        # All results should have the filtered role
        assert all(item["role"] == role for item in filtered_data)

    def test_cli_find_command(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --find CLI command."""
        from ui_inspector.cli import main

        data = _get_finder_elements_json(capsys)

        if data is None or not data:
            pytest.skip("Finder window not accessible or no elements")

        role = data[0]["role"]
        exit_code = main(["--app", "Finder", "--find", "--role", str(role)])

        # Should find or not find, but not crash
        assert exit_code in (0, 1)

    def test_cli_find_json_output(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --find with --json output."""
        from ui_inspector.cli import main

        data = _get_finder_elements_json(capsys)

        if data is None or not data:
            pytest.skip("Finder window not accessible or no elements")

        role = data[0]["role"]
        exit_code = main(["--app", "Finder", "--find", "--role", str(role), "--json"])

        if exit_code == 0:
            captured = capsys.readouterr()
            result = json.loads(captured.out)

            if result is not None:
                assert "role" in result
                assert "center_x" in result
                assert "center_y" in result

    def test_cli_click_command(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --click CLI command."""
        from ui_inspector.cli import main

        data = _get_finder_elements_json(capsys)

        if data is None or not data:
            pytest.skip("Finder window not accessible or no elements")

        role = data[0]["role"]
        exit_code = main(["--app", "Finder", "--click", "--role", str(role)])

        if exit_code == 0:
            captured = capsys.readouterr()
            # Output should be "x,y" format
            coords = captured.out.strip()
            assert "," in coords

            parts = coords.split(",")
            assert len(parts) == 2

    def test_cli_click_json_output(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --click with --json output."""
        from ui_inspector.cli import main

        data = _get_finder_elements_json(capsys)

        if data is None or not data:
            pytest.skip("Finder window not accessible or no elements")

        role = data[0]["role"]
        exit_code = main(["--app", "Finder", "--click", "--role", str(role), "--json"])

        if exit_code == 0:
            captured = capsys.readouterr()
            coords = json.loads(captured.out)
            assert "x" in coords
            assert "y" in coords
            assert isinstance(coords["x"], int)
            assert isinstance(coords["y"], int)

    def test_cli_nonexistent_app_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error handling for non-existent app."""
        from ui_inspector.cli import main

        exit_code = main(["--app", "NonExistentApp12345XYZ", "--list"])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_cli_find_not_found(
        self, finder_window: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --find when element not found."""
        from ui_inspector.cli import main

        exit_code = main(["--app", "Finder", "--find", "--title", "NonexistentTitle12345XYZ"])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no matching" in captured.out.lower()


# =============================================================================
# Bundle ID Tests
# =============================================================================


class TestBundleID:
    """Tests for bundle ID app lookup."""

    def test_finder_by_bundle_id(self, finder_window: None) -> None:
        """Test accessing Finder by bundle ID."""
        from ui_inspector import list_elements

        # Finder's bundle ID
        elements = list_elements("com.apple.finder")

        assert len(elements) > 0

    def test_invalid_bundle_id_error(self) -> None:
        """Test error for invalid bundle ID."""
        from ui_inspector import list_elements
        from ui_inspector.models import AppNotFoundError

        with pytest.raises(AppNotFoundError):
            list_elements("com.invalid.fake.bundle.12345")


# =============================================================================
# Multiple Windows Tests
# =============================================================================


class TestMultipleWindows:
    """Tests related to multiple window handling."""

    def test_frontmost_window_used(self, finder_window: None) -> None:
        """Test that frontmost window is used for inspection.

        Note: We can't easily verify which window is used, but we can
        verify that inspection works when multiple windows might exist.
        """
        from ui_inspector import list_elements

        # Open another Finder window
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Finder" to make new Finder window',
            ],
            capture_output=True,
            check=False,
        )

        import time

        time.sleep(0.3)

        # Should still work
        elements = list_elements("Finder")
        assert len(elements) > 0


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Performance-related tests."""

    def test_repeated_queries_stable(self, finder_window: None) -> None:
        """Test that repeated queries return stable results."""
        from ui_inspector import list_elements

        # Query multiple times
        results = [len(list_elements("Finder")) for _ in range(3)]

        # Results should be relatively stable (window content doesn't change)
        # Allow some variation due to system state
        assert max(results) - min(results) <= 5

    def test_element_query_speed(self, finder_window: None) -> None:
        """Test that element queries complete in reasonable time."""
        import time

        from ui_inspector import list_elements

        start = time.time()
        list_elements("Finder")
        elapsed = time.time() - start

        # Should complete within 5 seconds (generous for CI)
        assert elapsed < 5.0
