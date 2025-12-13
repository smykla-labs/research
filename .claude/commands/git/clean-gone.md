---
allowed-tools: Bash(bash:*)
argument-hint: [--dry-run] [--no-worktrees]
description: Clean up local branches with deleted remote tracking and their worktrees
---

Clean up local branches where the remote tracking branch has been deleted (marked as [gone]), plus merged worktrees, by default.

$ARGUMENTS

## Constraints

- **NEVER delete** the current branch — always skip and report in summary
- **NEVER remove** the main worktree — only remove feature/task worktrees
- **ALWAYS use** `bash -c '...'` format for atomic execution
- **ALWAYS render** the summary output EXACTLY as specified in Summary Output section — no prose, no custom formatting
- **ZERO tolerance** for accidental data loss — validate before destructive operations

## Context

Pre-execution state (establishes baseline for validation):

- Repository root: !`git rev-parse --show-toplevel`
- Current branch: !`git branch --show-current`
- Worktrees: !`git worktree list`

*Note: In-loop checks re-fetch these values for safety during iteration (prevents race conditions, ensures current branch never deleted)*

## Workflow

1. **Validate arguments** — Valid flags: `--dry-run`, `--no-worktrees`. Report invalid flags and stop.

2. **Clean branches and worktrees**:

   - **Default (full cleanup)**:

     Deletes branches that are gone OR merged (via squash/rebase), removes associated worktrees.

     ```bash
     bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null); [ -z "$remote" ] && remote=$(git remote | head -1); main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); current=$(git branch --show-current); del_branches=0; del_worktrees=0; kept_branches=""; skipped=""; git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do [ "$branch" = "$main" ] && continue; [ "$branch" = "$current" ] && echo "SKIPPED:$branch:current branch" && continue; delete=false; reason=""; case "$track" in *"[gone]"*) delete=true; reason="gone";; esac; if [ "$delete" = "false" ]; then unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ "$unmerged" -eq 0 ] 2>/dev/null && delete=true && reason="merged"; fi; if [ "$delete" = "true" ]; then wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); [ -n "$wt" ] && [ "$wt" != "$tl" ] && git worktree remove --force "$wt" 2>/dev/null && echo "REMOVED_WT:$(basename "$wt"):$branch"; git branch -D "$branch" >/dev/null 2>&1 && echo "DELETED:$branch:$reason"; else wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "KEPT_WT:$(basename "$wt"):$branch:$unmerged unmerged" || echo "KEPT:$branch:$unmerged unmerged"; fi; done'
     ```

   - **With `--dry-run` flag** (preview only, no changes):

     ```bash
     bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null); [ -z "$remote" ] && remote=$(git remote | head -1); main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); current=$(git branch --show-current); git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do [ "$branch" = "$main" ] && continue; [ "$branch" = "$current" ] && echo "WOULD_SKIP:$branch:current branch" && continue; delete=false; reason=""; case "$track" in *"[gone]"*) delete=true; reason="gone";; esac; if [ "$delete" = "false" ]; then unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ "$unmerged" -eq 0 ] 2>/dev/null && delete=true && reason="merged"; fi; if [ "$delete" = "true" ]; then wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "WOULD_REMOVE_WT:$(basename "$wt"):$branch"; echo "WOULD_DELETE:$branch:$reason"; else wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "WOULD_KEEP_WT:$(basename "$wt"):$branch:$unmerged unmerged" || echo "WOULD_KEEP:$branch:$unmerged unmerged"; fi; done'
     ```

   - **With `--no-worktrees` flag** (gone branches only, no worktree removal):

     ```bash
     bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | awk "/\[gone\]/ {print \$1}" | while read -r branch; do current=$(git branch --show-current); [ "$branch" = "$current" ] && echo "SKIPPED:$branch:current branch" && continue; git branch -D "$branch" >/dev/null 2>&1 && echo "DELETED:$branch:gone"; done'
     ```

   **Cleanup logic**:
   - Detects remote from main branch's upstream (works with origin, upstream, etc.)
   - Deletes branches marked as `[gone]` (remote tracking deleted)
   - Deletes branches fully merged via squash/rebase (detected via `git cherry`)
   - Removes associated worktrees before branch deletion
   - Skips main and current branch

3. **Render summary** from script output

## Summary Output

**CRITICAL**: After running the cleanup script, render the summary using a SINGLE `printf` command. Do NOT write prose or use multiple echo commands.

**Line prefixes** (from script output):

