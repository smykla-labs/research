---
allowed-tools: Read, Bash, Glob
argument-hint: <worktree-path>
description: Validate git worktree setup including symlinks, excludes, and tracking
model: haiku
---

Use the worktree-reviewer agent to validate git worktree configuration.

$ARGUMENTS

## Constraints

- **NEVER assume** worktree path — use $ARGUMENTS or current directory
- **ZERO tolerance** for hallucination — verify all paths exist before reporting

## Workflow

### Step 1: Determine Worktree Path

`$ARGUMENTS` may contain:
- **Explicit path**: e.g., `/path/to/worktree` → Use directly
- **Empty**: → Use current working directory

### Step 2: Verify Path is a Worktree

Check that the path is actually a git worktree:
- `.git` should be a file (not directory) containing `gitdir:`
- If not a worktree, report error to user

### Step 3: Invoke Reviewer

Invoke **worktree-reviewer** with the Task tool:
- **MUST include**: Worktree path to validate
- Format the prompt as:
  ```text
  Validate worktree at {path}
  ```

**If reviewer outputs STATUS: NEEDS_INPUT**:
- Parse questions from output
- Use `AskUserQuestion` tool to collect answers
- Resume reviewer with `ANSWERS: KEY=value`

**CRITICAL**: You MUST use `AskUserQuestion` tool for user questions — subagents cannot display interactive UI.

### Step 4: Report Results

Agent will output structured findings:
- Summary (PASS/WARN/FAIL)
- Worktree info (path, branch, tracking)
- Critical issues (must fix)
- Warnings (should fix)
- Checklist results
- Recommendations with exact commands

Report results to user with actionable next steps.

## Edge Cases

- **Empty input**: Use current directory as worktree path
- **Path is not a worktree**: Report error — `.git` should be a file, not directory
- **Path doesn't exist**: Report error immediately with the missing path
- **Current directory not in a git repo**: Report error

## Done When

- [ ] Worktree path determined (argument or current directory)
- [ ] Path verified as valid worktree
- [ ] Reviewer invoked with worktree path
- [ ] Results reported to user with actionable recommendations
