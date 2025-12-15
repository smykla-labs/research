"""Property-based tests for screen_recorder using Hypothesis."""

from __future__ import annotations

from pathlib import Path

from hypothesis import assume, given, settings
from hypothesis import strategies as st
from screen_recorder.actions import calculate_retry_delay
from screen_recorder.models import (
    RecordingConfig,
    RetryStrategy,
    VideoInfo,
    WindowBounds,
)

# =============================================================================
# WindowBounds Property Tests
# =============================================================================


class TestWindowBoundsProperties:
    """Property-based tests for WindowBounds."""

    @given(
        x=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
        width=st.floats(min_value=1, max_value=10000, allow_nan=False, allow_infinity=False),
        height=st.floats(min_value=1, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_as_region_always_valid(self, x: float, y: float, width: float, height: float) -> None:
        """Test that as_region is always valid for any positive dimensions."""
        bounds = WindowBounds(x=x, y=y, width=width, height=height)
        region = bounds.as_region

        # Must be 4 comma-separated integers
        parts = region.split(",")
        assert len(parts) == 4, f"Expected 4 parts, got {len(parts)}: {region}"

        # All parts must be valid integers
        for part in parts:
            int(part)  # Raises if not valid

    @given(
        x=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
        y=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
        width=st.floats(min_value=1, max_value=10000, allow_nan=False, allow_infinity=False),
        height=st.floats(min_value=1, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_as_region_matches_bounds(
        self, x: float, y: float, width: float, height: float
    ) -> None:
        """Test that as_region values match input bounds."""
        bounds = WindowBounds(x=x, y=y, width=width, height=height)
        region = bounds.as_region

        parts = [int(p) for p in region.split(",")]
        assert parts[0] == int(x), f"X mismatch: {parts[0]} != {int(x)}"
        assert parts[1] == int(y), f"Y mismatch: {parts[1]} != {int(y)}"
        assert parts[2] == int(width), f"Width mismatch: {parts[2]} != {int(width)}"
        assert parts[3] == int(height), f"Height mismatch: {parts[3]} != {int(height)}"


# =============================================================================
# VideoInfo Property Tests
# =============================================================================


class TestVideoInfoProperties:
    """Property-based tests for VideoInfo."""

    @given(
        file_size_bytes=st.integers(min_value=0, max_value=10_000_000_000)  # Up to 10GB
    )
    @settings(max_examples=100)
    def test_file_size_mb_calculation(self, file_size_bytes: int) -> None:
        """Test that file_size_mb is always correctly calculated."""
        video = VideoInfo(
            path=Path("/tmp/test.mov"),
            duration_seconds=5.0,
            frame_count=150,
            fps=30.0,
            width=1920,
            height=1080,
            file_size_bytes=file_size_bytes,
            format_name="mov",
        )

        # file_size_mb returns exact value (no rounding)
        expected_mb = file_size_bytes / (1024 * 1024)
        assert video.file_size_mb == expected_mb

    @given(file_size_bytes=st.integers(min_value=0, max_value=10_000_000_000))
    @settings(max_examples=100)
    def test_file_size_mb_non_negative(self, file_size_bytes: int) -> None:
        """Test that file_size_mb is never negative."""
        video = VideoInfo(
            path=Path("/tmp/test.mov"),
            duration_seconds=5.0,
            frame_count=150,
            fps=30.0,
            width=1920,
            height=1080,
            file_size_bytes=file_size_bytes,
            format_name="mov",
        )

        assert video.file_size_mb >= 0


# =============================================================================
# Retry Delay Property Tests
# =============================================================================


class TestRetryDelayProperties:
    """Property-based tests for retry delay calculation."""

    @given(
        attempt=st.integers(min_value=1, max_value=10),
        delay_ms=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=100)
    def test_exponential_delay_always_grows(self, attempt: int, delay_ms: int) -> None:
        """Test that exponential delay always grows or stays same with each attempt."""
        assume(attempt >= 2)  # Need at least 2 attempts to compare

        config = RecordingConfig(
            app_name="Test",
            retry_delay_ms=delay_ms,
            retry_strategy=RetryStrategy.EXPONENTIAL,
        )

        delay_prev = calculate_retry_delay(attempt - 1, config)
        delay_curr = calculate_retry_delay(attempt, config)

        assert delay_curr >= delay_prev, (
            f"Exponential delay should grow: attempt {attempt-1} ({delay_prev}s) "
            f"-> attempt {attempt} ({delay_curr}s)"
        )

    @given(
        attempt=st.integers(min_value=1, max_value=10),
        delay_ms=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=100)
    def test_fixed_delay_constant(self, attempt: int, delay_ms: int) -> None:
        """Test that fixed delay is always constant regardless of attempt."""
        config = RecordingConfig(
            app_name="Test",
            retry_delay_ms=delay_ms,
            retry_strategy=RetryStrategy.FIXED,
        )

        delay1 = calculate_retry_delay(1, config)
        delay_n = calculate_retry_delay(attempt, config)

        assert delay1 == delay_n, f"Fixed delay should be constant: {delay1} != {delay_n}"

    @given(
        attempt=st.integers(min_value=1, max_value=10),
        delay_ms=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=100)
    def test_delay_non_negative(self, attempt: int, delay_ms: int) -> None:
        """Test that delay is always non-negative."""
        for strategy in [RetryStrategy.FIXED, RetryStrategy.EXPONENTIAL]:
            config = RecordingConfig(
                app_name="Test",
                retry_delay_ms=delay_ms,
                retry_strategy=strategy,
            )
            delay = calculate_retry_delay(attempt, config)
            assert delay >= 0, f"Delay should be non-negative for {strategy}: {delay}"

    @given(
        attempt=st.integers(min_value=1, max_value=10),
        delay_ms=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=100)
    def test_exponential_bounded_reasonable(self, attempt: int, delay_ms: int) -> None:
        """Test that exponential delay doesn't exceed reasonable bounds."""
        config = RecordingConfig(
            app_name="Test",
            retry_delay_ms=delay_ms,
            retry_strategy=RetryStrategy.EXPONENTIAL,
        )
        delay = calculate_retry_delay(attempt, config)
        base_delay = delay_ms / 1000.0

        # With base_delay <= 10 and attempt <= 10, max delay is 10 * 2^9 = 5120s
        max_reasonable = base_delay * (2 ** (attempt - 1))
        assert delay <= max_reasonable, f"Delay {delay}s exceeds reasonable bound {max_reasonable}s"
