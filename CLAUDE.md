# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Knowledge base and research artifacts for investigations, experiments, and learnings. Not a production codebase—primarily documentation and prompt templates.

## Structure

### Specifications & Guides

- `ai/prompt-engineering-spec.md` - Best practices for writing AI agent prompts (v1.0.1)
- `ai/troubleshooting-doc-spec.md` - Guidelines for writing troubleshooting documentation (v1.1)
- `ai/claude-code-subagents-guide.md` - Comprehensive guide for Claude Code subagents
- `ai/claude-code-commands-guide.md` - Comprehensive guide for Claude Code slash commands
- `ai/claude-code-settings-merge.md` - How Claude Code merges settings from multiple files
- `ai/claude-code-thinking-modes.md` - Extended thinking modes and keyword usage

### Examples

- `ai/claude-code-wrong-shell.md` - Example troubleshooting doc (follows troubleshooting-doc-spec)

### Prompt Templates

- `ai/prompts/` - Reusable AI agent prompt templates
  - `_template.md` - Blank template for creating new prompts
  - `prompt-author-agent.md` - Agent for creating/refining prompts (follows spec)
  - `planning-agent.md` - Planning agent for creating implementation specs
  - `executor-agent.md` - Executor agent for single-task implementation
  - `session-manager.md` - Agent for capturing session context for handover
  - `worktree-manager.md` - Agent for creating git worktrees with context transfer

### Claude Code Configuration

- `.claude/agents/subagent-manager.md` - Meta-agent for creating/modifying/transforming subagents
- `.claude/agents/command-manager.md` - Creates slash commands for subagents and workflows
- `.claude/commands/subagent.md` - Slash command to invoke subagent-manager (`/subagent`)
- `.claude/commands/command.md` - Slash command to invoke command-manager (`/command`)

### Working Directories

- `tmp/` - Temporary files and working directories (gitignored)

## Agent Workflow System

This repository contains a two-agent workflow system for structured development:

### Planning Agent (`ai/prompts/planning-agent.md`)

- **Purpose**: Investigate codebase and create comprehensive implementation plans
- **Output**: `tmp/tasks/YYMMDD-{task-slug}/implementation_plan.md`
- **Constraints**: Never implements changes, only plans
- **Key sections in output**:
  - Workflow Commands (lint, format, test)
  - Progress Tracker (checklist with NEXT pointer)
  - Technical Context (architecture, rationale, file paths)
  - Execution Plan (session-sized phases with 3-7 steps each)

### Executor Agent (`ai/prompts/executor-agent.md`)

- **Purpose**: Execute ONE task from implementation spec, then hand off
- **Constraints**: Single task only, stops at session boundary
- **Workflow**:
  1. Branch setup (confirms with user if unclear)
  2. Load spec and identify NEXT task
  3. Implement code changes
  4. **Update Progress Tracker** (mark done, update NEXT) — BEFORE verification
  5. Verify (lint/test)
  6. Knowledge capture (if applicable)
  7. Commit implementation changes only
- **Progress update ordering**: Progress reflects work done, not verification status—update immediately after implementation, before lint/test/commit
- **Knowledge capture**: Updates CLAUDE.md or `.claude/session-{topic}.md` for insights
- **Commit/PR style**: Focus on WHAT/WHY, exclude phase numbers and task completion status

## Key Principles

- Task directory naming: `tmp/tasks/YYMMDD-{task-slug}/`
- Progress tracking: In-spec Progress Tracker with NEXT pointer
- Session boundaries: One task per executor session
- Context preservation: Specs must be self-contained for fresh sessions
- Blockers: Stop and ask user rather than assuming

## Subagent Patterns

### Subagent Limitations

Two key limitations affect subagent architecture:

1. **AskUserQuestion filtered**: Tool not available to subagents ([GitHub Issue #12890](https://github.com/anthropics/claude-code/issues/12890))
2. **Task tool unavailable**: Subagents cannot spawn other subagents

**Implication**: All user interaction and agent orchestration must happen at the parent level (commands or main conversation).

### STATUS: NEEDS_INPUT Relay Pattern

For user input, use status-based relay:

1. **Subagent** outputs `STATUS: NEEDS_INPUT` block with questions
2. **Parent command** parses questions, uses `AskUserQuestion` tool
3. **Parent** resumes subagent with `ANSWERS: KEY1=value, KEY2=value`

```
STATUS: NEEDS_INPUT
questions:
  1. KEY: Question? [option1|option2 (recommended)]
summary: awaiting {what}
```

### STATUS: READY_FOR_REVIEW Relay Pattern

For quality review (subagents cannot invoke quality reviewers):

1. **Subagent** outputs `STATUS: READY_FOR_REVIEW` with embedded content
2. **Parent command** invokes quality reviewer with content
3. **If pass**: Parent writes file to final location
4. **If fail**: Parent resumes subagent with `REVIEW_FEEDBACK:` (max 3 attempts)

```
STATUS: READY_FOR_REVIEW
agent_name: {name}
agent_location: {.claude/agents/ or ~/.claude/agents/}
slash_command: {yes: /command-name | no}
content:
~~~markdown
{full agent definition}
~~~
summary: Agent ready for quality review
```

### Mandatory Agent Requirements

Every production-quality subagent MUST include:

1. **Uncertainty in Constraints**: `**NEVER assume** — output STATUS: NEEDS_INPUT if unclear`
2. **Uncertainty in Edge Cases**: `**Uncertainty**: Output STATUS: NEEDS_INPUT — never guess`
3. **Strong keywords**: NEVER, ALWAYS, ZERO, MAXIMUM in constraints
4. **Done When checklist**: Clear completion criteria

### Mandatory Command Requirements

Commands invoking subagents MUST include:

1. **Full STATUS workflow** with all cases (NEEDS_INPUT, READY_FOR_REVIEW, COMPLETED)
2. **Quality review orchestration** for creator agents (parent invokes reviewer)
3. **CRITICAL warning** about using `AskUserQuestion` tool
4. **Mode detection** if agent has multiple modes

## Prompt Authoring

When creating or modifying AI agent prompts:

1. **Reference spec**: Follow `ai/prompt-engineering-spec.md` for all guidelines
2. **Use template**: Start from `ai/prompts/_template.md` for new prompts
3. **Or use agent**: Copy `ai/prompts/prompt-author-agent.md` with task description

### Quick Reference (from spec)

**Structure order**: Role → Constraints → Success Criteria → Edge Cases → Workflow → Output

**Principles**:

- Explicit > Implicit (state everything)
- Show, don't tell (examples over descriptions)
- One task per prompt section
- Handle edge cases explicitly
- Test against diverse inputs

**Anti-patterns**:

- Vague instructions, negative framing, assumption of context
- Edge case stuffing (use examples instead)
- Placeholders in final output
