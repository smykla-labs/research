---
allowed-tools: Bash(bash:*)
argument-hint: [--no-worktrees]
description: Clean up local branches with deleted remote tracking and their worktrees
---

Clean up local branches where the remote tracking branch has been deleted (marked as [gone]), plus merged worktrees, by default.

$ARGUMENTS

## Constraints

- **NEVER delete** the current branch — always skip and report in summary
- **NEVER remove** the main worktree — only remove feature/task worktrees
- **ALWAYS use** `bash -c '...'` format for atomic execution
- **ZERO tolerance** for accidental data loss — validate before destructive operations

## Context

Pre-execution state (establishes baseline for validation):

- Repository root: !`git rev-parse --show-toplevel`
- Current branch: !`git branch --show-current`
- Worktrees: !`git worktree list`

*Note: In-loop checks re-fetch these values for safety during iteration (prevents race conditions, ensures current branch never deleted)*

## Workflow

1. **Validate arguments** — Valid flag: `--no-worktrees`. Report invalid flags and stop.

2. **Phase 1: Clean gone branches** (always runs):

   - **Default (with worktree cleanup)**:

     ```bash
     bash -c 'git fetch --prune --all && git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | awk "/\[gone\]/ {print \$1}" | while read -r branch; do current=$(git branch --show-current); [ "$branch" = "$current" ] && echo "⚠️ Skipping current branch: $branch" && continue; wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); tl=$(git rev-parse --show-toplevel); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "🗂️ Removing worktree: $(basename "$wt") (project: $(basename "$tl"))" && git worktree remove --force "$wt"; echo "🗑️ Deleting branch: $branch" && git branch -D "$branch"; done'
     ```

   - **With `--no-worktrees` flag** (skip worktree removal):

     ```bash
     bash -c 'git fetch --prune --all && git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | awk "/\[gone\]/ {print \$1}" | while read -r branch; do current=$(git branch --show-current); [ "$branch" = "$current" ] && echo "⚠️ Skipping current branch: $branch" && continue; echo "🗑️ Deleting branch: $branch" && git branch -D "$branch"; done'
     ```

3. **Phase 2: Clean merged worktrees** (default, skipped with `--no-worktrees`):

   Removes worktrees for branches that are fully merged but NOT marked as [gone] (still have remote tracking).

   ```bash
   bash -c 'main=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed "s@^refs/remotes/origin/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); worktrees=$(git worktree list --porcelain | grep "^worktree " | sed "s/^worktree //" | tail -n +2); [ -z "$worktrees" ] && exit 0; echo "$worktrees" | while read -r wt; do [ -z "$wt" ] && continue; branch=$(git worktree list --porcelain | grep -A2 "^worktree $wt$" | grep "^branch " | sed "s@^branch refs/heads/@@"); [ -z "$branch" ] && continue; current=$(git branch --show-current); [ "$branch" = "$current" ] && echo "ℹ️ Keeping worktree: $(basename "$wt") (current branch)" && continue; if git merge-base --is-ancestor "$branch" "origin/$main" 2>/dev/null; then echo "🗂️ Removing merged worktree: $(basename "$wt") (project: $(basename "$tl"), branch: $branch)" && git worktree remove --force "$wt" && git branch -d "$branch" && echo "🗑️ Deleted merged branch: $branch"; else echo "ℹ️ Keeping worktree: $(basename "$wt") (branch $branch not yet merged to $main)"; fi; done; exit 0'
   ```

   - Only removes worktrees for branches fully merged into main/master
   - Uses safe delete (`-d`) since branch is verified merged
   - Skips current branch with info message
   - Reports kept worktrees with reason (not merged)

4. **Report results**:
   - Count removed worktrees
   - Count deleted branches
   - List any skipped items (current branch)
   - Report summary to user

## Flags

| Flag             | Effect                                                                   |
|:-----------------|:-------------------------------------------------------------------------|
| (none)           | Full cleanup: gone branches + worktrees + merged worktrees **(default)** |
| `--no-worktrees` | Branches only: clean gone branches, skip all worktree removal            |

## Notes

- Full worktree cleanup is ON by default — use `--no-worktrees` to disable
- Current branch is never deleted
- Main worktree is never removed
- Uses `git worktree remove --force` to handle uncommitted changes in worktrees
- Uses `git branch -D` for gone branches (force, since remote is gone)
- Uses `git branch -d` for merged worktrees (safe, verified merged)

**CRITICAL**: All scripts use `bash -c '...'` format for reliable atomic execution.

## Edge Cases

- **Invalid flags**: Report unknown flag, show valid options (`--no-worktrees`), stop execution
- **No [gone] branches**: Report "No branches marked as [gone]" and exit (no cleanup needed)
- **Current branch is [gone]**: Skip deletion, warn user, report in summary (user must switch first)
- **Uncommitted changes in worktree**: Force remove with `--force` flag (preserves branch safety)
- **No worktrees exist**: Skip Phase 2, complete Phase 1 normally
- **Multiple worktrees, mixed states**: Process each independently, report counts
- **Uncertainty about merge status**: Use `git merge-base --is-ancestor` for safe detection

## Done When

- [ ] Arguments validated — invalid flags rejected, stop if present
- [ ] Phase 1: Gone branches deleted + worktrees cleaned (skipped with `--no-worktrees` flag)
- [ ] Phase 2: Merged worktrees removed (only runs by default, skipped with `--no-worktrees`)
- [ ] Results reported with counts: worktrees removed, branches deleted, items skipped
- [ ] Summary shows what was cleaned and what was skipped (current branch, main worktree)
