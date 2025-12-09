---
argument-hint: [agent-file-path]
description: Review subagent definitions for quality compliance against best practices
---

Use the subagent-quality-reviewer agent to audit agent files for quality issues.

$ARGUMENTS

## When to Use

- After creating or modifying subagent definitions
- Before committing agent files to version control
- When auditing existing agents for compliance
- When user says "review agent", "audit agent", "check agent quality"

## Workflow

1. **Invoke subagent-quality-reviewer** with the Task tool
   - Include agent file path(s): `$ARGUMENTS`
   - If no path provided, ask user which agent to review
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Display quality report with grade and issues
3. **Report findings**:
   - Overall grade (A/B/C/D/F)
   - Count of critical issues, warnings, suggestions
   - Priority recommendations for fixes
4. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
