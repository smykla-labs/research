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
- **ALWAYS output** the summary directly as text (NOT via bash/printf) — use ANSI escape codes for colors
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
     bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null); [ -z "$remote" ] && remote=$(git remote | head -1); main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); current=$(git branch --show-current); merged_prs=""; command -v gh &>/dev/null && merged_prs=$(gh pr list --state merged --limit 200 --json headRefName --jq ".[].headRefName" 2>/dev/null | tr "\n" "|"); git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do [ "$branch" = "$main" ] && continue; [ "$branch" = "$current" ] && echo "SKIPPED:$branch:current branch" && continue; delete=false; reason=""; case "$track" in *"[gone]"*) delete=true; reason="gone";; esac; if [ "$delete" = "false" ]; then unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ "$unmerged" -eq 0 ] 2>/dev/null && delete=true && reason="merged"; fi; if [ "$delete" = "false" ] && [ -n "$merged_prs" ] && echo "|${merged_prs}" | grep -q "|${branch}|"; then delete=true; reason="squash-merged"; fi; if [ "$delete" = "true" ]; then wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); [ -n "$wt" ] && [ "$wt" != "$tl" ] && git worktree remove --force "$wt" 2>/dev/null && echo "REMOVED_WT:$(basename "$wt"):$branch"; git branch -D "$branch" >/dev/null 2>&1 && echo "DELETED:$branch:$reason"; else wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "KEPT_WT:$(basename "$wt"):$branch:$unmerged unmerged" || echo "KEPT:$branch:$unmerged unmerged"; fi; done'
     ```

   - **With `--dry-run` flag** (preview only, no changes):

     ```bash
     bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null); [ -z "$remote" ] && remote=$(git remote | head -1); main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); current=$(git branch --show-current); merged_prs=""; command -v gh &>/dev/null && merged_prs=$(gh pr list --state merged --limit 200 --json headRefName --jq ".[].headRefName" 2>/dev/null | tr "\n" "|"); git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do [ "$branch" = "$main" ] && continue; [ "$branch" = "$current" ] && echo "WOULD_SKIP:$branch:current branch" && continue; delete=false; reason=""; case "$track" in *"[gone]"*) delete=true; reason="gone";; esac; if [ "$delete" = "false" ]; then unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ "$unmerged" -eq 0 ] 2>/dev/null && delete=true && reason="merged"; fi; if [ "$delete" = "false" ] && [ -n "$merged_prs" ] && echo "|${merged_prs}" | grep -q "|${branch}|"; then delete=true; reason="squash-merged"; fi; if [ "$delete" = "true" ]; then wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "WOULD_REMOVE_WT:$(basename "$wt"):$branch"; echo "WOULD_DELETE:$branch:$reason"; else wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "WOULD_KEEP_WT:$(basename "$wt"):$branch:$unmerged unmerged" || echo "WOULD_KEEP:$branch:$unmerged unmerged"; fi; done'
     ```

   - **With `--no-worktrees` flag** (gone branches only, no worktree removal):

     ```bash
     bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | awk "/\[gone\]/ {print \$1}" | while read -r branch; do current=$(git branch --show-current); [ "$branch" = "$current" ] && echo "SKIPPED:$branch:current branch" && continue; git branch -D "$branch" >/dev/null 2>&1 && echo "DELETED:$branch:gone"; done'
     ```

   **Cleanup logic**:
   - Detects remote from main branch's upstream (works with origin, upstream, etc.)
   - Deletes branches marked as `[gone]` (remote tracking deleted)
   - Deletes branches fully merged via rebase/cherry-pick (detected via `git cherry`)
   - Deletes branches squash-merged via PR (detected via `gh pr list --state merged`)
   - Removes associated worktrees before branch deletion
   - Skips main and current branch

3. **Output summary directly** — parse script output and render as formatted text (NOT via bash)

## Summary Output

**CRITICAL**: After running the cleanup script, output the summary directly as text. Do NOT use bash/printf commands — output truncation can occur. Output the formatted text directly in your response.

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

**Colors** (apply using markdown formatting that renders in terminal):

- **Bold**: Section headers and title
- **Green**: Deleted items
- **Yellow**: Skipped items
- **Cyan**: Kept items

**Required format** — output directly as text:

```
**Cleanup Summary**

Deleted:
  🗑️ fix/old-feature (gone)              ← green
  🗂️ fix-old-feature-wt (worktree)       ← green

Skipped:
  ⚠️ feat/current-work (current branch)  ← yellow

Kept:
  🗂️ wt-name (worktree) - branch (N unmerged)  ← cyan
  ℹ️ feat/in-progress (14 unmerged)      ← cyan
```

**Dry-run format** — use "Would delete/remove" and different header:

```
**Dry Run Preview**

Would delete:
  🗑️ fix/old-feature (gone)              ← green
  🗂️ fix-old-feature-wt (worktree)       ← green

Would skip:
  ⚠️ feat/current-work (current branch)  ← yellow

Would keep:
  🗂️ wt-name (worktree) - branch (N unmerged)  ← cyan
  ℹ️ feat/in-progress (14 unmerged)      ← cyan
```

**Empty state** — output directly:

```
✅ Repository already clean — no branches to process  ← green
```

**Rules**:

- Output text directly — NEVER use bash/printf for summary
- Use markdown bold (`**text**`) for title and section headers
- Only include sections with items (omit empty Deleted/Skipped/Kept)
- Build the output dynamically based on parsed script output

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
- Uses `git cherry` to detect rebase/cherry-pick merges (compares patch IDs)
- Uses `gh pr list --state merged` to detect squash merges (GitHub API, requires `gh` CLI)
- Detects remote dynamically from main branch's upstream (works with origin, upstream, etc.)
- Falls back gracefully if `gh` is unavailable (squash merges won't be detected)

**CRITICAL**: All scripts use `bash -c '...'` format for reliable atomic execution.

## Edge Cases

- **Invalid flags**: Report unknown flag, show valid options (`--dry-run`, `--no-worktrees`), stop execution
- **No cleanable branches**: Report "No branches to clean" and exit
- **Current branch is [gone] or merged**: Skip deletion, warn user, report in summary
- **Uncommitted changes in worktree**: Force remove with `--force` flag (preserves branch safety)
- **No worktrees exist**: Still checks and deletes merged branches without worktrees
- **Multiple worktrees, mixed states**: Process each independently, report counts
- **Squash-merged branches**: Detected via `gh pr list --state merged` (requires `gh` CLI and GitHub repo)
- **Rebase/cherry-pick merged branches**: Detected via `git cherry` (works locally without API)
- **gh CLI unavailable**: Falls back to `git cherry` only (squash merges won't be detected)
- **No remote configured**: Falls back to first available remote
- **Non-origin remote (upstream, etc.)**: Detected from main branch's upstream tracking

## Done When

- [ ] Arguments validated — invalid flags rejected, stop if present
- [ ] Gone and merged branches deleted, associated worktrees removed
- [ ] With `--dry-run`: preview only, no actual changes made
- [ ] With `--no-worktrees`: only gone branches deleted, no worktree removal, no merged detection
- [ ] Summary output directly as text with ANSI colors — NOT via bash/printf
