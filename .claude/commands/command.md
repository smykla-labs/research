---
argument-hint: [agent-path-or-description]
description: Create slash commands for agents or standalone workflows
---

Use the command-creator agent to create a slash command.

$ARGUMENTS

## Mode Detection

Determine command type from input:

| Input Pattern                   | Type              | Tell Subagent                              |
|:--------------------------------|:------------------|:-------------------------------------------|
| Path to `.claude/agents/*.md`   | **Agent command** | "Create command for agent at {path}"       |
| Path to `~/.claude/agents/*.md` | **Agent command** | "Create command for agent at {path}"       |
| Description without path        | **Standalone**    | "Create standalone command: {description}" |

**CRITICAL**: State the type explicitly in your Task tool prompt.

## Workflow

### Step 1: Invoke command-creator

Use the Task tool with the detected type stated explicitly.

### Step 2: Parse Status Block

Parse the status block from subagent output:

**If `STATUS: NEEDS_INPUT`**:
1. Parse questions from the `questions:` field
2. Use `AskUserQuestion` tool to present to user
3. Format answers: `ANSWERS: KEY=value, ...`
4. Resume subagent with `resume` parameter

**If `STATUS: QUALITY_FAILED`**:
- Quality review failed after 3 automatic fix attempts
- Present the `remaining_issues:` to the user
- Report that manual intervention is required to achieve PASS

**If `STATUS: COMPLETED`**:
- Command creation is done (passed quality review)
- Report success with command name and test example

## Status Flow

```
command-creator
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
├── STATUS: QUALITY_FAILED → present remaining issues → manual intervention needed
└── STATUS: COMPLETED → done (quality review passed)
```

**Note**: Quality review and fixes happen automatically inside command-creator (Phase 4/4b).
`STATUS: QUALITY_FAILED` only appears if automatic fixes fail after 3 attempts.

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print as text.
