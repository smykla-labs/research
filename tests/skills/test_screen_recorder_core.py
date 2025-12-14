"""Tests for screen_recorder.core module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# noinspection PyProtectedMember
from screen_recorder.actions import _build_scale_filter

# noinspection PyProtectedMember
from screen_recorder.core import (
    _describe_filters,
    _matches_config_filters,
    check_dependencies,
    compute_hash_distance,
    get_process_info,
    get_spaces_plist,
    get_video_info,
    get_window_space_mapping,
    require_ffmpeg,
    require_ffprobe,
)
from screen_recorder.models import (
    DependencyError,
    RecordingConfig,
)

# =============================================================================
# check_dependencies Tests
# =============================================================================


class TestCheckDependencies:
    """Tests for check_dependencies function."""

    def test_all_tools_present(self) -> None:
        """Test when all tools are available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/tool"
            result = check_dependencies()

        assert result["screencapture"] is True
        assert result["ffmpeg"] is True
        assert result["ffprobe"] is True

    def test_missing_ffmpeg(self) -> None:
        """Test when ffmpeg is missing."""
        def which_side_effect(tool: str) -> str | None:
            if tool == "ffmpeg":
                return None
            return f"/usr/bin/{tool}"

        with patch("shutil.which", side_effect=which_side_effect):
            result = check_dependencies()

        assert result["screencapture"] is True
        assert result["ffmpeg"] is False
        assert result["ffprobe"] is True

    def test_all_tools_missing(self) -> None:
        """Test when all tools are missing."""
        with patch("shutil.which", return_value=None):
            result = check_dependencies()

        assert result["screencapture"] is False
        assert result["ffmpeg"] is False
        assert result["ffprobe"] is False


# =============================================================================
# require_ffmpeg / require_ffprobe Tests
# =============================================================================


class TestRequireFfmpeg:
    """Tests for require_ffmpeg function."""

    def test_ffmpeg_present_no_error(self) -> None:
        """Test no error when ffmpeg is available."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            require_ffmpeg()  # Should not raise

    def test_ffmpeg_missing_raises_dependency_error(self) -> None:
        """Test DependencyError when ffmpeg is missing."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(DependencyError) as exc_info:
                require_ffmpeg()

        assert "ffmpeg not found" in str(exc_info.value)
        assert "brew install ffmpeg" in str(exc_info.value)


class TestRequireFfprobe:
    """Tests for require_ffprobe function."""

    def test_ffprobe_present_no_error(self) -> None:
        """Test no error when ffprobe is available."""
        with patch("shutil.which", return_value="/usr/bin/ffprobe"):
            require_ffprobe()  # Should not raise

    def test_ffprobe_missing_raises_dependency_error(self) -> None:
        """Test DependencyError when ffprobe is missing."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(DependencyError) as exc_info:
                require_ffprobe()

        assert "ffprobe not found" in str(exc_info.value)


# =============================================================================
# get_spaces_plist Tests
# =============================================================================


class TestGetSpacesPlist:
    """Tests for get_spaces_plist function."""

    def test_successful_plist_read(self) -> None:
        """Test successful reading and parsing of spaces plist."""
        # Minimal plist XML structure
        # noinspection HttpUrlsUsage
        plist_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>SpacesDisplayConfiguration</key>
    <dict>
        <key>Management Data</key>
        <dict>
            <key>Monitors</key>
            <array/>
        </dict>
    </dict>
</dict>
</plist>"""

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = plist_xml

        with patch("subprocess.run", return_value=mock_result):
            result = get_spaces_plist()

        assert "SpacesDisplayConfiguration" in result

    def test_plutil_failure_returns_empty_dict(self) -> None:
        """Test empty dict returned when plutil fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error"

        with patch("subprocess.run", return_value=mock_result):
            result = get_spaces_plist()

        assert result == {}

    def test_invalid_plist_returns_empty_dict(self) -> None:
        """Test empty dict returned for invalid plist data."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b"not valid plist data"

        with patch("subprocess.run", return_value=mock_result):
            result = get_spaces_plist()

        assert result == {}


