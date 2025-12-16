"""Core functionality for window detection and image processing."""

from __future__ import annotations

import functools
import plistlib
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .models import (
    CaptureConfig,
    VerificationResult,
    VerificationStrategy,
    WindowNotFoundError,
    WindowTarget,
)

if TYPE_CHECKING:
    pass

# Spaces plist path
SPACES_PLIST_PATH = Path.home() / "Library/Preferences/com.apple.spaces.plist"


@functools.cache
def _get_quartz():
    """Lazy load Quartz framework (cached)."""
    import Quartz

    return Quartz


@functools.cache
def _get_psutil():
    """Lazy load psutil (cached)."""
    import psutil

    return psutil


@functools.cache
def _get_pil():
    """Lazy load PIL (cached)."""
    from PIL import Image as PILImage

    return PILImage


@functools.cache
def _get_imagehash():
    """Lazy load imagehash (cached)."""
    import imagehash

    return imagehash


def get_spaces_plist() -> dict:
    """Read the spaces plist file."""
    result = subprocess.run(
        ["plutil", "-convert", "xml1", "-o", "-", str(SPACES_PLIST_PATH)],
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return {}

    try:
        return plistlib.loads(result.stdout)
    except plistlib.InvalidFileException:
        return {}


def get_window_space_mapping(plist_data: dict) -> dict[int, int]:
    """Map window IDs to Space indexes (1-based)."""
    window_to_space: dict[int, int] = {}

    config = plist_data.get("SpacesDisplayConfiguration", {})
    mgmt_data = config.get("Management Data", {})
    monitors = mgmt_data.get("Monitors", [])

    for monitor in monitors:
        monitor_spaces = monitor.get("Spaces", [])
        for idx, space in enumerate(monitor_spaces, start=1):
            tile_mgr = space.get("TileLayoutManager", {})
            for tile in tile_mgr.get("TileSpaces", []):
                window_id = tile.get("TileWindowID")
                if window_id:
                    window_to_space[window_id] = idx

    return window_to_space


def get_process_info(pid: int) -> tuple[str | None, list[str]]:
    """Get process executable path and command line."""
    psutil = _get_psutil()

    try:
        proc = psutil.Process(pid)
        return proc.exe(), proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None, []


def _matches_config_filters(
    config: CaptureConfig,
    window: dict,
    process_info: tuple[str | None, list[str]],
) -> bool:
    """Check if window matches all config filters.

    Args:
        config: Capture configuration with filters.
        window: Window info dict from CGWindowListCopyWindowInfo.
        process_info: Tuple of (exe_path, cmdline) from get_process_info.

    Returns:
        True if window matches all filters, False otherwise.
    """
    app_name = window.get("kCGWindowOwnerName", "") or ""
    window_title = window.get("kCGWindowName", "") or ""
    pid = window.get("kCGWindowOwnerPID", 0)
    exe_path, cmdline = process_info

    if config.app_name and config.app_name.lower() not in app_name.lower():
        return False
    if config.title_pattern and not re.search(config.title_pattern, window_title, re.IGNORECASE):
        return False
    if config.pid and pid != config.pid:
        return False
    if config.path_contains and (not exe_path or config.path_contains not in exe_path):
        return False
    if config.path_excludes and exe_path and config.path_excludes in exe_path:
        return False
    return not config.args_contains or config.args_contains in " ".join(cmdline)


def _describe_filters(config: CaptureConfig) -> str:
    """Build human-readable description of active filters.

    Args:
        config: Capture configuration with filters.

    Returns:
        Comma-separated filter descriptions or 'no filters'.
    """
    filters = []
    if config.app_name:
        filters.append(f"app_name={config.app_name}")
    if config.title_pattern:
        filters.append(f"title_pattern={config.title_pattern}")
    if config.pid:
        filters.append(f"pid={config.pid}")
    if config.args_contains:
        filters.append(f"args_contains={config.args_contains}")
    return ", ".join(filters) or "no filters"


def find_target_window(config: CaptureConfig) -> WindowTarget:
    """Find the target window based on configuration.

    Args:
        config: Capture configuration with window filters.

    Returns:
        WindowTarget with window information.

    Raises:
        WindowNotFoundError: If no matching window found.
    """
    Q = _get_quartz()

    all_windows = Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionAll, Q.kCGNullWindowID)
    if not all_windows:
        raise WindowNotFoundError("No windows available")

    # Get space mapping
    plist_data = get_spaces_plist()
    window_space_map = get_window_space_mapping(plist_data)

    process_cache: dict[int, tuple[str | None, list[str]]] = {}

    for window in all_windows:
        # Skip non-main windows (layer != 0) and titleless windows
        if window.get("kCGWindowLayer", 0) != 0:
            continue
        if not window.get("kCGWindowName"):
            continue

        pid = window.get("kCGWindowOwnerPID", 0)

        # Get process info for path/args filtering
        if pid not in process_cache:
            process_cache[pid] = get_process_info(pid)
        process_info = process_cache[pid]

        # Apply all config filters
        if not _matches_config_filters(config, window, process_info):
            continue

        # Found a match
        app_name = window.get("kCGWindowOwnerName", "") or ""
        window_title = window.get("kCGWindowName", "") or ""
        exe_path, cmdline = process_info
        bounds = window.get("kCGWindowBounds", {})
        return WindowTarget(
            window_id=window.get("kCGWindowNumber", 0),
            app_name=app_name,
            window_title=window_title,
            pid=pid,
            bounds_x=bounds.get("X", 0.0),
            bounds_y=bounds.get("Y", 0.0),
            bounds_width=bounds.get("Width", 0.0),
            bounds_height=bounds.get("Height", 0.0),
            space_index=window_space_map.get(window.get("kCGWindowNumber", 0)),
            exe_path=exe_path,
            cmdline=tuple(cmdline),
        )

    # No match found
    raise WindowNotFoundError(f"No window found matching: {_describe_filters(config)}")


