"""Comprehensive tests for macOS Verified Screenshot skill."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from verified_screenshot import (
    CaptureConfig,
    CaptureError,
    CaptureResult,
    MaxRetriesError,
    RetryStrategy,
    ScreenshotError,
    VerificationResult,
    VerificationStrategy,
    WindowNotFoundError,
    WindowTarget,
    main,
    sanitize_app_name,
)
from verified_screenshot.actions import calculate_retry_delay, generate_output_path
from verified_screenshot.cli import (
    build_config,
    parse_retry_strategy,
    parse_verification_strategies,
)
from verified_screenshot.core import (
    verify_basic,
    verify_content,
    verify_dimensions,
    verify_text,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_target() -> WindowTarget:
    """Create a sample window target for testing."""
    return WindowTarget(
        window_id=12345,
        app_name="TestApp",
        window_title="Test Window",
        pid=9999,
        bounds_x=100.0,
        bounds_y=100.0,
        bounds_width=800.0,
        bounds_height=600.0,
        space_index=1,
        exe_path="/Applications/TestApp.app/Contents/MacOS/TestApp",
        cmdline=("testapp", "--debug"),
    )


@pytest.fixture
def sample_config() -> CaptureConfig:
    """Create a sample capture configuration."""
    return CaptureConfig(
        app_name="TestApp",
        title_pattern=".*Test.*",
        output_path="test_output.png",
        max_retries=3,
        verification_strategies=(VerificationStrategy.BASIC,),
    )


@pytest.fixture
def sample_verification_result() -> VerificationResult:
    """Create a sample verification result."""
    return VerificationResult(
        strategy=VerificationStrategy.BASIC,
        passed=True,
        message="Valid image file",
        details={"path": "test.png", "size": 1024},
    )


@pytest.fixture
def sample_capture_result(sample_target: WindowTarget) -> CaptureResult:
    """Create a sample capture result."""
    return CaptureResult(
        path=Path("test_output.png"),
        attempt=1,
        window_id=sample_target.window_id,
        app_name=sample_target.app_name,
        window_title=sample_target.window_title,
        expected_width=sample_target.bounds_width,
        expected_height=sample_target.bounds_height,
        actual_width=800,
        actual_height=600,
        verifications=(
            VerificationResult(
                strategy=VerificationStrategy.BASIC,
                passed=True,
                message="Valid",
                details={},
            ),
        ),
        verified=True,
        image_hash="abc123",
    )


@pytest.fixture
def temp_image(tmp_path: Path) -> Path:
    """Create a temporary valid PNG image for testing with varied content."""
    from PIL import Image, ImageDraw

    # Create image with varied content (not single color)
    img = Image.new("RGB", (100, 100), color="white")
    draw = ImageDraw.Draw(img)
    # Add colored rectangles to make it non-blank
    draw.rectangle([10, 10, 50, 50], fill="red")
    draw.rectangle([40, 40, 90, 90], fill="blue")
    draw.ellipse([20, 20, 80, 80], fill="green")
    img_path = tmp_path / "test_image.png"
    img.save(img_path)
    return img_path


@pytest.fixture
def blank_image(tmp_path: Path) -> Path:
    """Create a temporary blank PNG image for testing."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="white")
    img_path = tmp_path / "blank_image.png"
    img.save(img_path)
    return img_path


# =============================================================================
# WindowTarget Tests
# =============================================================================


class TestWindowTarget:
    """Tests for WindowTarget dataclass."""

    def test_field_access(self, sample_target: WindowTarget) -> None:
        """Test field access."""
        assert sample_target.window_id == 12345
        assert sample_target.app_name == "TestApp"
        assert sample_target.window_title == "Test Window"
        assert sample_target.pid == 9999

    def test_bounds_property(self, sample_target: WindowTarget) -> None:
        """Test bounds property."""
        bounds = sample_target.bounds
        assert bounds["x"] == 100.0
        assert bounds["y"] == 100.0
        assert bounds["width"] == 800.0
        assert bounds["height"] == 600.0

    def test_to_dict(self, sample_target: WindowTarget) -> None:
        """Test to_dict method."""
        data = sample_target.to_dict()
        assert data["window_id"] == 12345
        assert data["app_name"] == "TestApp"
        assert data["bounds"]["width"] == 800.0
        assert data["cmdline"] == ["testapp", "--debug"]

    def test_frozen_immutable(self, sample_target: WindowTarget) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_target.app_name = "NewApp"  # type: ignore[misc]


# =============================================================================
# CaptureConfig Tests
# =============================================================================