# =============================================================================
# get_window_space_mapping Tests
# =============================================================================


class TestGetWindowSpaceMapping:
    """Tests for get_window_space_mapping function."""

    def test_empty_plist_returns_empty_dict(self) -> None:
        """Test empty dict for empty plist data."""
        result = get_window_space_mapping({})
        assert result == {}

    def test_plist_without_monitors_returns_empty(self) -> None:
        """Test empty dict when no Monitors key."""
        plist_data = {
            "SpacesDisplayConfiguration": {
                "Management Data": {}
            }
        }
        result = get_window_space_mapping(plist_data)
        assert result == {}

    def test_extracts_window_space_mappings(self) -> None:
        """Test correct window to space mapping extraction."""
        plist_data = {
            "SpacesDisplayConfiguration": {
                "Management Data": {
                    "Monitors": [
                        {
                            "Spaces": [
                                {
                                    "TileLayoutManager": {
                                        "TileSpaces": [
                                            {"TileWindowID": 12345},
                                            {"TileWindowID": 67890},
                                        ]
                                    }
                                },
                                {
                                    "TileLayoutManager": {
                                        "TileSpaces": [
                                            {"TileWindowID": 11111},
                                        ]
                                    }
                                },
                            ]
                        }
                    ]
                }
            }
        }
        result = get_window_space_mapping(plist_data)

        assert result[12345] == 1
        assert result[67890] == 1
        assert result[11111] == 2

    def test_ignores_missing_window_id(self) -> None:
        """Test tiles without TileWindowID are skipped."""
        plist_data = {
            "SpacesDisplayConfiguration": {
                "Management Data": {
                    "Monitors": [
                        {
                            "Spaces": [
                                {
                                    "TileLayoutManager": {
                                        "TileSpaces": [
                                            {"SomeOtherKey": "value"},
                                            {"TileWindowID": 12345},
                                        ]
                                    }
                                },
                            ]
                        }
                    ]
                }
            }
        }
        result = get_window_space_mapping(plist_data)

        assert len(result) == 1
        assert result[12345] == 1


# =============================================================================
# get_process_info Tests
# =============================================================================


class TestGetProcessInfo:
    """Tests for get_process_info function."""

    def test_returns_exe_and_cmdline(self) -> None:
        """Test successful process info retrieval."""
        mock_process = Mock()
        mock_process.exe.return_value = "/Applications/TestApp.app/Contents/MacOS/TestApp"
        mock_process.cmdline.return_value = ["TestApp", "--arg1", "value"]

        with patch("screen_recorder.core._get_psutil") as mock_psutil_getter:
            mock_psutil = Mock()
            mock_psutil.Process.return_value = mock_process
            mock_psutil_getter.return_value = mock_psutil

            exe_path, cmdline = get_process_info(1234)

        assert exe_path == "/Applications/TestApp.app/Contents/MacOS/TestApp"
        assert cmdline == ["TestApp", "--arg1", "value"]

    def test_no_such_process_returns_none_empty(self) -> None:
        """Test graceful handling of non-existent process."""
        with patch("screen_recorder.core._get_psutil") as mock_psutil_getter:
            mock_psutil = Mock()
            mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
            mock_psutil.AccessDenied = type("AccessDenied", (Exception,), {})
            mock_psutil.ZombieProcess = type("ZombieProcess", (Exception,), {})
            mock_psutil.Process.side_effect = mock_psutil.NoSuchProcess()
            mock_psutil_getter.return_value = mock_psutil

            exe_path, cmdline = get_process_info(99999)

        assert exe_path is None
        assert cmdline == []

    def test_access_denied_returns_none_empty(self) -> None:
        """Test graceful handling of access denied."""
        with patch("screen_recorder.core._get_psutil") as mock_psutil_getter:
            mock_psutil = Mock()
            mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
            mock_psutil.AccessDenied = type("AccessDenied", (Exception,), {})
            mock_psutil.ZombieProcess = type("ZombieProcess", (Exception,), {})
            mock_psutil.Process.side_effect = mock_psutil.AccessDenied()
            mock_psutil_getter.return_value = mock_psutil

            exe_path, cmdline = get_process_info(1234)

        assert exe_path is None
        assert cmdline == []


