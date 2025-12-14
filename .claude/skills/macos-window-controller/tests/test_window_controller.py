"""Comprehensive tests for macos-window-controller."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from scripts.actions import activate_window, sanitize_app_name, take_screenshot
from scripts.cli import build_filter, create_parser, main
from scripts.core import (
    filter_windows,
    find_window,
    get_process_info,
    get_spaces_plist,
    get_window_space_mapping,
)
from scripts.models import (
    ActivationError,
    PlistReadError,
    ScreenshotError,
    WindowFilter,
    WindowInfo,
    WindowNotFoundError,
)

# -- Fixtures --


@pytest.fixture
def sample_window() -> WindowInfo:
    """Create a sample window for testing."""
    return WindowInfo(
        app_name="GoLand",
        window_title="research – core.py",
        window_id=1234,
        pid=5678,
        layer=0,
        on_screen=True,
        alpha=1.0,
        bounds_x=100.0,
        bounds_y=200.0,
        bounds_width=1200.0,
        bounds_height=800.0,
        space_index=2,
        exe_path="/Applications/GoLand.app/Contents/MacOS/goland",
        cmdline=("/Applications/GoLand.app/Contents/MacOS/goland", "-project", "/path/to/research"),
    )


@pytest.fixture
def sample_windows(sample_window: WindowInfo) -> list[WindowInfo]:
    """Create a list of sample windows."""
    return [
        sample_window,
        WindowInfo(
            app_name="Terminal",
            window_title="bash",
            window_id=2345,
            pid=9012,
            layer=0,
            on_screen=True,
            alpha=1.0,
            bounds_x=0.0,
            bounds_y=0.0,
            bounds_width=800.0,
            bounds_height=600.0,
            space_index=1,
            exe_path="/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal",
            cmdline=("/bin/bash",),
        ),
        WindowInfo(
            app_name="Safari",
            window_title="",  # No title (background window)
            window_id=3456,
            pid=3456,
            layer=0,
            on_screen=False,
            alpha=0.0,
            bounds_x=0.0,
            bounds_y=0.0,
            bounds_width=0.0,
            bounds_height=0.0,
            space_index=None,
            exe_path="/Applications/Safari.app/Contents/MacOS/Safari",
            cmdline=("/Applications/Safari.app/Contents/MacOS/Safari",),
        ),
        WindowInfo(
            app_name="Dock",
            window_title="",
            window_id=4567,
            pid=1000,
            layer=-20,  # Non-main layer
            on_screen=True,
            alpha=1.0,
            bounds_x=0.0,
            bounds_y=0.0,
            bounds_width=1920.0,
            bounds_height=50.0,
            space_index=None,
            exe_path="/System/Library/CoreServices/Dock.app/Contents/MacOS/Dock",
            cmdline=(),
        ),
    ]


@pytest.fixture
def sample_plist_data() -> dict:
    """Sample spaces plist structure."""
    return {
        "SpacesDisplayConfiguration": {
            "Management Data": {
                "Monitors": [
                    {
                        "Spaces": [
                            {
                                "TileLayoutManager": {
                                    "TileSpaces": [
                                        {"TileWindowID": 1111},
                                        {"TileWindowID": 2222},
                                    ]
                                }
                            },
                            {
                                "TileLayoutManager": {
                                    "TileSpaces": [
                                        {"TileWindowID": 3333},
                                    ]
                                }
                            },
                        ]
                    }
                ]
            }
        }
    }


# -- TestWindowInfo --


class TestWindowInfo:
    """Tests for WindowInfo dataclass."""

    def test_bounds_property(self, sample_window: WindowInfo) -> None:
        """Test bounds property returns correct dict."""
        bounds = sample_window.bounds
        assert bounds == {
            "x": 100.0,
            "y": 200.0,
            "width": 1200.0,
            "height": 800.0,
        }

    def test_to_dict_contains_bounds(self, sample_window: WindowInfo) -> None:
        """Test to_dict includes bounds and removes individual fields."""
        data = sample_window.to_dict()
        assert "bounds" in data
        assert data["bounds"]["width"] == 1200.0
        assert "bounds_x" not in data
        assert "bounds_y" not in data
        assert "bounds_width" not in data
        assert "bounds_height" not in data

    def test_to_dict_contains_all_fields(self, sample_window: WindowInfo) -> None:
        """Test to_dict includes all expected fields."""
        data = sample_window.to_dict()
        expected_fields = {
            "app_name",
            "window_title",
            "window_id",
            "pid",
            "layer",
            "on_screen",
            "alpha",
            "bounds",
            "space_index",
            "exe_path",
            "cmdline",
        }
        assert set(data.keys()) == expected_fields

    def test_default_values(self) -> None:
        """Test WindowInfo with minimal required fields."""
        window = WindowInfo(
            app_name="Test",
            window_title="Title",
            window_id=1,
            pid=1,
            layer=0,
            on_screen=True,
            alpha=1.0,
            bounds_x=0.0,
            bounds_y=0.0,
            bounds_width=100.0,
            bounds_height=100.0,
        )
        assert window.space_index is None
        assert window.exe_path is None
        assert window.cmdline == ()


# -- TestWindowFilter --


class TestWindowFilter:
    """Tests for WindowFilter dataclass."""

    def test_default_values(self) -> None:
        """Test WindowFilter with default values."""
        f = WindowFilter()
        assert f.app_name is None
        assert f.title_pattern is None
        assert f.pid is None
        assert f.path_contains is None
        assert f.path_excludes is None
        assert f.args_contains is None
        assert f.main_window_only is True

    def test_with_all_fields(self) -> None:
        """Test WindowFilter with all fields set."""
        f = WindowFilter(
            app_name="GoLand",
            title_pattern=".*\\.py",
            pid=1234,
            path_contains="/Applications",
            path_excludes=".gradle",
            args_contains="--project",
            main_window_only=False,
        )
        assert f.app_name == "GoLand"
        assert f.title_pattern == ".*\\.py"
        assert f.pid == 1234
        assert f.path_contains == "/Applications"
        assert f.path_excludes == ".gradle"
        assert f.args_contains == "--project"
        assert f.main_window_only is False


# -- TestGetSpacesPlist --


class TestGetSpacesPlist:
    """Tests for get_spaces_plist function."""

    def test_success(self, sample_plist_data: dict) -> None:
        """Test successful plist read."""
        import plistlib

        plist_bytes = plistlib.dumps(sample_plist_data)

        with mock.patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=plist_bytes,
            )
            result = get_spaces_plist()
            assert result == sample_plist_data

    def test_failure_command_error(self) -> None:
        """Test plist read failure raises PlistReadError."""
        with mock.patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=1,
                stderr=b"File not found",
            )
            with pytest.raises(PlistReadError) as exc_info:
                get_spaces_plist()
            assert "Cannot read spaces plist" in str(exc_info.value)

    def test_invalid_plist_format(self) -> None:
        """Test invalid plist format raises PlistReadError."""
        with mock.patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=b"not valid plist data",
            )
            with pytest.raises(PlistReadError) as exc_info:
                get_spaces_plist()
            assert "Invalid plist format" in str(exc_info.value)


# -- TestGetWindowSpaceMapping --


class TestGetWindowSpaceMapping:
    """Tests for get_window_space_mapping function."""

    def test_parsing(self, sample_plist_data: dict) -> None:
        """Test window-to-space mapping extraction."""
        mapping = get_window_space_mapping(sample_plist_data)
        assert mapping == {
            1111: 1,
            2222: 1,
            3333: 2,
        }

    def test_empty_plist(self) -> None:
        """Test empty plist returns empty mapping."""
        mapping = get_window_space_mapping({})
        assert mapping == {}

    def test_missing_monitors(self) -> None:
        """Test missing Monitors key."""
        plist = {"SpacesDisplayConfiguration": {"Management Data": {}}}
        mapping = get_window_space_mapping(plist)
        assert mapping == {}

    def test_multiple_monitors(self) -> None:
        """Test multiple monitors with separate spaces."""
        plist = {
            "SpacesDisplayConfiguration": {
                "Management Data": {
                    "Monitors": [
                        {
                            "Spaces": [
                                {"TileLayoutManager": {"TileSpaces": [{"TileWindowID": 100}]}},
                            ]
                        },
                        {
                            "Spaces": [
                                {"TileLayoutManager": {"TileSpaces": [{"TileWindowID": 200}]}},
                                {"TileLayoutManager": {"TileSpaces": [{"TileWindowID": 300}]}},
                            ]
                        },
                    ]
                }
            }
        }
        mapping = get_window_space_mapping(plist)
        # Each monitor starts counting from 1
        assert mapping == {100: 1, 200: 1, 300: 2}


# -- TestGetProcessInfo --


class TestGetProcessInfo:
    """Tests for get_process_info function."""

    def test_success(self) -> None:
        """Test successful process info retrieval."""
        mock_proc = mock.Mock()
        mock_proc.exe.return_value = "/usr/bin/python"
        mock_proc.cmdline.return_value = ["python", "-m", "pytest"]

        with mock.patch("scripts.core._get_psutil") as mock_psutil:
            mock_psutil.return_value.Process.return_value = mock_proc
            exe_path, cmdline = get_process_info(1234)
            assert exe_path == "/usr/bin/python"
            assert cmdline == ["python", "-m", "pytest"]

    def test_no_such_process(self) -> None:
        """Test handling of NoSuchProcess exception."""
        with mock.patch("scripts.core._get_psutil") as mock_psutil:
            psutil_mod = mock_psutil.return_value
            psutil_mod.NoSuchProcess = Exception
            psutil_mod.AccessDenied = Exception
            psutil_mod.ZombieProcess = Exception
            psutil_mod.Process.side_effect = psutil_mod.NoSuchProcess("No such process")
            exe_path, cmdline = get_process_info(9999)
            assert exe_path is None
            assert cmdline == []

    def test_access_denied(self) -> None:
        """Test handling of AccessDenied exception."""
        with mock.patch("scripts.core._get_psutil") as mock_psutil:
            psutil_mod = mock_psutil.return_value
            psutil_mod.NoSuchProcess = Exception
            psutil_mod.AccessDenied = Exception
            psutil_mod.ZombieProcess = Exception
            psutil_mod.Process.side_effect = psutil_mod.AccessDenied("Access denied")
            exe_path, cmdline = get_process_info(1)
            assert exe_path is None
            assert cmdline == []


# -- TestFilterWindows --


class TestFilterWindows:
    """Tests for filter_windows and _matches_filter functions."""

    def test_filter_by_app_name(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by app name (case-insensitive, partial)."""
        f = WindowFilter(app_name="goland", main_window_only=False)
        result = filter_windows(sample_windows, f)
        assert len(result) == 1
        assert result[0].app_name == "GoLand"

    def test_filter_by_title_pattern(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by title regex pattern."""
        f = WindowFilter(title_pattern=r".*\.py", main_window_only=False)
        result = filter_windows(sample_windows, f)
        assert len(result) == 1
        assert "core.py" in result[0].window_title

    def test_filter_by_pid(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by process ID."""
        f = WindowFilter(pid=9012, main_window_only=False)
        result = filter_windows(sample_windows, f)
        assert len(result) == 1
        assert result[0].app_name == "Terminal"

    def test_filter_by_path_contains(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by executable path contains."""
        f = WindowFilter(path_contains="Utilities", main_window_only=False)
        result = filter_windows(sample_windows, f)
        assert len(result) == 1
        assert result[0].app_name == "Terminal"

    def test_filter_by_path_excludes(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by executable path excludes."""
        f = WindowFilter(path_excludes="System", main_window_only=False)
        result = filter_windows(sample_windows, f)
        # Should exclude Terminal, Safari, and Dock (all in System paths)
        assert all("System" not in (w.exe_path or "") for w in result)

    def test_filter_by_args_contains(self, sample_windows: list[WindowInfo]) -> None:
        """Test filtering by command line args."""
        f = WindowFilter(args_contains="research", main_window_only=False)
        result = filter_windows(sample_windows, f)
        assert len(result) == 1
        assert result[0].app_name == "GoLand"

    def test_main_window_only_filter(self, sample_windows: list[WindowInfo]) -> None:
        """Test main_window_only excludes non-layer-0 and empty-title windows."""
        f = WindowFilter(main_window_only=True)
        result = filter_windows(sample_windows, f)
        # Should exclude Dock (layer != 0) and Safari (empty title)
        assert all(w.layer == 0 and w.window_title for w in result)

    def test_combined_filters(self, sample_windows: list[WindowInfo]) -> None:
        """Test multiple filter criteria combined."""
        f = WindowFilter(
            app_name="GoLand",
            title_pattern=r"core",
            path_contains="Applications",
            main_window_only=False,
        )
        result = filter_windows(sample_windows, f)
        assert len(result) == 1
        assert result[0].app_name == "GoLand"


# -- TestFindWindow --


class TestFindWindow:
    """Tests for find_window function."""

    def test_single_match(self, sample_windows: list[WindowInfo]) -> None:
        """Test finding a single matching window."""
        with mock.patch("scripts.core.get_all_windows", return_value=sample_windows):
            result = find_window(WindowFilter(app_name="Terminal"))
            assert result is not None
            assert result.app_name == "Terminal"

    def test_no_match(self, sample_windows: list[WindowInfo]) -> None:
        """Test finding no matching window returns None."""
        with mock.patch("scripts.core.get_all_windows", return_value=sample_windows):
            result = find_window(WindowFilter(app_name="NonExistent"))
            assert result is None

    def test_multiple_matches_returns_first(self) -> None:
        """Test multiple matches returns first window."""
        windows = [
            WindowInfo(
                app_name="Terminal",
                window_title="session1",
                window_id=1,
                pid=100,
                layer=0,
                on_screen=True,
                alpha=1.0,
                bounds_x=0,
                bounds_y=0,
                bounds_width=100,
                bounds_height=100,
            ),
            WindowInfo(
                app_name="Terminal",
                window_title="session2",
                window_id=2,
                pid=101,
                layer=0,
                on_screen=True,
                alpha=1.0,
                bounds_x=0,
                bounds_y=0,
                bounds_width=100,
                bounds_height=100,
            ),
        ]
        with mock.patch("scripts.core.get_all_windows", return_value=windows):
            result = find_window(WindowFilter(app_name="Terminal"))
            assert result is not None
            assert result.window_title == "session1"


# -- TestActivateWindow --


class TestActivateWindow:
    """Tests for activate_window and sanitize_app_name functions."""

    def test_sanitize_valid_names(self) -> None:
        """Test sanitize_app_name allows valid characters."""
        assert sanitize_app_name("GoLand") == "GoLand"
        assert sanitize_app_name("Visual Studio Code") == "Visual Studio Code"
        assert sanitize_app_name("Safari (Beta)") == "Safari (Beta)"
        assert sanitize_app_name("app-name.test") == "app-name.test"

    def test_sanitize_invalid_name(self) -> None:
        """Test sanitize_app_name rejects invalid characters."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App; rm -rf /")
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name('App"; echo pwned')

    def test_activate_success(self, sample_window: WindowInfo) -> None:
        """Test successful window activation."""
        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions.subprocess.run") as mock_run,
            mock.patch("scripts.actions.time.sleep"),
        ):
            mock_run.return_value = mock.Mock(returncode=0)
            result = activate_window(WindowFilter(app_name="GoLand"))
            assert result.app_name == "GoLand"
            mock_run.assert_called_once()

    def test_activate_window_not_found(self) -> None:
        """Test activation fails when window not found."""
        with (
            mock.patch("scripts.actions.find_window", return_value=None),
            pytest.raises(WindowNotFoundError, match="No window found"),
        ):
            activate_window(WindowFilter(app_name="NonExistent"))

    def test_activate_osascript_failure(self, sample_window: WindowInfo) -> None:
        """Test activation fails when osascript returns error."""
        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions.subprocess.run") as mock_run,
        ):
            mock_run.return_value = mock.Mock(
                returncode=1,
                stderr=b"Application not found",
            )
            with pytest.raises(ActivationError, match="Failed to activate"):
                activate_window(WindowFilter(app_name="GoLand"))


# -- TestTakeScreenshot --


class TestTakeScreenshot:
    """Tests for take_screenshot function."""

    def test_screenshot_success(self, sample_window: WindowInfo, tmp_path: Path) -> None:
        """Test successful screenshot capture."""
        output_path = tmp_path / "test.png"

        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions._activate_by_app_name") as mock_activate,
            mock.patch("scripts.actions._get_quartz") as mock_quartz,
        ):
            Q = mock_quartz.return_value
            Q.CGWindowListCreateImage.return_value = mock.Mock()
            Q.CFURLCreateWithFileSystemPath.return_value = mock.Mock()
            Q.CGImageDestinationCreateWithURL.return_value = mock.Mock()
            Q.CGImageDestinationFinalize.return_value = True

            result = take_screenshot(WindowFilter(app_name="GoLand"), output_path)
            assert result == output_path
            mock_activate.assert_called_once()

    def test_screenshot_no_activate(self, sample_window: WindowInfo, tmp_path: Path) -> None:
        """Test screenshot without activation."""
        output_path = tmp_path / "test.png"

        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions._activate_by_app_name") as mock_activate,
            mock.patch("scripts.actions._get_quartz") as mock_quartz,
        ):
            Q = mock_quartz.return_value
            Q.CGWindowListCreateImage.return_value = mock.Mock()
            Q.CFURLCreateWithFileSystemPath.return_value = mock.Mock()
            Q.CGImageDestinationCreateWithURL.return_value = mock.Mock()
            Q.CGImageDestinationFinalize.return_value = True

            take_screenshot(WindowFilter(app_name="GoLand"), output_path, activate_first=False)
            mock_activate.assert_not_called()

    def test_screenshot_window_not_found(self) -> None:
        """Test screenshot fails when window not found."""
        with (
            mock.patch("scripts.actions.find_window", return_value=None),
            mock.patch("scripts.actions._get_quartz"),
            pytest.raises(WindowNotFoundError, match="No window found"),
        ):
            take_screenshot(WindowFilter(app_name="NonExistent"))

    def test_screenshot_image_capture_fails(
        self, sample_window: WindowInfo, tmp_path: Path
    ) -> None:
        """Test screenshot fails when CGWindowListCreateImage returns None."""
        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions._activate_by_app_name"),
            mock.patch("scripts.actions._get_quartz") as mock_quartz,
        ):
            Q = mock_quartz.return_value
            Q.CGWindowListCreateImage.return_value = None

            with pytest.raises(ScreenshotError, match="Failed to capture"):
                take_screenshot(WindowFilter(app_name="GoLand"), tmp_path / "test.png")

    def test_screenshot_destination_fails(self, sample_window: WindowInfo, tmp_path: Path) -> None:
        """Test screenshot fails when destination creation fails."""
        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions._activate_by_app_name"),
            mock.patch("scripts.actions._get_quartz") as mock_quartz,
        ):
            Q = mock_quartz.return_value
            Q.CGWindowListCreateImage.return_value = mock.Mock()
            Q.CFURLCreateWithFileSystemPath.return_value = mock.Mock()
            Q.CGImageDestinationCreateWithURL.return_value = None

            with pytest.raises(ScreenshotError, match="Failed to create destination"):
                take_screenshot(WindowFilter(app_name="GoLand"), tmp_path / "test.png")

    def test_screenshot_auto_path_generation(self, sample_window: WindowInfo) -> None:
        """Test screenshot generates output path when not provided."""
        with (
            mock.patch("scripts.actions.find_window", return_value=sample_window),
            mock.patch("scripts.actions._activate_by_app_name"),
            mock.patch("scripts.actions._get_quartz") as mock_quartz,
            mock.patch("scripts.actions.Path.mkdir"),
        ):
            Q = mock_quartz.return_value
            Q.CGWindowListCreateImage.return_value = mock.Mock()
            Q.CFURLCreateWithFileSystemPath.return_value = mock.Mock()
            Q.CGImageDestinationCreateWithURL.return_value = mock.Mock()
            Q.CGImageDestinationFinalize.return_value = True

            result = take_screenshot(WindowFilter(app_name="GoLand"))
            assert result.suffix == ".png"
            assert "goland" in str(result).lower()


# -- TestCLI --


class TestCLI:
    """Tests for CLI parser and handlers."""

    def test_parser_creates_valid_parser(self) -> None:
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None
        assert parser.description is not None

    def test_parser_list_action(self) -> None:
        """Test --list flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--list"])
        assert args.list is True

    def test_parser_find_action(self) -> None:
        """Test --find flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--find", "GoLand"])
        assert args.find == "GoLand"

    def test_parser_find_no_app(self) -> None:
        """Test --find without app name."""
        parser = create_parser()
        args = parser.parse_args(["--find"])
        assert args.find == ""

    def test_parser_activate_action(self) -> None:
        """Test --activate flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--activate", "Terminal"])
        assert args.activate == "Terminal"

    def test_parser_screenshot_action(self) -> None:
        """Test --screenshot flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--screenshot", "Safari", "-o", "test.png"])
        assert args.screenshot == "Safari"
        assert args.output == "test.png"

    def test_parser_filters(self) -> None:
        """Test filter arguments parsing."""
        parser = create_parser()
        args = parser.parse_args([
            "--find",
            "GoLand",
            "--title",
            ".*\\.py",
            "--pid",
            "1234",
            "--path-contains",
            "/Applications",
            "--path-excludes",
            ".gradle",
            "--args-contains",
            "research",
            "--all-windows",
        ])
        assert args.title == ".*\\.py"
        assert args.pid == 1234
        assert args.path_contains == "/Applications"
        assert args.path_excludes == ".gradle"
        assert args.args_contains == "research"
        assert args.all_windows is True

    def test_parser_json_output(self) -> None:
        """Test --json flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--list", "--json"])
        assert args.json is True

    def test_parser_short_flags(self) -> None:
        """Test short flag variants."""
        parser = create_parser()
        args = parser.parse_args(["-l", "-j"])
        assert args.list is True
        assert args.json is True

    def test_build_filter_from_args(self) -> None:
        """Test building WindowFilter from parsed args."""
        parser = create_parser()
        args = parser.parse_args([
            "--find",
            "GoLand",
            "--title",
            "core",
            "--pid",
            "999",
        ])
        f = build_filter(args)
        assert f.app_name == "GoLand"
        assert f.title_pattern == "core"
        assert f.pid == 999
        assert f.main_window_only is True

    def test_main_no_action_shows_help(self) -> None:
        """Test main with no arguments returns 1."""
        result = main([])
        assert result == 1

    def test_main_list_success(self, sample_windows: list[WindowInfo]) -> None:
        """Test main --list succeeds."""
        with mock.patch("scripts.cli.get_all_windows", return_value=sample_windows):
            result = main(["--list"])
            assert result == 0

    def test_main_list_json(self, sample_windows: list[WindowInfo]) -> None:
        """Test main --list --json outputs JSON."""
        with mock.patch("scripts.cli.get_all_windows", return_value=sample_windows):
            result = main(["--list", "--json"])
            assert result == 0

    def test_main_find_success(self, sample_window: WindowInfo) -> None:
        """Test main --find succeeds when window found."""
        with mock.patch("scripts.cli.find_windows", return_value=[sample_window]):
            result = main(["--find", "GoLand"])
            assert result == 0

    def test_main_find_not_found(self) -> None:
        """Test main --find returns 1 when no window found."""
        with mock.patch("scripts.cli.find_windows", return_value=[]):
            result = main(["--find", "NonExistent"])
            assert result == 1

    def test_main_activate_success(self, sample_window: WindowInfo) -> None:
        """Test main --activate succeeds."""
        with mock.patch("scripts.cli.activate_window", return_value=sample_window):
            result = main(["--activate", "GoLand"])
            assert result == 0

    def test_main_activate_error(self) -> None:
        """Test main --activate handles errors."""
        side_effect = WindowNotFoundError("Not found")
        with mock.patch("scripts.cli.activate_window", side_effect=side_effect):
            result = main(["--activate", "NonExistent"])
            assert result == 1

    def test_main_screenshot_success(self, sample_window: WindowInfo, tmp_path: Path) -> None:
        """Test main --screenshot succeeds."""
        output_path = tmp_path / "test.png"
        with mock.patch("scripts.cli.take_screenshot", return_value=output_path):
            result = main(["--screenshot", "GoLand", "-o", str(output_path)])
            assert result == 0
