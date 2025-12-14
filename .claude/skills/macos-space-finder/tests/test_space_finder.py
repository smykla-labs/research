"""Comprehensive tests for macOS Space Finder script."""

from __future__ import annotations

import json
import plistlib
from unittest.mock import MagicMock, patch

import pytest
from scripts import (
    SPACE_TYPE_FULLSCREEN,
    SPACE_TYPE_NAMES,
    SPACE_TYPE_NORMAL,
    ActivationError,
    PlistReadError,
    SpaceInfo,
    activate_app,
    create_parser,
    find_space_by_app,
    get_current_space,
    get_spaces_plist,
    go_to_space,
    main,
    parse_spaces,
    sanitize_app_name,
)

# Import private functions from cli module for testing
from scripts.cli import (
    _handle_current,
    _handle_find,
    _handle_go,
    _handle_list,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_space_normal() -> SpaceInfo:
    """Create a sample normal desktop space."""
    return SpaceInfo(
        index=1,
        display="Main",
        managed_space_id=1,
        space_type=SPACE_TYPE_NORMAL,
        uuid="",
        is_current=True,
        app_name=None,
        window_title=None,
        window_id=None,
        pid=None,
    )


@pytest.fixture
def sample_space_fullscreen() -> SpaceInfo:
    """Create a sample full-screen app space."""
    return SpaceInfo(
        index=2,
        display="Main",
        managed_space_id=3100,
        space_type=SPACE_TYPE_FULLSCREEN,
        uuid="CEA547F2-95AE-47A1-B995-25A45BB3DA08",
        is_current=False,
        app_name="GoLand",
        window_title="research – find_space.py",
        window_id=176051,
        pid=9275,
    )


@pytest.fixture
def sample_spaces(
    sample_space_normal: SpaceInfo,
    sample_space_fullscreen: SpaceInfo,
) -> list[SpaceInfo]:
    """Create a list of sample spaces."""
    return [
        sample_space_normal,
        sample_space_fullscreen,
        SpaceInfo(
            index=3,
            display="Main",
            managed_space_id=3124,
            space_type=SPACE_TYPE_FULLSCREEN,
            uuid="9E9C0F2B-E7D0-4A9D-B5DC-07EA454EE5DF",
            is_current=False,
            app_name="Ghostty",
            window_title="terminal session",
            window_id=146010,
            pid=76445,
        ),
    ]


@pytest.fixture
def sample_plist_data() -> dict:
    """Create sample plist data structure."""
    return {
        "SpacesDisplayConfiguration": {
            "Management Data": {
                "Monitors": [
                    {
                        "Display Identifier": "Main",
                        "Current Space": {
                            "ManagedSpaceID": 1,
                        },
                        "Spaces": [
                            {
                                "ManagedSpaceID": 1,
                                "type": 0,
                                "uuid": "",
                            },
                            {
                                "ManagedSpaceID": 3100,
                                "type": 4,
                                "uuid": "CEA547F2-95AE-47A1-B995-25A45BB3DA08",
                                "TileLayoutManager": {
                                    "TileSpaces": [
                                        {
                                            "appName": "GoLand",
                                            "name": "research – find_space.py",
                                            "TileWindowID": 176051,
                                            "pid": 9275,
                                        }
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
# SpaceInfo Tests
# =============================================================================


class TestSpaceInfo:
    """Tests for SpaceInfo dataclass."""

    def test_type_name_normal(self, sample_space_normal: SpaceInfo) -> None:
        """Test type_name property for normal space."""
        assert sample_space_normal.type_name == "Normal"

    def test_type_name_fullscreen(self, sample_space_fullscreen: SpaceInfo) -> None:
        """Test type_name property for full-screen space."""
        assert sample_space_fullscreen.type_name == "FullSc"

    def test_type_name_unknown(self) -> None:
        """Test type_name property for unknown type."""
        space = SpaceInfo(
            index=1,
            display="Main",
            managed_space_id=1,
            space_type=99,
            uuid="",
            is_current=False,
            app_name=None,
            window_title=None,
            window_id=None,
            pid=None,
        )
        assert space.type_name == "99"

    def test_display_app_name_with_app(self, sample_space_fullscreen: SpaceInfo) -> None:
        """Test display_app_name with app set."""
        assert sample_space_fullscreen.display_app_name == "GoLand"

    def test_display_app_name_without_app(self, sample_space_normal: SpaceInfo) -> None:
        """Test display_app_name without app (returns dash)."""
        assert sample_space_normal.display_app_name == "-"

    def test_display_title_with_title(self, sample_space_fullscreen: SpaceInfo) -> None:
        """Test display_title with title set."""
        assert sample_space_fullscreen.display_title == "research – find_space.py"

    def test_display_title_without_title(self, sample_space_normal: SpaceInfo) -> None:
        """Test display_title without title (returns dash)."""
        assert sample_space_normal.display_title == "-"

    def test_display_title_truncation(self) -> None:
        """Test display_title truncates long titles."""
        space = SpaceInfo(
            index=1,
            display="Main",
            managed_space_id=1,
            space_type=0,
            uuid="",
            is_current=False,
            app_name=None,
            window_title="A" * 100,
            window_id=None,
            pid=None,
        )
        assert len(space.display_title) == 38

    def test_frozen_immutable(self, sample_space_normal: SpaceInfo) -> None:
        """Test that SpaceInfo is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            sample_space_normal.index = 5  # type: ignore[misc]

    def test_to_dict(self, sample_space_fullscreen: SpaceInfo) -> None:
        """Test to_dict method returns correct structure."""
        data = sample_space_fullscreen.to_dict()
        assert data["index"] == 2
        assert data["display"] == "Main"
        assert data["managed_space_id"] == 3100
        assert data["space_type"] == 4
        assert data["type_name"] == "FullSc"
        assert data["is_current"] is False
        assert data["app_name"] == "GoLand"
        assert data["window_title"] == "research – find_space.py"
        assert data["window_id"] == 176051
        assert data["pid"] == 9275


# =============================================================================
# Plist Parsing Tests
# =============================================================================


class TestGetSpacesPlist:
    """Tests for get_spaces_plist function."""

    def test_successful_read(self, sample_plist_data: dict) -> None:
        """Test successful plist read."""
        plist_bytes = plistlib.dumps(sample_plist_data)

        with patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=plist_bytes,
            )
            result = get_spaces_plist()

        assert result == sample_plist_data

    def test_plutil_failure(self) -> None:
        """Test handling of plutil failure."""
        with patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr=b"Error reading plist",
            )

            with pytest.raises(PlistReadError, match="Cannot read spaces plist"):
                get_spaces_plist()

    def test_invalid_plist_format(self) -> None:
        """Test handling of invalid plist format."""
        with patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=b"not valid plist data",
            )

            with pytest.raises(PlistReadError, match="Invalid plist format"):
                get_spaces_plist()


class TestParseSpaces:
    """Tests for parse_spaces function."""

    def test_parse_normal_space(self, sample_plist_data: dict) -> None:
        """Test parsing normal desktop space."""
        spaces = parse_spaces(sample_plist_data)

        assert len(spaces) == 2
        assert spaces[0].index == 1
        assert spaces[0].space_type == SPACE_TYPE_NORMAL
        assert spaces[0].is_current is True
        assert spaces[0].app_name is None

    def test_parse_fullscreen_space(self, sample_plist_data: dict) -> None:
        """Test parsing full-screen app space."""
        spaces = parse_spaces(sample_plist_data)

        assert spaces[1].index == 2
        assert spaces[1].space_type == SPACE_TYPE_FULLSCREEN
        assert spaces[1].is_current is False
        assert spaces[1].app_name == "GoLand"
        assert spaces[1].window_title == "research – find_space.py"
        assert spaces[1].window_id == 176051
        assert spaces[1].pid == 9275

    def test_parse_empty_plist(self) -> None:
        """Test parsing empty plist data."""
        spaces = parse_spaces({})
        assert spaces == []

    def test_parse_missing_monitors(self) -> None:
        """Test parsing plist without monitors."""
        data = {"SpacesDisplayConfiguration": {"Management Data": {}}}
        spaces = parse_spaces(data)
        assert spaces == []

    def test_parse_multiple_monitors(self) -> None:
        """Test parsing plist with multiple monitors."""
        data = {
            "SpacesDisplayConfiguration": {
                "Management Data": {
                    "Monitors": [
                        {
                            "Display Identifier": "Main",
                            "Current Space": {"ManagedSpaceID": 1},
                            "Spaces": [{"ManagedSpaceID": 1, "type": 0, "uuid": ""}],
                        },
                        {
                            "Display Identifier": "External",
                            "Current Space": {"ManagedSpaceID": 2},
                            "Spaces": [{"ManagedSpaceID": 2, "type": 0, "uuid": ""}],
                        },
                    ]
                }
            }
        }
        spaces = parse_spaces(data)
        assert len(spaces) == 2
        assert spaces[0].display == "Main"
        assert spaces[1].display == "External"


# =============================================================================
# Space Finding Tests
# =============================================================================


class TestFindSpaceByApp:
    """Tests for find_space_by_app function."""

    def test_find_by_exact_app_name(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test finding space by exact app name."""
        matches = find_space_by_app(sample_spaces, "GoLand")
        assert len(matches) == 1
        assert matches[0].app_name == "GoLand"

    def test_find_by_partial_app_name(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test finding space by partial app name."""
        matches = find_space_by_app(sample_spaces, "Go")
        assert len(matches) == 1
        assert matches[0].app_name == "GoLand"

    def test_find_case_insensitive(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test case-insensitive search."""
        matches = find_space_by_app(sample_spaces, "goland")
        assert len(matches) == 1
        assert matches[0].app_name == "GoLand"

    def test_find_by_window_title(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test finding space by window title."""
        matches = find_space_by_app(sample_spaces, "find_space")
        assert len(matches) == 1
        assert matches[0].app_name == "GoLand"

    def test_find_no_matches(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test when no spaces match."""
        matches = find_space_by_app(sample_spaces, "NonExistentApp")
        assert matches == []

    def test_find_multiple_matches(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test when multiple spaces match."""
        # Both GoLand and Ghostty contain 'o'
        matches = find_space_by_app(sample_spaces, "o")
        assert len(matches) == 2


class TestGetCurrentSpace:
    """Tests for get_current_space function."""

    def test_get_current_space(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test getting the current space."""
        current = get_current_space(sample_spaces)
        assert current is not None
        assert current.is_current is True
        assert current.index == 1

    def test_no_current_space(self) -> None:
        """Test when no space is marked as current."""
        spaces = [
            SpaceInfo(
                index=1,
                display="Main",
                managed_space_id=1,
                space_type=0,
                uuid="",
                is_current=False,
                app_name=None,
                window_title=None,
                window_id=None,
                pid=None,
            )
        ]
        current = get_current_space(spaces)
        assert current is None


# =============================================================================
# App Activation Tests
# =============================================================================


class TestSanitizeAppName:
    """Tests for sanitize_app_name function."""

    def test_valid_simple_name(self) -> None:
        """Test valid simple app name."""
        assert sanitize_app_name("GoLand") == "GoLand"

    def test_valid_name_with_spaces(self) -> None:
        """Test valid name with spaces."""
        assert sanitize_app_name("IntelliJ IDEA") == "IntelliJ IDEA"

    def test_valid_name_with_hyphen(self) -> None:
        """Test valid name with hyphen."""
        assert sanitize_app_name("VS-Code") == "VS-Code"

    def test_valid_name_with_period(self) -> None:
        """Test valid name with period."""
        assert sanitize_app_name("App.Name") == "App.Name"

    def test_invalid_name_with_quotes(self) -> None:
        """Test rejection of name with quotes."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name('App"Name')

    def test_invalid_name_with_semicolon(self) -> None:
        """Test rejection of name with semicolon."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App;Name")

    def test_invalid_name_with_shell_chars(self) -> None:
        """Test rejection of shell special characters."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App$(whoami)")


class TestActivateApp:
    """Tests for activate_app function."""

    def test_successful_activation(self) -> None:
        """Test successful app activation."""
        with patch("scripts.actions.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            activate_app("GoLand")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "osascript"
        assert 'tell application "GoLand" to activate' in call_args[2]

    def test_activation_failure(self) -> None:
        """Test handling of activation failure."""
        with patch("scripts.actions.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr=b"App not found",
            )

            with pytest.raises(ActivationError, match="Failed to activate"):
                activate_app("NonExistentApp")


# =============================================================================
# Go To Space Tests
# =============================================================================


class TestGoToSpace:
    """Tests for go_to_space function."""

    def test_go_to_different_space(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test switching to a different space."""
        with (
            patch("scripts.actions.activate_app") as mock_activate,
            patch("scripts.actions.time.sleep"),
        ):
            target, original, success = go_to_space(sample_spaces, "GoLand")

        assert success is True
        assert target is not None
        assert target.app_name == "GoLand"
        assert original is not None
        assert original.is_current is True

        # Should activate GoLand, then return to original (Finder for normal desktop)
        assert mock_activate.call_count == 2

    def test_go_to_current_space(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test when target is already current space (no switching needed)."""
        # Make GoLand the current space
        spaces = [
            SpaceInfo(
                index=1,
                display="Main",
                managed_space_id=1,
                space_type=0,
                uuid="",
                is_current=False,
                app_name=None,
                window_title=None,
                window_id=None,
                pid=None,
            ),
            SpaceInfo(
                index=2,
                display="Main",
                managed_space_id=3100,
                space_type=4,
                uuid="",
                is_current=True,
                app_name="GoLand",
                window_title="test",
                window_id=123,
                pid=456,
            ),
        ]

        with patch("scripts.actions.activate_app") as mock_activate:
            target, original, success = go_to_space(spaces, "GoLand")

        assert success is True
        assert target.app_name == "GoLand"
        mock_activate.assert_not_called()

    def test_go_to_nonexistent_app(self, sample_spaces: list[SpaceInfo]) -> None:
        """Test switching to non-existent app."""
        target, original, success = go_to_space(sample_spaces, "NonExistent")

        assert success is False
        assert target is None
        assert original is not None


# =============================================================================
# CLI Handler Tests
# =============================================================================


class TestHandlers:
    """Tests for CLI handler functions."""

    def test_handle_list(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list handler output."""
        result = _handle_list(sample_spaces)

        assert result == 0
        captured = capsys.readouterr()
        assert "Idx" in captured.out
        assert "GoLand" in captured.out

    def test_handle_current_with_app(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --current handler with app space."""
        spaces = [
            SpaceInfo(
                index=1,
                display="Main",
                managed_space_id=1,
                space_type=4,
                uuid="",
                is_current=True,
                app_name="GoLand",
                window_title="test",
                window_id=123,
                pid=456,
            )
        ]
        result = _handle_current(spaces)

        assert result == 0
        captured = capsys.readouterr()
        assert "GoLand" in captured.out

    def test_handle_current_desktop(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --current handler with normal desktop."""
        result = _handle_current(sample_spaces)

        assert result == 0
        captured = capsys.readouterr()
        assert "Desktop" in captured.out

    def test_handle_find_success(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test find handler with matching app."""
        result = _handle_find(sample_spaces, "GoLand")

        assert result == 0
        captured = capsys.readouterr()
        assert "Found: Space 2" in captured.out
        assert "GoLand" in captured.out

    def test_handle_find_not_found(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test find handler with no match."""
        result = _handle_find(sample_spaces, "NonExistent")

        assert result == 1
        captured = capsys.readouterr()
        assert "No space found" in captured.out

    def test_handle_go_success(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --go handler success."""
        with patch("scripts.actions.activate_app"), patch("scripts.actions.time.sleep"):
            result = _handle_go(sample_spaces, "GoLand")

        assert result == 0
        captured = capsys.readouterr()
        assert "Switched to: GoLand" in captured.out

    def test_handle_go_not_found(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --go handler with no match."""
        result = _handle_go(sample_spaces, "NonExistent")

        assert result == 1
        captured = capsys.readouterr()
        assert "No space found" in captured.out

    def test_handle_list_json(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list --json handler output."""
        result = _handle_list(sample_spaces, json_output=True)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 3
        assert data[1]["app_name"] == "GoLand"

    def test_handle_current_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --current --json handler output."""
        spaces = [
            SpaceInfo(
                index=1,
                display="Main",
                managed_space_id=1,
                space_type=4,
                uuid="",
                is_current=True,
                app_name="GoLand",
                window_title="test",
                window_id=123,
                pid=456,
            )
        ]
        result = _handle_current(spaces, json_output=True)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["app_name"] == "GoLand"

    def test_handle_find_json(
        self, sample_spaces: list[SpaceInfo], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test find --json handler output."""
        result = _handle_find(sample_spaces, "GoLand", json_output=True)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["app_name"] == "GoLand"


# =============================================================================
# Argument Parser Tests
# =============================================================================


class TestCreateParser:
    """Tests for create_parser function."""

    def test_parser_list_flag(self) -> None:
        """Test --list flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--list"])
        assert args.list is True

    def test_parser_current_flag(self) -> None:
        """Test --current flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--current"])
        assert args.current is True

    def test_parser_go_flag(self) -> None:
        """Test --go flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--go", "GoLand"])
        assert args.go == "GoLand"

    def test_parser_positional_app(self) -> None:
        """Test positional app argument."""
        parser = create_parser()
        args = parser.parse_args(["GoLand"])
        assert args.app_query == "GoLand"

    def test_parser_app_with_spaces(self) -> None:
        """Test app name with spaces."""
        parser = create_parser()
        args = parser.parse_args(["IntelliJ IDEA"])
        assert args.app_query == "IntelliJ IDEA"

    def test_parser_json_flag(self) -> None:
        """Test --json flag parsing."""
        parser = create_parser()
        args = parser.parse_args(["--list", "--json"])
        assert args.json is True

    def test_parser_short_flags(self) -> None:
        """Test short flag variants (-l, -c, -g, -j)."""
        parser = create_parser()

        args = parser.parse_args(["-l"])
        assert args.list is True

        args = parser.parse_args(["-c"])
        assert args.current is True

        args = parser.parse_args(["-g", "GoLand"])
        assert args.go == "GoLand"

        args = parser.parse_args(["-l", "-j"])
        assert args.list is True
        assert args.json is True


# =============================================================================
# Main Function Tests
# =============================================================================


class TestMain:
    """Tests for main function."""

    def test_main_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main with no arguments shows help."""
        result = main([])
        assert result == 1
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()

    def test_main_list(
        self, sample_plist_data: dict, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main with --list."""
        plist_bytes = plistlib.dumps(sample_plist_data)

        with patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=plist_bytes)
            result = main(["--list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "GoLand" in captured.out

    def test_main_plist_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main with plist read error."""
        with patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr=b"Error")
            result = main(["--list"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_main_list_json(
        self, sample_plist_data: dict, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main with --list --json."""
        plist_bytes = plistlib.dumps(sample_plist_data)

        with patch("scripts.core.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=plist_bytes)
            result = main(["--list", "--json"])

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert data[1]["app_name"] == "GoLand"


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_space_type_names_complete(self) -> None:
        """Test that all known space types have names."""
        assert SPACE_TYPE_NORMAL in SPACE_TYPE_NAMES
        assert SPACE_TYPE_FULLSCREEN in SPACE_TYPE_NAMES

    def test_space_type_values(self) -> None:
        """Test space type constant values."""
        assert SPACE_TYPE_NORMAL == 0
        assert SPACE_TYPE_FULLSCREEN == 4