# =============================================================================
# _matches_config_filters Tests
# =============================================================================


class TestMatchesConfigFilters:
    """Tests for _matches_config_filters function."""

    def test_no_filters_matches_any_window(self) -> None:
        """Test window matches when no filters are set."""
        config = RecordingConfig()
        window = {"kCGWindowOwnerName": "Safari", "kCGWindowName": "Test Page"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_app_name_filter_matches(self) -> None:
        """Test app_name filter with matching window."""
        config = RecordingConfig(app_name="Safari")
        window = {"kCGWindowOwnerName": "Safari", "kCGWindowName": "Test"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_app_name_filter_case_insensitive(self) -> None:
        """Test app_name filter is case insensitive."""
        config = RecordingConfig(app_name="safari")
        window = {"kCGWindowOwnerName": "Safari", "kCGWindowName": "Test"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_app_name_filter_partial_match(self) -> None:
        """Test app_name filter with partial match."""
        config = RecordingConfig(app_name="Code")
        window = {"kCGWindowOwnerName": "Visual Studio Code", "kCGWindowName": "Test"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_app_name_filter_no_match(self) -> None:
        """Test app_name filter with non-matching window."""
        config = RecordingConfig(app_name="Chrome")
        window = {"kCGWindowOwnerName": "Safari", "kCGWindowName": "Test"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is False

    def test_title_pattern_filter_matches(self) -> None:
        """Test title_pattern filter with regex match."""
        config = RecordingConfig(title_pattern=r"Test.*Page")
        window = {"kCGWindowOwnerName": "Safari", "kCGWindowName": "Test - My Page"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_title_pattern_filter_no_match(self) -> None:
        """Test title_pattern filter with non-matching title."""
        config = RecordingConfig(title_pattern=r"^Exact Title$")
        window = {"kCGWindowOwnerName": "Safari", "kCGWindowName": "Different Title"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is False

    def test_pid_filter_matches(self) -> None:
        """Test pid filter with matching process."""
        config = RecordingConfig(pid=1234)
        window = {"kCGWindowOwnerName": "App", "kCGWindowName": "Win", "kCGWindowOwnerPID": 1234}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_pid_filter_no_match(self) -> None:
        """Test pid filter with different process."""
        config = RecordingConfig(pid=1234)
        window = {"kCGWindowOwnerName": "App", "kCGWindowName": "Win", "kCGWindowOwnerPID": 5678}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is False

    def test_path_contains_filter_matches(self) -> None:
        """Test path_contains filter with matching path."""
        config = RecordingConfig(path_contains="JetBrains")
        window = {"kCGWindowOwnerName": "GoLand", "kCGWindowName": "Project"}
        process_info = ("/Applications/JetBrains/GoLand.app/Contents/MacOS/goland", [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_path_contains_filter_no_path(self) -> None:
        """Test path_contains filter when no exe path."""
        config = RecordingConfig(path_contains="JetBrains")
        window = {"kCGWindowOwnerName": "GoLand", "kCGWindowName": "Project"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is False

    def test_path_excludes_filter_excludes(self) -> None:
        """Test path_excludes filter excludes matching path."""
        config = RecordingConfig(app_name="GoLand", path_excludes="sandbox")
        window = {"kCGWindowOwnerName": "GoLand", "kCGWindowName": "Project"}
        process_info = ("/Applications/JetBrains/GoLand-sandbox.app/Contents/MacOS/goland", [])

        assert _matches_config_filters(config, window, process_info) is False

    def test_path_excludes_filter_allows_non_matching(self) -> None:
        """Test path_excludes filter allows non-matching path."""
        config = RecordingConfig(app_name="GoLand", path_excludes="sandbox")
        window = {"kCGWindowOwnerName": "GoLand", "kCGWindowName": "Project"}
        process_info = ("/Applications/JetBrains/GoLand.app/Contents/MacOS/goland", [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_args_contains_filter_matches(self) -> None:
        """Test args_contains filter with matching cmdline."""
        config = RecordingConfig(args_contains="--experimental")
        window = {"kCGWindowOwnerName": "App", "kCGWindowName": "Win"}
        process_info = ("/usr/bin/app", ["app", "--experimental", "--other"])

        assert _matches_config_filters(config, window, process_info) is True

    def test_args_contains_filter_no_match(self) -> None:
        """Test args_contains filter with non-matching cmdline."""
        config = RecordingConfig(args_contains="--experimental")
        window = {"kCGWindowOwnerName": "App", "kCGWindowName": "Win"}
        process_info = ("/usr/bin/app", ["app", "--production"])

        assert _matches_config_filters(config, window, process_info) is False

    def test_multiple_filters_all_must_match(self) -> None:
        """Test multiple filters - all must match."""
        config = RecordingConfig(app_name="GoLand", title_pattern="research")
        window = {"kCGWindowOwnerName": "GoLand", "kCGWindowName": "research - main.go"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is True

    def test_multiple_filters_one_fails(self) -> None:
        """Test multiple filters - one failure rejects."""
        config = RecordingConfig(app_name="GoLand", title_pattern="other-project")
        window = {"kCGWindowOwnerName": "GoLand", "kCGWindowName": "research - main.go"}
        process_info = (None, [])

        assert _matches_config_filters(config, window, process_info) is False


# =============================================================================
# _describe_filters Tests
# =============================================================================


class TestDescribeFilters:
    """Tests for _describe_filters function."""

    def test_no_filters_returns_no_filters(self) -> None:
        """Test 'no filters' message when no filters set."""
        config = RecordingConfig()
        result = _describe_filters(config)
        assert result == "no filters"

    def test_app_name_filter_described(self) -> None:
        """Test app_name filter is described."""
        config = RecordingConfig(app_name="Safari")
        result = _describe_filters(config)
        assert "app_name=Safari" in result

    def test_title_pattern_filter_described(self) -> None:
        """Test title_pattern filter is described."""
        config = RecordingConfig(title_pattern="Test.*")
        result = _describe_filters(config)
        assert "title_pattern=Test.*" in result

    def test_pid_filter_described(self) -> None:
        """Test pid filter is described."""
        config = RecordingConfig(pid=1234)
        result = _describe_filters(config)
        assert "pid=1234" in result

    def test_args_contains_filter_described(self) -> None:
        """Test args_contains filter is described."""
        config = RecordingConfig(args_contains="sandbox")
        result = _describe_filters(config)
        assert "args_contains=sandbox" in result

    def test_multiple_filters_comma_separated(self) -> None:
        """Test multiple filters are comma-separated."""
        config = RecordingConfig(app_name="GoLand", title_pattern="research")
        result = _describe_filters(config)
        assert "app_name=GoLand" in result
        assert "title_pattern=research" in result
        assert ", " in result


# =============================================================================
# _build_scale_filter Tests
# =============================================================================


class TestBuildScaleFilter:
    """Tests for _build_scale_filter function."""

    def test_no_constraints_returns_empty(self) -> None:
        """Test empty filter when no constraints."""
        result = _build_scale_filter(None, None)
        assert result == ""

    def test_max_width_only(self) -> None:
        """Test scale filter with only max_width."""
        result = _build_scale_filter(720, None)
        assert "720" in result
        assert "-1" in result  # Height scales proportionally

    def test_max_height_only(self) -> None:
        """Test scale filter with only max_height."""
        result = _build_scale_filter(None, 480)
        assert "480" in result
        assert "-1" in result  # Width scales proportionally

    def test_both_width_and_height(self) -> None:
        """Test scale filter with both constraints."""
        result = _build_scale_filter(1280, 720)
        assert "1280" in result
        assert "720" in result
        assert "force_original_aspect_ratio" in result


# =============================================================================
# compute_hash_distance Tests
# =============================================================================


class TestComputeHashDistance:
    """Tests for compute_hash_distance function."""

    def test_identical_hashes_zero_distance(self) -> None:
        """Test identical hashes have zero distance."""
        with patch("screen_recorder.core._get_imagehash") as mock_getter:
            mock_imagehash = Mock()
            h1 = Mock()
            h2 = Mock()
            h1.__sub__ = Mock(return_value=0)
            mock_imagehash.hex_to_hash.side_effect = [h1, h2]
            mock_getter.return_value = mock_imagehash

            result = compute_hash_distance("0123456789abcdef", "0123456789abcdef")

        assert result == 0

    def test_different_hashes_nonzero_distance(self) -> None:
        """Test different hashes have non-zero distance."""
        with patch("screen_recorder.core._get_imagehash") as mock_getter:
            mock_imagehash = Mock()
            h1 = Mock()
            h2 = Mock()
            h1.__sub__ = Mock(return_value=12)
            mock_imagehash.hex_to_hash.side_effect = [h1, h2]
            mock_getter.return_value = mock_imagehash

            # noinspection SpellCheckingInspection
            result = compute_hash_distance("0123456789abcdef", "fedcba9876543210")

        assert result == 12


# =============================================================================
# get_video_info Tests
# =============================================================================


class TestGetVideoInfo:
    """Tests for get_video_info function."""

    @pytest.fixture
    def sample_ffprobe_output(self) -> bytes:
        """Sample ffprobe JSON output."""
        import json
        return json.dumps({
            "streams": [{
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30/1",
                "nb_read_frames": "150",
            }],
            "format": {
                "duration": "5.0",
                "size": "5000000",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            }
        }).encode()

    def test_parses_ffprobe_output(self, sample_ffprobe_output: bytes, tmp_path: Path) -> None:
        """Test successful parsing of ffprobe output."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake video content")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = sample_ffprobe_output

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            info = get_video_info(video_path)

        assert info.width == 1920
        assert info.height == 1080
        assert info.fps == 30.0
        assert info.frame_count == 150
        assert info.duration_seconds == 5.0
        assert info.file_size_bytes == 5000000

    def test_ffprobe_failure_raises_value_error(self, tmp_path: Path) -> None:
        """Test ValueError on ffprobe failure."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error: file not found"

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(ValueError) as exc_info:
                get_video_info(video_path)

        assert "ffprobe failed" in str(exc_info.value)

    def test_parses_fractional_frame_rate(self, tmp_path: Path) -> None:
        """Test parsing fractional frame rate like 30000/1001."""
        import json

        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        ffprobe_output = json.dumps({
            "streams": [{
                "width": 1280,
                "height": 720,
                "avg_frame_rate": "30000/1001",
                "nb_read_frames": "150",
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ffprobe_output

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            info = get_video_info(video_path)

        assert abs(info.fps - 29.97) < 0.01

    def test_fallback_frame_count_from_duration(self, tmp_path: Path) -> None:
        """Test frame count estimation when nb_read_frames is missing."""
        import json

        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        ffprobe_output = json.dumps({
            "streams": [{
                "width": 1280,
                "height": 720,
                "avg_frame_rate": "30/1",
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ffprobe_output

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            info = get_video_info(video_path)

        assert info.frame_count == 150  # 5.0 * 30

    def test_requires_ffprobe(self, tmp_path: Path) -> None:
        """Test DependencyError when ffprobe not available."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        with patch("shutil.which", return_value=None):
            with pytest.raises(DependencyError):
                get_video_info(video_path)
