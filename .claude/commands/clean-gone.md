---
allowed-tools: Bash(bash:*)
description: Clean up local branches with deleted remote tracking branches
---

Clean up local branches where the remote tracking branch has been deleted (marked as [gone]).

## When to Use

- After feature branches have been merged and deleted remotely
- Regular repository maintenance to remove stale local branches
- Before creating new worktrees to free up disk space
- When user says "clean gone branches", "remove stale branches", "cleanup worktrees"

## Context

- Current branch: !`git branch --show-current`
- Git status: !`git status --porcelain`
- Worktrees: !`git worktree list`

## Workflow

**CRITICAL**: Execute the Implementation script as a single bash command. Do NOT manually run each step.

The script performs:

1. **Fetch and prune remote references** — updates remote-tracking branches and marks deleted remote branches as [gone]
2. **Identify branches marked as [gone]** — finds branches with `[gone]` upstream status
3. **For each [gone] branch**:
   - Check if branch has an associated worktree (not the main worktree)
   - If worktree exists: remove it with `git worktree remove --force`
   - Delete the branch with `git branch -D`
4. **Report completion** with summary of removed worktrees and branches

## Implementation

Run this complete script as a single command:

```bash
bash -c 'git fetch --prune --all && git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | awk "/\[gone\]/ {print \$1}" | while read -r branch; do wt=$(git worktree list | awk -v b="[$branch]" "\$0 ~ b {print \$1}"); tl=$(git rev-parse --show-toplevel); [ -n "$wt" ] && [ "$wt" != "$tl" ] && git worktree remove --force "$wt"; git branch -D "$branch"; done'
```

## Expected Results

- Removed worktrees are reported with their paths
- Deleted branches are listed by name
- Summary confirms cleanup completion
- If no [gone] branches exist, reports "No branches marked as [gone]"