def compute_image_hash(image_path: Path) -> str:
    """Compute perceptual hash of an image.

    Args:
        image_path: Path to the image file.

    Returns:
        Hex string of the perceptual hash.
    """
    PILImage = _get_pil()
    imagehash = _get_imagehash()

    img = PILImage.open(image_path)
    phash = imagehash.phash(img)
    return str(phash)


def compute_hash_distance(hash1: str, hash2: str) -> int:
    """Compute hamming distance between two hash strings.

    Args:
        hash1: First hash string.
        hash2: Second hash string.

    Returns:
        Hamming distance (number of differing bits).
    """
    imagehash = _get_imagehash()

    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    return h1 - h2


def get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Get image dimensions.

    Args:
        image_path: Path to the image file.

    Returns:
        Tuple of (width, height).
    """
    PILImage = _get_pil()
    img = PILImage.open(image_path)
    return img.size


def is_image_blank(image_path: Path, threshold: float = 0.99) -> bool:
    """Check if an image is mostly blank (single color).

    Args:
        image_path: Path to the image file.
        threshold: Ratio of pixels that must be same color to be "blank".

    Returns:
        True if image is blank.
    """
    PILImage = _get_pil()
    img = PILImage.open(image_path).convert("RGB")
    pixels = list(img.getdata())

    if not pixels:
        return True

    # Count most common color
    from collections import Counter

    color_counts = Counter(pixels)
    most_common_count = color_counts.most_common(1)[0][1]

    return most_common_count / len(pixels) >= threshold


def verify_basic(image_path: Path) -> VerificationResult:
    """Basic verification: file exists, size > 0, valid image format.

    Args:
        image_path: Path to the image file.

    Returns:
        VerificationResult with pass/fail status.
    """
    PILImage = _get_pil()

    if not image_path.exists():
        return VerificationResult(
            strategy=VerificationStrategy.BASIC,
            passed=False,
            message="File does not exist",
            details={"path": str(image_path)},
        )

    file_size = image_path.stat().st_size
    if file_size == 0:
        return VerificationResult(
            strategy=VerificationStrategy.BASIC,
            passed=False,
            message="File is empty",
            details={"path": str(image_path), "size": 0},
        )

    try:
        img = PILImage.open(image_path)
        img.verify()
    except Exception as e:
        return VerificationResult(
            strategy=VerificationStrategy.BASIC,
            passed=False,
            message=f"Invalid image format: {e}",
            details={"path": str(image_path), "error": str(e)},
        )

    return VerificationResult(
        strategy=VerificationStrategy.BASIC,
        passed=True,
        message="Valid image file",
        details={"path": str(image_path), "size": file_size},
    )


def verify_dimensions(
    image_path: Path,
    expected_width: float,
    expected_height: float,
    tolerance: float = 0.1,
) -> VerificationResult:
    """Verify image dimensions match expected (within tolerance).

    Accounts for Retina display scaling (2x) by checking if dimensions
    match at 1x or 2x scale factor.

    Args:
        image_path: Path to the image file.
        expected_width: Expected width in logical pixels.
        expected_height: Expected height in logical pixels.
        tolerance: Allowed variance as fraction (default 10%).

    Returns:
        VerificationResult with pass/fail status.
    """
    try:
        actual_width, actual_height = get_image_dimensions(image_path)
    except Exception as e:
        return VerificationResult(
            strategy=VerificationStrategy.DIMENSIONS,
            passed=False,
            message=f"Could not read image dimensions: {e}",
            details={"error": str(e)},
        )

    # Check dimensions at 1x and 2x (Retina) scale factors
    scale_factors = [1, 2]  # Common scale factors
    best_match = None
    best_diff = float("inf")

    for scale in scale_factors:
        scaled_expected_w = expected_width * scale
        scaled_expected_h = expected_height * scale

        width_diff = abs(actual_width - scaled_expected_w) / max(scaled_expected_w, 1)
        height_diff = abs(actual_height - scaled_expected_h) / max(scaled_expected_h, 1)
        total_diff = width_diff + height_diff

        if total_diff < best_diff:
            best_diff = total_diff
            best_match = {
                "scale": scale,
                "width_diff": width_diff,
                "height_diff": height_diff,
                "scaled_expected_w": scaled_expected_w,
                "scaled_expected_h": scaled_expected_h,
            }

    passed = best_match["width_diff"] <= tolerance and best_match["height_diff"] <= tolerance

    return VerificationResult(
        strategy=VerificationStrategy.DIMENSIONS,
        passed=passed,
        message="Dimensions match" if passed else "Dimensions mismatch",
        details={
            "expected": {"width": expected_width, "height": expected_height},
            "expected_scaled": {
                "width": best_match["scaled_expected_w"],
                "height": best_match["scaled_expected_h"],
            },
            "actual": {"width": actual_width, "height": actual_height},
            "detected_scale": best_match["scale"],
            "tolerance": tolerance,
            "width_diff_pct": round(best_match["width_diff"] * 100, 2),
            "height_diff_pct": round(best_match["height_diff"] * 100, 2),
        },
    )


def verify_content(
    image_path: Path,
    previous_hash: str | None = None,
    hash_threshold: int = 5,
) -> VerificationResult:
    """Verify image has meaningful content (not blank, differs from previous).

    Args:
        image_path: Path to the image file.
        previous_hash: Hash of previous capture (for comparison).
        hash_threshold: Minimum hamming distance to consider "different".

    Returns:
        VerificationResult with pass/fail status.
    """
    # Check if blank
    if is_image_blank(image_path):
        return VerificationResult(
            strategy=VerificationStrategy.CONTENT,
            passed=False,
            message="Image appears blank",
            details={"blank": True},
        )

    # Compute current hash
    try:
        current_hash = compute_image_hash(image_path)
    except Exception as e:
        return VerificationResult(
            strategy=VerificationStrategy.CONTENT,
            passed=False,
            message=f"Could not compute image hash: {e}",
            details={"error": str(e)},
        )

    # Compare with previous if provided
    if previous_hash:
        distance = compute_hash_distance(current_hash, previous_hash)
        if distance < hash_threshold:
            return VerificationResult(
                strategy=VerificationStrategy.CONTENT,
                passed=False,
                message="Image too similar to previous capture",
                details={
                    "current_hash": current_hash,
                    "previous_hash": previous_hash,
                    "distance": distance,
                    "threshold": hash_threshold,
                },
            )

    return VerificationResult(
        strategy=VerificationStrategy.CONTENT,
        passed=True,
        message="Image has meaningful content",
        details={"hash": current_hash, "blank": False},
    )


def verify_text(image_path: Path, expected_texts: tuple[str, ...]) -> VerificationResult:
    """Verify expected text appears in the image via OCR.

    Args:
        image_path: Path to the image file.
        expected_texts: Texts that should appear in the image.

    Returns:
        VerificationResult with pass/fail status.
    """
    if not expected_texts:
        return VerificationResult(
            strategy=VerificationStrategy.TEXT,
            passed=True,
            message="No text verification required",
            details={},
        )

    try:
        import pytesseract
    except ImportError:
        return VerificationResult(
            strategy=VerificationStrategy.TEXT,
            passed=False,
            message="pytesseract not installed (install with: pip install pytesseract)",
            details={"error": "missing_dependency"},
        )

    PILImage = _get_pil()

    try:
        img = PILImage.open(image_path)
        ocr_text = pytesseract.image_to_string(img)
    except Exception as e:
        return VerificationResult(
            strategy=VerificationStrategy.TEXT,
            passed=False,
            message=f"OCR failed: {e}",
            details={"error": str(e)},
        )

    missing_texts = [t for t in expected_texts if t.lower() not in ocr_text.lower()]

    if missing_texts:
        return VerificationResult(
            strategy=VerificationStrategy.TEXT,
            passed=False,
            message=f"Expected text not found: {missing_texts}",
            details={
                "expected": list(expected_texts),
                "missing": missing_texts,
                "ocr_sample": ocr_text[:200],
            },
        )

    return VerificationResult(
        strategy=VerificationStrategy.TEXT,
        passed=True,
        message="All expected text found",
        details={"expected": list(expected_texts), "found": True},
    )
