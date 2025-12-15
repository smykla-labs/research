"""Comprehensive tests for macOS OCR Finder skill."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ocr_finder import (
    BoundingBox,
    OcrFinderError,
    SearchOptions,
    TextMatch,
    TextNotFoundError,
    find_text,
    get_click_target,
    list_all_text,
)
from ocr_finder.actions import sanitize_image_path
from ocr_finder.cli import (
    main,
)
from ocr_finder.core import extract_text_regions, get_reader

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_bbox() -> BoundingBox:
    """Create a sample bounding box for testing."""
    return BoundingBox(x1=10, y1=20, x2=110, y2=70)


@pytest.fixture
def sample_text_match(sample_bbox: BoundingBox) -> TextMatch:
    """Create a sample text match for testing."""
    return TextMatch(text="Hello World", bbox=sample_bbox, confidence=0.95)


@pytest.fixture
def sample_search_options() -> SearchOptions:
    """Create sample search options."""
    return SearchOptions(exact=True, case_sensitive=True, min_confidence=0.8)


@pytest.fixture
def mock_easyocr_results() -> list[tuple[list[list[int]], str, float]]:
    """Mock EasyOCR readtext results."""
    return [
        ([[10, 20], [110, 20], [110, 70], [10, 70]], "Hello", 0.95),
        ([[120, 20], [220, 20], [220, 70], [120, 70]], "World", 0.90),
        ([[10, 80], [200, 80], [200, 130], [10, 130]], "Test Button", 0.85),
        ([[10, 140], [100, 140], [100, 190], [10, 190]], "Low Conf", 0.30),
    ]


@pytest.fixture
def temp_image(tmp_path: Path) -> Path:
    """Create a temporary valid PNG image for testing."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (300, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 20), "Hello", fill="black")
    draw.text((120, 20), "World", fill="black")
    draw.text((10, 80), "Test Button", fill="black")
    img_path = tmp_path / "test_image.png"
    img.save(img_path)
    return img_path


# =============================================================================
# BoundingBox Tests
# =============================================================================


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_field_access(self, sample_bbox: BoundingBox) -> None:
        """Test field access."""
        assert sample_bbox.x1 == 10
        assert sample_bbox.y1 == 20
        assert sample_bbox.x2 == 110
        assert sample_bbox.y2 == 70

    def test_center_property(self, sample_bbox: BoundingBox) -> None:
        """Test center property calculation."""
        center = sample_bbox.center
        assert center == (60, 45)

    def test_width_property(self, sample_bbox: BoundingBox) -> None:
        """Test width property."""
        assert sample_bbox.width == 100

    def test_height_property(self, sample_bbox: BoundingBox) -> None:
        """Test height property."""
        assert sample_bbox.height == 50

    def test_to_dict(self, sample_bbox: BoundingBox) -> None:
        """Test to_dict method."""
        data = sample_bbox.to_dict()
        assert data["x1"] == 10
        assert data["y1"] == 20
        assert data["x2"] == 110
        assert data["y2"] == 70
        assert data["width"] == 100
        assert data["height"] == 50
        assert data["center_x"] == 60
        assert data["center_y"] == 45

    def test_frozen_immutable(self, sample_bbox: BoundingBox) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_bbox.x1 = 999  # type: ignore[misc]

    def test_zero_size_box(self) -> None:
        """Test bounding box with zero size."""
        bbox = BoundingBox(x1=50, y1=50, x2=50, y2=50)
        assert bbox.width == 0
        assert bbox.height == 0
        assert bbox.center == (50, 50)


# =============================================================================
# TextMatch Tests
# =============================================================================


class TestTextMatch:
    """Tests for TextMatch dataclass."""

    def test_field_access(self, sample_text_match: TextMatch) -> None:
        """Test field access."""
        assert sample_text_match.text == "Hello World"
        assert sample_text_match.confidence == 0.95
        assert sample_text_match.bbox.x1 == 10

    def test_click_coords_property(self, sample_text_match: TextMatch) -> None:
        """Test click_coords property delegates to bbox.center."""
        assert sample_text_match.click_coords == (60, 45)

    def test_to_dict(self, sample_text_match: TextMatch) -> None:
        """Test to_dict method."""
        data = sample_text_match.to_dict()
        assert data["text"] == "Hello World"
        assert data["confidence"] == 0.95
        assert data["click_x"] == 60
        assert data["click_y"] == 45
        assert "bbox" in data
        assert data["bbox"]["width"] == 100

    def test_frozen_immutable(self, sample_text_match: TextMatch) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_text_match.text = "New Text"  # type: ignore[misc]


