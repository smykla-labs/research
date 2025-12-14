"""Actions for screenshot capture with verification and retry logic."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .core import (
    _get_quartz,
    compute_image_hash,
    find_target_window,
    get_image_dimensions,
    verify_basic,
    verify_content,
    verify_dimensions,
    verify_text,
)
from .models import (
    CaptureConfig,
    CaptureError,
    CaptureResult,
    MaxRetriesError,
    RetryStrategy,
    VerificationResult,
    VerificationStrategy,
    WindowTarget,
)

if TYPE_CHECKING:
    pass


def sanitize_app_name(app_name: str) -> str:
    """Sanitize application name for AppleScript.

    Args:
        app_name: Raw application name.

    Returns:
        Sanitized name safe for AppleScript.

    Raises:
        ValueError: If app name contains invalid characters.
    """
    if not re.match(r"^[\w\s.\-()]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")
    return app_name.replace('"', '\\"')


def activate_window(target: WindowTarget, wait_time: float = 0.5) -> None:
    """Activate a window (switches to its Space).

    Args:
        target: Window target information.
        wait_time: Seconds to wait after activation.

    Raises:
        CaptureError: If activation fails.
    """
    try:
        sanitized = sanitize_app_name(target.app_name)
    except ValueError as e:
        raise CaptureError(f"Cannot activate: {e}") from e

    result = subprocess.run(
        ["osascript", "-e", f'tell application "{sanitized}" to activate'],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise CaptureError(f"Failed to activate {target.app_name}: {stderr}")

    if wait_time > 0:
        time.sleep(wait_time)


def capture_window_image(
    target: WindowTarget,
    output_path: Path,
    no_shadow: bool = True,
) -> Path:
    """Capture a window image using CGWindowListCreateImage.

    Args:
        target: Window target information.
        output_path: Path to save the screenshot.
        no_shadow: Whether to exclude window shadow.

    Returns:
        Path to the saved screenshot.

    Raises:
        CaptureError: If capture fails.
    """
    Q = _get_quartz()

    # Build image options
    options = Q.kCGWindowImageDefault
    if no_shadow:
        options |= Q.kCGWindowImageBoundsIgnoreFraming

    image = Q.CGWindowListCreateImage(
        Q.CGRectNull,
        Q.kCGWindowListOptionIncludingWindow,
        target.window_id,
        options,
    )

    if image is None:
        raise CaptureError(f"Failed to capture window {target.window_id}")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as PNG
    url = Q.CFURLCreateWithFileSystemPath(
        None, str(output_path.absolute()), Q.kCFURLPOSIXPathStyle, False
    )
    dest = Q.CGImageDestinationCreateWithURL(url, "public.png", 1, None)

    if dest is None:
        raise CaptureError(f"Failed to create destination: {output_path}")

    Q.CGImageDestinationAddImage(dest, image, None)

    if not Q.CGImageDestinationFinalize(dest):
        raise CaptureError(f"Failed to finalize image: {output_path}")

    return output_path


def run_verifications(
    image_path: Path,
    target: WindowTarget,
    config: CaptureConfig,
    previous_hash: str | None = None,
) -> tuple[VerificationResult, ...]:
    """Run all configured verification strategies.

    Args:
        image_path: Path to the screenshot.
        target: Window target information.
        config: Capture configuration.
        previous_hash: Hash of previous capture for comparison.

    Returns:
        Tuple of verification results.
    """
    results: list[VerificationResult] = []
    strategies = config.verification_strategies

    # Expand ALL to individual strategies
    if VerificationStrategy.ALL in strategies:
        strategies = (
            VerificationStrategy.BASIC,
            VerificationStrategy.DIMENSIONS,
            VerificationStrategy.CONTENT,
        )
        if config.expected_text:
            strategies = (*strategies, VerificationStrategy.TEXT)

    for strategy in strategies:
        if strategy == VerificationStrategy.BASIC:
            results.append(verify_basic(image_path))

        elif strategy == VerificationStrategy.DIMENSIONS:
            results.append(
                verify_dimensions(
                    image_path,
                    target.bounds_width,
                    target.bounds_height,
                )
            )

        elif strategy == VerificationStrategy.CONTENT:
            results.append(
                verify_content(
                    image_path,
                    previous_hash,
                    config.hash_threshold,
                )
            )

        elif strategy == VerificationStrategy.TEXT:
            results.append(verify_text(image_path, config.expected_text))

    return tuple(results)


def calculate_retry_delay(
    attempt: int,
    config: CaptureConfig,
) -> float:
    """Calculate delay before next retry.

    Args:
        attempt: Current attempt number (1-based).
        config: Capture configuration.

    Returns:
        Delay in seconds.
    """
    base_delay = config.retry_delay_ms / 1000.0

    if config.retry_strategy == RetryStrategy.EXPONENTIAL:
        return base_delay * (2 ** (attempt - 1))

    return base_delay


def generate_output_path(target: WindowTarget, base_path: str | None = None) -> Path:
    """Generate output path for screenshot.

    Args:
        target: Window target information.
        base_path: Optional base path (can include directory and/or filename).

    Returns:
        Path for the screenshot file.
    """
    if base_path:
        path = Path(base_path)
        if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
            return path
        # Treat as directory
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^\w\-]", "_", target.app_name.lower())
        return path / f"{safe_name}_{timestamp}.png"

    # Default to screenshots directory
    screenshots_dir = Path("screenshots")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^\w\-]", "_", target.app_name.lower())
    return screenshots_dir / f"{safe_name}_{timestamp}.png"


def capture_verified(config: CaptureConfig) -> CaptureResult:
    """Capture a screenshot with verification and retry logic.

    This is the main entry point for the skill. It:
    1. Finds the target window based on filters
    2. Optionally activates the window
    3. Captures the screenshot
    4. Runs verification checks
    5. Retries on failure up to max_retries times

    Args:
        config: Capture configuration.

    Returns:
        CaptureResult with screenshot path and verification details.

    Raises:
        WindowNotFoundError: If target window not found.
        MaxRetriesError: If verification fails after all retries.
    """
    # Find target window
    target = find_target_window(config)

    # Generate output path
    output_path = generate_output_path(target, config.output_path)

    previous_hash: str | None = None
    last_result: CaptureResult | None = None

    for attempt in range(1, config.max_retries + 1):
        # Activate window if configured (and always re-activate on retry with REACTIVATE strategy)
        should_activate = config.activate_first or (
            attempt > 1 and config.retry_strategy == RetryStrategy.REACTIVATE
        )

        if should_activate:
            # Increase settle time on retries
            settle_time = config.settle_ms / 1000.0
            if attempt > 1:
                settle_time *= attempt  # Progressive increase
            activate_window(target, settle_time)
        elif attempt > 1:
            # Wait before retry even without activation
            delay = calculate_retry_delay(attempt, config)
            time.sleep(delay)

        # Use unique filename for each attempt to avoid caching issues
        attempt_path = output_path.with_stem(f"{output_path.stem}_attempt{attempt}")

        # Capture screenshot
        try:
            capture_window_image(target, attempt_path, config.no_shadow)
        except CaptureError as e:
            if attempt == config.max_retries:
                raise MaxRetriesError(f"Capture failed after {attempt} attempts: {e}") from e
            continue

        # Get actual dimensions
        try:
            actual_width, actual_height = get_image_dimensions(attempt_path)
        except Exception:
            actual_width, actual_height = 0, 0

        # Run verifications
        verifications = run_verifications(attempt_path, target, config, previous_hash)
        all_passed = all(v.passed for v in verifications)

        # Compute hash for this capture
        try:
            current_hash = compute_image_hash(attempt_path)
        except Exception:
            current_hash = None

        result = CaptureResult(
            path=attempt_path,
            attempt=attempt,
            window_id=target.window_id,
            app_name=target.app_name,
            window_title=target.window_title,
            expected_width=target.bounds_width,
            expected_height=target.bounds_height,
            actual_width=actual_width,
            actual_height=actual_height,
            verifications=verifications,
            verified=all_passed,
            image_hash=current_hash,
        )

        last_result = result

        if all_passed:
            # Rename to final path on success
            if attempt_path != output_path:
                attempt_path.rename(output_path)
                result = CaptureResult(
                    path=output_path,
                    attempt=attempt,
                    window_id=target.window_id,
                    app_name=target.app_name,
                    window_title=target.window_title,
                    expected_width=target.bounds_width,
                    expected_height=target.bounds_height,
                    actual_width=actual_width,
                    actual_height=actual_height,
                    verifications=verifications,
                    verified=True,
                    image_hash=current_hash,
                )
            return result

        # Update previous hash for content comparison
        if current_hash:
            previous_hash = current_hash

        # Clean up failed attempt
        if attempt_path.exists() and attempt_path != output_path:
            attempt_path.unlink()

    # All retries exhausted
    failed_strategies = [v.strategy.value for v in last_result.verifications if not v.passed]
    raise MaxRetriesError(
        f"Verification failed after {config.max_retries} attempts. "
        f"Failed checks: {', '.join(failed_strategies)}"
    )


def capture_simple(
    app_name: str | None = None,
    title_pattern: str | None = None,
    output_path: str | None = None,
    max_retries: int = 5,
) -> CaptureResult:
    """Simple capture with sensible defaults.

    Convenience wrapper around capture_verified for common use cases.

    Args:
        app_name: Application name to find.
        title_pattern: Regex pattern for window title.
        output_path: Output path for screenshot.
        max_retries: Maximum retry attempts.

    Returns:
        CaptureResult with screenshot details.
    """
    config = CaptureConfig(
        app_name=app_name,
        title_pattern=title_pattern,
        output_path=output_path,
        max_retries=max_retries,
        verification_strategies=(VerificationStrategy.BASIC, VerificationStrategy.CONTENT),
    )
    return capture_verified(config)
