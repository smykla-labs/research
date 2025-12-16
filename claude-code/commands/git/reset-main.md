---
allowed-tools: Bash(bash:*)
argument-hint: [remote]
description: Reset current branch to remote's default branch and unset upstream tracking
---

Reset branch to sync with remote's default branch after PR merge.

$ARGUMENTS

## Constraints

- **NEVER output preamble** — execute script immediately without announcing intent
- **ALWAYS use** `bash -c '...'` format for atomic execution

## Workflow

1. **Parse arguments** — extract remote name from `$ARGUMENTS` (if provided)

2. **Execute reset script**:

   - **With remote specified** (e.g., `origin`):

     ```bash
     bash -c 'remote="REMOTE_NAME"; main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; git fetch "$remote" && git reset --hard "$remote/$main" && git branch --unset-upstream 2>/dev/null; echo "Reset to $remote/$main, upstream tracking removed"'
     ```

   - **Without remote** (auto-detect):

     ```bash
     bash -c 'git remote | grep -q "^upstream$" && remote="upstream" || remote="origin"; main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; git fetch "$remote" && git reset --hard "$remote/$main" && git branch --unset-upstream 2>/dev/null; echo "Reset to $remote/$main, upstream tracking removed"'
     ```

3. **Output result directly** — no additional formatting needed

## Notes

- Detects remote: prefers `upstream`, falls back to `origin`
- Detects default branch from remote HEAD (falls back to `main`)
- Useful after PR is squash-merged to sync local branch with main