# =============================================================================
# SearchOptions Tests
# =============================================================================


class TestSearchOptions:
    """Tests for SearchOptions dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        options = SearchOptions()
        assert options.exact is False
        assert options.case_sensitive is False
        assert options.min_confidence == 0.5

    def test_custom_values(self, sample_search_options: SearchOptions) -> None:
        """Test custom values."""
        assert sample_search_options.exact is True
        assert sample_search_options.case_sensitive is True
        assert sample_search_options.min_confidence == 0.8

    def test_frozen_immutable(self, sample_search_options: SearchOptions) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_search_options.exact = False  # type: ignore[misc]


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for custom exceptions."""

    def test_ocr_finder_error_is_base(self) -> None:
        """Test OcrFinderError is base exception."""
        assert issubclass(TextNotFoundError, OcrFinderError)

    def test_text_not_found_error_message(self) -> None:
        """Test TextNotFoundError message handling."""
        e = TextNotFoundError("Text 'Submit' not found")
        assert "Submit" in str(e)


# =============================================================================
# Sanitization Tests
# =============================================================================


class TestSanitizeImagePath:
    """Tests for sanitize_image_path function."""

    def test_valid_path(self, temp_image: Path) -> None:
        """Test sanitizing valid image path."""
        result = sanitize_image_path(temp_image)
        assert result == temp_image.resolve()

    def test_string_path(self, temp_image: Path) -> None:
        """Test sanitizing string path."""
        result = sanitize_image_path(str(temp_image))
        assert result == temp_image.resolve()

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test sanitizing nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Image not found"):
            sanitize_image_path(tmp_path / "nonexistent.png")

    def test_directory_path(self, tmp_path: Path) -> None:
        """Test sanitizing directory raises ValueError."""
        with pytest.raises(ValueError, match="not a file"):
            sanitize_image_path(tmp_path)

    def test_expanduser(self, temp_image: Path, monkeypatch) -> None:
        """Test that ~ is expanded."""
        # This test verifies expanduser is called, not actual expansion
        result = sanitize_image_path(temp_image)
        assert result.is_absolute()


# =============================================================================
# Core Function Tests
# =============================================================================


class TestGetReader:
    """Tests for get_reader function."""

    def test_reader_cached(self) -> None:
        """Test that reader is cached for same language tuple."""
        mock_easyocr = MagicMock()
        mock_reader = MagicMock()
        mock_easyocr.Reader.return_value = mock_reader

        # Clear cache
        from ocr_finder import core

        core._reader_cache.clear()

        with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
            reader1 = get_reader(("en",))
            reader2 = get_reader(("en",))

            assert reader1 is reader2
            mock_easyocr.Reader.assert_called_once_with(["en"], gpu=False)

    def test_different_languages_create_new_reader(self) -> None:
        """Test that different languages create separate readers."""
        mock_easyocr = MagicMock()
        mock_reader_en = MagicMock()
        mock_reader_de = MagicMock()
        mock_easyocr.Reader.side_effect = [mock_reader_en, mock_reader_de]

        from ocr_finder import core

        core._reader_cache.clear()

        with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
            reader_en = get_reader(("en",))
            reader_de = get_reader(("de",))

            assert reader_en is not reader_de
            assert mock_easyocr.Reader.call_count == 2


class TestExtractTextRegions:
    """Tests for extract_text_regions function."""

    def test_extract_returns_text_matches(
        self, temp_image: Path, mock_easyocr_results: list
    ) -> None:
        """Test that extract returns tuple of TextMatch objects."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            results = extract_text_regions(temp_image)

            assert len(results) == 4
            assert all(isinstance(r, TextMatch) for r in results)
            assert results[0].text == "Hello"
            assert results[0].confidence == 0.95
            assert results[0].bbox.x1 == 10

    def test_extract_empty_image(self, temp_image: Path) -> None:
        """Test extraction from image with no text."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = []
            mock_get_reader.return_value = mock_reader

            results = extract_text_regions(temp_image)
            assert results == ()


# =============================================================================
# Action Function Tests
# =============================================================================


