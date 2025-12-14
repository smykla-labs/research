"""Tests for screen_recorder verification functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from screen_recorder.core import (
    extract_frame,
    verify_basic,
    verify_duration,
    verify_frames,
    verify_motion,
)
from screen_recorder.models import (
    VerificationStrategy,
)

# =============================================================================
# verify_basic Tests
# =============================================================================


class TestVerifyBasic:
    """Tests for verify_basic function."""

    def test_file_exists_and_not_empty_passes(self, tmp_path: Path) -> None:
        """Test verification passes for valid file."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"some video content")

        result = verify_basic(video_path)

        assert result.passed is True
        assert result.strategy == VerificationStrategy.BASIC
        assert "Valid video file" in result.message

    def test_file_not_exists_fails(self, tmp_path: Path) -> None:
        """Test verification fails for non-existent file."""
        video_path = tmp_path / "nonexistent.mov"

        result = verify_basic(video_path)

        assert result.passed is False
        assert "does not exist" in result.message
        assert str(video_path) in result.details.get("path", "")

    def test_empty_file_fails(self, tmp_path: Path) -> None:
        """Test verification fails for empty file."""
        video_path = tmp_path / "empty.mov"
        video_path.write_bytes(b"")

        result = verify_basic(video_path)

        assert result.passed is False
        assert "empty" in result.message.lower()
        assert result.details.get("size") == 0

    def test_details_include_file_size(self, tmp_path: Path) -> None:
        """Test details include file size for valid file."""
        video_path = tmp_path / "test.mov"
        content = b"x" * 1024
        video_path.write_bytes(content)

        result = verify_basic(video_path)

        assert result.details["size"] == 1024


# =============================================================================
# verify_duration Tests
# =============================================================================


