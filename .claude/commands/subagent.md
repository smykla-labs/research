---
argument-hint: <file|description|@file>
description: Create, modify, or transform subagent definitions
---

Use the subagent-manager agent to create, modify, or transform a subagent definition.

$ARGUMENTS

## Constraints

- **NEVER assume** mode — detect from input path explicitly
- **NEVER skip** quality review — all agents must pass reviewer with grade A
- **ALWAYS enforce** STATUS block output from subagent
- **ZERO tolerance** for incomplete agents — retry up to 3 times

## Mode Detection

Determine mode from input path BEFORE invoking subagent:

| Input Pattern                             | Mode          | Tell subagent                                                           |
|:------------------------------------------|:--------------|:------------------------------------------------------------------------|
| Path contains `ai/prompts/` or `prompts/` | **Transform** | "TRANSFORM prompt template at {path} into NEW agent in .claude/agents/" |
| Path contains `.claude/agents/`           | **Modify**    | "MODIFY this existing agent IN PLACE: {path}"                           |
| No file path provided                     | **Create**    | "CREATE a new agent: {description}"                                     |
| Any other path                            | **Transform** | "TRANSFORM prompt template at {path} into NEW agent in .claude/agents/" |

**CRITICAL**: State the mode explicitly in your Task tool prompt.

**Transform vs Modify**:
- **Transform**: Source is a PROMPT (e.g., `ai/prompts/*.md`). Create NEW agent file in `.claude/agents/`. Source file stays UNTOUCHED.
- **Modify**: Source is an EXISTING AGENT (e.g., `.claude/agents/*.md`). Edit the file IN PLACE.

## Workflow

Due to Claude Code limitations (AskUserQuestion filtered from subagents, Task tool not available to subagents), follow this status-based flow:

### Step 1: Invoke subagent-manager

Use the Task tool with the detected mode stated explicitly.

### Step 2: Parse Status Block

Parse the status block from subagent output:

**If `STATUS: NEEDS_INPUT`**:
1. Parse the questions from the `questions:` field
2. Use `AskUserQuestion` tool to present ALL questions to the user
3. Format answers: `ANSWERS: MODEL=X, TOOLS=X, PERMISSION=X, LOCATION=X, SLASH_COMMAND=X`
4. Resume subagent with `resume` parameter

**If `STATUS: READY_FOR_REVIEW`**:
1. Parse: `agent_name`, `agent_location`, `slash_command`, and `content` (in `~~~markdown` fences)
2. Invoke **subagent-quality-reviewer**:
   ```
   Review this agent definition:

   ~~~markdown
   {content from status block}
   ~~~
   ```
3. Parse review result:
   - **Grade A**: Write agent to `{agent_location}/{agent_name}.md`, proceed to Step 3
   - **Grade < A**: Resume subagent with `REVIEW_FEEDBACK:` (see Quality Fix Loop)

### Quality Fix Loop (max 3 attempts)

If quality review returns grade < A:

1. Resume subagent with:
   ```
   REVIEW_FEEDBACK:
   grade: {grade}
   critical_issues:
   {list from review}
   warnings:
   {list from review}
   ```
2. Subagent will fix issues and output `STATUS: READY_FOR_REVIEW` again
3. Repeat quality review
4. After 3 failed attempts, report to user:
   - Final grade and remaining issues
   - Manual intervention required

### Step 3: Handle Slash Command Request

After writing the agent (quality review passed):

**If `slash_command: yes: /command-name`**:
1. Invoke **command-manager** subagent:
   ```
   Create slash command for agent at {agent_location}/{agent_name}.md
   Agent name: {agent_name}
   Command name: {command-name}
   Save to: {.claude/commands/ or ~/.claude/commands/ based on agent_location}
   ```
2. Handle `STATUS: READY_FOR_REVIEW` from command-manager (same quality flow)
3. Report both agent and command to user

**If `slash_command: no`**:
- Report success with agent path and summary

## Status Chaining Summary

```
subagent-manager
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
└── STATUS: READY_FOR_REVIEW → invoke quality-reviewer
    ├── Grade A → write file → check slash_command
    │   ├── yes → invoke command-manager → quality review → write → done
    │   └── no → done
    └── Grade < A → resume with REVIEW_FEEDBACK (max 3x)
```

**Note**: Quality review is orchestrated here because subagents cannot spawn other subagents (Task tool not available to subagents).

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print as text.
