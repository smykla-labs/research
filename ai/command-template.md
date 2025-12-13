# Claude Code Slash Command Template

Comprehensive template for creating production-quality Claude Code slash commands.

---

## Quick Reference

| Section            | Required | When to Include                                      |
|:-------------------|:---------|:-----------------------------------------------------|
| Frontmatter        | ✅        | Always                                               |
| Purpose Statement  | ✅        | Always (first line after frontmatter)                |
| `$ARGUMENTS`       | ✅        | Always (unless no-arg command)                       |
| Constraints        | ✅        | Always — behavioral guardrails and safety rules      |
| Mode Detection     | ❌        | Target subagent has multiple operational modes       |
| Context            | ❌        | Command needs runtime info (git status, pwd, etc.)   |
| Workflow           | ✅        | Always for subagent invokers; optional for scripts   |
| Status Flow        | ❌        | Complex orchestration with quality review            |
| Expected Questions | ❌        | Subagent uses `STATUS: NEEDS_INPUT` with known keys  |
| Flags              | ❌        | Command accepts flag arguments (e.g., `--verbose`)   |
| Notes              | ❌        | Important caveats or warnings                        |

---

## Command Types

| Type                  | Purpose                                   | Complexity | Example                |
|:----------------------|:------------------------------------------|:-----------|:-----------------------|
| **Script Executor**   | Run bash scripts directly                 | Simple     | `clean-gone`           |
| **Simple Invoker**    | Invoke one subagent, basic STATUS         | Simple     | `handover`, `wt`       |
| **Content Passer**    | Read content, pass to reviewer            | Medium     | `review-command`       |
| **Full Orchestrator** | Multi-agent with quality review           | Complex    | `subagent`, `command`  |

---

## Templates

### Script Executor

Direct bash script execution without subagents.

````markdown
---
allowed-tools: Bash({required-commands}:*)
argument-hint: [--{flag}]
description: {What this command does in ≤10 words}
---

{One-line purpose statement describing what this command does.}

$ARGUMENTS

## Constraints

- **NEVER** {dangerous action} — {why and what to do instead}
- **ALWAYS** {required behavior} — {rationale}
- **ZERO tolerance** for {unacceptable outcome} — {safeguard}

## Context

- {Label}: !`{bash command}`
- {Label}: !`{bash command}`

## Workflow

1. **Validate arguments** — {What to check, when to stop}

2. **{Phase 1 name}**:

   ```bash
   bash -c '{complete script}'
   ```

3. **{Phase 2 name}** (optional/conditional):

   {Description of when this runs.}

   ```bash
   bash -c '{complete script}'
   ```

4. **Report results**:
   - {What to report}
   - {Summary format}

## Flags

| Flag          | Effect                               |
|:--------------|:-------------------------------------|
| (none)        | {Default behavior}                   |
| `--{flag}`    | {What this flag changes}             |

## Notes

- {Important caveat or warning}
- {Safety consideration}

**CRITICAL**: {Most important constraint in bold.}
````

---

### Simple Invoker

Invoke a single subagent with basic STATUS handling.

````markdown
---
allowed-tools: Bash({commands}:*)
argument-hint: <{input-type}|@file>
description: {What this command does in ≤10 words}
---

Use the {agent-name} agent to {brief purpose}.

$ARGUMENTS

## Context

- {Label}: !`{bash command}`
- {Label}: !`{bash command}`

## Workflow

1. **Invoke {agent-name}** with the Task tool
   - Include: `$ARGUMENTS`
   - Include context from above: {which context fields}
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report {what} to user
3. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.

## Expected Questions

The agent may request input for:

- **{KEY}**: {What this question asks} ({option1}|{option2}|{option3})
- **{KEY}**: {What this question asks} ({option1}|{option2})

## Example Invocation

```
{Example of how to invoke this command with realistic arguments}
```
````

---

### Content Passer

Read content and pass to a reviewer subagent.

````markdown
---
allowed-tools: Read, Grep, Glob
argument-hint: <file-path|@file>
description: {Review action} against {standards}
model: haiku
---

Use the {reviewer-agent} agent to validate {what}.

$ARGUMENTS

## Context

{Reference guide/standards}: @{path/to/guide.md}