- `DELETED:branch:reason` → deleted branch
- `REMOVED_WT:worktree:branch` → removed worktree
- `SKIPPED:branch:reason` → skipped branch
- `KEPT:branch:reason` → kept branch
- `KEPT_WT:worktree:branch:reason` → kept worktree

**Dry-run prefixes** (same format, different header):

- `WOULD_DELETE:branch:reason` → would delete branch
- `WOULD_REMOVE_WT:worktree:branch` → would remove worktree
- `WOULD_SKIP:branch:reason` → would skip branch
- `WOULD_KEEP:branch:reason` → would keep branch
- `WOULD_KEEP_WT:worktree:branch:reason` → would keep worktree

**Colors**: bold=`\033[1m`, green=`\033[32m`, yellow=`\033[33m`, cyan=`\033[36m`, dim=`\033[90m`, reset=`\033[0m`

**Required format** — single `printf` command:

```bash
printf '\033[1m🧹 Cleanup Summary\033[0m\n\n\033[1mDeleted:\033[0m\n  \033[32m🗑️ fix/old-feature (merged)\033[0m\n  \033[32m🗂️ fix-old-feature-wt (worktree)\033[0m\n\n\033[1mSkipped:\033[0m\n  \033[33m⚠️ feat/current-work (current branch)\033[0m\n\n\033[1mKept:\033[0m\n  \033[36mℹ️ feat/in-progress (14 unmerged)\033[0m\n\n\033[90m───────────────────────────────\nDeleted: 2 branches, 1 worktree\nKept: 1 branch\033[0m\n'
```

**Dry-run format** — use "Would delete/remove" and different header:

```bash
printf '\033[1m🔍 Dry Run Preview\033[0m\n\n\033[1mWould delete:\033[0m\n  \033[32m🗑️ fix/old-feature (merged)\033[0m\n  \033[32m🗂️ fix-old-feature-wt (worktree)\033[0m\n\n\033[1mWould skip:\033[0m\n  \033[33m⚠️ feat/current-work (current branch)\033[0m\n\n\033[1mWould keep:\033[0m\n  \033[36mℹ️ feat/in-progress (14 unmerged)\033[0m\n\n\033[90m───────────────────────────────\nWould delete: 2 branches, 1 worktree\nWould keep: 1 branch\033[0m\n'
```

**Empty state**:

```bash
printf '\033[32m✅ Repository already clean — no branches to process\033[0m\n'
```

**Rules**:
- Use ONE `printf` command only — no multiple commands
- Only include sections with items (omit empty Deleted/Skipped/Kept)
- Build the entire output string dynamically based on parsed script output

## Flags

| Flag             | Effect                                                                   |
|:-----------------|:-------------------------------------------------------------------------|
| (none)           | Full cleanup: gone branches + worktrees + merged worktrees **(default)** |
| `--dry-run`      | Preview only: show what would be deleted without making changes          |
| `--no-worktrees` | Branches only: clean gone branches, skip all worktree removal            |

## Notes

- Full worktree cleanup is ON by default — use `--no-worktrees` to disable
- Current branch is never deleted
- Main worktree is never removed
- Uses `git worktree remove --force` to handle uncommitted changes in worktrees
- Uses `git branch -D` for gone branches (force, since remote is gone)
- Uses `git cherry` to detect squash/rebase merges (not just `--is-ancestor`)
- Detects remote dynamically from main branch's upstream (works with origin, upstream, etc.)

**CRITICAL**: All scripts use `bash -c '...'` format for reliable atomic execution.

## Edge Cases

- **Invalid flags**: Report unknown flag, show valid options (`--dry-run`, `--no-worktrees`), stop execution
- **No cleanable branches**: Report "No branches to clean" and exit
- **Current branch is [gone] or merged**: Skip deletion, warn user, report in summary
- **Uncommitted changes in worktree**: Force remove with `--force` flag (preserves branch safety)
- **No worktrees exist**: Still checks and deletes merged branches without worktrees
- **Multiple worktrees, mixed states**: Process each independently, report counts
- **Squash/rebase merged branches**: Detected via `git cherry`, deleted with all commits merged
- **No remote configured**: Falls back to first available remote
- **Non-origin remote (upstream, etc.)**: Detected from main branch's upstream tracking

## Done When

- [ ] Arguments validated — invalid flags rejected, stop if present
- [ ] Gone and merged branches deleted, associated worktrees removed
- [ ] With `--dry-run`: preview only, no actual changes made
- [ ] With `--no-worktrees`: only gone branches deleted, no worktree removal, no merged detection
- [ ] Summary rendered via single `printf` with ANSI colors — EXACTLY as specified in Summary Output section
