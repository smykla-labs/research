---
allowed-tools: Bash(bash -c:*), Bash(pwd:*), Bash(git:*), Bash(ls:*)
argument-hint: <task-description|@file> [--quick] [--no-pbcopy] [--no-ide] [--ide <name>]
description: Create git worktree with context transfer for feature branches
---

Create a git worktree with context transfer via worktree-manager agents.

$ARGUMENTS

## Arguments

- `--quick`: Use lightweight agent (no questions, sensible defaults, faster)
- `--no-pbcopy`: Skip copying the cd command to clipboard
- `--no-ide`: Disable automatic IDE detection (clipboard won't include IDE command)
- `--ide <name>`: Override auto-detected IDE with specified IDE (e.g., `--ide webstorm`)

**IDE auto-detection** (enabled by default):
- Detects from Tier 1 config files: go.mod → goland, pyproject.toml → pycharm, etc.
- Clipboard command: `<ide> <path>; cd <path> && mise trust && direnv allow`
- If ambiguous (multiple Tier 1 files): skips IDE, full agent asks user

## Constraints

- **CRITICAL: ALWAYS use `bash -c '...'`** — NEVER execute script directly, ALWAYS wrap in `bash -c '{script}'`
- **NEVER create** worktree without user confirmation of branch name
- **NEVER assume** remote or default branch — detect explicitly
- **ALWAYS check** for uncommitted changes before creating worktree
- **ZERO tolerance** for data loss — handle uncommitted changes explicitly

## Context (Pre-gathered)

- Current directory: !`pwd`
- Git status: !`git status --porcelain`
- Available remotes: !`git remote -v`
- Current branch: !`git branch --show-current`
- Project config files (for IDE detection): !`ls go.mod Cargo.toml pyproject.toml setup.py pom.xml build.gradle build.gradle.kts Gemfile composer.json CMakeLists.txt tsconfig.json package.json requirements.txt 2>/dev/null | tr '\n' ' ' || echo "none"`

## Workflow

### Step 0: Select Agent Mode

**Use `worktree-manager-light` (fast mode) when:**
- `--quick` flag is present, OR
- Task description has 4+ words AND does NOT contain ambiguous phrases

**Use `worktree-manager` (full mode) when:**
- Task is short (< 4 words)
- Contains ambiguous phrases: "work on", "make changes", "do something", "changes to"
- No task description provided

**Ambiguous phrase detection** (case-insensitive):
```
ambiguous = ["work on", "make changes", "do something", "changes to", "update something"]
use_light = --quick OR (word_count >= 4 AND no ambiguous phrase)
```

### Step 1: Invoke Selected Agent

**For LIGHT mode (`worktree-manager-light`):**
- Include: task description, directory, remotes, project config files
- Include: `--no-pbcopy`, `--no-ide`, `--ide <name>` flags if present
- Agent auto-detects IDE from Tier 1 config files by default
- Agent will output `STATUS: SCRIPT_READY` immediately (no questions)

**For FULL mode (`worktree-manager`):**
- Include: task description (`$ARGUMENTS` minus flags)
- Include: all context from above (directory, git status, remotes, current branch, project config files)
- Include: `--no-pbcopy`, `--no-ide`, `--ide <name>` flags if present
- Agent auto-detects IDE; asks user if ambiguous (multiple Tier 1 files)
- If no task description provided: ask agent to request details via `STATUS: NEEDS_INPUT`

### Step 2: Parse status block from output

- `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS: KEY=value, ...`
- `STATUS: SCRIPT_READY` → Execute script (see step 3)
- `STATUS: COMPLETED` → Report worktree path, branch name, and clipboard status to user

**Note**: Light agent will NEVER output `NEEDS_INPUT` — it always proceeds with defaults.

### Step 3: For SCRIPT_READY — execute script

- Extract script from the `script:` code block (content inside ```bash ... ```)
- **⚠️ CRITICAL ⚠️**: You MUST execute with `bash -c '{script}'`
  - ✅ CORRECT: `Bash(command: "bash -c 'set -euo pipefail; R=...; ...'")`
  - ❌ WRONG: `Bash(command: "set -euo pipefail; R=...; ...")`
- **NEVER run the script directly** — the script contains shell syntax that REQUIRES `bash -c` wrapper
- If execution fails: Resume agent with `SCRIPT_ERROR: {error message}` for correction

### Step 4: If script execution succeeds

Resume agent with `SCRIPT_OUTPUT: success` to get final formatted output

### Step 5: Repeat until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.

## Expected Questions

The agent may request input for:

- **TYPE**: Branch type when task is ambiguous [feat|fix|chore|docs|test|refactor|ci|build]
- **DESCRIPTION**: Brief description for branch name when task is too vague
- **ACTION**: Uncommitted changes handling [commit|stash|abort]
- **REMOTE**: Which remote if multiple exist
- **BRANCH**: Default branch if auto-detection fails
- **IDE**: Which JetBrains IDE when auto-detection fails or multiple Tier 1 config files found [goland|pycharm|webstorm|idea|rubymine|phpstorm|clion|rustrover]

## Notes

- The agent generates a single consolidated script to minimize approvals
- **Only untracked/ignored files are symlinked**: `.claude/`, `.klaudiush/`, `tmp/`, `.envrc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.gemini*`
- **Tracked files are NOT symlinked** — they already exist in worktree after `git worktree add`
- Script checks `git ls-files` before each symlink to determine if file is tracked
- Worktree-specific git excludes are configured automatically for symlinked files
- Clipboard contains ready-to-execute `cd && mise trust && direnv allow` command (unless `--no-pbcopy`)
- IDE auto-detection is ON by default — clipboard command starts with `<ide> <path>;` to open worktree
- Use `--no-ide` to disable IDE auto-detection
- IDE auto-detection uses Tier 1 config files (go.mod, Cargo.toml, pyproject.toml, etc.)

## Light Agent Behavior

When using `--quick` or auto-detected fast mode:
- **No questions asked** — uses sensible defaults
- **Branch prefix**: Defaults to `chore/` when type is unclear
- **Dirty worktree**: Ignored (proceeds anyway)
- **Remote**: Auto-selects `upstream` else `origin`
- **Default branch**: Detects or defaults to `main`
- **IDE detection**: Auto-detects from Tier 1 config files by default; skips if ambiguous (no questions)
