# Claude Code Skills Development Specification

Version 3.0.0 | Derived from: `space-finder`, `window-controller`, `browser-controller`

This document defines requirements, guidelines, and best practices for developing Claude Code skills. Use it to validate new skills for consistency, quality, security, and maintainability.

---

## Table of Contents

1. [Directory Structure](#directory-structure)
2. [Skill Types](#skill-types)
3. [Required Files](#required-files)
4. [Code Architecture](#code-architecture)
5. [Naming Conventions](#naming-conventions)
6. [Data Models](#data-models)
7. [Exception Handling](#exception-handling)
8. [Security Requirements](#security-requirements)
9. [CLI Design](#cli-design)
10. [Shared Modules](#shared-modules)
11. [CLI Wrapper](#cli-wrapper)
12. [JSON Output](#json-output)
13. [Artifact Output](#artifact-output)
14. [Testing Requirements](#testing-requirements)
15. [Documentation](#documentation)
16. [Validation & Verification](#validation--verification)
17. [Quality Checklist](#quality-checklist)

---

## Directory Structure

Skills are organized as a uv workspace with centralized tests and shared modules:

```
# Root workspace
pyproject.toml                  # Workspace config, shared dependencies
uv.lock                         # Single lockfile for all skills
tests/
└── skills/                     # Centralized test location
    ├── test_space_finder.py
    ├── test_verified_screenshot.py
    └── test_window_controller.py

# Skills directory structure
claude-code/
├── artifacts/                  # Default output for skill artifacts
│   ├── browser-controller/     # Per-skill artifact directories
│   ├── window-controller/
│   └── ...
└── skills/
    ├── _bin/                   # CLI wrapper (excluded from workspace)
    │   └── claude-code-skills  # Unified CLI entry point
    ├── _shared/                # Shared modules (excluded from workspace)
    │   ├── __init__.py
    │   └── artifacts.py        # Artifact management utilities
    ├── {skill-name}/           # Python-based skill
    │   ├── SKILL.md            # Required: Skill documentation
    │   ├── pyproject.toml      # Required: Project configuration
    │   └── {package_name}/     # Required: Python package
    │       ├── __init__.py     # Public API exports
    │       ├── __main__.py     # Entry point (python -m {package_name})
    │       └── cli.py          # CLI interface (Typer app)
    └── {docs-skill}/           # Documentation-only skill
        ├── SKILL.md            # Required: Main documentation
        ├── pyproject.toml      # Required: package = false
        └── *.md                # Additional documentation files
```

### Naming Rules

- **Skill directory**: `kebab-case` (e.g., `space-finder`)
- **Python package**: Unique `snake_case` name (e.g., `space_finder`, `verified_screenshot`)
- **Test file**: `test_{package_name}.py` in `tests/skills/`

### Workspace Configuration

Root `pyproject.toml` defines the workspace:

```toml
[tool.uv.workspace]
members = ["claude-code/skills/*"]
exclude = ["claude-code/skills/_bin", "claude-code/skills/_shared"]
```

Skills are installed as editable packages via `uv pip install -e .claude/skills/{skill-name}`.

---

## Skill Types

### Python-Based Skills

Executable skills with CLI interface. Requires:

- `pyproject.toml` with `package = true`
- Python package with `__init__.py`, `__main__.py`, `cli.py`
- Installable entry point in `[project.scripts]`

### Documentation-Only Skills

Knowledge/reference skills without executable code. Requires:

- `pyproject.toml` with `package = false`
- `SKILL.md` with proper frontmatter
- Additional markdown files as needed

Example `pyproject.toml` for documentation-only skill:

```toml
[project]
name = "web-automation-investigation"
version = "0.1.0"
description = "Complete guide for investigating and implementing web browser automation"
requires-python = ">=3.11"
dependencies = []

[tool.uv]
package = false
```

---

## Required Files

### `pyproject.toml` (Python-Based Skill)

```toml
[project]
name = "skill-name"
version = "1.0.0"
description = "Brief description of what the skill does"
requires-python = ">=3.11"
dependencies = []  # Managed by workspace root

[project.scripts]
skill-name = "package_name.cli:main"

[tool.uv]
package = true
```

**Requirements:**

- Python version: `>=3.11`
- Dependencies: Empty list (managed by workspace root `pyproject.toml`)
- Package flag: `package = true` (installable package)
- Entry point: Define in `[project.scripts]` for CLI access

### `pyproject.toml` (Workspace Root)

All shared dependencies are defined in the root:

```toml
[project]
name = "workspace-name"
dependencies = [
    # Shared dependencies for all skills
    "pyobjc-framework-Quartz>=10.0",
    "psutil>=5.9",
    "typer>=0.15.0",  # CLI framework
]

[tool.uv]
package = false

[tool.uv.workspace]
members = ["claude-code/skills/*"]
exclude = ["claude-code/skills/_bin", "claude-code/skills/_shared"]
```

### `SKILL.md`

Must include YAML frontmatter:

```yaml
---
name: skill-name
description: One-line description for Claude Code skill discovery
---
```

See [Documentation](#documentation) section for full requirements.

---

## Code Architecture

### Minimum Required Files

Every Python-based skill MUST have these files:

| File           | Purpose                                      |
|----------------|----------------------------------------------|
| `__init__.py`  | Public API exports with `__all__`            |
| `__main__.py`  | Entry point for `python -m {package_name}`   |
| `cli.py`       | Typer CLI application                        |

### Recommended Additional Files

| File           | Purpose                                   | When to Use                    |
|----------------|-------------------------------------------|--------------------------------|
| `models.py`    | Data classes, exceptions, constants       | Skills with domain models      |
| `core.py`      | Core logic, parsing, filtering            | Skills with business logic     |
| `actions.py`   | Actions with external effects             | Skills with side effects       |

### Extended Structures

Skills may include additional modules as needed:

```
{package_name}/
├── __init__.py
├── __main__.py
├── cli.py
├── models.py           # Optional: Data models
├── core.py             # Optional: Core logic
├── actions.py          # Optional: Side-effect operations
├── backends/           # Optional: Protocol implementations
│   ├── __init__.py
│   ├── cdp.py          # Chrome DevTools Protocol
│   └── marionette.py   # Firefox Marionette
├── utils/              # Optional: Utility functions
│   └── __init__.py
└── screencapturekit.py # Optional: Platform-specific modules
```

### File Header

Every Python file MUST start with:

```python
"""Brief description of the module."""

from __future__ import annotations
```

### Import Organization

```python
"""Module docstring."""

from __future__ import annotations

# Standard library
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

# Third-party
import typer

# Local imports
from .models import SomeClass, SomeError

# TYPE_CHECKING block for type-only imports
if TYPE_CHECKING:
    from collections.abc import Sequence
```

### `__init__.py` Pattern

Export all public API with explicit `__all__`:

```python
"""Skill name - Brief description."""

from .actions import action_func, sanitize_func
from .cli import main
from .core import core_func
from .models import (
    CONSTANT,
    DataClass,
    BaseError,
    SpecificError,
)

__all__ = [
    # Constants (alphabetical)
    "CONSTANT",
    # Exceptions (alphabetical)
    "BaseError",
    "SpecificError",
    # Data classes (alphabetical)
    "DataClass",
    # Functions (alphabetical)
    "action_func",
    "core_func",
    "main",
    "sanitize_func",
]
```

### `__main__.py` Pattern

```python
"""Package entry point for running as module: python -m {package_name}."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
```

---

## Naming Conventions

### Files

- Module names: `snake_case.py`
- Test files: `test_{module_name}.py`

### Classes

- Data classes: `PascalCase` nouns (e.g., `WindowInfo`, `SpaceInfo`)
- Exceptions: `PascalCase` ending in `Error` (e.g., `ActivationError`)
- Filter classes: `{Domain}Filter` (e.g., `WindowFilter`)

### Functions

- Public functions: `snake_case` verbs (e.g., `find_window`, `get_spaces`)
- Private functions: `_snake_case` (e.g., `_matches_filter`)
- Handler functions: `_handle_{action}` (e.g., `_handle_list`)
- Sanitization: `sanitize_{thing}` (e.g., `sanitize_app_name`)

### Constants

- All caps with underscores: `SPACES_PLIST_PATH`
- Type mappings: `{DOMAIN}_TYPE_{NAME}` (e.g., `SPACE_TYPE_FULLSCREEN`)
- Skill name: `SKILL_NAME = "skill-name"` (for artifact tracking)

### CLI Arguments (Typer)

| Long Flag      | Short Flag | Pattern         |
|----------------|------------|-----------------|
| `--list`       | `-l`       | List all items  |
| `--find`       | `-f`       | Find/search     |
| `--current`    | `-c`       | Current state   |
| `--go`         | `-g`       | Navigate/switch |
| `--activate`   | `-a`       | Activate        |
| `--screenshot` | `-s`       | Screenshot      |
| `--json`       | `-j`       | JSON output     |
| `--output`     | `-o`       | Output path     |
| `--title`      | `-t`       | Title filter    |

---

## Data Models

### Frozen Dataclasses

All data models MUST use frozen dataclasses for immutability:

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ItemInfo:
    """Information about an item."""

    # Required fields first
    name: str
    item_id: int

    # Optional fields with defaults
    extra_info: str | None = None
    items: tuple[str, ...] = field(default_factory=tuple)  # Use tuple, not list
```

**Requirements:**

- `frozen=True` for all data classes
- Use `tuple` for collections (hashable)
- Include docstring
- Required fields before optional
- Type hints for all fields

### `to_dict()` Method

Every data class MUST implement `to_dict()` for JSON serialization:

```python
def to_dict(self) -> dict:
    """Convert to dictionary for JSON serialization."""
    return {
        "name": self.name,
        "item_id": self.item_id,
        "extra_info": self.extra_info,
        # Include computed properties
        "computed_field": self.computed_property,
    }
```

### Properties for Display

Add properties for display formatting:

```python
@property
def display_name(self) -> str:
    """Name for display, with fallback."""
    return self.name or "-"

@property
def type_name(self) -> str:
    """Human-readable type name."""
    return TYPE_NAMES.get(self.type_code, str(self.type_code))
```

---

## Exception Handling

### Exception Hierarchy

Every skill MUST define a base exception and specific exceptions:

```python
class SkillError(Exception):
    """Base exception for skill-related errors."""


class PlistReadError(SkillError):
    """Failed to read plist file."""


class ActivationError(SkillError):
    """Failed to activate application."""


class NotFoundError(SkillError):
    """Resource not found."""
```

**Naming:**

- Base: `{Skill}Error` or `{Domain}Error` (e.g., `WindowError`, `SpacesError`)
- Specific: Short, descriptive (e.g., `ActivationError` not `AppActivationError`)
- End with `Error`

### Error Handling Pattern

```python
def function_with_error() -> Result:
    """Description.

    Raises:
        SpecificError: When specific condition occurs.
    """
    try:
        result = external_call()
    except ExternalError as e:
        raise SpecificError(f"Context: {e}") from e

    if not result:
        raise SpecificError("Error message with context")

    return result
```

### CLI Error Handling (Typer)

```python
@app.command("action")
def action_cmd(json_output: JsonOpt = False) -> None:
    """Perform action."""
    try:
        result = perform_action()
        if json_output:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Success: {result.name}")
    except SkillError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
```

---

## Security Requirements

### Input Sanitization

**CRITICAL**: Any input used in shell commands or AppleScript MUST be sanitized.

```python
import re

def sanitize_app_name(app_name: str) -> str:
    """Sanitize application name for safe use in AppleScript.

    Args:
        app_name: Raw application name.

    Returns:
        Sanitized application name safe for AppleScript.

    Raises:
        ValueError: If the app name contains invalid characters.
    """
    # Allow only safe characters: alphanumeric, spaces, hyphens, underscores, periods, parentheses
    if not re.match(r"^[\w\s.\-()]+$", app_name):
        raise ValueError(f"Invalid characters in app name: {app_name}")

    # Defense in depth: escape quotes even though regex should prevent them
    return app_name.replace('"', '\\"')
```

### Safe Subprocess Calls

```python
import subprocess

def safe_subprocess(args: list[str], *, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run subprocess safely.

    NEVER use shell=True. Always pass args as a list.
    """
    return subprocess.run(
        args,
        capture_output=capture_output,
        check=False,  # Handle errors explicitly
    )
```

### Security Checklist

- [ ] All user input is validated/sanitized before use
- [ ] No `shell=True` in subprocess calls
- [ ] No string interpolation in shell commands
- [ ] AppleScript strings are escaped
- [ ] File paths are validated
- [ ] No eval/exec of user input

---

## CLI Design

Skills use [Typer](https://typer.tiangolo.com/) for CLI interfaces with subcommand-based structure.

### App Structure

```python
"""Command-line interface for skill name."""

from __future__ import annotations

import json
import sys
from typing import Annotated

import typer

from .core import get_items, find_items
from .models import SkillError

# Skill name for artifact tracking
SKILL_NAME = "skill-name"

app = typer.Typer(
    name="skill-name",
    help="Brief skill description.",
)
```

### Type Aliases for Options

Define reusable type aliases for common options:

```python
# Common type aliases
JsonOpt = Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")]
AppArg = Annotated[str, typer.Argument(help="Application name")]
TitleOpt = Annotated[str | None, typer.Option("--title", "-t", help="Regex for title")]
OutputOpt = Annotated[
    str | None,
    typer.Option("--output", "-o", help="Output path (must have .png extension)"),
]
```

### Command Pattern

```python
@app.command("list")
def list_cmd(
    json_output: JsonOpt = False,
) -> None:
    """List all items."""
    try:
        items = get_items()

        if json_output:
            print(json.dumps([item.to_dict() for item in items], indent=2))
        else:
            for item in items:
                print(f"{item.name}: {item.description}")

    except SkillError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("find")
def find_cmd(
    query: Annotated[str, typer.Argument(help="Search query")],
    title: TitleOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Find items matching query."""
    try:
        items = find_items(query, title_pattern=title)

        if not items:
            msg = {"error": f"No items found for: {query}"}
            print(json.dumps(msg) if json_output else f"No items found for: {query}")
            raise typer.Exit(1)

        if json_output:
            print(json.dumps([item.to_dict() for item in items], indent=2))
        else:
            for item in items:
                print(f"Found: {item.name}")
                print(f"  Description: {item.description}\n")

    except SkillError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e
```

### Main Function Pattern

```python
def main(argv: list[str] | None = None) -> int:
    """Main entry point for skill-name CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["skill-name", *list(argv)]
    try:
        app(prog_name="skill-name")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
```

### Handler Functions (Optional)

For complex commands, extract handler functions:

```python
def _handle_list(items: Sequence[Item], *, json_output: bool = False) -> int:
    """Handle list command."""
    if json_output:
        print(json.dumps([item.to_dict() for item in items], indent=2))
    else:
        for item in items:
            print(f"{item.name}: {item.description}")
    return 0


@app.command("list")
def list_cmd(json_output: JsonOpt = False) -> None:
    """List all items."""
    try:
        items = get_items()
        result = _handle_list(items, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)
    except SkillError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
```

---

## Shared Modules

### `_shared/artifacts.py`

Provides consistent artifact output management for all skills.

**Location:** `claude-code/skills/_shared/artifacts.py`

**Key Functions:**

```python
from _shared.artifacts import (
    ArtifactError,
    ArtifactResult,
    save_artifact,
    validate_extension,
    get_default_artifact_path,
)
```

**Output Structure:**

```
claude-code/artifacts/<skill-name>/<YYMMDDHHMMSS>-<description>.<ext>
```

**Usage Pattern:**

```python
import tempfile
from pathlib import Path

from _shared.artifacts import save_artifact, validate_extension, ArtifactError

SKILL_NAME = "window-controller"

@app.command("screenshot")
def screenshot_cmd(
    app_name: str,
    output: OutputOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Take screenshot of window."""
    try:
        # Validate output extension if provided
        if output is not None:
            validate_extension(output, ["png"])

        # Create temp file for capture
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Capture to temp file
            capture_screenshot(app_name, tmp_path)

            # Save with tracking
            result = save_artifact(
                source_path=tmp_path,
                skill_name=SKILL_NAME,
                description=f"screenshot_{app_name}",
                output_path=output,
                allowed_extensions=["png"],
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        if json_output:
            print(json.dumps({
                "screenshot": str(result.primary_path),
                "tracking_copy": str(result.tracking_path),
            }, indent=2))
        else:
            print(f"Screenshot saved: {result.primary_path}")

    except ArtifactError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e
```

**Fallback Pattern:**

For skills that may run without `_shared` available:

```python
try:
    from _shared.artifacts import save_artifact, validate_extension, ArtifactError
except ImportError:
    # Fallback implementation when _shared not available
    class ArtifactError(Exception):
        pass

    def save_artifact(source_path, skill_name, description, output_path=None, allowed_extensions=None):
        # Minimal fallback implementation
        ...

    def validate_extension(path, allowed=None):
        # Minimal fallback implementation
        ...
```

---

## CLI Wrapper

### `claude-code-skills`

Unified CLI wrapper that auto-discovers and runs Python-based skills.

**Location:** `claude-code/skills/_bin/claude-code-skills`

**Setup:**

Add to PATH for global access:

```bash
export PATH="$PATH:/path/to/research/claude-code/skills/_bin"
```

**Usage:**

```bash
# List available skills
claude-code-skills --list

# Get help for a skill
claude-code-skills <skill-name> --help

# Run a skill command
claude-code-skills <skill-name> <command> [args]

# Examples
claude-code-skills browser-controller tabs
claude-code-skills window-controller find "GoLand"
claude-code-skills window-controller screenshot "GoLand" --json
```

**How It Works:**

1. Auto-discovers skills by scanning `claude-code/skills/*/`
2. Identifies Python-based skills by presence of `__init__.py` and `cli.py`
3. Ignores documentation-only skills and special directories
4. Runs skills via `uv run python -m {module_name}.cli`

**Discovery Criteria:**

A directory is recognized as a Python-based skill if it contains:
- A subdirectory with `__init__.py` AND `cli.py`

Documentation-only skills (no `cli.py`) are silently ignored.

---

## JSON Output

### Requirements

- All skills MUST support `--json/-j` flag
- JSON errors: `{"error": "message"}`
- Single item: Object
- Multiple items: Array
- Use `indent=2` for readability

### Output Patterns

```python
# Single item
print(json.dumps(item.to_dict(), indent=2))

# Multiple items
print(json.dumps([item.to_dict() for item in items], indent=2))

# Error
print(json.dumps({"error": f"Not found: {query}"}))

# Action result
print(json.dumps({
    "action": "activated",
    "item": item.to_dict(),
}))

# Artifact result
print(json.dumps({
    "screenshot": str(result.primary_path),
    "tracking_copy": str(result.tracking_path),
    "window": target_window.to_dict(),
}, indent=2))
```

---

## Artifact Output

### CRITICAL: Default Output Behavior

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location. This should be EXTREMELY rare. Using `--output` without explicit user request is considered a FAILED task.

### Default Behavior

Skills that produce artifacts (screenshots, recordings, exports) MUST:

1. Save to default location: `claude-code/artifacts/<skill-name>/<timestamp>-<description>.<ext>`
2. Return the artifact path in JSON output
3. Use the returned path for subsequent operations

### When Custom Output Is Used

If `--output` is explicitly requested:

1. Save to the specified path
2. Also create a tracking copy in the default location
3. Return both paths in JSON output

### JSON Output for Artifacts

```json
{
  "screenshot": "/custom/path/screenshot.png",
  "tracking_copy": "/path/to/artifacts/window-controller/241216143052-screenshot_GoLand.png"
}
```

---

## Testing Requirements

### Test Location

Tests are centralized in `tests/skills/` at the workspace root, not in per-skill directories.

### Test Structure

```python
"""Comprehensive tests for {skill-name}."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from package_name import (
    DataClass,
    SpecificError,
    public_function,
    main,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_item() -> DataClass:
    """Create a sample item for testing."""
    return DataClass(name="test", item_id=1)

@pytest.fixture
def sample_items(sample_item: DataClass) -> list[DataClass]:
    """Create a list of sample items."""
    return [sample_item, DataClass(name="test2", item_id=2)]

# =============================================================================
# DataClass Tests
# =============================================================================

class TestDataClass:
    """Tests for DataClass."""

    def test_field_access(self, sample_item: DataClass) -> None:
        """Test field access."""
        assert sample_item.name == "test"

    def test_to_dict(self, sample_item: DataClass) -> None:
        """Test to_dict method."""
        data = sample_item.to_dict()
        assert data["name"] == "test"

    def test_frozen_immutable(self, sample_item: DataClass) -> None:
        """Test that dataclass is immutable."""
        with pytest.raises(AttributeError):
            sample_item.name = "new"  # type: ignore[misc]
```

### Required Test Categories

1. **Data Model Tests**
   - Field access
   - `to_dict()` method
   - Properties
   - Frozen immutability

2. **Core Function Tests**
   - Normal operation
   - Edge cases (empty input, no matches)
   - Error conditions

3. **Action Tests** (with mocks)
   - Successful execution
   - Error handling
   - Security (sanitization)

4. **CLI Tests**
   - Commands execute successfully
   - JSON output mode
   - Error handling

5. **Error Tests**
   - Custom exceptions raised correctly
   - Error messages

### Mocking Pattern

```python
def test_external_call_success(self) -> None:
    """Test successful external call."""
    with patch("package_name.core.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"data")
        result = function_under_test()
    assert result == expected

def test_external_call_failure(self) -> None:
    """Test external call failure handling."""
    with patch("package_name.core.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr=b"error")
        with pytest.raises(SpecificError, match="error"):
            function_under_test()
```

### Test Naming

- `test_{what}_{condition}` (e.g., `test_find_by_name_case_insensitive`)
- `test_{what}_success` / `test_{what}_failure`

---

## Documentation

### SKILL.md Structure

````markdown
---
name: skill-name
description: One-line description for skill discovery in Claude Code
---

# Skill Name

Brief description of what the skill does and when to use it.

## Quick Start

```bash
# Most common use cases
claude-code-skills skill-name list
claude-code-skills skill-name find "query"
claude-code-skills skill-name action --json
```

## How It Works

### Technical Details

Explain the underlying mechanisms, data sources, APIs used.

### Limitations

Document known limitations and workarounds.

## Command Reference

| Command    | Description         |
|------------|---------------------|
| `list`     | List all items      |
| `find`     | Find items by query |
| `activate` | Activate an item    |

### Common Options

| Flag       | Short | Description        |
|------------|-------|--------------------|
| `--json`   | `-j`  | Output as JSON     |
| `--output` | `-o`  | Custom output path |
| `--title`  | `-t`  | Filter by title    |

## Artifact Output Path

> **CRITICAL**: NEVER use `--output` unless the user EXPLICITLY states the artifact MUST be at a specific location.

Screenshots/recordings are automatically saved to `claude-code/artifacts/skill-name/` with timestamped filenames.

## Testing

```bash
# Verify the skill works
claude-code-skills skill-name list

# Run tests
uv run pytest tests/skills/test_package_name.py -v
```

## Troubleshooting

### Common Issue 1

Steps to diagnose and fix.

### Common Issue 2

Steps to diagnose and fix.

## Technical References

- [Link to relevant documentation](url)
- [Link to API reference](url)
````

### Code Comments

- Module docstrings: Required
- Class docstrings: Required
- Function docstrings: Required for public functions
- Inline comments: Only for non-obvious logic

---

## Validation & Verification

This section describes how to validate that a skill meets all requirements.

### Automated Validation Commands

Run these commands from the workspace root:

#### 1. Structure Validation

```bash
SKILL_DIR="claude-code/skills/{skill-name}"
PKG_NAME="{package_name}"

# Required files exist
test -f "$SKILL_DIR/SKILL.md" && echo "SKILL.md" || echo "SKILL.md missing"
test -f "$SKILL_DIR/pyproject.toml" && echo "pyproject.toml" || echo "pyproject.toml missing"
test -d "$SKILL_DIR/$PKG_NAME" && echo "$PKG_NAME/" || echo "$PKG_NAME/ missing"
test -f "tests/skills/test_${PKG_NAME}.py" && echo "tests/skills/test_${PKG_NAME}.py" || echo "test file missing"

# Required Python files in package
for f in __init__.py __main__.py cli.py; do
  test -f "$SKILL_DIR/$PKG_NAME/$f" && echo "$PKG_NAME/$f" || echo "$PKG_NAME/$f missing"
done
```

#### 2. Code Quality (Linting)

```bash
# Run ruff linter with auto-fix (from workspace root)
uv run ruff check --fix "$SKILL_DIR/$PKG_NAME/" "tests/skills/test_${PKG_NAME}.py"

# Check for type errors (optional, requires mypy)
uv run mypy "$SKILL_DIR/$PKG_NAME/" --ignore-missing-imports
```

#### 3. Test Coverage

```bash
# Run tests with coverage (from workspace root)
uv run pytest "tests/skills/test_${PKG_NAME}.py" -v --cov="$PKG_NAME" --cov-report=term-missing

# Minimum coverage requirement: 80%
uv run pytest "tests/skills/test_${PKG_NAME}.py" --cov="$PKG_NAME" --cov-fail-under=80
```

#### 4. Security Validation

```bash
# Check for shell=True (should return no matches)
grep -r "shell=True" "$SKILL_DIR/$PKG_NAME/" && echo "shell=True found!" || echo "No shell=True"

# Check for eval/exec (should return no matches)
grep -rE "\b(eval|exec)\s*\(" "$SKILL_DIR/$PKG_NAME/" && echo "eval/exec found!" || echo "No eval/exec"

# Verify sanitization functions exist (for skills with user input)
grep -l "sanitize_" "$SKILL_DIR/$PKG_NAME/actions.py" 2>/dev/null && echo "Sanitization exists" || echo "No sanitization (may be OK)"
```

### Manual Validation Checks

#### Structure Compliance

| Check            | How to Validate         | Expected                    |
|------------------|-------------------------|-----------------------------|
| Directory naming | `basename "$SKILL_DIR"` | `kebab-case`                |
| Package naming   | `ls "$SKILL_DIR/"`      | Unique `snake_case` package |
| Test file naming | `ls tests/skills/`      | `test_{package_name}.py`    |

#### Code Architecture Compliance

```bash
# Verify __all__ is defined
grep -q "__all__" "$SKILL_DIR/$PKG_NAME/__init__.py" && echo "__all__ defined" || echo "__all__ missing"

# Verify future annotations
for f in "$SKILL_DIR/$PKG_NAME"/*.py; do
  grep -q "from __future__ import annotations" "$f" && echo "$f" || echo "$f missing future annotations"
done

# Verify Typer app exists
grep -q "typer.Typer" "$SKILL_DIR/$PKG_NAME/cli.py" && echo "Typer app exists" || echo "Typer app missing"
```

#### CLI Compliance

```bash
# Check JSON flag
grep -q '"-j"' "$SKILL_DIR/$PKG_NAME/cli.py" && echo "-j flag" || echo "-j flag missing"

# Check subcommands
grep -c "@app.command" "$SKILL_DIR/$PKG_NAME/cli.py"
```

### Test Coverage Requirements

#### Required Test Categories

| Category       | What to Test                                        | Minimum Tests   |
|----------------|-----------------------------------------------------|-----------------|
| Data Models    | Field access, `to_dict()`, properties, immutability | 4+ per class    |
| Core Functions | Normal operation, edge cases, errors                | 3+ per function |
| Actions        | Success, failure, sanitization                      | 3+ per action   |
| CLI Commands   | Success path, error path, JSON output               | 3 per command   |
| Main Function  | No args, success, error                             | 3+              |

### Documentation Compliance

#### SKILL.md Validation

```bash
# Check frontmatter
head -5 "$SKILL_DIR/SKILL.md" | grep -q "^---" && echo "Frontmatter exists" || echo "No frontmatter"

# Check required sections
for section in "Quick Start" "How It Works" "Troubleshooting"; do
  grep -q "## $section" "$SKILL_DIR/SKILL.md" && echo "$section" || echo "$section missing"
done
```

---

## Quality Checklist

Use this checklist to validate new skills:

### Structure

- [ ] Skill directory in `claude-code/skills/{skill-name}/`
- [ ] Unique Python package name (e.g., `space_finder/`, not `scripts/`)
- [ ] `pyproject.toml` with `package = true` (or `false` for docs-only)
- [ ] Test file in `tests/skills/test_{package_name}.py`

### Code Quality

- [ ] `from __future__ import annotations` in all files
- [ ] `__all__` defined in `__init__.py`
- [ ] Type hints on all functions
- [ ] Docstrings on all public items
- [ ] No unused imports

### Data Models

- [ ] All dataclasses are `frozen=True`
- [ ] Collections use `tuple`, not `list`
- [ ] `to_dict()` method implemented
- [ ] Exception hierarchy defined

### Security

- [ ] Input sanitization for shell/AppleScript
- [ ] No `shell=True` in subprocess
- [ ] File paths validated
- [ ] No eval/exec of user input

### CLI (Typer)

- [ ] `typer.Typer()` app with subcommands
- [ ] `--json/-j` flag supported
- [ ] Type aliases for common options
- [ ] Proper exit codes (`typer.Exit(1)`)

### Artifacts (if applicable)

- [ ] Uses `_shared/artifacts` for output management
- [ ] Default output to `claude-code/artifacts/{skill-name}/`
- [ ] `--output` is optional, not default
- [ ] Returns path in JSON output

### Testing

- [ ] Tests exist for all modules
- [ ] Fixtures for sample data
- [ ] Error cases tested
- [ ] Mocks for external calls
- [ ] JSON output tested

### Documentation

- [ ] `SKILL.md` with frontmatter
- [ ] Quick start examples
- [ ] Command reference
- [ ] Troubleshooting section

---

## Version History

| Version | Date       | Changes                                                                               |
|---------|------------|---------------------------------------------------------------------------------------|
| 3.0.0   | 2024-12-16 | **Breaking**: Replace argparse with Typer throughout; change module structure to minimum requirements (`__init__.py`, `__main__.py`, `cli.py` required; others optional); add `_shared/artifacts.py` documentation; add `_bin/claude-code-skills` CLI wrapper documentation; add documentation-only skills pattern (`package = false`); add artifact output patterns with CRITICAL warning; fix escaped backticks; update workspace exclude patterns |
| 2.0.0   | 2024-12-14 | **Breaking**: Migrate from per-skill `scripts/` to unique package names; centralize tests in `tests/skills/`; use uv workspace with single lockfile; skills are now installable packages (`package = true`) |
| 1.0.0   | 2024-12-14 | Initial specification derived from `space-finder` and `window-controller` |