class TestCaptureConfig:
    """Tests for CaptureConfig dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = CaptureConfig()
        assert config.max_retries == 5
        assert config.settle_ms == 1000
        assert config.no_shadow is True
        assert config.activate_first is True

    def test_to_dict(self, sample_config: CaptureConfig) -> None:
        """Test to_dict method."""
        data = sample_config.to_dict()
        assert data["app_name"] == "TestApp"
        assert data["max_retries"] == 3
        assert "basic" in data["verification_strategies"]

    def test_frozen_immutable(self, sample_config: CaptureConfig) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            sample_config.app_name = "NewApp"  # type: ignore[misc]


# =============================================================================
# CaptureResult Tests
# =============================================================================


class TestCaptureResult:
    """Tests for CaptureResult dataclass."""

    def test_all_passed_true(self, sample_capture_result: CaptureResult) -> None:
        """Test all_passed when all verifications pass."""
        assert sample_capture_result.all_passed is True

    def test_all_passed_false(self) -> None:
        """Test all_passed when a verification fails."""
        result = CaptureResult(
            path=Path("test.png"),
            attempt=1,
            window_id=1,
            app_name="App",
            window_title="Title",
            expected_width=800,
            expected_height=600,
            actual_width=800,
            actual_height=600,
            verifications=(
                VerificationResult(
                    strategy=VerificationStrategy.BASIC,
                    passed=False,
                    message="Failed",
                    details={},
                ),
            ),
            verified=False,
        )
        assert result.all_passed is False

    def test_dimensions_match(self, sample_capture_result: CaptureResult) -> None:
        """Test dimensions_match property."""
        assert sample_capture_result.dimensions_match is True

    def test_dimensions_mismatch(self) -> None:
        """Test dimensions_match when dimensions don't match."""
        result = CaptureResult(
            path=Path("test.png"),
            attempt=1,
            window_id=1,
            app_name="App",
            window_title="Title",
            expected_width=800,
            expected_height=600,
            actual_width=400,  # 50% off
            actual_height=600,
            verifications=(),
            verified=False,
        )
        assert result.dimensions_match is False

    def test_to_dict(self, sample_capture_result: CaptureResult) -> None:
        """Test to_dict method."""
        data = sample_capture_result.to_dict()
        assert data["path"] == "test_output.png"
        assert data["attempt"] == 1
        assert data["verified"] is True
        assert data["image_hash"] == "abc123"


# =============================================================================
# VerificationResult Tests
# =============================================================================


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_to_dict(self, sample_verification_result: VerificationResult) -> None:
        """Test to_dict method."""
        data = sample_verification_result.to_dict()
        assert data["strategy"] == "basic"
        assert data["passed"] is True
        assert data["message"] == "Valid image file"


# =============================================================================
# Sanitization Tests
# =============================================================================


class TestSanitization:
    """Tests for input sanitization."""

    def test_sanitize_valid_app_name(self) -> None:
        """Test sanitizing valid app names."""
        assert sanitize_app_name("GoLand") == "GoLand"
        assert sanitize_app_name("Visual Studio Code") == "Visual Studio Code"
        assert sanitize_app_name("iTerm2") == "iTerm2"

    def test_sanitize_app_name_with_special_chars(self) -> None:
        """Test sanitizing app names with allowed special chars."""
        assert sanitize_app_name("App-Name") == "App-Name"
        assert sanitize_app_name("App_Name") == "App_Name"
        assert sanitize_app_name("App.Name") == "App.Name"
        assert sanitize_app_name("App (2)") == "App (2)"

    def test_sanitize_invalid_app_name(self) -> None:
        """Test that invalid app names raise ValueError."""
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App; rm -rf /")
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App`command`")
        with pytest.raises(ValueError, match="Invalid characters"):
            sanitize_app_name("App$VAR")


# =============================================================================
# Verification Function Tests
# =============================================================================


class TestVerifyBasic:
    """Tests for verify_basic function."""

    def test_valid_image(self, temp_image: Path) -> None:
        """Test verification of valid image."""
        result = verify_basic(temp_image)
        assert result.passed is True
        assert result.strategy == VerificationStrategy.BASIC

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test verification of nonexistent file."""
        result = verify_basic(tmp_path / "nonexistent.png")
        assert result.passed is False
        assert "does not exist" in result.message

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test verification of empty file."""
        empty_file = tmp_path / "empty.png"
        empty_file.touch()
        result = verify_basic(empty_file)
        assert result.passed is False
        assert "empty" in result.message.lower()


