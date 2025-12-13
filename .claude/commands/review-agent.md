---
argument-hint: <agent-file-path|@file>
description: Review subagent definitions for quality compliance against best practices
---

Use the subagent-reviewer agent to audit agent files for quality issues.

$ARGUMENTS

## Constraints

- **NEVER assume** file content — always read and verify before passing to reviewer
- **NEVER hallucinate** agent definitions — review ONLY exact content provided
- **ALWAYS pass** full content to reviewer — not just file paths
- **ZERO tolerance** for false positives — only flag genuine issues

## Workflow

1. **Invoke subagent-reviewer** with the Task tool
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
