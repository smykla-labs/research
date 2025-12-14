"""Comprehensive tests for macOS Window Controller script."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from window_controller import (
    ActivationError,
    ScreenshotError,
    WindowError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
    build_filter,
    create_parser,
    filter_windows,
    get_process_info,
    get_spaces_plist,
    get_window_space_mapping,
    main,
    sanitize_app_name,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_window_goland() -> WindowInfo:
    """Create a sample GoLand window."""
    return WindowInfo(
        app_name="GoLand",
        window_title="research – window_controller.py",
        window_id=190027,
        pid=57878,
        layer=0,
        on_screen=True,
        alpha=1.0,
        bounds_x=0.0,
        bounds_y=39.0,
        bounds_width=2056.0,
        bounds_height=1290.0,
        space_index=3,
        exe_path="/Users/dev/Applications/GoLand.app/Contents/MacOS/goland",
        cmdline=["goland", "."],
    )


@pytest.fixture
def sample_window_sandbox() -> WindowInfo:
    """Create a sample JetBrains sandbox IDE window."""
    return WindowInfo(
        app_name="Main",
        window_title="monokai-islands – editor.kt",
        window_id=200123,
        pid=60000,
        layer=0,
        on_screen=True,
        alpha=1.0,
        bounds_x=0.0,
        bounds_y=39.0,
        bounds_width=2056.0,
        bounds_height=1290.0,
        space_index=4,
        exe_path="/Users/dev/.gradle/caches/modules-2/files-2.1/goland-2025.3/jbr/java",
        cmdline=["java", "-Didea.plugin.in.sandbox.mode=true", "com.intellij.idea.Main"],
    )


@pytest.fixture
def sample_window_chrome() -> WindowInfo:
    """Create a sample Chrome window."""
    return WindowInfo(
        app_name="Google Chrome",
        window_title="GitHub - anthropics/claude-code",
        window_id=150000,
        pid=12345,
        layer=0,
        on_screen=True,
        alpha=1.0,
        bounds_x=100.0,
        bounds_y=100.0,
        bounds_width=1200.0,
        bounds_height=800.0,
        space_index=1,
        exe_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        cmdline=["Google Chrome"],
    )


@pytest.fixture
def sample_window_no_title() -> WindowInfo:
    """Create a window without a title (background window)."""
    return WindowInfo(
        app_name="Finder",
        window_title="",
        window_id=100000,
        pid=500,
        layer=1,  # Non-main layer
        on_screen=False,
        alpha=0.0,
        bounds_x=0.0,
        bounds_y=0.0,
        bounds_width=0.0,
        bounds_height=0.0,
        space_index=None,
        exe_path="/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder",
        cmdline=["Finder"],
    )


@pytest.fixture
def sample_windows(
    sample_window_goland: WindowInfo,
    sample_window_sandbox: WindowInfo,
    sample_window_chrome: WindowInfo,
    sample_window_no_title: WindowInfo,
) -> list[WindowInfo]:
    """Create a list of sample windows."""
    return [
        sample_window_goland,
        sample_window_sandbox,
        sample_window_chrome,
        sample_window_no_title,
    ]


@pytest.fixture
def sample_plist_data() -> dict:
    """Create sample spaces plist data structure."""
    return {
        "SpacesDisplayConfiguration": {
            "Management Data": {
                "Monitors": [
                    {
                        "Display Identifier": "Main",
                        "Current Space": {"ManagedSpaceID": 1},
                        "Spaces": [
                            {"ManagedSpaceID": 1, "type": 0, "uuid": ""},
                            {
                                "ManagedSpaceID": 3,
                                "type": 4,
                                "uuid": "ABC123",
                                "TileLayoutManager": {
                                    "TileSpaces": [
                                        {"TileWindowID": 190027},
                                        {"TileWindowID": 200123},
                                    ]
                                },
                            },
                        ],
                    }
                ]
            }
        }
    }


# =============================================================================
# WindowInfo Tests
# =============================================================================


class TestWindowInfo:
    """Tests for WindowInfo dataclass."""

    def test_bounds_property(self, sample_window_goland: WindowInfo) -> None:
        """Test bounds property returns correct dict."""
        bounds = sample_window_goland.bounds
        assert bounds == {
            "x": 0.0,
            "y": 39.0,
            "width": 2056.0,
            "height": 1290.0,
        }

    def test_to_dict(self, sample_window_goland: WindowInfo) -> None:
        """Test to_dict conversion."""
        data = sample_window_goland.to_dict()
        assert data["app_name"] == "GoLand"
        assert data["window_title"] == "research – window_controller.py"
        assert data["window_id"] == 190027
        assert data["pid"] == 57878
        assert "bounds" in data
        assert data["bounds"]["width"] == 2056.0
        # Ensure bounds_x, bounds_y etc are not in the output
        assert "bounds_x" not in data
        assert "bounds_y" not in data


# =============================================================================
# WindowFilter Tests
# =============================================================================


class TestWindowFilter:
    """Tests for WindowFilter dataclass."""

    def test_default_filter(self) -> None:
        """Test default filter values."""
        f = WindowFilter()
        assert f.app_name is None
        assert f.title_pattern is None
        assert f.pid is None
        assert f.path_contains is None
        assert f.path_excludes is None
        assert f.args_contains is None
        assert f.main_window_only is True

    def test_custom_filter(self) -> None:
        """Test custom filter initialization."""
        f = WindowFilter(
            app_name="GoLand",
            title_pattern="research.*",
            main_window_only=False,
        )
        assert f.app_name == "GoLand"
        assert f.title_pattern == "research.*"
        assert f.main_window_only is False


# =============================================================================
# Filter Windows Tests
# =============================================================================


class TestFilterWindows:
    """Tests for filter_windows function."""

    def test_filter_by_app_name(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by app name (partial, case-insensitive)."""
        f = WindowFilter(app_name="goland")
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].app_name == "GoLand"

    def test_filter_by_app_name_partial(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by partial app name."""
        f = WindowFilter(app_name="chrome")
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].app_name == "Google Chrome"

    def test_filter_by_title_pattern(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by title regex pattern."""
        f = WindowFilter(title_pattern=r"research.*")
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert "research" in results[0].window_title

    def test_filter_by_pid(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by PID."""
        f = WindowFilter(pid=57878)
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].pid == 57878

    def test_filter_by_path_contains(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by executable path contains."""
        f = WindowFilter(path_contains=".gradle")
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].app_name == "Main"

    def test_filter_by_path_excludes(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by executable path excludes."""
        f = WindowFilter(app_name="GoLand", path_excludes=".gradle")
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].app_name == "GoLand"

    def test_filter_by_args_contains(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by command line args."""
        f = WindowFilter(args_contains="idea.plugin.in.sandbox.mode")
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].app_name == "Main"

    def test_filter_main_window_only_excludes_no_title(
        self, sample_windows: list[WindowInfo]
    ) -> None:
        """Test main_window_only excludes windows without title."""
        f = WindowFilter(main_window_only=True)
        results = filter_windows(sample_windows, f)
        # Should exclude the no-title window
        assert all(w.window_title for w in results)

    def test_filter_all_windows(self, sample_windows: list[WindowInfo]) -> None:
        """Test disabling main_window_only includes all windows."""
        f = WindowFilter(main_window_only=False)
        results = filter_windows(sample_windows, f)
        assert len(results) == len(sample_windows)

    def test_filter_combined(self, sample_windows: list[WindowInfo]) -> None:
        """Test combining multiple filters."""
        f = WindowFilter(
            app_name="Main",
            args_contains="sandbox",
        )
        results = filter_windows(sample_windows, f)
        assert len(results) == 1
        assert results[0].app_name == "Main"

    def test_filter_no_matches(self, sample_windows: list[WindowInfo]) -> None:
        """Test filter with no matches returns empty list."""
        f = WindowFilter(app_name="NonExistentApp")
        results = filter_windows(sample_windows, f)
        assert results == []


# =============================================================================
# Sanitize App Name Tests
# =============================================================================


class TestSanitizeAppName:
    """Tests for _sanitize_app_name function."""

    def test_valid_app_name(self) -> None:
        """Test valid app names pass through."""
        assert sanitize_app_name("GoLand") == "GoLand"
        assert sanitize_app_name("Google Chrome") == "Google Chrome"
        assert sanitize_app_name("IntelliJ IDEA") == "IntelliJ IDEA"

    def test_app_name_with_parentheses(self) -> None:
        """Test app names with parentheses are valid."""
        assert sanitize_app_name("App (Beta)") == "App (Beta)"

    def test_app_name_with_dots(self) -> None:
        """Test app names with dots are valid."""
        assert sanitize_app_name("Visual Studio Code.app") == "Visual Studio Code.app"

    def test_app_name_with_quotes_rejected(self) -> None:
        """Test double quotes are rejected (security measure)."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name('App with "quotes"')

    def test_invalid_characters_rejected(self) -> None:
        """Test invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App; rm -rf /")

        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App`whoami`")

        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App$PATH")


# =============================================================================
# Space Plist Tests
# =============================================================================


class TestSpacesPlist:
    """Tests for spaces plist functions."""

    def test_get_window_space_mapping(self, sample_plist_data: dict) -> None:
        """Test window to space mapping extraction."""
        mapping = get_window_space_mapping(sample_plist_data)
        # Space index should be 2 (second space, 1-indexed)
        assert mapping.get(190027) == 2
        assert mapping.get(200123) == 2

    def test_get_window_space_mapping_empty(self) -> None:
        """Test empty plist returns empty mapping."""
        mapping = get_window_space_mapping({})
        assert mapping == {}

    @patch("window_controller.core.subprocess.run")
    def test_get_spaces_plist_success(self, mock_run: MagicMock) -> None:
        """Test successful plist reading."""
        import plistlib

        plist_bytes = plistlib.dumps({"test": "data"})
        mock_run.return_value = MagicMock(returncode=0, stdout=plist_bytes)

        result = get_spaces_plist()
        assert result == {"test": "data"}

    @patch("window_controller.core.subprocess.run")
    def test_get_spaces_plist_failure(self, mock_run: MagicMock) -> None:
        """Test plist reading failure raises PlistReadError."""
        from window_controller.models import PlistReadError

        mock_run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"error")

        with pytest.raises(PlistReadError, match="Cannot read spaces plist"):
            get_spaces_plist()


