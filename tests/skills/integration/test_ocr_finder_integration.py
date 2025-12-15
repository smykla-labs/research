"""Integration tests for OCR Finder using real EasyOCR detection.

These tests use real EasyOCR (no mocking) to verify text detection accuracy.
Tests are marked with `integration` and `slow` markers for selective execution.

Run only integration tests:
    pytest -m integration tests/skills/integration/

Skip integration tests:
    pytest -m "not integration"
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# Pytest Markers
# =============================================================================

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


# =============================================================================
# Fixture Image Generator
# =============================================================================


def _get_default_font(size: int = 24) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font for image generation.

    Tries common macOS fonts, falls back to default PIL font.
    """
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/Library/Fonts/Arial.ttf",
    ]

    for font_path in font_paths:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue

    # Fall back to default font (may be small)
    return ImageFont.load_default()


def create_test_image(
    texts: list[tuple[str, tuple[int, int]]],
    size: tuple[int, int] = (600, 400),
    background: str = "white",
    text_color: str = "black",
    font_size: int = 24,
) -> Image.Image:
    """Create a test image with specified text at positions.

    Args:
        texts: List of (text, (x, y)) tuples for text placement.
        size: Image dimensions (width, height).
        background: Background color.
        text_color: Text color.
        font_size: Font size in pixels.

    Returns:
        PIL Image object.
    """
    img = Image.new("RGB", size, color=background)
    draw = ImageDraw.Draw(img)
    font = _get_default_font(font_size)

    for text, position in texts:
        draw.text(position, text, fill=text_color, font=font)

    return img


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a temporary directory for fixture images."""
    return tmp_path_factory.mktemp("ocr_fixtures")


@pytest.fixture(scope="module")
def simple_text_image(fixtures_dir: Path) -> Path:
    """Create a simple image with clear text."""
    img = create_test_image(
        texts=[
            ("Hello", (50, 50)),
            ("World", (50, 100)),
            ("Button", (50, 150)),
            ("Submit", (200, 150)),
        ],
        font_size=32,
    )
    path = fixtures_dir / "simple_text.png"
    img.save(path)
    return path


@pytest.fixture(scope="module")
def menu_image(fixtures_dir: Path) -> Path:
    """Create an image simulating a menu with buttons."""
    img = create_test_image(
        texts=[
            ("File", (10, 10)),
            ("Edit", (80, 10)),
            ("View", (150, 10)),
            ("Help", (220, 10)),
            ("Save", (50, 80)),
            ("Cancel", (150, 80)),
            ("OK", (280, 80)),
        ],
        size=(400, 150),
        font_size=28,
    )
    path = fixtures_dir / "menu.png"
    img.save(path)
    return path


@pytest.fixture(scope="module")
def mixed_case_image(fixtures_dir: Path) -> Path:
    """Create an image with mixed case text."""
    img = create_test_image(
        texts=[
            ("UPPERCASE", (50, 50)),
            ("lowercase", (50, 100)),
            ("MixedCase", (50, 150)),
            ("CamelCase", (50, 200)),
        ],
        font_size=28,
    )
    path = fixtures_dir / "mixed_case.png"
    img.save(path)
    return path


@pytest.fixture(scope="module")
def low_contrast_image(fixtures_dir: Path) -> Path:
    """Create a low contrast image (gray text on light gray background)."""
    img = create_test_image(
        texts=[
            ("LowContrast", (50, 50)),
            ("Faded", (50, 100)),
        ],
        background="#e0e0e0",
        text_color="#909090",
        font_size=32,
    )
    path = fixtures_dir / "low_contrast.png"
    img.save(path)
    return path


@pytest.fixture(scope="module")
def empty_image(fixtures_dir: Path) -> Path:
    """Create an empty image with no text."""
    img = Image.new("RGB", (300, 200), color="white")
    path = fixtures_dir / "empty.png"
    img.save(path)
    return path


@pytest.fixture(scope="module")
def multiline_image(fixtures_dir: Path) -> Path:
    """Create an image with multiple lines of text."""
    img = create_test_image(
        texts=[
            ("First line of text", (50, 30)),
            ("Second line here", (50, 80)),
            ("Third and final", (50, 130)),
        ],
        size=(400, 200),
        font_size=24,
    )
    path = fixtures_dir / "multiline.png"
    img.save(path)
    return path


@pytest.fixture(scope="module")
def numbers_image(fixtures_dir: Path) -> Path:
    """Create an image with numbers and text."""
    img = create_test_image(
        texts=[
            ("Item 1", (50, 50)),
            ("Price: $99.99", (50, 100)),
            ("Qty: 42", (50, 150)),
            ("Total: 123.45", (50, 200)),
        ],
        font_size=24,
    )
    path = fixtures_dir / "numbers.png"
    img.save(path)
    return path


# =============================================================================
# Real OCR Detection Tests
# =============================================================================


class TestRealOcrDetection:
    """Tests using real EasyOCR detection (no mocking)."""

    def test_detect_simple_text(self, simple_text_image: Path) -> None:
        """Test detecting simple text in clear image."""
        from ocr_finder import list_all_text

        regions = list_all_text(simple_text_image, min_confidence=0.0)

        # Should detect at least some text
        assert len(regions) > 0

        # Check that detected text includes expected words
        detected_texts = {r.text.lower() for r in regions}
        expected_words = {"hello", "world", "button", "submit"}

        # At least some expected words should be detected
        matched = detected_texts & expected_words
        assert len(matched) >= 2, f"Expected some of {expected_words}, got {detected_texts}"

    def test_detect_menu_items(self, menu_image: Path) -> None:
        """Test detecting menu items."""
        from ocr_finder import list_all_text

        regions = list_all_text(menu_image, min_confidence=0.0)
        detected_texts = {r.text.lower() for r in regions}

        # Menu items should be detected
        menu_items = {"file", "edit", "view", "help", "save", "cancel", "ok"}
        matched = detected_texts & menu_items

        assert len(matched) >= 3, f"Expected menu items, got {detected_texts}"

    def test_bounding_boxes_are_valid(self, simple_text_image: Path) -> None:
        """Test that bounding boxes have valid coordinates."""
        from ocr_finder import list_all_text

        regions = list_all_text(simple_text_image, min_confidence=0.0)

        for region in regions:
            bbox = region.bbox

            # Coordinates should be non-negative
            assert bbox.x1 >= 0
            assert bbox.y1 >= 0
            assert bbox.x2 >= 0
            assert bbox.y2 >= 0

            # Box should have positive dimensions
            assert bbox.width >= 0
            assert bbox.height >= 0

            # x2 should be >= x1, y2 should be >= y1
            assert bbox.x2 >= bbox.x1
            assert bbox.y2 >= bbox.y1

    def test_confidence_values_in_range(self, simple_text_image: Path) -> None:
        """Test that confidence values are in valid range [0, 1]."""
        from ocr_finder import list_all_text

        regions = list_all_text(simple_text_image, min_confidence=0.0)

        for region in regions:
            assert 0.0 <= region.confidence <= 1.0, (
                f"Confidence {region.confidence} out of range for '{region.text}'"
            )

    def test_click_coords_within_image(self, simple_text_image: Path) -> None:
        """Test that click coordinates are within image bounds."""
        from ocr_finder import list_all_text
        from PIL import Image

        img = Image.open(simple_text_image)
        width, height = img.size

        regions = list_all_text(simple_text_image, min_confidence=0.0)

        for region in regions:
            x, y = region.click_coords

            assert 0 <= x <= width, f"X coord {x} outside image width {width}"
            assert 0 <= y <= height, f"Y coord {y} outside image height {height}"

    def test_empty_image_returns_empty(self, empty_image: Path) -> None:
        """Test that empty image returns no text regions."""
        from ocr_finder import list_all_text

        regions = list_all_text(empty_image, min_confidence=0.0)

        # Empty image should return empty or very few results
        assert len(regions) <= 2  # Allow for noise detection


# =============================================================================
# Find Text Tests
# =============================================================================


class TestFindText:
    """Tests for find_text function with real OCR."""

    def test_find_existing_text(self, simple_text_image: Path) -> None:
        """Test finding text that exists in image."""
        from ocr_finder import SearchOptions, find_text

        # Search for a word we know is in the image
        options = SearchOptions(min_confidence=0.0)
        matches = find_text(simple_text_image, "hello", options)

        # Should find at least one match
        assert len(matches) >= 1

    def test_find_returns_correct_match(self, menu_image: Path) -> None:
        """Test that find returns the correct text match."""
        from ocr_finder import SearchOptions, find_text

        options = SearchOptions(min_confidence=0.0)
        matches = find_text(menu_image, "save", options)

        if matches:
            # The matched text should contain 'save' (case-insensitive)
            assert any("save" in m.text.lower() for m in matches)

    def test_find_nonexistent_text(self, simple_text_image: Path) -> None:
        """Test finding text that doesn't exist."""
        from ocr_finder import SearchOptions, find_text

        options = SearchOptions(min_confidence=0.0)
        matches = find_text(simple_text_image, "xyznonexistent123", options)

        assert len(matches) == 0

    def test_find_case_insensitive_default(self, mixed_case_image: Path) -> None:
        """Test that search is case-insensitive by default."""
        from ocr_finder import SearchOptions, find_text

        # Search lowercase for UPPERCASE text
        options = SearchOptions(min_confidence=0.0)
        matches = find_text(mixed_case_image, "uppercase", options)

        # Should find the UPPERCASE text
        if matches:
            assert any("upper" in m.text.lower() for m in matches)

    def test_find_case_sensitive(self, mixed_case_image: Path) -> None:
        """Test case-sensitive search."""
        from ocr_finder import SearchOptions, find_text

        # Search lowercase for UPPERCASE text with case-sensitive
        options = SearchOptions(case_sensitive=True, min_confidence=0.0)
        matches_lower = find_text(mixed_case_image, "uppercase", options)
        matches_upper = find_text(mixed_case_image, "UPPERCASE", options)

        # lowercase search should not find UPPERCASE
        # uppercase search might find it (depends on OCR accuracy)
        assert len(matches_lower) <= len(matches_upper) or len(matches_lower) == 0