class TestVerifyDimensions:
    """Tests for verify_dimensions function."""

    def test_matching_dimensions(self, temp_image: Path) -> None:
        """Test verification when dimensions match at 1x scale."""
        result = verify_dimensions(temp_image, 100, 100)
        assert result.passed is True
        assert result.details["detected_scale"] == 1

    def test_matching_dimensions_retina(self, temp_image: Path) -> None:
        """Test verification when dimensions match at 2x (Retina) scale."""
        # 100x100 image should match 50x50 at 2x scale
        result = verify_dimensions(temp_image, 50, 50)
        assert result.passed is True
        assert result.details["detected_scale"] == 2

    def test_mismatched_dimensions(self, temp_image: Path) -> None:
        """Test verification when dimensions don't match at any scale."""
        # 100x100 image doesn't match 800x600 at any scale
        result = verify_dimensions(temp_image, 800, 600)
        assert result.passed is False
        assert "mismatch" in result.message.lower()

    def test_within_tolerance(self, temp_image: Path) -> None:
        """Test verification within tolerance."""
        # 100x100 image, expect 105x105 with 10% tolerance
        result = verify_dimensions(temp_image, 105, 105, tolerance=0.1)
        assert result.passed is True


class TestVerifyContent:
    """Tests for verify_content function."""

    def test_non_blank_image(self, temp_image: Path) -> None:
        """Test verification of non-blank image."""
        result = verify_content(temp_image)
        assert result.passed is True
        assert "hash" in result.details

    def test_blank_image(self, blank_image: Path) -> None:
        """Test verification of blank image."""
        result = verify_content(blank_image)
        assert result.passed is False
        assert "blank" in result.message.lower()


class TestVerifyText:
    """Tests for verify_text function."""

    def test_no_expected_text(self, temp_image: Path) -> None:
        """Test when no text verification required."""
        result = verify_text(temp_image, ())
        assert result.passed is True


# =============================================================================
# CLI Tests
# =============================================================================


