---
allowed-tools: Bash(pwd:*), Bash(git:*)
argument-hint: [session-focus]
description: Capture session context for continuity between Claude Code sessions
---

Invoke session-handover agent to capture critical context for session continuity.

$ARGUMENTS

## Constraints

- **NEVER assume** session scope — if multiple task threads exist, agent will ask
- **NEVER skip** file save and clipboard copy — both are required
- **ALWAYS verify** agent output contains `STATUS:` block
- **ZERO tolerance** for incomplete handover — all applicable sections must exist

## Context

- Current directory: !`pwd`
- Recent changes: !`git status --porcelain`

## Workflow

1. **Invoke session-handover** via Task tool
   - Include user's focus if provided: `$ARGUMENTS`
   - Include current directory and git status from context above
2. **Parse status block**:
   - `STATUS: NEEDS_INPUT` → Use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report file location and clipboard status
3. **Confirm completion**: File saved to `.claude/sessions/`, copied to clipboard

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
