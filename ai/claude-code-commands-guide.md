# Claude Code Slash Commands Guide

Comprehensive guide for creating, managing, and optimizing Claude Code slash commands.

---

## 1. Fundamentals

### What Are Slash Commands?

User-invoked shortcuts stored as Markdown files that Claude Code executes when you type `/command-name`. They provide:

- **Quick access** — Frequently used prompts as simple commands
- **Parameterization** — Pass arguments via `$ARGUMENTS` or positional `$1`, `$2`
- **Dynamic context** — Pre-execute bash commands to gather runtime info
- **Subagent orchestration** — Coordinate complex multi-agent workflows

Source: [Slash Commands Docs][slash-docs]

### File Locations

```
.claude/commands/         # Project-level (shared via git)
~/.claude/commands/       # User-level (personal, all projects)
```

Project commands override user commands when names conflict. Commands show their scope in `/help`:
- `(project)` — from `.claude/commands/`
- `(user)` — from `~/.claude/commands/`

### Basic Syntax

```
/<command-name> [arguments]
```

Example: `/review src/main.ts --strict`

---

## 2. File Format

### Minimal Command

```markdown
Review the code for quality issues.

$ARGUMENTS
```

### Full Command with Frontmatter

```markdown
---
allowed-tools: Bash(git:*), Read, Write
argument-hint: <file-path|@file>
description: Review code for quality issues
model: haiku
disable-model-invocation: false
---

Review the following code for quality, security, and maintainability issues.

$ARGUMENTS

Focus on:
- Code clarity and readability
- Security vulnerabilities
- Performance considerations
```

### Section Order

