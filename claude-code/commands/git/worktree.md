---
allowed-tools: Bash(bash -c:*), Bash(pwd:*), Bash(git:*)
argument-hint: <task-description|@file> [--no-pbcopy]
description: Create git worktree with context transfer for feature branches
---

Create a git worktree with context transfer via the worktree-manager agent.

$ARGUMENTS

## Arguments

- `--no-pbcopy`: Skip copying the cd command to clipboard

## Constraints

- **NEVER create** worktree without user confirmation of branch name
- **NEVER assume** remote or default branch — detect explicitly
- **ALWAYS check** for uncommitted changes before creating worktree
- **ZERO tolerance** for data loss — handle uncommitted changes explicitly

## Context (Pre-gathered)

- Current directory: !`pwd`
- Git status: !`git status --porcelain`
- Available remotes: !`git remote -v`
- Current branch: !`git branch --show-current`

## Workflow

1. **Invoke worktree-manager** with the Task tool
   - Include: task description (`$ARGUMENTS` minus flags)
   - Include: all context from above (directory, git status, remotes, current branch)
   - Include: `--no-pbcopy` flag if present in arguments
   - If no task description provided: ask agent to request details via `STATUS: NEEDS_INPUT`

2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS: KEY=value, ...`
   - `STATUS: SCRIPT_READY` → Execute script (see step 3)
   - `STATUS: COMPLETED` → Report worktree path, branch name, and clipboard status to user

3. **For SCRIPT_READY — execute script**:
   - Extract script from the `script:` code block (content inside ```bash ... ```)
   - **CRITICAL**: Execute with `bash -c '{script}'` — script wrapped in single quotes after `-c`
   - **NEVER run the script directly** — ALWAYS use `bash -c '...'` wrapper
   - If execution fails: Resume agent with `SCRIPT_ERROR: {error message}` for correction

4. **If script execution succeeds**: Resume agent with `SCRIPT_OUTPUT: success` to get final formatted output

5. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.

## Expected Questions

The agent may request input for:

- **TYPE**: Branch type when task is ambiguous [feat|fix|chore|docs|test|refactor|ci|build]
- **DESCRIPTION**: Brief description for branch name when task is too vague
- **ACTION**: Uncommitted changes handling [commit|stash|abort]
- **REMOTE**: Which remote if multiple exist
- **BRANCH**: Default branch if auto-detection fails

## Notes

- The agent generates a single consolidated script to minimize approvals
- **Only untracked/ignored files are symlinked**: `.claude/`, `.klaudiush/`, `tmp/`, `.envrc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.gemini*`
- **Tracked files are NOT symlinked** — they already exist in worktree after `git worktree add`
- Script checks `git ls-files` before each symlink to determine if file is tracked
- Worktree-specific git excludes are configured automatically for symlinked files
- Clipboard contains ready-to-execute `cd && mise trust && direnv allow` command (unless `--no-pbcopy`)