## Workflow

### Step 1: Determine Input Type

`$ARGUMENTS` may contain either:
- **File path**: e.g., `.claude/{type}/foo.md` → Read the file first
- **Inline content**: e.g., `@.claude/{type}/foo.md` expands to actual content → Use directly

**Detection**:
- If `$ARGUMENTS` starts with `---` (frontmatter) → It's inline content
- If `$ARGUMENTS` is a path (contains `.md`, `.claude/`, etc.) → Read the file

### Step 2: Get Actual Content

**If file path**: Read the file using the Read tool
- **VERIFY** the file was read successfully
- If file not found, report error to user immediately

**If inline content**: Use `$ARGUMENTS` directly

### Step 3: Invoke Reviewer

**CRITICAL**: You MUST pass actual file content to the reviewer, NOT just a path.

Invoke **{reviewer-agent}** with the Task tool:
- **MUST include**: Full file content in `~~~markdown` fences
- **MUST include**: The {guide name} from context above
- Format the prompt as:
  ```
  Review this {artifact type} definition:

  ~~~markdown
  {actual file content here}
  ~~~
  ```

### Step 4: Report Results

Agent will output structured findings:
- Summary (PASS/WARN/FAIL)
- Critical issues (must fix)
- Warnings (should fix)
- Recommendations

Report results to user with actionable next steps.

**CRITICAL**: NEVER invoke the reviewer without actual file content. Passing just a path allows hallucination.

**Note**: This command uses STATUS: COMPLETED only (no NEEDS_INPUT workflow).
````

---

### Full Orchestrator

Complex multi-agent workflow with quality review.

````markdown
---
argument-hint: <path|description>
description: {Action} with quality review
---

Use the {primary-agent} agent to {purpose}.

$ARGUMENTS

## Mode Detection

Determine mode from input path BEFORE invoking subagent:

| Input Pattern              | Mode        | Tell Subagent            |
|:---------------------------|:------------|:-------------------------|
| Path contains `{pattern1}` | **{Mode1}** | "{MODE1}: {instruction}" |
| Path contains `{pattern2}` | **{Mode2}** | "{MODE2}: {instruction}" |
| No file path provided      | **{Mode3}** | "{MODE3}: {instruction}" |

**CRITICAL**: State the mode explicitly in your Task tool prompt.

**Mode Differences**:
- **{Mode1}**: {What happens in this mode}
- **{Mode2}**: {What happens in this mode}
- **{Mode3}**: {What happens in this mode}

## Workflow

Due to Claude Code limitations (AskUserQuestion filtered from subagents, Task tool not available to subagents), follow this status-based flow:

### Step 1: Invoke {primary-agent}

Use the Task tool with the detected mode stated explicitly in the prompt.

### Step 2: Parse Status Block

**CRITICAL**: The agent MUST output a `STATUS:` block. Parse the status block from subagent output.

**If no STATUS block found** (agent output prose/summary instead):
- Resume the agent with: "Output STATUS: READY_FOR_REVIEW with the {artifact} content in ~~~markdown fences. Do NOT output prose summaries."
- The agent constraint requires STATUS block output — enforce this.

**If `STATUS: NEEDS_INPUT`**:
1. Parse questions from the `questions:` field
2. Use `AskUserQuestion` tool to present to user
3. Format answers: `ANSWERS: KEY=value, ...`
4. Resume subagent with `resume` parameter

**If `STATUS: READY_FOR_REVIEW`**:
1. Parse: `{artifact}_name`, `{artifact}_location`, and `content` (in `~~~markdown` fences)
2. Invoke **{quality-reviewer}**:
   ```
   Review this {artifact} definition:

   ~~~markdown
   {content from status block}
   ~~~
   ```
3. Parse review result:
   - **PASS**: Write {artifact} to `{location}/{name}.md`, report success
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
{primary-agent}
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
- Final success message when {artifact} is written (after PASS)
- Final failure message if quality review fails after 3 attempts
- Questions via `AskUserQuestion` when STATUS: NEEDS_INPUT

**Do NOT show to user**:
- Intermediate STATUS blocks or agent responses
- Quality review feedback (this is for the agent to fix)
- Prose summaries or explanations from the agent

