---
allowed-tools: Bash(bash -c:*), Bash(bash -n:*), Bash(pwd:*), Bash(git:*)
argument-hint: <task-description|@file>
description: Create git worktree with context transfer for feature branches
---

Create a git worktree with context transfer via the worktree-manager agent.

$ARGUMENTS

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
   - Include: task description (`$ARGUMENTS`)
   - Include: all context from above (directory, git status, remotes, current branch)
   - If no task description provided: ask agent to request details via `STATUS: NEEDS_INPUT`

2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS: KEY=value, ...`
   - `STATUS: SCRIPT_READY` → Validate and execute (see step 3)
   - `STATUS: COMPLETED` → Report worktree path, branch name, clipboard contents to user

3. **For SCRIPT_READY — validate then execute**:
   - Extract script from the `script:` code block
   - **Syntax check**: Run `bash -n -c '{script}'` to validate syntax (no execution)
   - If syntax check fails: Resume agent with `SCRIPT_ERROR: {error message}` for correction
   - If syntax check passes: Execute with `bash -c '{script}'`

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
- Symlinks are created for: `.claude/`, `.klaudiush/`, `tmp/`, `.envrc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.gemini*`
- Tracked files are handled via `git update-index --skip-worktree` — no manual intervention needed
- Worktree-specific git excludes are configured automatically
- Clipboard contains ready-to-execute `cd && mise trust` command