# =============================================================================
# Process Info Tests
# =============================================================================


class TestProcessInfo:
    """Tests for process info retrieval."""

    @patch("window_controller.core._get_psutil")
    def test_get_process_info_success(self, mock_get_psutil: MagicMock) -> None:
        """Test successful process info retrieval."""
        mock_psutil = MagicMock()
        mock_proc = MagicMock()
        mock_proc.exe.return_value = "/usr/bin/app"
        mock_proc.cmdline.return_value = ["app", "--flag"]
        mock_psutil.Process.return_value = mock_proc
        mock_get_psutil.return_value = mock_psutil

        exe_path, cmdline = get_process_info(12345)
        assert exe_path == "/usr/bin/app"
        assert cmdline == ["app", "--flag"]

    @patch("window_controller.core._get_psutil")
    def test_get_process_info_no_such_process(self, mock_get_psutil: MagicMock) -> None:
        """Test process info when process doesn't exist."""
        mock_psutil = MagicMock()
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception
        mock_psutil.ZombieProcess = Exception
        mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess()
        mock_get_psutil.return_value = mock_psutil

        exe_path, cmdline = get_process_info(99999)
        assert exe_path is None
        assert cmdline == []


# =============================================================================
# CLI Parser Tests
# =============================================================================


class TestCLIParser:
    """Tests for CLI argument parser."""

    def test_list_action(self) -> None:
        """Test --list argument."""
        parser = create_parser()
        args = parser.parse_args(["--list"])
        assert args.list is True

    def test_find_action(self) -> None:
        """Test --find argument."""
        parser = create_parser()
        args = parser.parse_args(["--find", "GoLand"])
        assert args.find == "GoLand"

    def test_find_action_empty(self) -> None:
        """Test --find with no app name."""
        parser = create_parser()
        args = parser.parse_args(["--find"])
        assert args.find == ""

    def test_activate_action(self) -> None:
        """Test --activate argument."""
        parser = create_parser()
        args = parser.parse_args(["--activate", "GoLand"])
        assert args.activate == "GoLand"

    def test_screenshot_action(self) -> None:
        """Test --screenshot argument."""
        parser = create_parser()
        args = parser.parse_args(["--screenshot", "GoLand", "--output", "test.png"])
        assert args.screenshot == "GoLand"
        assert args.output == "test.png"

    def test_filter_options(self) -> None:
        """Test filter options."""
        parser = create_parser()
        args = parser.parse_args([
            "--find", "Main",
            "--title", "project.*",
            "--pid", "12345",
            "--path-contains", ".gradle",
            "--args-contains", "sandbox",
        ])
        assert args.find == "Main"
        assert args.title == "project.*"
        assert args.pid == 12345
        assert args.path_contains == ".gradle"
        assert args.args_contains == "sandbox"

    def test_screenshot_options(self) -> None:
        """Test screenshot-specific options."""
        parser = create_parser()
        args = parser.parse_args([
            "--screenshot", "GoLand",
            "--no-activate",
            "--settle-ms", "2000",
        ])
        assert args.screenshot == "GoLand"
        assert args.no_activate is True
        assert args.settle_ms == 2000

    def test_json_output(self) -> None:
        """Test --json flag."""
        parser = create_parser()
        args = parser.parse_args(["--find", "GoLand", "--json"])
        assert args.json is True