The user should see a clean flow: questions (if any) → success/failure result.
````

---

## Frontmatter Reference

### Fields

| Field                      | Required    | Purpose                                       | Default                    |
|:---------------------------|:------------|:----------------------------------------------|:---------------------------|
| `allowed-tools`            | Conditional | Restrict which tools this command can use     | Inherits all               |
| `argument-hint`            | Recommended | Show expected args in autocomplete            | None                       |
| `description`              | Recommended | Shown in `/help`, enables `SlashCommand` tool | First line of content      |
| `model`                    | No          | Override model for this command               | Inherits from conversation |
| `disable-model-invocation` | No          | Prevent `SlashCommand` tool from calling this | `false`                    |

**Conditional**: `allowed-tools` is REQUIRED when using bash pre-execution (`!`backtick``).

### allowed-tools Patterns

```yaml
# Git operations only
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)

# Read-only analysis
allowed-tools: Read, Grep, Glob

# General bash (for script executors)
allowed-tools: Bash(bash:*)

# Multiple specific commands
allowed-tools: Bash(pwd:*), Bash(git:*)

# Full access (default — omit entirely)
# (no allowed-tools field)
```

### argument-hint Format (REQUIRED)

**Format**: `<option1|option2|...>` — Angle brackets with pipe-separated options.

**CRITICAL**: This format is REQUIRED for all commands that accept arguments. Square brackets `[...]` are ONLY for optional flags.

| Pattern                    | Use Case                           | Example Command  |
|:---------------------------|:-----------------------------------|:-----------------|
| `<file-path\|@file>`       | File path or inline content        | `review-command` |
| `<path\|description>`      | Path or free-form description      | `command`        |
| `<file-path>`              | Single file path (one option)      | `review-agent`   |
| `<task-description>`       | Free-form text input               | `wt`             |
| `[--flag]`                 | Optional flag (square brackets OK) | `clean-gone`     |
| `<type> <scope> [message]` | Multiple required + optional       | `commit`         |

**Rules**:
- Use `<...>` for required/expected arguments
- Use `|` to separate alternative input types
- Use `[...]` ONLY for truly optional flags (e.g., `[--verbose]`)
- Be descriptive: `<file-path|@file>` not `<input>`
- **If files accepted**: Include `@file` option — `@path` expands to file contents inline

**Anti-patterns**:
- ❌ `[file-or-description]` — Square brackets imply optional; use `<file|description>`
- ❌ `[command-path-or-agent-path]` — Too verbose; use `<path|description>`
- ❌ `[options]` — Vague; specify actual options like `[--verbose|--dry-run]`

### Model Selection

| Model    | Use Case                                  |
|:---------|:------------------------------------------|
| `haiku`  | Simple reviews, lightweight tasks         |
| `sonnet` | Default, balanced complexity (omit field) |
| `opus`   | Complex orchestration, deep analysis      |

---

## Section Guidelines

### Purpose Statement

**Format**: Single sentence, first line after frontmatter.

**Pattern**: `{Action verb} {what} {via/with/using} {method}.` or `Use the {agent} agent to {purpose}.`

**Good:**

```markdown
Use the session-manager agent to capture critical session context for continuity.
```

```markdown
Clean up local branches where the remote tracking branch has been deleted (marked as [gone]).
```

**Bad:**

```markdown
This command helps with cleaning up branches.
```

Problems: Starts with "This command", doesn't specify what it does.

---

### Constraints Section

**Purpose**: Define explicit behavioral guardrails and safety rules.

**Format**: Bullet list with strong keywords (NEVER, ALWAYS, ZERO tolerance).

**Good:**

```markdown
## Constraints

- **NEVER delete** the current branch — always skip and report in summary
- **NEVER remove** the main worktree — only remove feature/task worktrees
- **ALWAYS use** `bash -c '...'` format for atomic execution
- **ZERO tolerance** for accidental data loss — validate before destructive operations
```

**Bad:**

```markdown
## Constraints

- Be careful with branches
- Don't delete important things
```

Problems: Too vague, no strong keywords, no specific actions.

---

### Mode Detection Section

**Purpose**: Detect operational mode from input BEFORE invoking subagent.

**Format**: Decision table + explicit mode instructions.

