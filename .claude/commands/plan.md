---
argument-hint: <task-description|plan-path+changes|doc-path|@file>
description: Create, modify, or transform implementation plans via implementation-planner agent
---

Create, modify, or transform comprehensive implementation plans using the implementation-planner agent.

$ARGUMENTS

## Constraints

- **NEVER skip mode detection** — ALWAYS detect mode BEFORE invoking planner
- **NEVER proceed without grade A** — Plan MUST achieve grade A from quality review
- **NEVER write plan until grade A** — Pass content back and forth until quality passes
- **ZERO tolerance for placeholder plans** — Reject plans with `{placeholder}` patterns
- **ALWAYS orchestrate quality review** — Parent command invokes reviewer, not subagent
- **MAXIMUM 3 review attempts** — After 3 feedback cycles, report failure to user

## Mode Detection

Determine mode from input BEFORE invoking planner:

| Input Pattern                                      | Mode          | Tell Planner                                         |
|:---------------------------------------------------|:--------------|:-----------------------------------------------------|
| Task description only (no file path)               | **Create**    | "CREATE: {task description}"                         |
| Path to existing plan + change description         | **Modify**    | "MODIFY: {plan-path}\nChanges: {change description}" |
| Path to non-plan document (spec, RFC, issue, etc.) | **Transform** | "TRANSFORM: {doc-path}"                              |

**Detection logic:**

1. Check if input contains path to existing file
2. If yes: Check if file is in `tmp/tasks/*/implementation_plan.md` → **Modify** mode
3. If yes but not in `tmp/tasks/` → **Transform** mode
4. If no file path → **Create** mode

**Note**: Improve mode is triggered internally by quality review loop when grade < A

**CRITICAL**: State the mode explicitly in your Task tool prompt to implementation-planner.

## Workflow

### Create & Transform Modes

1. **Ask user about worktree preference** using `AskUserQuestion` tool:
   - Question: "Do you want a worktree for this implementation?"
   - Options: [yes (recommended)|no (use current directory)]
   - Store answer for next step

2. **Invoke implementation-planner** with Task tool:
   - State detected mode explicitly: "CREATE: {description}" or "TRANSFORM: {path}"
   - Include full user request: `$ARGUMENTS`
   - Include `use_worktree: yes` or `use_worktree: no` based on user's answer
   - Parse status block from planner:
     - `STATUS: NEEDS_INPUT` → Parse `questions:` section, use `AskUserQuestion` tool, resume with `ANSWERS: KEY1=value1, KEY2=value2`
     - `STATUS: READY_FOR_REVIEW` → Extract fields: `task_slug`, `plan_location`, `content:` (full plan in ~~~markdown fences)
   - Repeat until `STATUS: READY_FOR_REVIEW`

3. **Quality review loop** (see below)

**Note**: The planner includes worktree/branch setup as Phase 1 based on user's preference. The executor will create the worktree when executing the plan.

### Modify Mode

1. **Skip worktree question** — Not applicable for modifying existing plans

2. **Invoke implementation-planner** with Task tool:
   - State mode explicitly: "MODIFY: {plan-path}\nChanges: {change description}"
   - Include full user request: `$ARGUMENTS`
   - Parse status block from planner:
     - `STATUS: NEEDS_INPUT` → Parse `questions:` section, use `AskUserQuestion` tool, resume with `ANSWERS: KEY1=value1, KEY2=value2`
     - `STATUS: READY_FOR_REVIEW` → Extract fields: `task_slug`, `plan_location`, `content:` (full plan in ~~~markdown fences)
   - Repeat until `STATUS: READY_FOR_REVIEW`

3. **Quality review loop** (see below)

### Quality Review Loop (All Modes)

1. **Invoke quality reviewer**:
   - Invoke implementation-plan-reviewer with Task tool
   - Pass plan content extracted from `content:` section
   - Parse reviewer output for grade (in Summary table: `| **Overall Grade** | {grade} |`)
   - **If grade = A**: Proceed to next step
   - **If grade < A**: Resume implementation-planner with:
     ```text
     REVIEW_FEEDBACK:
     grade: {B|C|D|F}
     critical_issues:
     - {issue from reviewer}
     warnings:
     - {warning from reviewer}
     plan_location: {plan_location from planner}
     ```
   - **Track attempts**: 1, 2, 3
   - **After 3rd failed attempt**: Report to user with final grade, issues list, recommend refining task description
   - Repeat quality review until grade A or max attempts reached

2. **Write plan to final location** (only after grade A):
   - Use Write tool to save plan content to `plan_location`
   - Confirm file written successfully

3. **Report success to user**:
   - Plan location (file path)
   - Worktree preference (yes/no — executor will create if yes)
   - Quality grade (A)
   - Number of review iterations
   - Brief summary (task slug, number of phases)
   - Mode used (Create/Modify/Transform)

**CRITICAL**: For `NEEDS_INPUT` from subagents, you MUST use `AskUserQuestion` tool. Do NOT print questions as text. Format answers as `ANSWERS: KEY1=value1, KEY2=value2`.

## Expected Questions

The implementation-planner may request input for:

- **SCOPE**: What specific component or feature should be planned
- **GOAL**: Desired outcome or problem to solve
- **FILES**: Specific files or directories to focus on
- **LINT**: Lint command (when not auto-discovered)
- **TEST**: Test command (when not auto-discovered)
- **TYPE**: Branch type (feat|fix|chore|docs|test|refactor|ci|build)
- **REMOTE**: Git remote (upstream|origin)
- **BRANCH**: Default branch (main|master|custom)
- **WORKTREE**: Worktree path pattern (when use_worktree: yes)