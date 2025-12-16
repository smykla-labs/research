"""Shared utilities for claude-code skills."""

from .artifacts import (
    ArtifactError,
    ArtifactResult,
    encode_path_for_filename,
    generate_artifact_filename,
    get_artifacts_dir,
    get_default_artifact_path,
    get_default_output_path,
    get_skill_artifacts_dir,
    sanitize_description,
    save_artifact,
    validate_extension,
)

__all__ = [
    "ArtifactError",
    "ArtifactResult",
    "encode_path_for_filename",
    "generate_artifact_filename",
    "get_artifacts_dir",
    "get_default_artifact_path",
    "get_default_output_path",
    "get_skill_artifacts_dir",
    "sanitize_description",
    "save_artifact",
    "validate_extension",
]