**CRITICAL**: Always state the mode in the Task tool prompt.

**Good:**

```markdown
## Mode Detection

Determine mode from input path BEFORE invoking subagent:

| Input Pattern                   | Mode          | Tell Subagent           |
|:--------------------------------|:--------------|:------------------------|
| Path contains `.claude/agents/` | **Modify**    | "MODIFY: {path}"        |
| Path contains `prompts/`        | **Transform** | "TRANSFORM: {path}"     |
| No file path provided           | **Create**    | "CREATE: {description}" |

**CRITICAL**: State the mode explicitly in your Task tool prompt.
```

**Bad:**

```markdown
## Mode Detection

Figure out what mode based on the input.
```

Problems: No decision table, no explicit instructions.

---

### Context Section

**Purpose**: Pre-execute bash commands to gather runtime info.

**Format**: Labeled list with `!`backtick`` expressions.

**CRITICAL**: Requires `allowed-tools` with appropriate `Bash(...)` permissions.

**When to Include:**

| Context Type      | Bash Command                    | Include When              |
|:------------------|:--------------------------------|:--------------------------|
| Working directory | `pwd`                           | Path-sensitive operations |
| Git status        | `git status --short`            | File change workflows     |
| Current branch    | `git branch --show-current`     | Branch-aware operations   |
| Recent commits    | `git log --oneline -5`          | Commit message generation |
| Staged changes    | `git diff --cached --stat`      | Pre-commit workflows      |
| Worktrees         | `git worktree list`             | Worktree operations       |
| Repository root   | `git rev-parse --show-toplevel` | Path resolution           |

**Good:**

```markdown
## Context

- Repository root: !`git rev-parse --show-toplevel`
- Current branch: !`git branch --show-current`
- Worktrees: !`git worktree list`
```

**Bad:**

```markdown
## Context

Get the current git info before running.
```

Problems: No actual bash commands, just description.

---

### Workflow Section

**Purpose**: Step-by-step execution flow with STATUS handling.

**Format**: Numbered steps with specific actions.

**Mandatory Elements for Subagent Invokers:**

1. Task tool invocation with explicit mode/context
2. STATUS block parsing with all relevant cases
3. `AskUserQuestion` for `NEEDS_INPUT`
4. Repeat loop until `COMPLETED`
5. CRITICAL warning about `AskUserQuestion`

**Good:**

```markdown
## Workflow

1. **Invoke {agent-name}** with the Task tool
   - Include: `$ARGUMENTS`
   - Include context from above
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report results to user
3. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
```

**Bad:**

```markdown
## Workflow

1. Call the agent
2. Show results
```

Problems: No STATUS handling, no tool instructions.

---

### Expected Questions Section

**Purpose**: Document what questions the subagent may ask via `STATUS: NEEDS_INPUT`.

**Format**: Bullet list with KEY, description, and options.

**Good:**

```markdown
## Expected Questions

The agent may request input for:

- **TYPE**: Branch type selection when task description is ambiguous (feat|fix|chore|docs)
- **ACTION**: How to handle uncommitted changes (commit|stash|abort)
- **REMOTE**: Which remote to use if multiple exist
```

**Bad:**

```markdown
## Expected Questions

The agent might ask some questions.
```

Problems: No specific keys, no options listed.

---

## STATUS Block Handling

### STATUS: NEEDS_INPUT

**Command action**: Parse questions → `AskUserQuestion` tool → Resume with `ANSWERS:`

```markdown
**If `STATUS: NEEDS_INPUT`**:
1. Parse questions from the `questions:` field
2. Use `AskUserQuestion` tool to present to user
3. Format answers: `ANSWERS: KEY=value, KEY=value`
4. Resume subagent with `resume` parameter
```

### STATUS: COMPLETED

**Command action**: Report success → Done

```markdown
**If `STATUS: COMPLETED`**:
- Report results to user
- Done
```

### STATUS: READY_FOR_REVIEW

**Command action**: Invoke reviewer → Write if PASS → Resume with feedback if not

```markdown
**If `STATUS: READY_FOR_REVIEW`**:
1. Parse: `artifact_name`, `artifact_location`, `content`
2. Invoke **{quality-reviewer}** with embedded content
3. If PASS: Write to final location, report success
4. If WARN/FAIL: Resume with `REVIEW_FEEDBACK:` (max 3x)
```