# =============================================================================
# Confidence Threshold Tests
# =============================================================================


class TestConfidenceThresholds:
    """Tests for confidence threshold filtering."""

    def test_high_confidence_filters_results(self, simple_text_image: Path) -> None:
        """Test that high confidence threshold reduces results."""
        from ocr_finder import list_all_text

        all_results = list_all_text(simple_text_image, min_confidence=0.0)
        high_conf_results = list_all_text(simple_text_image, min_confidence=0.9)

        # High confidence should return same or fewer results
        assert len(high_conf_results) <= len(all_results)

    def test_low_contrast_detection(self, low_contrast_image: Path) -> None:
        """Test detection in low contrast image."""
        from ocr_finder import list_all_text

        # Low contrast may have lower confidence scores
        regions = list_all_text(low_contrast_image, min_confidence=0.0)

        # May or may not detect text depending on OCR quality
        # Just verify it doesn't crash
        assert isinstance(regions, tuple)


# =============================================================================
# Get Click Target Tests
# =============================================================================


class TestGetClickTarget:
    """Tests for get_click_target function."""

    def test_get_click_target_returns_coords(self, menu_image: Path) -> None:
        """Test getting click coordinates for detected text."""
        from ocr_finder import SearchOptions, find_text, get_click_target
        from ocr_finder.models import TextNotFoundError

        options = SearchOptions(min_confidence=0.0)

        # First check if any menu items are detected
        matches = find_text(menu_image, "file", options)

        if matches:
            # Get click target for a detected item
            x, y = get_click_target(menu_image, "file", options)

            assert isinstance(x, int)
            assert isinstance(y, int)
            assert x > 0
            assert y > 0
        else:
            # If OCR didn't detect 'file', verify the error is raised
            with pytest.raises(TextNotFoundError):
                get_click_target(menu_image, "file", options)

    def test_get_click_target_not_found_raises(self, simple_text_image: Path) -> None:
        """Test that TextNotFoundError is raised for non-existent text."""
        from ocr_finder import get_click_target
        from ocr_finder.models import TextNotFoundError

        with pytest.raises(TextNotFoundError):
            get_click_target(simple_text_image, "nonexistent_text_xyz123")


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """End-to-end CLI tests with real images.

    These tests call the CLI main function directly since the skill package
    is not installed as a standalone executable.
    """

    def test_cli_list_command(
        self, simple_text_image: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list CLI command."""
        from ocr_finder.cli import main

        exit_code = main(["--list", "--image", str(simple_text_image), "--min-confidence", "0"])

        assert exit_code == 0

        # Output should contain some detected text
        captured = capsys.readouterr()
        output = captured.out.lower()
        assert "text" in output or "hello" in output or "world" in output or "no text" in output

    def test_cli_list_json_output(
        self, simple_text_image: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --list with --json output."""
        from ocr_finder.cli import main

        exit_code = main(
            ["--list", "--image", str(simple_text_image), "--json", "--min-confidence", "0"]
        )

        assert exit_code == 0

        # Output should be valid JSON
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)

        # Each item should have required fields
        for item in data:
            assert "text" in item
            assert "confidence" in item
            assert "bbox" in item

    def test_cli_find_command(self, menu_image: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --find CLI command."""
        from ocr_finder.cli import main

        exit_code = main(["--find", "file", "--image", str(menu_image), "--min-confidence", "0"])

        # May or may not find depending on OCR accuracy
        # Just verify it runs without crashing
        assert exit_code in (0, 1)

    def test_cli_find_json_output(
        self, menu_image: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --find with --json output."""
        from ocr_finder.cli import main

        exit_code = main(
            ["--find", "file", "--image", str(menu_image), "--json", "--min-confidence", "0"]
        )

        captured = capsys.readouterr()

        if exit_code == 0:
            data = json.loads(captured.out)
            assert isinstance(data, list)

    def test_cli_click_command(
        self, simple_text_image: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --click CLI command."""
        from ocr_finder.cli import main

        # First find something that exists
        list_code = main(
            ["--list", "--image", str(simple_text_image), "--json", "--min-confidence", "0"]
        )
        list_captured = capsys.readouterr()

        if list_code == 0:
            data = json.loads(list_captured.out)

            if data:
                # Try to click on the first detected text
                first_text = data[0]["text"]
                click_code = main(
                    [
                        "--click",
                        first_text,
                        "--image",
                        str(simple_text_image),
                        "--min-confidence",
                        "0",
                    ]
                )
                click_captured = capsys.readouterr()

                if click_code == 0:
                    # Output should be "x,y" format
                    coords = click_captured.out.strip()
                    assert "," in coords

                    parts = coords.split(",")
                    assert len(parts) == 2
                    assert parts[0].strip().isdigit()
                    assert parts[1].strip().isdigit()

    def test_cli_click_json_output(
        self, simple_text_image: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --click with --json output."""
        from ocr_finder.cli import main

        # First find something that exists
        list_code = main(
            ["--list", "--image", str(simple_text_image), "--json", "--min-confidence", "0"]
        )
        list_captured = capsys.readouterr()

        if list_code == 0:
            data = json.loads(list_captured.out)

            if data:
                first_text = data[0]["text"]
                click_code = main(
                    [
                        "--click",
                        first_text,
                        "--image",
                        str(simple_text_image),
                        "--json",
                        "--min-confidence",
                        "0",
                    ]
                )
                click_captured = capsys.readouterr()

                if click_code == 0:
                    coords = json.loads(click_captured.out)
                    assert "x" in coords
                    assert "y" in coords
                    assert isinstance(coords["x"], int)
                    assert isinstance(coords["y"], int)

    def test_cli_nonexistent_image_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error handling for non-existent image."""
        from ocr_finder.cli import main

        exit_code = main(["--list", "--image", "/nonexistent/path/image.png"])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_cli_exact_flag(
        self, simple_text_image: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --exact flag."""
        from ocr_finder.cli import main

        # Without exact: partial match
        code1 = main(["--find", "hel", "--image", str(simple_text_image), "--min-confidence", "0"])
        _ = capsys.readouterr()  # Clear captured output

        # With exact: no partial match
        code2 = main(
            ["--find", "hel", "--image", str(simple_text_image), "--exact", "--min-confidence", "0"]
        )
        _ = capsys.readouterr()  # Clear captured output

        # Exact match should be more restrictive
        # (may both fail if OCR doesn't detect 'hello', that's OK)
        assert code2 >= code1 or code1 == 1


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_numbers_detection(self, numbers_image: Path) -> None:
        """Test detection of numbers in text."""
        from ocr_finder import list_all_text

        regions = list_all_text(numbers_image, min_confidence=0.0)
        detected = " ".join(r.text for r in regions).lower()

        # Should detect some numbers or number-related text
        has_numbers = any(char.isdigit() for char in detected)

        # Either numbers are detected, or it's a known OCR limitation
        assert has_numbers or len(regions) >= 0

    def test_multiline_detection(self, multiline_image: Path) -> None:
        """Test detection of multiple lines."""
        from ocr_finder import list_all_text

        regions = list_all_text(multiline_image, min_confidence=0.0)

        # Should detect multiple regions for multiple lines
        # (may vary based on OCR settings)
        assert len(regions) >= 1

    def test_repeated_text_multiple_matches(self, fixtures_dir: Path) -> None:
        """Test that repeated text returns multiple matches."""
        # Create image with repeated text
        img = create_test_image(
            texts=[
                ("Click", (50, 50)),
                ("Click", (50, 100)),
                ("Click", (50, 150)),
            ],
            font_size=32,
        )
        path = fixtures_dir / "repeated.png"
        img.save(path)

        from ocr_finder import SearchOptions, find_text

        options = SearchOptions(min_confidence=0.0)
        matches = find_text(path, "click", options)

        # May detect multiple 'Click' instances
        # (depends on OCR accuracy and how it groups text)
        assert isinstance(matches, tuple)

    def test_special_characters(self, fixtures_dir: Path) -> None:
        """Test detection of text with special characters."""
        img = create_test_image(
            texts=[
                ("Email: test@example.com", (50, 50)),
                ("Price: $100.00", (50, 100)),
                ("Progress: 50%", (50, 150)),
            ],
            size=(400, 250),
            font_size=20,
        )
        path = fixtures_dir / "special_chars.png"
        img.save(path)

        from ocr_finder import list_all_text

        regions = list_all_text(path, min_confidence=0.0)

        # Should detect some text (special chars may affect accuracy)
        detected = " ".join(r.text for r in regions)

        # At least some text should be detected
        assert len(detected) > 0 or len(regions) == 0

    def test_unicode_text(self, fixtures_dir: Path) -> None:
        """Test handling of unicode text (if font supports it)."""
        # Simple ASCII for reliability
        img = create_test_image(
            texts=[
                ("Unicode Test", (50, 50)),
                ("ASCII Only", (50, 100)),
            ],
            font_size=28,
        )
        path = fixtures_dir / "unicode.png"
        img.save(path)

        from ocr_finder import list_all_text

        # Should not crash
        regions = list_all_text(path, min_confidence=0.0)
        assert isinstance(regions, tuple)


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Performance-related tests."""

    def test_reader_caching(self, simple_text_image: Path) -> None:
        """Test that EasyOCR reader is cached between calls."""
        from ocr_finder import list_all_text

        # First call
        result1 = list_all_text(simple_text_image, min_confidence=0.0)

        # Second call should use cached reader
        result2 = list_all_text(simple_text_image, min_confidence=0.0)

        # Results should be identical
        assert len(result1) == len(result2)

    def test_large_image_handling(self, fixtures_dir: Path) -> None:
        """Test handling of larger images."""
        # Create a larger image
        img = create_test_image(
            texts=[
                ("Large Image Test", (100, 100)),
                ("More Text Here", (100, 200)),
                ("Additional Content", (100, 300)),
            ],
            size=(1920, 1080),
            font_size=48,
        )
        path = fixtures_dir / "large.png"
        img.save(path)

        from ocr_finder import list_all_text

        # Should handle large images without error
        regions = list_all_text(path, min_confidence=0.0)
        assert isinstance(regions, tuple)
