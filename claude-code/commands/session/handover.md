---
allowed-tools: Bash(pwd:*), Bash(git:*)
argument-hint: [session-focus]
description: Capture session context for continuity between Claude Code sessions
---

Invoke session-manager agent to capture critical context for session continuity.

$ARGUMENTS

## Constraints

- **NEVER assume** session scope — if multiple task threads exist, agent will ask
- **NEVER skip** file save and clipboard copy — both are required
- **ALWAYS verify** agent output contains `STATUS:` block
- **ZERO tolerance** for incomplete handover — all applicable sections must exist
- **ALWAYS collect skills** — Before invoking agent, identify all skills used in THIS session

## Context

- Current directory: !`pwd`
- Recent changes: !`git status --porcelain`

## Workflow

1. **Collect skills used in THIS session** (CRITICAL — do this FIRST):
   - Review the conversation history for Skill tool invocations
   - Look for patterns: `Skill(skill-name)`, skill names in tool calls
   - Common skills: `browser-controller`, `verified-screenshot`, `window-controller`, `ocr-finder`, `space-finder`, `screen-recorder`, and any `document-skills:*` variants
   - Note: Skills are ONLY those invoked via the Skill tool, not general tools like Read/Write/Bash

2. **Invoke session-manager** via Task tool with collected context:
   - User's focus if provided: `$ARGUMENTS`
   - Current directory and git status from context above
   - **Skills used in session** (from step 1) — format as:
     ```
     Skills used in this session:
     - `skill-name` — brief context of how/why it was used
     - `skill-name` — brief context
     ```
     If no skills were used: `Skills used in this session: None`

3. **Parse status block**:
   - `STATUS: NEEDS_INPUT` → Use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report file location and clipboard status

4. **Confirm completion**: File saved to `.claude/sessions/`, copied to clipboard

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
**CRITICAL**: Skills information MUST be passed to the agent — the agent cannot see your tool call history.