Sections MUST appear in this order (omit sections that don't apply):

1. **Frontmatter** (`---`)
2. **Purpose statement** (one line)
3. **`$ARGUMENTS`**
4. **Constraints** (required — behavioral guardrails)
5. **Mode Detection** (if subagent has multiple modes)
6. **Context** (if runtime info needed)
7. **Workflow** (required for subagent-invoking commands)

---

## 3. Frontmatter Reference

| Field                      | Required    | Purpose                                       | Default                    |
|:---------------------------|:------------|:----------------------------------------------|:---------------------------|
| `allowed-tools`            | No          | Restrict which tools this command can use     | Inherits all               |
| `argument-hint`            | If args     | Show expected args in autocomplete            | None                       |
| `description`              | Recommended | Shown in `/help`, enables `SlashCommand` tool | First line of content      |
| `model`                    | No          | Override model for this command               | Inherits from conversation |
| `disable-model-invocation` | No          | Prevent `SlashCommand` tool from calling this | `false`                    |

### argument-hint Format (REQUIRED)

**Format**: `<option1|option2|...>` — Angle brackets with pipe-separated options.

Commands that accept arguments MUST use this format. Square brackets `[...]` are ONLY for optional flags.

| Pattern                    | Use Case                          |
|:---------------------------|:----------------------------------|
| `<file-path\|@file>`       | File path or inline content       |
| `<path\|description>`      | Path or free-form description     |
| `<file-path>`              | Single file path                  |
| `[--flag]`                 | Optional flag only                |

**Rules**:
- Use `<...>` for required/expected arguments
- Use `|` to separate alternative input types
- **If files accepted**: Include `@file` option (`@path` expands to contents)
- Use `[...]` ONLY for truly optional flags

**Anti-patterns**:
- ❌ `[file-or-description]` → Use `<file|description>`
- ❌ `[options]` → Specify actual options

### Tool Restriction Examples

```yaml
#file: noinspection YAMLDuplicatedKeys
# Only git operations
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)

# Read-only analysis
allowed-tools: Read, Grep, Glob

# Full access (default)
# (omit allowed-tools entirely)
```

---

## 4. Arguments and Parameters

### `$ARGUMENTS` — All Arguments

Captures everything passed after the command name:

```markdown
Fix the issue described below:

$ARGUMENTS
```

```bash
/fix-issue The button doesn't respond to clicks on mobile
# $ARGUMENTS = "The button does not respond to clicks on mobile"
```

### `$1`, `$2`, etc. — Positional Arguments

Access specific arguments by position (like shell scripts):

```markdown
---
argument-hint: [file] [priority] [assignee]
---

Review $1 with priority $2 and assign to $3.
```

```bash
/review-file src/main.ts high alice
# $1 = "src/main.ts", $2 = "high", $3 = "alice"
```

### When to Use Each

| Pattern      | Use When                             |
|:-------------|:-------------------------------------|
| `$ARGUMENTS` | Flexible, free-form input            |
| `$1`, `$2`   | Structured input with specific roles |
| Both         | Structured prefix + free-form suffix |

---

## 5. Dynamic Features

### Bash Pre-Execution (`!`backtick``)

Execute bash commands before the prompt runs:

```markdown
---
allowed-tools: Bash(git:*)
---

## Context

- Current branch: !`git branch --show-current`
- Staged changes: !`git diff --cached --stat`
- Recent commits: !`git log --oneline -5`

## Task

Create a commit message for the staged changes.
```

**Requirements:**
- Must include `allowed-tools` with appropriate `Bash` permissions
- Command output is inserted where the backtick expression appears

### When to Include Context Section

Use this decision table to determine which context types to include:

| Context Type      | Bash Command                | Include When                   |
|:------------------|:----------------------------|:-------------------------------|
| Working directory | `pwd`                       | Path-sensitive operations      |
| Git status        | `git status --short`        | File change workflows          |
| Current branch    | `git branch --show-current` | Branch-aware operations        |
| Recent commits    | `git log --oneline -5`      | Commit message generation      |
| Staged changes    | `git diff --cached --stat`  | Pre-commit workflows           |
| Unstaged diff     | `git diff --stat`           | Code review workflows          |
| Environment       | `printenv \| grep PATTERN`  | Environment-sensitive commands |

**Rule**: If the subagent or task would benefit from knowing current state, include the relevant context.

### File Inclusion (`@path`)

Include file contents directly:

```markdown
Review the implementation in @src/utils/helpers.js

Compare with the tests in @tests/helpers.test.js
```

**Notes:**
- Path is relative to project root
- File content is inserted where `@path` appears
- Works with any text file

---

## 6. Commands vs Subagents

| Aspect          | Slash Commands               | Subagents                |
|:----------------|:-----------------------------|:-------------------------|
| **Location**    | `.claude/commands/`          | `.claude/agents/`        |
| **Invocation**  | Explicit (`/command`)        | Automatic or explicit    |
| **Context**     | Inline (main conversation)   | Isolated window          |
| **Parameters**  | `$ARGUMENTS`, `$1`, `$2`     | Via Task tool prompt     |
| **Persistence** | Results in main context      | Only summary returned    |
| **Use case**    | Quick prompts, orchestration | Complex autonomous tasks |

### When to Use Commands

- Frequently used prompts
- Simple, well-defined tasks
- Orchestrating subagents
- Tasks needing conversation context

### When to Use Subagents

- Complex investigation or analysis
- Tasks that would pollute main context
- Parallel execution needed
- Specialized tool access

---

## 7. Command + Subagent Orchestration

Commands excel at orchestrating subagents with mode detection and user interaction handling.

### Basic Pattern

```markdown
---
description: Analyze codebase architecture
argument-hint: [path-or-question]
---

Use the code-analyzer agent.

$ARGUMENTS

## Workflow

1. **Invoke code-analyzer** with the Task tool
   - Include: `$ARGUMENTS`
2. **Report findings** to user
```

### Mode Detection Pattern

For subagents with multiple modes of operation:

```markdown
---
description: Create, modify, or transform subagents
argument-hint: [file-or-description]
---

Use the subagent-manager agent.

$ARGUMENTS

## Mode Detection

Determine mode from input BEFORE invoking subagent:

| Input Pattern             | Mode          | Tell Subagent                     |
|:--------------------------|:--------------|:----------------------------------|
| Path in `prompts/`        | **Transform** | "TRANSFORM this prompt: {path}"   |
| Path in `.claude/agents/` | **Modify**    | "MODIFY this agent: {path}"       |
| No file provided          | **Create**    | "CREATE new agent: {description}" |

**CRITICAL**: State the mode explicitly in your Task tool prompt.
```

### User Input Relay Pattern (STATUS: NEEDS_INPUT)

Due to Claude Code limitation ([GitHub Issue #12890][gh-12890]), subagents cannot use `AskUserQuestion` directly. Commands must relay using the status-based pattern:

```markdown
## Workflow

1. **Invoke {agent-name}** with the Task tool
   - Include full user request: `$ARGUMENTS`
   - State detected mode explicitly
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report success to user
   - `STATUS: READY_FOR_NEXT` → Invoke specified next agent
3. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: You MUST use `AskUserQuestion` tool. Do NOT print questions as text.
```

### Status-Based Handoff Pattern (Recommended)

The most reliable pattern for multi-agent workflows. Subagents output structured status blocks that commands parse to chain agents.

Sources: [PubNub Best Practices][pubnub], [wshobson/agents][wshobson], [Delegation Setup Gist][delegation-gist]

#### Status Block Format

Subagents end their output with:

```
STATUS: {NEEDS_INPUT|COMPLETED|READY_FOR_NEXT|READY_FOR_REVIEW}
key1: value1
key2: value2
summary: one-line description
```

For `NEEDS_INPUT`, include a questions block:

```
STATUS: NEEDS_INPUT
questions:
  1. KEY: Question? [option1|option2 (recommended)|option3]
  2. KEY: Another question? [yes|no]
summary: awaiting {what user needs to provide}
```

For `READY_FOR_REVIEW`, include embedded content:

```
STATUS: READY_FOR_REVIEW
artifact_name: {name}
artifact_location: {path}
content:
~~~markdown
{full content here}
~~~
summary: Ready for quality review
```

**Why `READY_FOR_REVIEW`?** Subagents cannot spawn other subagents (Task tool not available). Commands must orchestrate quality review. See [Subagents Guide §13.3](claude-code-subagents-guide.md#133-task-tool-limitation).

#### Command Implementation

```markdown
## Workflow

1. **Invoke first-agent** with Task tool
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion`, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report success, done
   - `STATUS: READY_FOR_NEXT` → Invoke next agent with provided context
   - `STATUS: READY_FOR_REVIEW` → Invoke quality reviewer, write if passed, resume with feedback if not
3. **Repeat** until final `STATUS: COMPLETED`
```

#### Example: Agent Chain with Quality Review

```
subagent-manager
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
└── STATUS: READY_FOR_REVIEW → invoke quality-reviewer
    ├── Grade A → write file → check slash_command
    │   ├── yes → invoke command-manager → quality review → write → done
    │   └── no → done
    └── Grade < A → resume with REVIEW_FEEDBACK (max 3x)
```

#### Full Example Command

```markdown
---
argument-hint: [file-or-description]
description: Create subagent with optional slash command
---

Use subagent-manager.

$ARGUMENTS

## Workflow

1. **Invoke subagent-manager** with Task tool, stating mode explicitly
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion`, resume with `ANSWERS:`
   - `STATUS: READY_FOR_REVIEW` → Continue to step 3
3. **If `STATUS: READY_FOR_REVIEW`**:
   - Parse: `agent_name`, `agent_location`, `slash_command`, `content`
   - Invoke **subagent-quality-reviewer** with embedded content
   - If grade < A: Resume subagent-manager with `REVIEW_FEEDBACK:` (max 3 attempts)
   - If grade A: Write agent to `{agent_location}/{agent_name}.md`
4. **If `slash_command: yes: /command-name`**:
   - Invoke **command-manager** for the agent
   - Handle `STATUS: READY_FOR_REVIEW` from command-manager (same quality review flow)
   - Report both agent and command to user
5. **If `slash_command: no`**:
   - Report success with agent path
```

This pattern is more reliable than ad-hoc delegation blocks because:
- Status format is standardized and parseable
- Commands know exactly what to expect
- Commands orchestrate quality review (subagents cannot spawn subagents)
- Easy to add new status types for complex workflows

---

## 8. Namespacing

Use subdirectories to organize related commands:

```
.claude/commands/
├── git/
│   ├── commit.md      → /commit (project:git)
│   ├── pr.md          → /pr (project:git)
│   └── review.md      → /review (project:git)
├── test/
│   ├── run.md         → /run (project:test)
│   └── coverage.md    → /coverage (project:test)
└── deploy.md          → /deploy (project)
```

**Priority**: Commands in different subdirectories can share names. Subdirectory is shown in parentheses.

---

## 9. SlashCommand Tool

Claude can programmatically execute custom commands via the `SlashCommand` tool.

### Requirements

- Command must have `description` field in frontmatter
- `disable-model-invocation` must not be `true`
- Not in deny rules via `/permissions`

### Permission Rules

```
SlashCommand:/commit          # Exact match
SlashCommand:/review-pr:*     # Prefix match with any arguments
```

### Character Budget

- Default: 15,000 characters for all command descriptions
- Override: `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable

---

## 10. Examples

### Git Commit Command

````markdown
---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
argument-hint: [message]
description: Create a git commit with staged changes
---

## Context

- Status: !`git status --short`
- Staged: !`git diff --cached --stat`
- Recent: !`git log --oneline -5`

## Task

Create a commit with message: $ARGUMENTS

Follow conventional commits format. Ensure message is clear and concise.
````

### Code Review Command

````markdown
---
argument-hint: [file-or-directory]
description: Review code for quality issues
---

Use the code-reviewer agent to analyze the code.

$ARGUMENTS

## Workflow

1. **Invoke code-reviewer** with Task tool
   - Include: "Review $ARGUMENTS for quality, security, and maintainability"
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion`, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report findings organized by severity
3. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
````

### Subagent Orchestration Command

```markdown
---
argument-hint: [file-or-description]
description: Create, modify, or transform subagent definitions
---

Use the subagent-manager agent.

$ARGUMENTS

## Mode Detection

| Input Pattern             | Mode          | Tell Subagent           |
|:--------------------------|:--------------|:------------------------|
| Path in `prompts/`        | **Transform** | "TRANSFORM: {path}"     |
| Path in `.claude/agents/` | **Modify**    | "MODIFY: {path}"        |
| No file                   | **Create**    | "CREATE: {description}" |

## Workflow

1. **Invoke subagent-manager** with Task tool, stating mode
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion`, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report success, done
   - `STATUS: READY_FOR_COMMAND` → Continue to step 3
3. **If `STATUS: READY_FOR_COMMAND`**:
   - Parse: `agent_path`, `command_name`, `location`
   - Invoke **command-manager** with context
   - Handle any `STATUS: NEEDS_INPUT`
4. **Report success** when final `STATUS: COMPLETED`
```

---

## 11. Quality Review Integration

The `command-manager` agent includes automatic quality review before saving commands:

### Quality Workflow

```
Construction → Write to ~/.claude/tmp/{name}.md
            → Invoke command-reviewer
            → Status != PASS? → Fix issues → Re-review (max 3x)
            → PASS? → Move to final location → STATUS: COMPLETED
            → 3 failures? → STATUS: QUALITY_FAILED
```

### STATUS: QUALITY_FAILED

If automatic fixes fail after 3 attempts:

```
STATUS: QUALITY_FAILED
attempts: 3
final_status: {WARN|FAIL}
staging_path: ~/.claude/tmp/{command-name}.md
remaining_issues:
{list of unfixed issues}
summary: Unable to achieve PASS after 3 attempts. Manual intervention required.
```

Commands must handle this status:

```markdown
**If `STATUS: QUALITY_FAILED`**:
- Quality review failed after 3 automatic fix attempts
- Present `remaining_issues:` to user
- Report that manual intervention is required
```

### Setup Required

See [Subagents Guide §10](claude-code-subagents-guide.md#10-quality-review-integration) for `~/.claude/tmp/` setup.

---

## 12. Mandatory Requirements

Commands that invoke subagents MUST include these elements:

### STATUS Handling Workflow (Required)

Every command that invokes a subagent MUST include the full STATUS handling workflow:

```markdown
## Workflow

1. **Invoke {agent-name}** with the Task tool
   - Include full user request: `$ARGUMENTS`
   - State detected mode explicitly (if applicable)
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report success to user
   - `STATUS: READY_FOR_NEXT` → Invoke specified next agent
3. **Repeat** until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
```

**Why mandatory**: Production-quality agents use `STATUS: NEEDS_INPUT` for uncertainty handling. Without this workflow, users won't see the interactive UI and agents will be stuck waiting.

### Mode Detection (Conditional)

If the target subagent has multiple modes of operation, MUST include Mode Detection section with decision table.

### Context + allowed-tools (Conditional)

If using bash pre-execution (`!`backtick``), MUST include `allowed-tools` with appropriate `Bash(...)` permissions.

### Validation Checklist

Before finalizing a command, verify:

- [ ] If invoking subagent: Full STATUS handling workflow present
- [ ] If invoking subagent: CRITICAL warning about `AskUserQuestion` present
- [ ] If agent has modes: Mode Detection section present
- [ ] If using bash pre-exec: `allowed-tools` includes required permissions

---

## 13. Best Practices

### Design

| Practice                             | Why                                     |
|:-------------------------------------|:----------------------------------------|
| Clear descriptions                   | Enables `/help` and `SlashCommand` tool |
| Specific `argument-hint`             | Helps users understand expected input   |
| Minimal `allowed-tools`              | Security through least privilege        |
| Mode detection for multi-mode agents | Prevents ambiguity                      |

### Common Patterns

| Pattern                     | Use Case                          |
|:----------------------------|:----------------------------------|
| Context pre-population      | Gather runtime info before task   |
| Mode detection table        | Multi-mode subagent orchestration |
| `STATUS: NEEDS_INPUT` relay | User interaction via subagents    |
| Status-based handoff        | Chained subagent workflows        |

### Anti-Patterns

- Missing `description` — breaks `SlashCommand` tool
- Hardcoded paths — use `$ARGUMENTS` or `@path`
- Printing questions as text — use `AskUserQuestion` tool
- Assuming subagent mode — always detect from input
- **Missing STATUS workflow** — subagent gets stuck waiting for user input

---

## 14. Debugging

| Issue                     | Cause                    | Fix                                   |
|:--------------------------|:-------------------------|:--------------------------------------|
| Command not in `/help`    | Missing or empty file    | Check file exists in correct location |
| Arguments not passed      | Missing `$ARGUMENTS`     | Add `$ARGUMENTS` to command content   |
| Bash pre-exec fails       | Missing `allowed-tools`  | Add `Bash(command:*)` to frontmatter  |
| SlashCommand can't invoke | Missing `description`    | Add `description` to frontmatter      |
| User questions not shown  | Printing instead of tool | Use `AskUserQuestion` tool            |

---

## 15. Community Resources

### Command Collections

| Repository                        | Commands | Focus                      |
|:----------------------------------|:---------|:---------------------------|
| [wshobson/commands][wshobson-cmd] | 57       | Multi-agent orchestration  |
| [Claude-Command-Suite][cmd-suite] | 148+     | Full development lifecycle |
| [awesome-claude-code][awesome-cc] | Curated  | Best practices examples    |

### Official Documentation

- [Slash Commands Docs][slash-docs]
- [Claude Code Best Practices][bp]

---

## Sources

| Key                 | Source                                                           |
|:--------------------|:-----------------------------------------------------------------|
| `[slash-docs]`      | [Claude Code Slash Commands Documentation][slash-docs]           |
| `[bp]`              | [Claude Code Best Practices][bp]                                 |
| `[wshobson-cmd]`    | [wshobson/commands][wshobson-cmd]                                |
| `[cmd-suite]`       | [Claude-Command-Suite][cmd-suite]                                |
| `[awesome-cc]`      | [awesome-claude-code][awesome-cc]                                |
| `[pubnub]`          | [PubNub Best Practices for Subagents][pubnub]                    |
| `[wshobson]`        | [wshobson/agents - Multi-agent orchestration][wshobson]          |
| `[delegation-gist]` | [Claude Code Sub-Agent Delegation Setup][delegation-gist]        |
| `[gh-12890]`        | [AskUserQuestion Bug - GitHub Issue #12890][gh-12890]            |
| `[gh-1770]`         | [Parent-Child Agent Communication - GitHub Issue #1770][gh-1770] |
| `[gh-5812]`         | [Context Bridging Between Agents - GitHub Issue #5812][gh-5812]  |
| `[agent-design]`    | [Agent Design Lessons from Claude Code][agent-design]            |

[slash-docs]: https://code.claude.com/docs/en/slash-commands
[bp]: https://www.anthropic.com/engineering/claude-code-best-practices
[wshobson-cmd]: https://github.com/wshobson/commands
[cmd-suite]: https://github.com/qdhenry/Claude-Command-Suite
[awesome-cc]: https://github.com/hesreallyhim/awesome-claude-code
[pubnub]: https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/
[wshobson]: https://github.com/wshobson/agents
[delegation-gist]: https://gist.github.com/tomas-rampas/a79213bb4cf59722e45eab7aa45f155c
[gh-12890]: https://github.com/anthropics/claude-code/issues/12890
[gh-1770]: https://github.com/anthropics/claude-code/issues/1770
[gh-5812]: https://github.com/anthropics/claude-code/issues/5812
[agent-design]: https://jannesklaas.github.io/ai/2025/07/20/claude-code-agent-design.html