### STATUS: READY_FOR_NEXT

**Command action**: Invoke next agent with context

```markdown
**If `STATUS: READY_FOR_NEXT`**:
1. Parse: `next_agent`, `context`
2. Invoke specified agent with context
3. Continue STATUS handling
```

---

## Anti-Patterns

### Avoid These in Commands

| Anti-Pattern                        | Problem                           | Fix                                   |
|:------------------------------------|:----------------------------------|:--------------------------------------|
| `[file-or-description]` hint format | Square brackets imply optional    | Use `<file\|description>` format      |
| Missing `@file` in hint             | Users don't know inline works     | Add `@file` option if files accepted  |
| Missing `description`               | Breaks `SlashCommand` tool        | Add description to frontmatter        |
| Missing STATUS workflow             | Subagent gets stuck waiting       | Add full STATUS handling              |
| Printing questions as text          | User misses interactive UI        | Use `AskUserQuestion` tool            |
| Hardcoded paths                     | Not portable                      | Use `$ARGUMENTS` or `@path`           |
| Assuming subagent mode              | Wrong mode selected               | Detect from input, state explicitly   |
| Missing `allowed-tools`             | Bash pre-exec fails               | Add required `Bash(...)` permissions  |
| Passing path instead of content     | Reviewer hallucinates             | Read file, pass actual content        |
| Missing CRITICAL warning            | Executor forgets tool requirement | Always include for `NEEDS_INPUT`      |
| No mode detection table             | Ambiguous mode selection          | Add decision table with patterns      |
| Showing intermediate STATUS         | User sees internal details        | Filter output, show only final result |

### Common Mistakes by Command Type

**Script Executors:**

- Missing `allowed-tools: Bash(bash:*)`
- Scripts not wrapped in `bash -c '...'`
- Not validating arguments before execution

**Simple Invokers:**

- Missing CRITICAL warning for `AskUserQuestion`
- Not documenting expected questions
- Incomplete STATUS handling (missing cases)

**Content Passers:**

- Passing file path instead of content
- Not handling inline vs path input
- Missing file read verification

**Full Orchestrators:**

- Missing quality review loop
- No max retry limit
- Not filtering user output
- Missing no-STATUS-block fallback

---

## Quality Checklist

Use this checklist before finalizing any command.

### Frontmatter

- [ ] `description`: Present, ≤10 words, clear action
- [ ] `argument-hint`: Present if command takes arguments, uses `<option|option>` format
- [ ] `argument-hint`: If files accepted, includes `@file` option
- [ ] `allowed-tools`: Present if using bash pre-execution
- [ ] `model`: Set appropriately (haiku for simple, omit for default)

### Structure

- [ ] Purpose statement: First line, specific action
- [ ] `$ARGUMENTS`: Present if command takes arguments
- [ ] Correct section order: Frontmatter → Purpose → $ARGUMENTS → Constraints → Mode Detection → Context → Workflow

### Subagent Commands

- [ ] Mode Detection: Present if target agent has multiple modes
- [ ] Workflow: Full STATUS handling for all relevant cases
- [ ] CRITICAL warning: Present for `NEEDS_INPUT` handling
- [ ] Expected Questions: Documented if agent uses `STATUS: NEEDS_INPUT`

### Quality Review Commands (Full Orchestrator)

- [ ] Quality Fix Loop: Present with max 3 attempts
- [ ] No-STATUS fallback: Handles missing STATUS block
- [ ] Output to User: Filters internal details
- [ ] Status Flow: Visual diagram present

### Script Executors

- [ ] `allowed-tools`: Includes required bash permissions
- [ ] Scripts: Wrapped in `bash -c '...'`
- [ ] Flags: Documented if command accepts flags
- [ ] Safety: Notes include caveats and warnings

---

## Version History

| Date       | Version | Changes                                          |
|:-----------|:--------|:-------------------------------------------------|
| 2025-12-12 | 1.2     | Make Constraints section required (not optional) |
| 2025-12-12 | 1.1     | Replace "When to Use" with "Constraints" section |
| 2025-12-12 | 1.0     | Initial template                                 |