class TestVerifyDuration:
    """Tests for verify_duration function."""

    @pytest.fixture
    def mock_video_info_response(self) -> bytes:
        """Create mock ffprobe output."""
        return json.dumps({
            "streams": [{"width": 1920, "height": 1080, "avg_frame_rate": "30/1"}],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

    def test_exact_duration_match_passes(
        self, tmp_path: Path, mock_video_info_response: bytes
    ) -> None:
        """Test verification passes when duration matches exactly."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_video_info_response

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_duration(video_path, expected_duration=5.0)

        assert result.passed is True
        assert result.strategy == VerificationStrategy.DURATION
        assert "matches" in result.message.lower()

    def test_duration_within_tolerance_passes(self, tmp_path: Path) -> None:
        """Test verification passes when duration is within tolerance."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{"width": 1920, "height": 1080, "avg_frame_rate": "30/1"}],
            "format": {"duration": "5.3", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_duration(video_path, expected_duration=5.0, tolerance=0.5)

        assert result.passed is True

    def test_duration_outside_tolerance_fails(self, tmp_path: Path) -> None:
        """Test verification fails when duration exceeds tolerance."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{"width": 1920, "height": 1080, "avg_frame_rate": "30/1"}],
            "format": {"duration": "7.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_duration(video_path, expected_duration=5.0, tolerance=0.5)

        assert result.passed is False
        assert "mismatch" in result.message.lower()
        assert result.details["expected_seconds"] == 5.0
        assert result.details["actual_seconds"] == 7.0

    def test_ffprobe_failure_fails_gracefully(self, tmp_path: Path) -> None:
        """Test verification handles ffprobe failure gracefully."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error"

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_duration(video_path, expected_duration=5.0)

        assert result.passed is False
        assert "could not read" in result.message.lower()

    def test_details_include_all_duration_info(self, tmp_path: Path) -> None:
        """Test details include expected, actual, difference, and tolerance."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{"width": 1920, "height": 1080, "avg_frame_rate": "30/1"}],
            "format": {"duration": "5.2", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_duration(video_path, expected_duration=5.0, tolerance=0.5)

        assert "expected_seconds" in result.details
        assert "actual_seconds" in result.details
        assert "difference_seconds" in result.details
        assert "tolerance_seconds" in result.details


# =============================================================================
# verify_frames Tests
# =============================================================================


class TestVerifyFrames:
    """Tests for verify_frames function."""

    def test_min_frames_direct_passes(self, tmp_path: Path) -> None:
        """Test verification passes when frame count exceeds min_frames."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "150"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_frames(video_path, min_frames=100)

        assert result.passed is True
        assert result.strategy == VerificationStrategy.FRAMES
        assert result.details["actual_frames"] == 150
        assert result.details["minimum_required"] == 100

    def test_expected_duration_calculation_passes(self, tmp_path: Path) -> None:
        """Test verification with expected_duration calculates 80% threshold."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        # 5 seconds at 30 fps = 150 frames, 80% = 120 minimum
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "125"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_frames(video_path, expected_duration=5.0, expected_fps=30)

        assert result.passed is True
        # 5 * 30 * 0.8 = 120
        assert result.details["minimum_required"] == 120

    def test_insufficient_frames_fails(self, tmp_path: Path) -> None:
        """Test verification fails when frame count below threshold."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "50"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_frames(video_path, min_frames=100)

        assert result.passed is False
        assert "insufficient" in result.message.lower()

    def test_default_min_frames_is_one(self, tmp_path: Path) -> None:
        """Test default min_frames is 1 when nothing specified."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "1"
            }],
            "format": {"duration": "0.03", "size": "1000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_frames(video_path)  # No min_frames or expected_duration

        assert result.passed is True
        assert result.details["minimum_required"] == 1

    def test_ffprobe_failure_fails_gracefully(self, tmp_path: Path) -> None:
        """Test verification handles ffprobe failure gracefully."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error"

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_frames(video_path, min_frames=100)

        assert result.passed is False
        assert "could not read" in result.message.lower()


# =============================================================================
# verify_motion Tests
# =============================================================================


class TestVerifyMotion:
    """Tests for verify_motion function."""

    def test_motion_detected_passes(self, tmp_path: Path) -> None:
        """Test verification passes when motion is detected."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_ffprobe_result = Mock()
        mock_ffprobe_result.returncode = 0
        mock_ffprobe_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "150"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        mock_ffmpeg_result = Mock()
        mock_ffmpeg_result.returncode = 0

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            if "ffprobe" in cmd[0]:
                return mock_ffprobe_result
            return mock_ffmpeg_result

        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run", side_effect=subprocess_side_effect),
            patch("screen_recorder.core.extract_frame") as mock_extract,
            patch("screen_recorder.core.compute_image_hash", side_effect=["hash1", "hash2"]),
            patch("screen_recorder.core.compute_hash_distance", return_value=10),
        ):
            # Set up extract_frame to create dummy files
            def create_frame(_video, output, _time_seconds=0):
                output.write_bytes(b"fake image")
                return output
            mock_extract.side_effect = create_frame

            result = verify_motion(video_path)

        assert result.passed is True
        assert result.strategy == VerificationStrategy.MOTION
        assert "motion detected" in result.message.lower()

    def test_no_motion_fails(self, tmp_path: Path) -> None:
        """Test verification fails when no significant motion detected."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_ffprobe_result = Mock()
        mock_ffprobe_result.returncode = 0
        mock_ffprobe_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "150"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run", return_value=mock_ffprobe_result),
            patch("screen_recorder.core.extract_frame") as mock_extract,
            patch("screen_recorder.core.compute_image_hash", return_value="same_hash"),
            patch("screen_recorder.core.compute_hash_distance", return_value=2),  # Below threshold
        ):
            def create_frame(_video, output, _time_seconds=0):
                output.write_bytes(b"fake image")
                return output
            mock_extract.side_effect = create_frame

            result = verify_motion(video_path, hash_threshold=5)

        assert result.passed is False
        assert "no significant motion" in result.message.lower()

    def test_video_too_short_skips_check(self, tmp_path: Path) -> None:
        """Test verification skips for video shorter than MIN_DURATION_FOR_MOTION_CHECK."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_result = Mock()
        mock_result.returncode = 0
        # Duration less than MIN_DURATION_FOR_MOTION_CHECK (0.5s)
        mock_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "10"
            }],
            "format": {"duration": "0.3", "size": "10000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/ffprobe"),
            patch("subprocess.run", return_value=mock_result),
        ):
            result = verify_motion(video_path)

        assert result.passed is True
        assert "too short" in result.message.lower()

    def test_frame_extraction_failure_fails(self, tmp_path: Path) -> None:
        """Test verification fails when frame extraction fails."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_ffprobe_result = Mock()
        mock_ffprobe_result.returncode = 0
        mock_ffprobe_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "150"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        mock_ffmpeg_result = Mock()
        mock_ffmpeg_result.returncode = 1
        mock_ffmpeg_result.stderr = b"Error extracting frame"

        def subprocess_side_effect(*args, **_kwargs):
            cmd = args[0]
            if "ffprobe" in cmd[0]:
                return mock_ffprobe_result
            return mock_ffmpeg_result

        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run", side_effect=subprocess_side_effect),
        ):
            result = verify_motion(video_path)

        assert result.passed is False
        assert "extraction failed" in result.message.lower()

    def test_details_include_hash_info(self, tmp_path: Path) -> None:
        """Test details include hash values and distance."""
        video_path = tmp_path / "test.mov"
        video_path.write_bytes(b"fake")

        mock_ffprobe_result = Mock()
        mock_ffprobe_result.returncode = 0
        mock_ffprobe_result.stdout = json.dumps({
            "streams": [{
                "width": 1920, "height": 1080,
                "avg_frame_rate": "30/1", "nb_read_frames": "150"
            }],
            "format": {"duration": "5.0", "size": "1000000", "format_name": "mov"}
        }).encode()

        with (
            patch("shutil.which", return_value="/usr/bin/tool"),
            patch("subprocess.run", return_value=mock_ffprobe_result),
            patch("screen_recorder.core.extract_frame") as mock_extract,
            patch("screen_recorder.core.compute_image_hash", side_effect=["abc123", "def456"]),
            patch("screen_recorder.core.compute_hash_distance", return_value=15),
        ):
            def create_frame(_video, output, _time_seconds=0):
                output.write_bytes(b"fake image")
                return output
            mock_extract.side_effect = create_frame

            result = verify_motion(video_path)

        assert "first_hash" in result.details
        assert "last_hash" in result.details
        assert "hamming_distance" in result.details
        assert result.details["hamming_distance"] == 15


# =============================================================================
# extract_frame Tests
# =============================================================================


class TestExtractFrame:
    """Tests for extract_frame function."""

    def test_extract_frame_success(self, tmp_path: Path) -> None:
        """Test successful frame extraction."""
        video_path = tmp_path / "video.mov"
        video_path.write_bytes(b"fake video")
        output_path = tmp_path / "frame.png"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            # Simulate ffmpeg creating the output file
            output_path.write_bytes(b"fake image")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = extract_frame(video_path, output_path, time_seconds=1.0)

        assert result == output_path
        assert output_path.exists()

    def test_extract_frame_ffmpeg_failure(self, tmp_path: Path) -> None:
        """Test ValueError on ffmpeg failure."""
        video_path = tmp_path / "video.mov"
        video_path.write_bytes(b"fake video")
        output_path = tmp_path / "frame.png"

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error extracting frame"

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(ValueError) as exc_info:
                extract_frame(video_path, output_path)

        assert "extraction failed" in str(exc_info.value).lower()

    def test_extract_frame_output_not_created(self, tmp_path: Path) -> None:
        """Test ValueError when output file not created."""
        video_path = tmp_path / "video.mov"
        video_path.write_bytes(b"fake video")
        output_path = tmp_path / "frame.png"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = b""
        # Don't create the output file

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(ValueError) as exc_info:
                extract_frame(video_path, output_path)

        assert "extraction failed" in str(exc_info.value).lower()

    def test_extract_frame_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that parent directory is created if needed."""
        video_path = tmp_path / "video.mov"
        video_path.write_bytes(b"fake video")
        output_path = tmp_path / "subdir" / "nested" / "frame.png"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake image")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = extract_frame(video_path, output_path)

        assert result.parent.exists()
