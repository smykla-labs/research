---
allowed-tools: Bash(pwd:*), Bash(git:*)
description: Capture session context for continuity between Claude Code sessions
---

Use the session-handover agent to capture critical session context for continuity.

$ARGUMENTS

## When to Use

- End of session (natural stopping point)
- Before context limit is reached
- When switching between tasks
- When user says "handover", "end session", "capture context"

## Context

- Current directory: !`pwd`
- Recent file changes: !`git status --short`

## Workflow

1. **Invoke session-handover** with the Task tool
   - Include user's focus/summary if provided: `$ARGUMENTS`
   - Include current directory and git status from context above
   - If no arguments provided, ask agent to analyze current session
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions (e.g., which task thread to prioritize), use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Continue to step 3
   - No status block (agent completed workflow) → Continue to step 3
3. **Report completion**:
   - Confirm the file was saved to `.claude/sessions/`
   - Confirm the document was copied to clipboard
   - Share the filename and key sections captured

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.

## Example Invocation

```
Capture session context for handover. Focus on:
- What was investigated this session
- Any failed approaches and why they didn't work
- Current stopping point and next steps
```