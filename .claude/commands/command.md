---
description: Create, modify, or improve slash commands
argument-hint: <path|description>
---

Use the command-manager agent to create or improve a slash command.

$ARGUMENTS

## Constraints

- **NEVER assume** mode — detect from input path explicitly
- **NEVER skip** quality review — all commands must pass reviewer
- **ALWAYS enforce** STATUS block output from subagent
- **ZERO tolerance** for incomplete commands — retry up to 3 times

## Mode Detection

Determine mode from input path BEFORE invoking subagent:

| Input Pattern                                | Mode          | Tell Subagent                                                         |
|:---------------------------------------------|:--------------|:----------------------------------------------------------------------|
| Path contains `.claude/commands/`            | **Modify**    | "MODIFY this existing command IN PLACE: {path}"                       |
| Path contains `.claude/agents/`              | **Dispatch**  | "DISPATCH: Create command for agent at {path}"                        |
| Path contains `~/.claude/agents/`            | **Dispatch**  | "DISPATCH: Create command for agent at {path}"                        |
| No file path provided                        | **Create**    | "CREATE a new standalone command: {description}"                      |
| Any other path (not in commands/agents dir)  | **Transform** | "TRANSFORM this file into a NEW command in .claude/commands/: {path}" |

**CRITICAL**: State the mode explicitly in your Task tool prompt.

**Mode Differences**:
- **Create**: New standalone command from scratch
- **Modify**: Improve existing command in place (quality, structure, standards compliance)
- **Transform**: Convert non-command file to command format (source stays untouched)
- **Dispatch**: Create command that dispatches to an agent (invokes agent via Task tool)

## Workflow

Due to Claude Code limitations (AskUserQuestion filtered from subagents, Task tool not available to subagents), follow this status-based flow:

### Step 1: Invoke command-manager

Use the Task tool with the detected mode stated explicitly in the prompt.

### Step 2: Parse Status Block

**CRITICAL**: The agent MUST output a `STATUS:` block. Parse the status block from subagent output.

**If no STATUS block found** (agent output prose/summary instead):
- Resume the agent with: "Output STATUS: READY_FOR_REVIEW with the command content in ~~~markdown fences. Do NOT output prose summaries."
- The agent constraint requires STATUS block output — enforce this.

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
command-manager
├── (no STATUS block) → resume asking for STATUS block
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
└── STATUS: READY_FOR_REVIEW → invoke quality-reviewer
    ├── PASS → write file → report success
    └── WARN/FAIL → resume with REVIEW_FEEDBACK (max 3x)
```

**Note**: Quality review is orchestrated here because subagents cannot spawn other subagents (Task tool not available to subagents).

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print as text.

## Output to User

**Show to user ONLY**:
- Final success message when command is written (after PASS)
- Final failure message if quality review fails after 3 attempts
- Questions via `AskUserQuestion` when STATUS: NEEDS_INPUT

**Do NOT show to user**:
- Intermediate STATUS blocks or agent responses
- Quality review feedback (this is for the agent to fix)
- Prose summaries or explanations from the agent

The user should see a clean flow: questions (if any) → success/failure result.

## Edge Cases

- **Empty input**: Report error — command requires mode detection (path or description)
- **Ambiguous path**: Path matches multiple patterns → ask user via `STATUS: NEEDS_INPUT` to clarify
- **Mode detection fails**: No clear pattern match → stop and ask user which mode to use
- **Quality review fails 3 times**: Report final issues, ask for manual intervention
- **No STATUS block from subagent**: Resume with explicit instruction, enforce output format
- **Uncertainty about file format**: Use detection rules (contents vs path) — never assume

## Done When

- [ ] Mode detected from input (or user selected via question)
- [ ] command-manager invoked with explicit mode in prompt
- [ ] STATUS block parsed correctly
- [ ] If NEEDS_INPUT: Questions asked, answers collected via AskUserQuestion
- [ ] Quality review passed (or retried max 3 times)
- [ ] Command written to final location OR failure reported to user
- [ ] User shown only final result (no intermediate steps)
