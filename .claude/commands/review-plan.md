---
argument-hint: <file-path|@file>
description: Review implementation plan for quality and executor-readiness
---

Use the implementation-plan-reviewer agent to validate implementation specs against planning-agent template standards.

$ARGUMENTS

## Constraints

- **NEVER modify plans** — Read-only quality analysis and feedback
- **ALWAYS include full output** — Quality reports must show all findings with line numbers
- **ZERO tolerance for incomplete review** — All 7 mandatory sections must be checked

## Workflow

1. **Invoke implementation-plan-reviewer** with the Task tool
   - Include full user input: `$ARGUMENTS`
   - If file path provided, agent will read it
   - If content provided with `@file`, agent receives inline content
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report quality findings to user
3. **Present quality report** showing:
   - Overall grade (A-F)
   - Critical issues that block execution
   - Warnings and suggestions for improvement
   - Executor-readiness assessment

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.

## Expected Questions

The agent may request input for:

- **FILE_TYPE**: Confirm non-plan file is intended as implementation plan when structure unclear
- **SCOPE**: Clarify review scope when uncertain about requirements