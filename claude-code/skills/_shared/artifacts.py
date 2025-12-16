"""Artifacts directory utilities for skill outputs.

Provides a consistent output location for all skill artifacts
(screenshots, recordings, etc.) in the claude-code/artifacts directory.

Output Structure:
    claude-code/artifacts/<skill-name>/<YYMMDDHHMMSS>-<description>.<ext>

When --output is specified:
    1. Save to the specified path
    2. Also save a tracking copy to the default location with encoded path
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Maximum length for sanitized descriptions in filenames
MAX_DESCRIPTION_LENGTH = 50


class ArtifactError(Exception):
    """Error related to artifact creation or validation."""


@dataclass
class ArtifactResult:
    """Result of saving an artifact."""

    primary_path: Path
    tracking_path: Path
    skill_name: str
    description: str
    timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "primary_path": str(self.primary_path),
            "tracking_path": str(self.tracking_path),
            "skill_name": self.skill_name,
            "description": self.description,
            "timestamp": self.timestamp,
        }


def get_artifacts_dir() -> Path:
    """Get the root artifacts directory, creating it if necessary.

    Returns:
        Path to the artifacts directory.
    """
    skills_dir = Path(__file__).resolve().parent.parent
    artifacts_dir = skills_dir.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def get_skill_artifacts_dir(skill_name: str) -> Path:
    """Get the skill-specific artifacts directory.

    Args:
        skill_name: Name of the skill (e.g., "browser-controller").

    Returns:
        Path like: claude-code/artifacts/browser-controller/
    """
    skill_dir = get_artifacts_dir() / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    return skill_dir


def validate_extension(path: Path | str, allowed_extensions: list[str] | None = None) -> str:
    """Validate that a path has an extension.

    Args:
        path: Path to validate.
        allowed_extensions: Optional list of allowed extensions (without dots).

    Returns:
        The extension (without dot).

    Raises:
        ArtifactError: If path has no extension or extension not allowed.
    """
    p = Path(path)
    ext = p.suffix.lstrip(".")

    if not ext:
        raise ArtifactError(
            f"Artifact path must have an extension: {path}"
        )

    if allowed_extensions and ext.lower() not in [e.lower() for e in allowed_extensions]:
        raise ArtifactError(
            f"Extension '.{ext}' not allowed. Allowed: {', '.join(allowed_extensions)}"
        )

    return ext


def sanitize_description(description: str) -> str:
    """Sanitize a description for use in filenames.

    Args:
        description: Raw description text.

    Returns:
        Sanitized string safe for filenames.
    """
    # Replace spaces and special chars with underscores (exclude dots for safety)
    sanitized = re.sub(r"[^\w\-]", "_", description)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Limit length
    if len(sanitized) > MAX_DESCRIPTION_LENGTH:
        return sanitized[:MAX_DESCRIPTION_LENGTH]
    return sanitized


def encode_path_for_filename(path: Path | str) -> str:
    """Encode a path for use as part of a filename.

    Replaces path separators with underscores and strips the extension
    (since extension is added separately in the final filename).

    Args:
        path: Path to encode.

    Returns:
        Path string with / replaced by _ and extension stripped.
    """
    p = Path(path)
    # Get path without extension
    path_without_ext = str(p.with_suffix(""))
    # Remove leading / or drive letter
    if path_without_ext.startswith("/"):
        path_without_ext = path_without_ext[1:]
    # Replace separators
    return path_without_ext.replace("/", "_").replace("\\", "_")


def generate_artifact_filename(
    description: str,
    ext: str,
    timestamp: str | None = None,
) -> str:
    """Generate a timestamped artifact filename.

    Args:
        description: Description for the artifact.
        ext: File extension without dot.
        timestamp: Optional timestamp (defaults to now).

    Returns:
        Filename like: 241216143052-screenshot_goland.png
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")

    sanitized_desc = sanitize_description(description)
    return f"{timestamp}-{sanitized_desc}.{ext}"


def save_artifact(
    source_path: Path | str,
    skill_name: str,
    description: str,
    output_path: Path | str | None = None,
    allowed_extensions: list[str] | None = None,
) -> ArtifactResult:
    """Save an artifact with proper tracking.

    If output_path is None, saves to default location.
    If output_path is specified, saves to that location AND creates
    a tracking copy in the default location.

    Args:
        source_path: Path to the source file (temporary or staged).
        skill_name: Name of the skill creating the artifact.
        description: Human-readable description of the artifact.
        output_path: Optional custom output path.
        allowed_extensions: Optional list of allowed extensions.

    Returns:
        ArtifactResult with paths to saved files.

    Raises:
        ArtifactError: If validation fails or save fails.
    """
    source = Path(source_path)
    if not source.exists():
        raise ArtifactError(f"Source file does not exist: {source}")

    # Determine extension
    if output_path:
        ext = validate_extension(output_path, allowed_extensions)
    else:
        ext = validate_extension(source, allowed_extensions)

    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    skill_dir = get_skill_artifacts_dir(skill_name)

    if output_path is None:
        # No custom output - save only to default location
        filename = generate_artifact_filename(description, ext, timestamp)
        primary_path = skill_dir / filename
        tracking_path = primary_path

        shutil.copy2(source, primary_path)

    else:
        # Custom output specified - save to both locations
        # Resolve relative paths to absolute (relative to caller's cwd)
        custom_path = Path(output_path).resolve()

        # Validate custom path has extension
        validate_extension(custom_path, allowed_extensions)

        # Create parent directories for custom path
        custom_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to custom location
        shutil.copy2(source, custom_path)
        primary_path = custom_path

        # Generate tracking filename with encoded custom path
        encoded_custom = encode_path_for_filename(custom_path)
        tracking_filename = generate_artifact_filename(
            f"{description}-at-{encoded_custom}",
            ext,
            timestamp,
        )
        tracking_path = skill_dir / tracking_filename

        # Save tracking copy
        shutil.copy2(source, tracking_path)

    return ArtifactResult(
        primary_path=primary_path,
        tracking_path=tracking_path,
        skill_name=skill_name,
        description=description,
        timestamp=timestamp,
    )


def get_default_artifact_path(
    skill_name: str,
    description: str,
    ext: str,
) -> Path:
    """Get the default path for a new artifact (without saving).

    Useful for skills that write directly to the output path.

    Args:
        skill_name: Name of the skill.
        description: Description for the artifact.
        ext: File extension without dot.

    Returns:
        Path where artifact should be saved.
    """
    skill_dir = get_skill_artifacts_dir(skill_name)
    filename = generate_artifact_filename(description, ext)
    return skill_dir / filename


# Legacy compatibility
def get_default_output_path(prefix: str, ext: str) -> Path:
    """Generate a timestamped output path (legacy compatibility).

    DEPRECATED: Use get_default_artifact_path() instead.

    Args:
        prefix: Prefix for the filename (e.g., "screenshot", "recording").
        ext: File extension without the dot (e.g., "png", "gif").

    Returns:
        Path in the root artifacts directory.
    """
    artifacts = get_artifacts_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return artifacts / f"{prefix}_{timestamp}.{ext}"
