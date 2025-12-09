---
allowed-tools: Bash(pwd:*), Bash(git:*)
argument-hint: [task-description]
description: Create git worktree with context transfer for feature branches
---

Create a git worktree with context transfer via the worktree-creator agent.

$ARGUMENTS

## When to Use

- Starting new feature branches requiring isolation
- Before multi-task work to enable parallel development
- Isolating experiments without affecting main worktree
- When user says "create worktree", "new worktree", "wt"

## Context

- Current directory: !`pwd`
- Git status: !`git status --porcelain`
- Available remotes: !`git remote -v`
- Current branch: !`git branch --show-current`

## Workflow

1. **Invoke worktree-creator** with the Task tool
   - Include full task description: `$ARGUMENTS`
   - Include context from above (directory, git status, remotes, current branch)
   - If no task description provided, ask agent to prompt user for details
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report worktree path, branch name, and clipboard contents
3. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.

## Expected Questions

The agent may request input for:

- **TYPE**: Branch type selection when task description is ambiguous (feat|fix|chore|docs|test|refactor|ci|build)
- **ACTION**: How to handle uncommitted changes (commit|stash|abort)
- **REMOTE**: Which remote to use if multiple exist
- **BRANCH**: Default branch name if auto-detection fails