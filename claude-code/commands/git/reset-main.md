---
allowed-tools: Bash(bash:*), AskUserQuestion
argument-hint: [remote] [--force|-f]
description: Reset current branch to remote's default branch and unset upstream tracking
---

Reset branch to sync with remote's default branch after PR merge.

$ARGUMENTS

## Constraints

- **NEVER output preamble** — execute script immediately without announcing intent
- **ALWAYS use** `bash -c '...'` format for atomic execution
- **NEVER reset dirty worktree without confirmation** — unless `--force` or `-f` flag present

## Context

- Dirty state check: !`git status --porcelain | head -5`

## Workflow

1. **Parse arguments** — extract remote name and flags from `$ARGUMENTS`
   - `--force` or `-f`: skip dirty state confirmation
   - Any other argument: treat as remote name

2. **Check dirty state** (skip if `--force` or `-f`):
   - If context shows uncommitted changes, use `AskUserQuestion`:
     - Question: "Working directory has uncommitted changes. Reset anyway? Changes will be lost."
     - Show first 5 files from context as examples
     - Options: "Yes, reset anyway" / "No, abort"
   - If user says no: output "Aborted — working directory has uncommitted changes" and stop

3. **Execute reset script**:

   - **With remote specified** (e.g., `origin`):

     ```bash
     bash -c 'remote="REMOTE_NAME"; main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; git fetch "$remote" && git reset --hard "$remote/$main" && git branch --unset-upstream 2>/dev/null; echo "Reset to $remote/$main, upstream tracking removed"'
     ```

   - **Without remote** (auto-detect):

     ```bash
     bash -c 'git remote | grep -q "^upstream$" && remote="upstream" || remote="origin"; main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; git fetch "$remote" && git reset --hard "$remote/$main" && git branch --unset-upstream 2>/dev/null; echo "Reset to $remote/$main, upstream tracking removed"'
     ```

4. **Output result directly** — no additional formatting needed

## Flags

| Flag           | Effect                                           |
|:---------------|:-------------------------------------------------|
| `--force`, `-f`| Skip dirty state confirmation, reset immediately |

## Notes

- Detects remote: prefers `upstream`, falls back to `origin`
- Detects default branch from remote HEAD (falls back to `main`)
- Useful after PR is squash-merged to sync local branch with main
- Uncommitted changes will be lost on reset — use `--force` to skip confirmation
