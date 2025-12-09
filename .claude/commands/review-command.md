---
allowed-tools: Read, Grep, Glob
argument-hint: [command-file-path]
description: Review slash command quality against the commands guide
model: claude-3-5-haiku-20241022
---

Use the command-quality-reviewer agent to validate slash command files.

$ARGUMENTS

## When to Use

- After creating a new slash command
- Before committing command changes
- When command behavior is unexpected
- When user requests command review

## Context

Commands Guide: @ai/claude-code-commands-guide.md

## Workflow

1. **Invoke command-quality-reviewer** with the Task tool
   - Include command file path: `$ARGUMENTS`
   - Include the Commands Guide from context above
   - Ask agent to review against all quality standards
2. **Agent will output structured findings**:
   - Summary (PASS/WARN/FAIL)
   - Critical issues (must fix)
   - Warnings (should fix)
   - Info (consider)
   - Checklist results
   - Recommendations
3. **Report results** to user with actionable next steps

**Note**: This agent uses STATUS: COMPLETED only (no NEEDS_INPUT workflow).
