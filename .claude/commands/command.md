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

Due to Claude Code limitations (AskUserQuestion filtered from subagents, Task tool not available to subagents), follow this status-based flow:

### Step 1: Invoke command-creator

Use the Task tool with the detected type stated explicitly.

### Step 2: Parse Status Block

Parse the status block from subagent output:

**If `STATUS: NEEDS_INPUT`**:
1. Parse questions from the `questions:` field
2. Use `AskUserQuestion` tool to present to user
3. Format answers: `ANSWERS: KEY=value, ...`
4. Resume subagent with `resume` parameter

**If `STATUS: READY_FOR_REVIEW`**:
1. Parse: `command_name`, `command_location`, `for_agent`, and `content` (in `~~~markdown` fences)
2. Invoke **command-quality-reviewer**:
   ```
   Review this command definition:

   ~~~markdown
   {content from status block}
   ~~~
   ```
3. Parse review result:
   - **PASS**: Write command to `{command_location}/{command_name}.md`, report success
   - **WARN or FAIL**: Resume subagent with `REVIEW_FEEDBACK:` (see Quality Fix Loop)

### Quality Fix Loop (max 3 attempts)

If quality review returns WARN or FAIL:

1. Resume subagent with:
   ```
   REVIEW_FEEDBACK:
   status: {WARN or FAIL}
   critical_issues:
   {list from review}
   warnings:
   {list from review}
   ```
2. Subagent will fix issues and output `STATUS: READY_FOR_REVIEW` again
3. Repeat quality review
4. After 3 failed attempts, report to user:
   - Final status and remaining issues
   - Manual intervention required

## Status Flow

```
command-creator
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
└── STATUS: READY_FOR_REVIEW → invoke quality-reviewer
    ├── PASS → write file → done
    └── WARN/FAIL → resume with REVIEW_FEEDBACK (max 3x)
```

**Note**: Quality review is orchestrated here because subagents cannot spawn other subagents (Task tool not available to subagents).

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print as text.
