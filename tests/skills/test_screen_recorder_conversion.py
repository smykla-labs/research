"""Tests for screen_recorder conversion functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from screen_recorder.actions import (
    convert_to_gif,
    convert_to_mp4,
    convert_to_webp,
    convert_video,
)
from screen_recorder.models import (
    ConversionError,
    OutputFormat,
    VideoEncodingSettings,
)

# =============================================================================
# convert_to_gif Tests
# =============================================================================


class TestConvertToGif:
    """Tests for convert_to_gif function."""

    def test_successful_conversion(self, tmp_path: Path) -> None:
        """Test successful GIF conversion."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.gif"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake gif")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            result = convert_to_gif(input_path, output_path)

        assert result == output_path
        assert output_path.exists()

        # Verify ffmpeg was called
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd

    def test_ffmpeg_failure_raises_conversion_error(self, tmp_path: Path) -> None:
        """Test ConversionError on ffmpeg failure."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.gif"

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error converting"

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(ConversionError) as exc_info:
                convert_to_gif(input_path, output_path)

        assert "gif conversion failed" in str(exc_info.value).lower()

    def test_uses_scale_filter(self, tmp_path: Path) -> None:
        """Test scale filter is applied."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.gif"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake gif")
            return mock_result

        settings = VideoEncodingSettings(fps=10, max_width=720)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_to_gif(input_path, output_path, settings)

        # Check filter_complex contains scale
        cmd = mock_run.call_args[0][0]
        filter_idx = cmd.index("-filter_complex")
        filter_value = cmd[filter_idx + 1]
        assert "720" in filter_value
        assert "fps=10" in filter_value

    def test_default_settings(self, tmp_path: Path) -> None:
        """Test default settings when none provided."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.gif"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake gif")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_to_gif(input_path, output_path)  # No settings

        cmd = mock_run.call_args[0][0]
        filter_idx = cmd.index("-filter_complex")
        filter_value = cmd[filter_idx + 1]
        assert "fps=10" in filter_value  # Default fps for GIF


# =============================================================================
# convert_to_webp Tests
# =============================================================================


class TestConvertToWebp:
    """Tests for convert_to_webp function."""

    def test_successful_conversion(self, tmp_path: Path) -> None:
        """Test successful WebP conversion."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.webp"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake webp")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = convert_to_webp(input_path, output_path)

        assert result == output_path
        assert output_path.exists()

    def test_quality_settings_applied(self, tmp_path: Path) -> None:
        """Test quality settings are applied."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.webp"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake webp")
            return mock_result

        settings = VideoEncodingSettings(fps=10, quality=80)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_to_webp(input_path, output_path, settings)

        cmd = mock_run.call_args[0][0]
        assert "-q:v" in cmd
        q_idx = cmd.index("-q:v")
        assert cmd[q_idx + 1] == "80"

    def test_loop_flag_applied(self, tmp_path: Path) -> None:
        """Test loop flag is applied."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.webp"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake webp")
            return mock_result

        settings = VideoEncodingSettings(loop=True)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_to_webp(input_path, output_path, settings)

        cmd = mock_run.call_args[0][0]
        assert "-loop" in cmd
        loop_idx = cmd.index("-loop")
        assert cmd[loop_idx + 1] == "0"  # 0 = infinite loop

    def test_ffmpeg_failure_raises_conversion_error(self, tmp_path: Path) -> None:
        """Test ConversionError on ffmpeg failure."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.webp"

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error"

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(ConversionError) as exc_info:
                convert_to_webp(input_path, output_path)

        assert "webp conversion failed" in str(exc_info.value).lower()


# =============================================================================
# convert_to_mp4 Tests
# =============================================================================


class TestConvertToMp4:
    """Tests for convert_to_mp4 function."""

    def test_successful_conversion(self, tmp_path: Path) -> None:
        """Test successful MP4 conversion."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.mp4"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake mp4")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = convert_to_mp4(input_path, output_path)

        assert result == output_path

    def test_crf_settings_applied(self, tmp_path: Path) -> None:
        """Test CRF quality setting is applied."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.mp4"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake mp4")
            return mock_result

        settings = VideoEncodingSettings(crf=18)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_to_mp4(input_path, output_path, settings)

        cmd = mock_run.call_args[0][0]
        assert "-crf" in cmd
        crf_idx = cmd.index("-crf")
        assert cmd[crf_idx + 1] == "18"

    def test_fps_filter_applied(self, tmp_path: Path) -> None:
        """Test FPS filter is applied."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.mp4"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake mp4")
            return mock_result

        settings = VideoEncodingSettings(fps=30)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_to_mp4(input_path, output_path, settings)

        cmd = mock_run.call_args[0][0]
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "fps=30" in cmd[vf_idx + 1]

    def test_ffmpeg_failure_raises_conversion_error(self, tmp_path: Path) -> None:
        """Test ConversionError on ffmpeg failure."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.mp4"

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"Error"

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(ConversionError) as exc_info:
                convert_to_mp4(input_path, output_path)

        assert "mp4 conversion failed" in str(exc_info.value).lower()


# =============================================================================
# convert_video Tests
# =============================================================================


class TestConvertVideo:
    """Tests for convert_video function."""

    def test_mov_no_conversion_same_path(self, tmp_path: Path) -> None:
        """Test MOV format with same path does no conversion."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")

        result = convert_video(input_path, OutputFormat.MOV, input_path)

        assert result == input_path

    def test_mov_copies_to_output_path(self, tmp_path: Path) -> None:
        """Test MOV format copies file to output path."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video content")
        output_path = tmp_path / "output.mov"

        result = convert_video(input_path, OutputFormat.MOV, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"fake video content"

    def test_gif_conversion(self, tmp_path: Path) -> None:
        """Test GIF conversion delegated to convert_to_gif."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.gif"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake gif")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = convert_video(input_path, OutputFormat.GIF, output_path)

        assert result == output_path

    def test_webp_conversion(self, tmp_path: Path) -> None:
        """Test WebP conversion delegated to convert_to_webp."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.webp"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake webp")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = convert_video(input_path, OutputFormat.WEBP, output_path)

        assert result == output_path

    def test_mp4_conversion(self, tmp_path: Path) -> None:
        """Test MP4 conversion delegated to convert_to_mp4."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.mp4"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake mp4")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = convert_video(input_path, OutputFormat.MP4, output_path)

        assert result == output_path

    def test_auto_generate_output_path(self, tmp_path: Path) -> None:
        """Test output path auto-generated from input."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            # Create the expected output
            (tmp_path / "input.gif").write_bytes(b"fake gif")
            return mock_result

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            result = convert_video(input_path, OutputFormat.GIF)

        assert result.suffix == ".gif"
        assert result.stem == "input"

    def test_settings_passed_through(self, tmp_path: Path) -> None:
        """Test settings are passed to conversion function."""
        input_path = tmp_path / "input.mov"
        input_path.write_bytes(b"fake video")
        output_path = tmp_path / "output.gif"

        mock_result = Mock()
        mock_result.returncode = 0

        def run_side_effect(*_args, **_kwargs):
            output_path.write_bytes(b"fake gif")
            return mock_result

        settings = VideoEncodingSettings(fps=5, max_width=400)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", side_effect=run_side_effect) as mock_run,
        ):
            convert_video(input_path, OutputFormat.GIF, output_path, settings)

        cmd = mock_run.call_args[0][0]
        filter_idx = cmd.index("-filter_complex")
        filter_value = cmd[filter_idx + 1]
        assert "fps=5" in filter_value
        assert "400" in filter_value