class TestBuildFilter:
    """Tests for build_filter function."""

    def test_build_filter_from_find(self) -> None:
        """Test building filter from --find args."""
        parser = create_parser()
        args = parser.parse_args(["--find", "GoLand", "--title", "research"])
        f = build_filter(args)
        assert f.app_name == "GoLand"
        assert f.title_pattern == "research"

    def test_build_filter_from_activate(self) -> None:
        """Test building filter from --activate args."""
        parser = create_parser()
        args = parser.parse_args(["--activate", "Chrome"])
        f = build_filter(args)
        assert f.app_name == "Chrome"

    def test_build_filter_empty_find(self) -> None:
        """Test building filter with empty --find."""
        parser = create_parser()
        args = parser.parse_args(["--find", "--title", "test"])
        f = build_filter(args)
        assert f.app_name is None
        assert f.title_pattern == "test"


# =============================================================================
# Main Function Tests
# =============================================================================


class TestMain:
    """Tests for main entry point."""

    def test_no_action_shows_help(self) -> None:
        """Test no action returns 1."""
        result = main([])
        assert result == 1

    @patch("window_controller.cli.get_all_windows")
    def test_list_action(self, mock_get_windows: MagicMock) -> None:
        """Test --list action."""
        mock_get_windows.return_value = []
        result = main(["--list"])
        assert result == 0
        # get_all_windows may be called multiple times (once in main, once in list_all_windows)
        assert mock_get_windows.called

    @patch("window_controller.cli.find_windows")
    def test_find_no_results(self, mock_find: MagicMock) -> None:
        """Test --find with no results."""
        mock_find.return_value = []
        result = main(["--find", "NonExistent"])
        assert result == 1

    @patch("window_controller.cli.find_windows")
    def test_find_with_json(
        self,
        mock_find: MagicMock,
        sample_window_goland: WindowInfo,
        capsys,
    ) -> None:
        """Test --find with --json output."""
        mock_find.return_value = [sample_window_goland]
        result = main(["--find", "GoLand", "--json"])
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["app_name"] == "GoLand"


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for custom exceptions."""

    def test_window_error_base(self) -> None:
        """Test WindowError is base for all window exceptions."""
        assert issubclass(WindowNotFoundError, WindowError)
        assert issubclass(ActivationError, WindowError)
        assert issubclass(ScreenshotError, WindowError)

    def test_window_not_found_error(self) -> None:
        """Test WindowNotFoundError."""
        error = WindowNotFoundError("No window found")
        assert str(error) == "No window found"

    def test_activation_error(self) -> None:
        """Test ActivationError."""
        error = ActivationError("Failed to activate")
        assert str(error) == "Failed to activate"

    def test_screenshot_error(self) -> None:
        """Test ScreenshotError."""
        error = ScreenshotError("Failed to capture")
        assert str(error) == "Failed to capture"