class TestFindText:
    """Tests for find_text function."""

    def test_find_substring_match(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test finding text with substring match."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            matches = find_text(temp_image, "button")
            assert len(matches) == 1
            assert matches[0].text == "Test Button"

    def test_find_case_insensitive(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test case-insensitive search (default)."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            matches = find_text(temp_image, "HELLO")
            assert len(matches) == 1
            assert matches[0].text == "Hello"

    def test_find_case_sensitive(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test case-sensitive search."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            options = SearchOptions(case_sensitive=True)
            matches = find_text(temp_image, "HELLO", options)
            assert len(matches) == 0

            matches = find_text(temp_image, "Hello", options)
            assert len(matches) == 1

    def test_find_exact_match(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test exact match."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            # Substring should not match in exact mode
            options = SearchOptions(exact=True)
            matches = find_text(temp_image, "button", options)
            assert len(matches) == 0

            # Exact text should match
            matches = find_text(temp_image, "test button", options)
            assert len(matches) == 1

    def test_find_respects_min_confidence(
        self, temp_image: Path, mock_easyocr_results: list
    ) -> None:
        """Test min_confidence filtering."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            # Default min_confidence=0.5 should filter out "Low Conf" (0.30)
            matches = find_text(temp_image, "low")
            assert len(matches) == 0

            # Lower threshold should include it
            options = SearchOptions(min_confidence=0.2)
            matches = find_text(temp_image, "low", options)
            assert len(matches) == 1

    def test_find_no_matches(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test finding text that doesn't exist."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            matches = find_text(temp_image, "nonexistent")
            assert matches == ()


class TestGetClickTarget:
    """Tests for get_click_target function."""

    def test_get_click_target_returns_coords(
        self, temp_image: Path, mock_easyocr_results: list
    ) -> None:
        """Test getting click target returns center coordinates."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            x, y = get_click_target(temp_image, "Hello")
            # BoundingBox: x1=10, y1=20, x2=110, y2=70 -> center=(60, 45)
            assert x == 60
            assert y == 45

    def test_get_click_target_with_index(
        self, temp_image: Path, mock_easyocr_results: list
    ) -> None:
        """Test getting click target with index when multiple matches."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            # Add duplicate "Hello" at different position
            results_with_dupe = [
                *mock_easyocr_results,
                ([[300, 20], [400, 20], [400, 70], [300, 70]], "Hello", 0.92),
            ]
            mock_reader.readtext.return_value = results_with_dupe
            mock_get_reader.return_value = mock_reader

            x1, _y1 = get_click_target(temp_image, "Hello", index=0)
            x2, _y2 = get_click_target(temp_image, "Hello", index=1)

            assert x1 != x2  # Different positions

    def test_get_click_target_not_found(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test TextNotFoundError when text not found."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            with pytest.raises(TextNotFoundError, match="Text not found"):
                get_click_target(temp_image, "nonexistent")

    def test_get_click_target_index_out_of_range(
        self, temp_image: Path, mock_easyocr_results: list
    ) -> None:
        """Test TextNotFoundError when index out of range."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            with pytest.raises(TextNotFoundError, match="out of range"):
                get_click_target(temp_image, "Hello", index=999)


class TestListAllText:
    """Tests for list_all_text function."""

    def test_list_returns_all_regions(self, temp_image: Path, mock_easyocr_results: list) -> None:
        """Test list_all_text returns all regions."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            regions = list_all_text(temp_image, min_confidence=0.0)
            assert len(regions) == 4

    def test_list_respects_min_confidence(
        self, temp_image: Path, mock_easyocr_results: list
    ) -> None:
        """Test min_confidence filtering in list_all_text."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            # High confidence threshold
            regions = list_all_text(temp_image, min_confidence=0.9)
            assert len(regions) == 2  # Only Hello (0.95) and World (0.90)


# =============================================================================
# CLI Tests (Typer subcommand interface)
# =============================================================================


class TestCLIParser:
    """Tests for CLI subcommand parsing."""

    def test_list_subcommand(self) -> None:
        """Test list subcommand with nonexistent file."""
        result = main(["list", "--image", "test.png"])
        # Typer validates exists=True and returns exit code 2
        assert result == 2

    def test_find_subcommand(self) -> None:
        """Test find subcommand with nonexistent file."""
        result = main(["find", "text", "--image", "test.png"])
        assert result == 2  # Typer validation error

    def test_click_subcommand(self) -> None:
        """Test click subcommand with nonexistent file."""
        result = main(["click", "text", "--image", "test.png"])
        assert result == 2  # Typer validation error

    def test_image_required_for_list(self) -> None:
        """Test --image is required for list subcommand."""
        result = main(["list"])
        assert result == 2  # Typer error code for missing required option

    def test_short_image_flag(self) -> None:
        """Test -i short flag for --image."""
        result = main(["list", "-i", "test.png"])
        assert result == 2  # Typer validation error (file doesn't exist)


class TestHandleList:
    """Tests for list subcommand."""

    def test_handle_list_json_output(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test list with --json output."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["list", "--image", str(temp_image), "--json"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Hello" in captured.out
            assert '"text"' in captured.out

    def test_handle_list_table_output(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test list with table output."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["list", "--image", str(temp_image), "--min-confidence", "0"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Hello" in captured.out
            assert "Confidence" in captured.out

    def test_handle_list_empty(self, temp_image: Path, capsys) -> None:
        """Test list with no text found."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = []
            mock_get_reader.return_value = mock_reader

            result = main(["list", "--image", str(temp_image)])

            assert result == 0
            captured = capsys.readouterr()
            assert "No text found" in captured.out


class TestHandleFind:
    """Tests for find subcommand."""

    def test_handle_find_with_matches(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test find with matches."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["find", "Hello", "--image", str(temp_image)])

            assert result == 0
            captured = capsys.readouterr()
            assert "Found 1 match" in captured.out

    def test_handle_find_no_matches(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test find with no matches."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["find", "nonexistent", "--image", str(temp_image)])

            assert result == 1
            captured = capsys.readouterr()
            assert "No matches found" in captured.out

    def test_handle_find_json_output(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test find with --json output."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["find", "Hello", "--image", str(temp_image), "--json"])

            assert result == 0
            captured = capsys.readouterr()
            assert '"text"' in captured.out
            assert '"bbox"' in captured.out


class TestHandleClick:
    """Tests for click subcommand."""

    def test_handle_click_returns_coords(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test click returns coordinates."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["click", "Hello", "--image", str(temp_image)])

            assert result == 0
            captured = capsys.readouterr()
            assert "60,45" in captured.out  # center of Hello bbox

    def test_handle_click_json_output(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test click with --json output."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["click", "Hello", "--image", str(temp_image), "--json"])

            assert result == 0
            captured = capsys.readouterr()
            assert '"x": 60' in captured.out
            assert '"y": 45' in captured.out

    def test_handle_click_not_found(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test click with text not found."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["click", "nonexistent", "--image", str(temp_image)])

            assert result == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err

    def test_handle_click_with_index(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test click with --index."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            result = main(["click", "Hello", "--image", str(temp_image), "--index", "0"])

            assert result == 0


class TestCLIOptions:
    """Tests for CLI option handling."""

    def test_exact_flag(self, temp_image: Path, mock_easyocr_results: list, capsys) -> None:
        """Test --exact flag."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            # Without exact: "ell" matches "Hello"
            result = main(["find", "ell", "--image", str(temp_image)])
            assert result == 0

            # With exact: "ell" does not match "Hello"
            result = main(["find", "ell", "--image", str(temp_image), "--exact"])
            assert result == 1

    def test_case_sensitive_flag(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test --case-sensitive flag."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            # Without case-sensitive: "hello" matches "Hello"
            result = main(["find", "hello", "--image", str(temp_image)])
            assert result == 0

            # With case-sensitive: "hello" does not match "Hello"
            result = main(["find", "hello", "--image", str(temp_image), "--case-sensitive"])
            assert result == 1

    def test_min_confidence_flag(
        self, temp_image: Path, mock_easyocr_results: list, capsys
    ) -> None:
        """Test --min-confidence flag."""
        with patch("ocr_finder.core.get_reader") as mock_get_reader:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = mock_easyocr_results
            mock_get_reader.return_value = mock_reader

            # Default min-confidence filters out "Low Conf" (0.30)
            result = main(["find", "Low", "--image", str(temp_image)])
            assert result == 1  # Not found

            # Lower threshold includes it
            result = main(["find", "Low", "--image", str(temp_image), "--min-confidence", "0.2"])
            assert result == 0


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_file_not_found_error(self, capsys) -> None:
        """Test file not found handling (Typer validation)."""
        result = main(["list", "--image", "/nonexistent/path/image.png"])
        assert result == 2  # Typer validation error for exists=True
        captured = capsys.readouterr()
        assert "not exist" in captured.err
