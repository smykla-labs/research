---
argument-hint: [file-or-description]
description: Create, modify, or transform subagent definitions
---

Use the subagent-creator agent to create, modify, or transform a subagent definition.

$ARGUMENTS

## Mode Detection

Determine mode from input path BEFORE invoking subagent:

| Input Pattern | Mode | Tell subagent |
|:--------------|:-----|:--------------|
| Path contains `ai/prompts/` or `prompts/` | **Transform** | "TRANSFORM this prompt template: {path}" |
| Path contains `.claude/agents/` | **Modify** | "MODIFY this existing agent: {path}" |
| No file path provided | **Create** | "CREATE a new agent: {description}" |
| Any other path | **Transform** | "TRANSFORM this prompt template: {path}" |

**CRITICAL**: State the mode explicitly in your Task tool prompt.

## Workflow

Due to Claude Code limitation (AskUserQuestion is filtered from subagents), follow this status-based flow:

### Step 1: Invoke subagent-creator

Use the Task tool with the detected mode stated explicitly.

### Step 2: Parse Status Block

Parse the status block from subagent output:

**If `STATUS: NEEDS_INPUT`**:
1. Parse the questions from the `questions:` field
2. Use `AskUserQuestion` tool to present ALL questions to the user
3. Format answers: `ANSWERS: MODEL=X, TOOLS=X, PERMISSION=X, LOCATION=X, SLASH_COMMAND=X`
4. Resume subagent with `resume` parameter

**If `STATUS: COMPLETED`**:
- Agent creation is done, no further action needed
- Report success to user with the summary

**If `STATUS: READY_FOR_COMMAND`**:
- Parse: `agent_path`, `agent_name`, `command_name`, `command_location`
- Invoke **command-creator** subagent:
  ```
  Create slash command for agent at {agent_path}.
  Agent name: {agent_name}
  Command name: {command_name}
  Save to: {command_location}
  ```
- Handle any `STATUS: NEEDS_INPUT` from command-creator
- When command-creator returns `STATUS: COMPLETED`, report both agent and command to user

## Status Chaining Summary

```
subagent-creator
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
├── STATUS: COMPLETED → done
└── STATUS: READY_FOR_COMMAND → invoke command-creator
                                  └── STATUS: COMPLETED → done
```

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print as text.
