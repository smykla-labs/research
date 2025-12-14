# Claude Code Skills Development Specification

Version 2.0.0 | Derived from: `macos-space-finder`, `macos-window-controller`, `macos-verified-screenshot`

This document defines requirements, guidelines, and best practices for developing Claude Code skills. Use it to validate new skills for consistency, quality, security, and maintainability.

---

## Table of Contents

1. [Directory Structure](#directory-structure)
2. [Required Files](#required-files)
3. [Code Architecture](#code-architecture)
4. [Naming Conventions](#naming-conventions)
5. [Data Models](#data-models)
6. [Exception Handling](#exception-handling)
7. [Security Requirements](#security-requirements)
8. [CLI Design](#cli-design)
9. [JSON Output](#json-output)
10. [Testing Requirements](#testing-requirements)
11. [Documentation](#documentation)
12. [Validation & Verification](#validation--verification)
13. [Quality Checklist](#quality-checklist)

---

## Directory Structure

Skills are organized as a uv workspace with centralized tests:

```
# Root workspace
pyproject.toml                  # Workspace config, shared dependencies
uv.lock                         # Single lockfile for all skills
tests/
└── skills/                     # Centralized test location
    ├── test_space_finder.py
    ├── test_verified_screenshot.py
    └── test_window_controller.py

# Skill directory structure
.claude/skills/{skill-name}/
├── SKILL.md                    # Required: Skill documentation
├── pyproject.toml              # Required: Project configuration (workspace member)
└── {package_name}/             # Required: Python package (unique name)
    ├── __init__.py             # Public API exports
    ├── __main__.py             # Entry point (python -m {package_name})
    ├── models.py               # Data classes, exceptions, constants
    ├── core.py                 # Core functionality (pure logic)
    ├── actions.py              # Action functions (side effects)
    └── cli.py                  # CLI interface
```

### Naming Rules

- **Skill directory**: `kebab-case` (e.g., `macos-space-finder`)
- **Python package**: Unique `snake_case` name (e.g., `space_finder`, `verified_screenshot`)
- **Test file**: `test_{package_name}.py` in `tests/skills/`

### Workspace Configuration

Root `pyproject.toml` defines the workspace:

```toml
[tool.uv.workspace]
members = [".claude/skills/*"]
```

Skills are installed as editable packages via `uv pip install -e .claude/skills/{skill-name}`.

---

## Required Files

### `pyproject.toml` (Skill)

```toml
[project]
name = "macos-skill-name"
version = "0.1.0"
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
]

[tool.uv]
package = false

[tool.uv.workspace]
members = [".claude/skills/*"]
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

### Module Responsibilities

| Module       | Purpose                             | Side Effects            |
|--------------|-------------------------------------|-------------------------|
| `models.py`  | Data classes, exceptions, constants | None                    |
| `core.py`    | Core logic, parsing, filtering      | Minimal (reads only)    |
| `actions.py` | Actions with external effects       | Yes (subprocess, files) |
| `cli.py`     | CLI parsing and handlers            | Yes (stdout/stderr)     |

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
import argparse
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

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
from .cli import create_parser, main
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
    "create_parser",
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

### CLI Arguments

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

### CLI Error Handling

```python
def main(argv: Sequence[str] | None = None) -> int:
    try:
        # ... logic ...
    except SkillError as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0
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

### Parser Structure

```python
def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Brief skill description.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list              List all items
  %(prog)s --find "query"      Find items
  %(prog)s --json --list       Output as JSON
        """,
    )

    # Actions group
    parser.add_argument("--list", "-l", action="store_true", help="List all items")
    parser.add_argument("--find", "-f", metavar="QUERY", help="Find items")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # Positional argument (optional)
    parser.add_argument("query", nargs="?", metavar="QUERY", help="Search query")

    return parser
```

### Handler Pattern

```python
def _handle_list(items: Sequence[Item], *, json_output: bool = False) -> int:
    """Handle --list command."""
    if json_output:
        print(json.dumps([item.to_dict() for item in items], indent=2))
    else:
        for item in items:
            print(f"{item.name}: {item.description}")
    return 0
```

### Main Function

```python
def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Validate: at least one action required
    if not any([args.list, args.find, args.query]):
        parser.print_help()
        return 1

    try:
        # Load data
        data = load_data()

        # Dispatch to handlers
        json_output = args.json

        if args.list:
            return _handle_list(data, json_output=json_output)
        if args.find:
            return _handle_find(data, args.find, json_output=json_output)
        if args.query:
            return _handle_query(data, args.query, json_output=json_output)

    except SkillError as e:
        print(json.dumps({"error": str(e)}) if args.json else f"Error: {e}", file=sys.stderr)
        return 1

    return 0
```

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
from package_name.cli import _handle_action

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
   - Parser arguments
   - Short flags
   - Handler functions
   - Main function
   - JSON output mode

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

```markdown
---
name: skill-name
description: One-line description for skill discovery in Claude Code
---

# Skill Name

Brief description of what the skill does and when to use it.

## Quick Start

\```bash
# Most common use cases (using CLI entry point)
uv run skill-name --list
uv run skill-name --find "query"
uv run skill-name --json --list

# Or using module syntax
uv run python -m package_name --list
\```

## How It Works

### Technical Details

Explain the underlying mechanisms, data sources, APIs used.

### Limitations

Document known limitations and workarounds.

## Command Reference

| Flag     | Short | Description    |
|----------|-------|----------------|
| `--list` | `-l`  | List all items |
| `--find` | `-f`  | Find items     |
| `--json` | `-j`  | Output as JSON |

## Integration Examples

\```python
# Example code for programmatic use
import subprocess
result = subprocess.run(
    ["uv", "run", "skill-name", "--list", "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
\```

## Testing

\```bash
# Verify the skill works
uv run skill-name --list

# Run tests
uv run pytest tests/skills/test_package_name.py -v
\```

## Troubleshooting

### Common Issue 1

Steps to diagnose and fix.

### Common Issue 2

Steps to diagnose and fix.

## Technical References

- [Link to relevant documentation](url)
- [Link to API reference](url)
```

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
SKILL_DIR=".claude/skills/{skill-name}"
PKG_NAME="{package_name}"

# Required files exist
test -f "$SKILL_DIR/SKILL.md" && echo "✅ SKILL.md" || echo "❌ SKILL.md missing"
test -f "$SKILL_DIR/pyproject.toml" && echo "✅ pyproject.toml" || echo "❌ pyproject.toml missing"
test -d "$SKILL_DIR/$PKG_NAME" && echo "✅ $PKG_NAME/" || echo "❌ $PKG_NAME/ missing"
test -f "tests/skills/test_${PKG_NAME}.py" && echo "✅ tests/skills/test_${PKG_NAME}.py" || echo "❌ test file missing"

# Required Python files in package
for f in __init__.py __main__.py models.py core.py actions.py cli.py; do
  test -f "$SKILL_DIR/$PKG_NAME/$f" && echo "✅ $PKG_NAME/$f" || echo "❌ $PKG_NAME/$f missing"
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
grep -r "shell=True" "$SKILL_DIR/$PKG_NAME/" && echo "❌ shell=True found!" || echo "✅ No shell=True"

# Check for eval/exec (should return no matches)
grep -rE "\b(eval|exec)\s*\(" "$SKILL_DIR/$PKG_NAME/" && echo "❌ eval/exec found!" || echo "✅ No eval/exec"

# Verify sanitization functions exist
grep -l "sanitize_" "$SKILL_DIR/$PKG_NAME/actions.py" && echo "✅ Sanitization exists" || echo "⚠️ No sanitization"
```

### Manual Validation Checks

#### Structure Compliance

| Check | How to Validate | Expected |
|-------|-----------------|----------|
| Directory naming | `basename "$SKILL_DIR"` | `kebab-case` |
| Package naming | `ls "$SKILL_DIR/"` | Unique `snake_case` package |
| Test file naming | `ls tests/skills/` | `test_{package_name}.py` |

#### Code Architecture Compliance

```bash
# Verify __all__ is defined
grep -q "__all__" "$SKILL_DIR/$PKG_NAME/__init__.py" && echo "✅ __all__ defined" || echo "❌ __all__ missing"

# Verify future annotations
for f in "$SKILL_DIR/$PKG_NAME"/*.py; do
  grep -q "from __future__ import annotations" "$f" && echo "✅ $f" || echo "❌ $f missing future annotations"
done

# Verify __main__.py pattern
grep -q "sys.exit(main())" "$SKILL_DIR/$PKG_NAME/__main__.py" && echo "✅ __main__.py correct" || echo "❌ __main__.py pattern wrong"
```

#### Data Model Compliance

```bash
# Check frozen dataclasses
grep -E "@dataclass\(frozen=True\)" "$SKILL_DIR/$PKG_NAME/models.py" && echo "✅ Frozen dataclasses" || echo "❌ Not frozen"

# Check for list fields (should use tuple)
grep -E ":\s*list\[" "$SKILL_DIR/$PKG_NAME/models.py" && echo "⚠️ Using list (should use tuple)" || echo "✅ No list fields"

# Check to_dict exists
grep -q "def to_dict" "$SKILL_DIR/$PKG_NAME/models.py" && echo "✅ to_dict exists" || echo "❌ to_dict missing"
```

#### Exception Hierarchy Compliance

```bash
# Check base exception exists
grep -E "class \w+Error\(Exception\):" "$SKILL_DIR/$PKG_NAME/models.py" && echo "✅ Base exception" || echo "❌ No base exception"

# List all exceptions
grep -E "class \w+Error\(" "$SKILL_DIR/$PKG_NAME/models.py"
```

#### CLI Compliance

```bash
# Check short flags exist
grep -E '"-[a-z]"' "$SKILL_DIR/$PKG_NAME/cli.py" && echo "✅ Short flags exist" || echo "❌ No short flags"

# Check JSON flag
grep -q '"-j"' "$SKILL_DIR/$PKG_NAME/cli.py" && echo "✅ -j flag" || echo "❌ -j flag missing"

# Check help epilog with examples
grep -q "Examples:" "$SKILL_DIR/$PKG_NAME/cli.py" && echo "✅ Examples in help" || echo "❌ No examples"
```

### Test Coverage Requirements

#### Required Test Categories

| Category | What to Test | Minimum Tests |
|----------|--------------|---------------|
| Data Models | Field access, `to_dict()`, properties, immutability | 4+ per class |
| Core Functions | Normal operation, edge cases, errors | 3+ per function |
| Actions | Success, failure, sanitization | 3+ per action |
| CLI Parser | All flags, short flags, positional args | 1 per flag |
| CLI Handlers | Success path, error path, JSON output | 3 per handler |
| Main Function | No args, success, error | 3+ |

#### Test Pattern Validation

```bash
# Check fixture usage
grep -c "@pytest.fixture" "tests/skills/test_${PKG_NAME}.py"

# Check class-based tests
grep -c "class Test" "tests/skills/test_${PKG_NAME}.py"

# Check error testing
grep -c "pytest.raises" "tests/skills/test_${PKG_NAME}.py"
```

### Documentation Compliance

#### SKILL.md Validation

```bash
# Check frontmatter
head -5 "$SKILL_DIR/SKILL.md" | grep -q "^---" && echo "✅ Frontmatter exists" || echo "❌ No frontmatter"

# Check required sections
for section in "Quick Start" "How It Works" "Command Reference" "Troubleshooting"; do
  grep -q "## $section" "$SKILL_DIR/SKILL.md" && echo "✅ $section" || echo "❌ $section missing"
done

# Check command table
grep -q "| Flag" "$SKILL_DIR/SKILL.md" && echo "✅ Command table" || echo "❌ No command table"
```

### Full Validation Script

Create and run this script for comprehensive validation:

```bash
#!/bin/bash
# validate-skill.sh - Run from workspace root
# Usage: ./validate-skill.sh macos-space-finder space_finder

SKILL_NAME="${1:?Usage: $0 <skill-name> <package-name>}"
PKG_NAME="${2:?Usage: $0 <skill-name> <package-name>}"
SKILL_DIR=".claude/skills/$SKILL_NAME"

echo "=== Skill Validation: $SKILL_NAME ($PKG_NAME) ==="

# Structure
echo -e "\n--- Structure ---"
test -f "$SKILL_DIR/SKILL.md" && echo "✅ SKILL.md" || echo "❌ SKILL.md"
test -f "$SKILL_DIR/pyproject.toml" && echo "✅ pyproject.toml" || echo "❌ pyproject.toml"
test -d "$SKILL_DIR/$PKG_NAME" && echo "✅ $PKG_NAME/" || echo "❌ $PKG_NAME/"
for f in __init__.py __main__.py models.py core.py actions.py cli.py; do
  test -f "$SKILL_DIR/$PKG_NAME/$f" && echo "✅ $PKG_NAME/$f" || echo "❌ $PKG_NAME/$f"
done
test -f "tests/skills/test_${PKG_NAME}.py" && echo "✅ tests/skills/test_${PKG_NAME}.py" || echo "❌ tests/skills/test_${PKG_NAME}.py"

# Linting
echo -e "\n--- Linting ---"
uv run ruff check "$SKILL_DIR/$PKG_NAME/" "tests/skills/test_${PKG_NAME}.py" --quiet && echo "✅ Lint passed" || echo "❌ Lint failed"

# Tests
echo -e "\n--- Tests ---"
uv run pytest "tests/skills/test_${PKG_NAME}.py" -q && echo "✅ Tests passed" || echo "❌ Tests failed"

# Coverage
echo -e "\n--- Coverage ---"
uv run pytest "tests/skills/test_${PKG_NAME}.py" --cov="$PKG_NAME" --cov-fail-under=80 -q 2>/dev/null && \
  echo "✅ Coverage ≥80%" || echo "⚠️ Coverage <80%"

# Security
echo -e "\n--- Security ---"
! grep -rq "shell=True" "$SKILL_DIR/$PKG_NAME/" && echo "✅ No shell=True" || echo "❌ shell=True found"
! grep -rqE "\b(eval|exec)\s*\(" "$SKILL_DIR/$PKG_NAME/" && echo "✅ No eval/exec" || echo "❌ eval/exec found"
grep -q "sanitize_" "$SKILL_DIR/$PKG_NAME/actions.py" && echo "✅ Sanitization" || echo "⚠️ No sanitization"

# Code patterns
echo -e "\n--- Code Patterns ---"
grep -q "__all__" "$SKILL_DIR/$PKG_NAME/__init__.py" && echo "✅ __all__" || echo "❌ __all__"
grep -qE "@dataclass\(frozen=True\)" "$SKILL_DIR/$PKG_NAME/models.py" && echo "✅ Frozen" || echo "❌ Not frozen"
grep -q "def to_dict" "$SKILL_DIR/$PKG_NAME/models.py" && echo "✅ to_dict" || echo "❌ to_dict"

# CLI
echo -e "\n--- CLI ---"
grep -q '"-j"' "$SKILL_DIR/$PKG_NAME/cli.py" && echo "✅ -j flag" || echo "❌ -j flag"
grep -q "Examples:" "$SKILL_DIR/$PKG_NAME/cli.py" && echo "✅ Examples" || echo "❌ Examples"

# Documentation
echo -e "\n--- Documentation ---"
head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---" && echo "✅ Frontmatter" || echo "❌ Frontmatter"
grep -q "## Quick Start" "$SKILL_DIR/SKILL.md" && echo "✅ Quick Start" || echo "❌ Quick Start"
grep -q "## Troubleshooting" "$SKILL_DIR/SKILL.md" && echo "✅ Troubleshooting" || echo "❌ Troubleshooting"

echo -e "\n=== Validation Complete ==="
```

### CI/CD Integration

For automated validation in CI pipelines:

```yaml
# .github/workflows/validate-skills.yml
name: Validate Skills

on:
  pull_request:
    paths:
      - '.claude/skills/**'
      - 'tests/skills/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@681c641aba71e4a1c380be3ab5e12ad51f415867 # v7.1.6

      - name: Install workspace
        run: |
          uv sync
          uv pip install -e .claude/skills/macos-space-finder
          uv pip install -e .claude/skills/macos-verified-screenshot
          uv pip install -e .claude/skills/macos-window-controller

      - name: Validate Structure
        run: |
          for skill_pkg in "macos-space-finder:space_finder" "macos-verified-screenshot:verified_screenshot" "macos-window-controller:window_controller"; do
            skill="${skill_pkg%%:*}"
            pkg="${skill_pkg##*:}"
            echo "Checking $skill ($pkg)"
            test -f ".claude/skills/$skill/SKILL.md"
            test -f ".claude/skills/$skill/pyproject.toml"
            test -d ".claude/skills/$skill/$pkg"
            test -f "tests/skills/test_${pkg}.py"
          done

      - name: Lint
        run: |
          uv run ruff check .claude/skills/ tests/skills/

      - name: Test
        run: |
          uv run pytest tests/skills/ -v

      - name: Security Check
        run: |
          ! grep -r "shell=True" .claude/skills/*/
          ! grep -rE "\b(eval|exec)\s*\(" .claude/skills/*/
```

---

## Quality Checklist

Use this checklist to validate new skills:

### Structure

- [ ] Skill directory in `.claude/skills/{skill-name}/`
- [ ] Unique Python package name (e.g., `space_finder/`, not `scripts/`)
- [ ] `pyproject.toml` with `package = true`
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

### CLI

- [ ] Short and long flags for all options
- [ ] `--json/-j` flag supported
- [ ] Help text with examples
- [ ] Proper exit codes (0 success, 1+ error)

### Testing

- [ ] Tests exist for all modules
- [ ] Fixtures for sample data
- [ ] Error cases tested
- [ ] Mocks for external calls
- [ ] JSON output tested

### Documentation

- [ ] `SKILL.md` with frontmatter
- [ ] Quick start examples
- [ ] Command reference table
- [ ] Troubleshooting section

---

## Version History

| Version | Date       | Changes                                                                               |
|---------|------------|---------------------------------------------------------------------------------------|
| 2.0.0   | 2024-12-14 | **Breaking**: Migrate from per-skill `scripts/` to unique package names; centralize tests in `tests/skills/`; use uv workspace with single lockfile; skills are now installable packages (`package = true`) |
| 1.0.0   | 2024-12-14 | Initial specification derived from `macos-space-finder` and `macos-window-controller` |
