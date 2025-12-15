"""Configure pytest for skill tests."""

import sys
from pathlib import Path

# Add skill packages to path for imports
_skills_root = Path(__file__).parent.parent.parent / "claude-code" / "skills"
for skill_dir in _skills_root.iterdir():
    if skill_dir.is_dir() and (skill_dir / "pyproject.toml").exists():
        sys.path.insert(0, str(skill_dir))