class TestCLICommands:
    """Tests for CLI commands via main()."""

    def test_capture_command(
        self, sample_capture_result: CaptureResult, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test capture command with app argument."""
        with patch("verified_screenshot.cli.capture_verified") as mock_capture:
            mock_capture.return_value = sample_capture_result
            result = main(["capture", "TestApp"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Screenshot saved" in captured.out

    def test_find_command(
        self, sample_target: WindowTarget, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test find command with app argument."""
        with patch("verified_screenshot.cli.find_target_window") as mock_find:
            mock_find.return_value = sample_target
            result = main(["find", "TestApp"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Found: TestApp" in captured.out

    def test_short_flags(self, sample_capture_result: CaptureResult) -> None:
        """Test short flags work."""
        with patch("verified_screenshot.cli.capture_verified") as mock_capture:
            mock_capture.return_value = sample_capture_result
            result = main(["capture", "App", "-o", "out.png", "-j", "-r", "3"])
        assert result == 0

    def test_verification_strategies(self, sample_capture_result: CaptureResult) -> None:
        """Test --verify flag with multiple values."""
        with patch("verified_screenshot.cli.capture_verified") as mock_capture:
            mock_capture.return_value = sample_capture_result
            result = main(["capture", "App", "--verify", "basic", "--verify", "content"])
        assert result == 0

    def test_retry_options(self, sample_capture_result: CaptureResult) -> None:
        """Test retry options."""
        with patch("verified_screenshot.cli.capture_verified") as mock_capture:
            mock_capture.return_value = sample_capture_result
            result = main([
                "capture", "App",
                "--retries", "10",
                "--retry-delay", "1000",
                "--retry-strategy", "exponential",
            ])
        assert result == 0


class TestParseVerificationStrategies:
    """Tests for parse_verification_strategies function."""

    def test_basic(self) -> None:
        """Test parsing basic strategy."""
        result = parse_verification_strategies(["basic"])
        assert VerificationStrategy.BASIC in result

    def test_all(self) -> None:
        """Test parsing 'all' strategy."""
        result = parse_verification_strategies(["all"])
        assert VerificationStrategy.ALL in result

    def test_none(self) -> None:
        """Test parsing 'none' strategy."""
        result = parse_verification_strategies(["none"])
        assert len(result) == 0

    def test_multiple(self) -> None:
        """Test parsing multiple strategies."""
        result = parse_verification_strategies(["basic", "content", "dimensions"])
        assert len(result) == 3

    def test_default_when_none(self) -> None:
        """Test default strategies when None passed."""
        result = parse_verification_strategies(None)
        assert VerificationStrategy.BASIC in result
        assert VerificationStrategy.CONTENT in result


class TestParseRetryStrategy:
    """Tests for parse_retry_strategy function."""

    def test_fixed(self) -> None:
        """Test parsing fixed strategy."""
        assert parse_retry_strategy("fixed") == RetryStrategy.FIXED

    def test_exponential(self) -> None:
        """Test parsing exponential strategy."""
        assert parse_retry_strategy("exponential") == RetryStrategy.EXPONENTIAL

    def test_reactivate(self) -> None:
        """Test parsing reactivate strategy."""
        assert parse_retry_strategy("reactivate") == RetryStrategy.REACTIVATE

    def test_unknown_defaults_to_fixed(self) -> None:
        """Test unknown strategy defaults to fixed."""
        assert parse_retry_strategy("unknown") == RetryStrategy.FIXED


class TestBuildConfig:
    """Tests for build_config function."""

    def test_build_basic_config(self) -> None:
        """Test building config from basic args."""
        from verified_screenshot.cli import (
            CaptureOptions,
            OutputOptions,
            RetryOptions,
            VerificationOptions,
            WindowFilterOptions,
        )

        config = build_config(
            WindowFilterOptions(app_name="TestApp"),
            CaptureOptions(),
            OutputOptions(),
            VerificationOptions(),
            RetryOptions(),
        )
        assert config.app_name == "TestApp"
        assert config.max_retries == 5  # default

    def test_build_full_config(self) -> None:
        """Test building config with all options."""
        from verified_screenshot.cli import (
            CaptureOptions,
            OutputOptions,
            RetryOptions,
            VerificationOptions,
            WindowFilterOptions,
        )

        config = build_config(
            WindowFilterOptions(app_name="App", title=".*test.*"),
            CaptureOptions(no_activate=True),
            OutputOptions(output="out.png"),
            VerificationOptions(verify=["all"]),
            RetryOptions(retries=3),
        )
        assert config.app_name == "App"
        assert config.title_pattern == ".*test.*"
        assert config.output_path == "out.png"
        assert config.max_retries == 3
        assert config.activate_first is False


# =============================================================================
# Action Function Tests
# =============================================================================


class TestCalculateRetryDelay:
    """Tests for calculate_retry_delay function."""

    def test_fixed_delay(self) -> None:
        """Test fixed delay strategy."""
        config = CaptureConfig(retry_delay_ms=500, retry_strategy=RetryStrategy.FIXED)
        assert calculate_retry_delay(1, config) == 0.5
        assert calculate_retry_delay(2, config) == 0.5
        assert calculate_retry_delay(3, config) == 0.5

    def test_exponential_delay(self) -> None:
        """Test exponential delay strategy."""
        config = CaptureConfig(retry_delay_ms=500, retry_strategy=RetryStrategy.EXPONENTIAL)
        assert calculate_retry_delay(1, config) == 0.5
        assert calculate_retry_delay(2, config) == 1.0
        assert calculate_retry_delay(3, config) == 2.0


class TestGenerateOutputPath:
    """Tests for generate_output_path function."""

    def test_with_full_path(self, sample_target: WindowTarget, tmp_path: Path) -> None:
        """Test with full path specified."""
        test_path = str(tmp_path / "test.png")
        path = generate_output_path(sample_target, test_path)
        assert path == Path(test_path)

    def test_with_directory(self, sample_target: WindowTarget, tmp_path: Path) -> None:
        """Test with directory specified."""
        test_dir = str(tmp_path / "screenshots")
        path = generate_output_path(sample_target, test_dir)
        assert path.parent == Path(test_dir)
        assert path.suffix == ".png"
        assert "testapp" in path.stem.lower()

    def test_default_path(self, sample_target: WindowTarget) -> None:
        """Test default path generation."""
        path = generate_output_path(sample_target)
        assert path.parent == Path("screenshots")
        assert path.suffix == ".png"


# =============================================================================
# Main Function Tests
# =============================================================================


class TestMain:
    """Tests for main function."""

    def test_no_args_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that no args returns 2 and shows missing command."""
        result = main([])
        assert result == 2  # Typer returns 2 for missing command
        captured = capsys.readouterr()
        assert "Missing command" in captured.err

    def test_find_window_not_found(self) -> None:
        """Test find with non-existent window."""
        with patch("verified_screenshot.cli.find_target_window") as mock_find:
            mock_find.side_effect = WindowNotFoundError("Not found")
            result = main(["find", "NonExistent"])
        assert result == 1

    def test_capture_with_mock(self, sample_capture_result: CaptureResult) -> None:
        """Test capture action with mocked capture_verified."""
        with patch("verified_screenshot.cli.capture_verified") as mock_capture:
            mock_capture.return_value = sample_capture_result
            result = main(["capture", "TestApp"])
        assert result == 0


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for custom exceptions."""

    def test_screenshot_error_inheritance(self) -> None:
        """Test ScreenshotError is base for all exceptions."""
        assert issubclass(CaptureError, ScreenshotError)
        assert issubclass(WindowNotFoundError, ScreenshotError)
        assert issubclass(MaxRetriesError, ScreenshotError)

    def test_exception_messages(self) -> None:
        """Test exception message handling."""
        e = WindowNotFoundError("Window X not found")
        assert "Window X not found" in str(e)

        e = MaxRetriesError("Failed after 5 attempts")
        assert "5 attempts" in str(e)
