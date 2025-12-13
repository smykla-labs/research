# Claude Code Subagents Guide

Comprehensive guide for creating, managing, and optimizing Claude Code subagents.

---

## 1. Fundamentals

### What Are Subagents?

Specialized AI assistants with:

- **Isolated context window** — prevents pollution of main conversation ([Claude Code Best Practices][bp])
- **Custom system prompt** — domain-specific instructions ([Subagents Docs][docs])
- **Scoped tool access** — least-privilege permissions ([PubNub Best Practices][pubnub])
- **Model selection** — optimize cost/capability tradeoff ([Medianeth 2025 Guide][medianeth])

> "Each subagent operates in its own context, preventing pollution of the main conversation and keeping it focused on high-level objectives." — [PubNub Best Practices][pubnub]

### File Locations

```
.claude/agents/         # Project-level (higher priority)
~/.claude/agents/       # User-level (global)
```

Project agents override user agents when names conflict. ([Subagents Docs][docs])

### File Format

```yaml
---
name: agent-name
description: When this agent should be used
tools: Read, Grep, Glob           # Optional - inherits all if omitted
model: sonnet                     # Optional - sonnet|opus|haiku|inherit
permissionMode: default           # Optional
---

System prompt content here...
```

> "Each subagent is defined in a Markdown file with a specific structure including name, description, tools, model, and permissionMode fields in the frontmatter." — [Subagents Docs][docs]

---

## 2. Frontmatter Reference

| Field            | Required | Values                                        | Notes                                    |
|------------------|----------|-----------------------------------------------|------------------------------------------|
| `name`           | Yes      | lowercase, hyphens                            | Unique identifier                        |
| `description`    | Yes      | Natural language                              | Determines when Claude invokes the agent |
| `tools`          | No       | Comma-separated tool names                    | Omit to inherit all tools                |
| `model`          | No       | `sonnet`, `opus`, `haiku`, `inherit`          | Default: `sonnet`                        |
| `permissionMode` | No       | `default`, `acceptEdits`, `bypassPermissions` | Controls approval flow                   |

Source: [Subagents Docs][docs]

### Available Tools

```
Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, AskUserQuestion*
```

Plus any MCP tools registered in settings. ([Subagents Docs][docs])

**\*AskUserQuestion Limitation**: This tool is filtered out at the system level when spawning subagents ([GitHub Issue #12890][gh-12890]). Even if listed in `tools:`, subagents cannot use it. See §11 for workaround.

---

## 3. Tool Selection by Agent Type

| Agent Role        | Recommended Tools                       | Rationale           |
|-------------------|-----------------------------------------|---------------------|
| **Reviewer**      | `Read, Grep, Glob`                      | Read-only analysis  |
| **Researcher**    | `Read, Grep, Glob, WebFetch, WebSearch` | Gather information  |
| **Planner**       | `Read, Grep, Glob, Bash, Write`         | Investigate and doc |
| **Implementer**   | `Read, Edit, Write, Bash, Grep, Glob`   | Create and execute  |
| **Documentation** | `Read, Write, Edit, Glob, WebFetch`     | Research and write  |

Source: [awesome-claude-code-subagents][awesome]

> "Read-only agents (reviewers, auditors): Read, Grep, Glob—analyze without modifying. Code writers (developers, engineers): Read, Write, Edit, Bash, Glob, Grep—create and execute." — [awesome-claude-code-subagents][awesome]

**Principle**: Start narrow, expand after validation. Omitting `tools` grants all—potential security risk.

> "Scope tools per agent. PM & Architect are read-heavy (search, docs via MCP); Implementer gets Edit/Write/Bash plus UI testing." — [PubNub Best Practices][pubnub]

---

## 4. Model Selection Strategy

| Model      | Use Case                         | Cost/Speed            |
|------------|----------------------------------|-----------------------|
| **Haiku**  | Lightweight, frequent-use agents | 3x cheaper, 2x faster |
| **Sonnet** | Balanced complexity (default)    | Standard              |
| **Opus**   | Complex analysis, deep reasoning | Most capable          |

> "Claude Haiku 4.5 (released October 2025) has transformed agent engineering economics by delivering 90% of Sonnet 4.5's agentic coding performance at 2x the speed and 3x cost savings." — [Medianeth 2025 Guide][medianeth]

**Rule of thumb**: Use Haiku for frequent-use agents. Reserve Opus for complex analysis where the 10% capability gap matters.

> "Haiku 4.5 + Lightweight Agent achieves 90% of Sonnet 4.5's agentic performance—ideal for frequent-use agents." — [Medianeth 2025 Guide][medianeth]

---

## 5. Extended Thinking Configuration

### Not Configurable in Frontmatter

Extended thinking (Claude's internal reasoning mode) **cannot be configured** in subagent frontmatter. There is no `thinking`, `budget_tokens`, or similar field.

| Supported Fields | NOT Supported            |
|------------------|--------------------------|
| `name`           | `thinking`               |
| `description`    | `budget_tokens`          |
| `tools`          | `thinkingMode`           |
| `model`          | `extended_thinking`      |
| `permissionMode` | Any thinking-related key |
| `skills`         |                          |

Source: [Subagents Docs][docs]

### How Claude Code Handles Thinking

Claude Code uses **prompt-driven triggers** rather than configuration:

| Keyword                       | Approx. Budget |
|-------------------------------|----------------|
| `think`                       | ~4,000 tokens  |
| `think hard` / `megathink`    | ~10,000 tokens |
| `think harder` / `ultrathink` | ~31,999 tokens |

Source: [Claude Code Thinking Guide][cc-thinking]

> "You can activate different levels of thinking by incorporating specific keywords into your prompts." — [Claude Code Thinking Guide][cc-thinking]

### Workaround: Prompt-Based Hints

Embed thinking triggers in the system prompt:

```markdown
---
name: deep-analyzer
description: Complex analysis requiring extended reasoning
model: opus
---

When analyzing complex problems, think hard before providing your answer.

## Workflow

1. Think through all implications carefully
2. Consider edge cases
3. Provide comprehensive analysis
```

**Important**: This is a prompt hint, not a configuration—Claude Code decides the actual thinking budget based on model capability and task complexity.

### API vs Claude Code

At the API level, thinking is configured per-request ([Extended Thinking Docs][ext-thinking]):

```json
{
  "thinking": {
    "type": "enabled",
    "budget_tokens": 10000
  }
}
```

Claude Code abstracts this away. Factors that influence thinking:

- **Model capability**: Opus uses more thinking than Haiku
- **Task complexity**: Inferred from conversation context
- **Keyword triggers**: The phrases listed above

### Interleaved Thinking

Claude 4 models support interleaved thinking—reasoning between tool calls. This is automatic in Claude Code when using agents with tools. At API level, requires beta header `interleaved-thinking-2025-05-14`. ([Extended Thinking Docs][ext-thinking])

### Practical Guidance

| Goal                            | Approach                                    |
|---------------------------------|---------------------------------------------|
| More reasoning depth            | Use `model: opus`                           |
| Trigger extended thinking       | Include "think hard" in prompts             |
| Maximum reasoning               | Use "ultrathink" keyword + Opus model       |
| Precise thinking budget control | Use API directly, not Claude Code subagents |

**Bottom line**: Model selection (`opus` > `sonnet` > `haiku`) has more practical impact on reasoning depth than trying to configure thinking budgets directly.

---

## 6. System Prompt Design

### Structure Template

```markdown
---
name: example-agent
description: When and why to use this agent
tools: Read, Edit, Write, Bash
model: sonnet
---

You are a [role] specializing in [domain].

## Expertise

- [Capability 1]
- [Capability 2]

## Workflow

1. [First action]
2. [Second action]
3. [Verification step]

## Constraints

- **KEYWORD** — explanation of constraint
- **KEYWORD** — explanation of constraint

## Output Format

[Expected deliverable format]

## Edge Cases

- **Empty input**: Action to take
- **Multiple items**: How to handle
- **Uncertainty**: Output `STATUS: NEEDS_INPUT` block — never guess

## Examples

<example type="good">
<input>[sample input]</input>
<output>[expected output]</output>
</example>

<example type="bad">
<input>[problematic input]</input>
<why_bad>
- [Problem 1]
- [Problem 2]
</why_bad>
<correct>
[What to do instead]
</correct>
</example>

## Done When

- [ ] [Completion criterion 1]
- [ ] [Completion criterion 2]
- [ ] [Verification passed]
```

### Best Practices

| Practice                  | Why                               | Source            |
|---------------------------|-----------------------------------|-------------------|
| Include examples          | LLMs excel at pattern recognition | [ClaudeLog][clog] |
| State constraints         | Prevents scope creep              | [PubNub][pubnub]  |
| Define output format      | Ensures consistent deliverables   | [PubNub][pubnub]  |
| Add verification steps    | Catches errors before handoff     | [PubNub][pubnub]  |
| Use action-oriented verbs | Clearer than passive descriptions | [PubNub][pubnub]  |

> "Give each subagent one clear goal, input, output, and handoff rule. Keep descriptions action-oriented." — [PubNub Best Practices][pubnub]

> "Provide positive/negative examples in your system prompts. LLMs excel at pattern recognition and repetition." — [ClaudeLog Custom Agents][clog]

### Constraint Formatting

Use strong keywords with em-dash formatting for maximum clarity:

```markdown
## Constraints

- **NEVER assume** — If uncertain about requirements, output STATUS: NEEDS_INPUT block
- **ALWAYS verify** — Run lint/test before marking task complete
- **ZERO tolerance** — No hardcoded secrets or credentials in code
- **MAXIMUM 3 files** — Per commit to keep changes reviewable
```

#### Constraint Keywords

| Keyword               | Use For               |
|:----------------------|:----------------------|
| `NEVER`               | Absolute prohibitions |
| `ALWAYS`              | Mandatory actions     |
| `ZERO`                | No exceptions allowed |
| `MAXIMUM` / `MINIMUM` | Numeric limits        |
| `ONLY`                | Scope restrictions    |
| `MUST`                | Required steps        |

#### Mandatory Constraint: Uncertainty Handling

Every agent MUST include uncertainty handling in the Constraints section:

```markdown
- **NEVER assume** — If requirements are unclear, output `STATUS: NEEDS_INPUT` block
```

This ensures agents ask for clarification instead of guessing wrong.

### Edge Cases Section

Every agent MUST include an Edge Cases section covering:

| Edge Case               | Why Required                               |
|:------------------------|:-------------------------------------------|
| **Empty/missing input** | Prevents errors on incomplete requests     |
| **Partial completion**  | Defines behavior when blocked mid-task     |
| **Multiple items**      | Clarifies batch vs sequential handling     |
| **Uncertainty**         | MANDATORY — triggers `STATUS: NEEDS_INPUT` |

#### Mandatory Edge Case: Uncertainty

```markdown
## Edge Cases

- **Uncertainty about requirements**: Output `STATUS: NEEDS_INPUT` block — never assume or guess
```

This mirrors the constraint and ensures uncertainty is handled in both decision flow and edge case handling.

### Examples Section

Use typed examples with good/bad patterns:

```markdown
## Examples

<example type="good">
<input>Review pkg/auth/handler.go</input>
<output>
**Critical**: SQL injection at line 45...
**Warnings**: Missing error context at line 23...
</output>
</example>

<example type="bad">
<input>Review the code</input>
<why_bad>
- No file path specified
- Would require guessing which files to review
</why_bad>
<correct>
Output `STATUS: NEEDS_INPUT` asking for specific file path
</correct>
</example>
```

The `<why_bad>` and `<correct>` tags help the agent learn from counter-examples.

### Done When Section

Every agent SHOULD end with a completion checklist:

```markdown
## Done When

- [ ] Primary deliverable created
- [ ] All verification steps passed
- [ ] No TODO comments left in output
- [ ] Status block includes all required fields
```

This provides clear success criteria and prevents premature completion.

### Anti-Patterns

- Vague role descriptions ("helpful assistant")
- Missing constraints (agent does unexpected work)
- No examples (inconsistent behavior)
- Implicit assumptions (agent guesses wrong)

> "Begin with a carefully scoped set of tools for your custom agent and progressively expand the tool scope as you validate its behavior." — [ClaudeLog Custom Agents][clog]

### Do Blank Lines Matter?

**Question**: Does this:

```markdown
## Constraints

- ONLY investigate and plan—never implement
```

behave differently than this?

```markdown
## Constraints
- ONLY investigate and plan—never implement
```

**Short answer**: For Claude's understanding—**no meaningful difference**. For human readability and markdown rendering—**yes**.

#### Research Findings

| Aspect              | Finding                                                                                                                 | Source                           |
|---------------------|-------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| **Performance**     | Claude-3.7 shows "remarkable stability" when formatting elements (including newlines) are removed—less than 1% variance | [arXiv:2508.13666][arxiv-format] |
| **Token cost**      | Newlines account for ~14.6% of input tokens for Claude                                                                  | [arXiv:2508.13666][arxiv-format] |
| **Output behavior** | Models "tend to generate code in a familiar formatting style, regardless of that in the input"                          | [arXiv:2508.13666][arxiv-format] |
| **Markdown spec**   | Blank lines after ATX headings (`#`) are recommended but not required by CommonMark                                     | [CommonMark Spec][commonmark]    |

#### Why Blank Lines Are Still Recommended

1. **Human readability**: Easier to scan and maintain agent definitions
2. **Markdown rendering**: Some parsers handle edge cases better with blank lines ([Markdown Guide][mdguide])
3. **Linting**: Tools like markdownlint (MD022) expect blank lines around headings
4. **Consistency**: Matches Claude Code's own documentation style

#### When to Skip Blank Lines

- Token-constrained scenarios where every token counts
- Programmatically generated prompts where readability is irrelevant

**Bottom line**: Use blank lines for readability. Claude understands both formats equally well, but humans maintaining your agent files will thank you.

### Should XML Examples Be in Code Blocks?

**Question**: Should `<example>` tags in system prompts be wrapped in ` ```xml ` code blocks?

```markdown
## Examples

<example type="good">
<input>Create agent for X</input>
<output>...</output>
</example>
```

vs:

~~~markdown
## Examples

```xml
<example type="good">
<input>Create agent for X</input>
<output>...</output>
</example>
```
~~~

**Short answer**: **No.** Use raw XML for structural prompt elements.

#### How Claude Interprets XML

| Format                  | Claude's Interpretation                                                |
|:------------------------|:-----------------------------------------------------------------------|
| Raw `<example>`         | "This is a structural section marker—I should **follow this pattern**" |
| ` ```xml <example>``` ` | "This is **code/content to examine**—I'm looking at XML syntax"        |

Claude treats raw XML tags as **structural signposting** that creates "explicit boundaries that help Claude maintain separation between different components" ([Anthropic XML Docs][xml-docs]). Code blocks shift this interpretation from "active structure" to "quoted content."

#### Research Findings

| Finding                                                                                               | Source                          |
|:------------------------------------------------------------------------------------------------------|:--------------------------------|
| Claude is "12% more likely to adhere to all specified elements and constraints when using XML format" | [Algorithm Unmasked][xml-vs-md] |
| All Anthropic documentation shows XML examples as raw, never code-blocked                             | [Anthropic XML Docs][xml-docs]  |
| XML provides "clear structural cues about how different parts of a prompt relate"                     | [Anthropic XML Docs][xml-docs]  |

#### Negative Impacts of Code-Blocking XML

| Impact                    | Severity | Explanation                                               |
|:--------------------------|:---------|:----------------------------------------------------------|
| Reduced pattern adherence | Moderate | Examples become "illustrative" rather than "prescriptive" |
| Nested code block issues  | High     | Examples containing code can't have inner ` ``` ` blocks  |
| Semantic confusion        | Mild     | Model may describe examples rather than follow them       |

#### When Code Blocks ARE Appropriate

- **Documenting XML syntax** (like in guides/specs—this very section uses code blocks to show the difference)
- **Showing XML as output format** the agent should produce
- **Meta-discussion** about XML structure itself

**Bottom line**: Keep raw XML for structural prompt elements (`<example>`, `<input>`, `<output>`, `<constraints>`). The subagent definitions in this repository use XML as Claude was trained to interpret it—as structural markers guiding behavior.

[xml-docs]: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags
[xml-vs-md]: https://algorithmunmasked.com/2025/05/14/mastering-claude-prompts-xml-vs-markdown-formatting-for-optimal-results/

---

## 7. Slash Commands Integration

Slash commands provide a user-friendly interface to invoke subagents. For comprehensive command documentation, see **[Claude Code Commands Guide](claude-code-commands-guide.md)**.

### Quick Reference

| Aspect         | Slash Commands               | Subagents                |
|:---------------|:-----------------------------|:-------------------------|
| **Location**   | `.claude/commands/`          | `.claude/agents/`        |
| **Invocation** | Explicit (`/command`)        | Automatic or explicit    |
| **Context**    | Inline (main conversation)   | Isolated window          |
| **Use case**   | Quick prompts, orchestration | Complex autonomous tasks |

### Key Patterns for Subagent Orchestration

Commands orchestrate subagents using these patterns:

1. **Mode Detection** — Determine subagent mode from input before invoking
2. **Status-Based Handoff** — Parse `STATUS:` blocks to handle questions, chaining, and completion
3. **User Input Relay** — Handle `STATUS: NEEDS_INPUT` via `AskUserQuestion` tool

See [Commands Guide §7](claude-code-commands-guide.md#7-command--subagent-orchestration) for detailed patterns and examples.

---

## 8. Agent Invocation

### Automatic Delegation

Claude invokes agents based on `description` matching the current task.

#### Description Formula

High-quality descriptions follow this pattern:

```
{What the agent does}. Use {TRIGGER} {scenario1}, {scenario2}, {scenario3}. {Value proposition}.
```

| Component     | Purpose                 | Examples                                                |
|:--------------|:------------------------|:--------------------------------------------------------|
| **What**      | Primary capability      | "Summarizes code files", "Creates implementation plans" |
| **Trigger**   | When to invoke          | `PROACTIVELY`, `MUST BE USED`, `immediately after`      |
| **Scenarios** | 2-3 specific situations | "after code changes", "when exploring unfamiliar code"  |
| **Value**     | Benefit to user         | "Accelerates comprehension", "Prevents rework"          |

#### Trigger Keywords

| Keyword                 | Strength  | Use When                                       |
|:------------------------|:----------|:-----------------------------------------------|
| `Use PROACTIVELY`       | Strong    | Agent should auto-invoke in matching scenarios |
| `MUST BE USED`          | Strongest | Critical workflow step, never skip             |
| `Use immediately after` | Strong    | Post-action trigger                            |
| `Use when`              | Medium    | Conditional invocation                         |

#### Examples

**Strong description:**

```yaml
description: Summarizes code files into concise descriptions. Use PROACTIVELY when user asks "what does this file do?", when exploring unfamiliar code, or when needing quick orientation. Accelerates comprehension without reading entire files.
```

**Weak description (avoid):**

```yaml
description: Helps with code analysis
```

Problems: No trigger keywords, no scenarios, no value proposition.

> "Use phrases like 'use PROACTIVELY' or 'MUST BE USED' in description to encourage automatic delegation." — [Subagents Docs][docs]

### Manual Invocation

```
> Use the planning-agent to analyze this codebase
> Have the code-reviewer check my recent changes
> Ask the researcher to find examples of retry patterns
```

### Interactive Management

```bash
/agents    # Create, edit, delete, view agents
```

> "You can use the `/agents` command to modify tool access—it provides an interactive interface that lists all available tools." — [Subagents Docs][docs]

---

## 9. Example Agents

### Planning Agent

```markdown
---
name: planning-agent
description: Investigates codebase and creates implementation specs. Use at the start of complex features.
tools: Read, Grep, Glob, Bash, Write
model: opus
---

You are a planning agent. Your task is to investigate a codebase and produce a comprehensive implementation plan that enables a fresh AI session to execute without re-investigating.

## Constraints

- ONLY investigate and plan—never implement
- ONLY modify the plan file—no other files
- If you encounter blockers, STOP and ask the user

## Workflow

1. Analyze the task
2. Investigate relevant code
3. Discover project commands (lint, test)
4. Create plan in `tmp/tasks/YYMMDD-{slug}/implementation_plan.md`

## Output Requirements

- Self-contained: fresh executor can start immediately
- Each phase: 3-7 steps, ≤10 files
- Include: file paths, commands, verification steps
```

### Executor Agent

```markdown
---
name: executor-agent
description: Implements ONE task from an implementation spec. Use to execute planned work step-by-step.
tools: Read, Edit, Write, Bash, Grep, Glob
model: sonnet
permissionMode: acceptEdits
---

You are an executor agent. Your task is to implement ONE task from an implementation spec, then prepare a clean handover.

## Constraints

- SINGLE TASK ONLY—do NOT continue to subsequent tasks
- Update progress BEFORE running verification
- Commit ONLY implementation changes

## Workflow

1. Load spec, identify NEXT task
2. Implement the task
3. Update progress tracker (mark done, move NEXT pointer)
4. Run lint/test
5. Commit implementation changes

## Session Boundary

After completing ONE task, your work is done. The updated Progress Tracker serves as handover.
```

### Code Reviewer

Based on patterns from [awesome-claude-code-subagents][awesome]:

```markdown
---
name: code-reviewer
description: Reviews code for quality, security, and maintainability. Use PROACTIVELY after writing or modifying code.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You are a senior code reviewer ensuring high standards.

## Workflow

1. Run `git diff` to see recent changes
2. Analyze modified files
3. Provide prioritized feedback

## Review Checklist

- Code is simple and readable
- Functions and variables well-named
- No duplicated code
- Proper error handling
- No exposed secrets
- Input validation present
- Test coverage adequate

## Output Format

**Critical** (must fix):

- [Issue with file:line and fix suggestion]

**Warnings** (should fix):

- [Issue with rationale]

**Suggestions** (consider):

- [Improvement opportunity]
```

### Researcher

```markdown
---
name: researcher
description: Investigates technical questions, finds patterns, and summarizes findings. Use for exploration tasks.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: haiku
---

You are a research specialist. Investigate questions thoroughly and provide concise, actionable summaries.

## Workflow

1. Understand the question
2. Search codebase for relevant patterns
3. Search web for best practices (if applicable)
4. Synthesize findings

## Output Format

**Summary**: [1-2 sentence answer]

**Evidence**:

- [Finding 1 with source]
- [Finding 2 with source]

**Recommendations**:

- [Actionable suggestion]
```

---

## 10. Quality Review Integration

### Parent-Orchestrated Quality Review

The `agent-manager` and `command-manager` agents delegate quality review to their parent commands. This is required because **subagents cannot spawn other subagents** (Task tool not available to subagents).

```
Creator Agent                     Parent Command
─────────────                     ──────────────
Construction complete
    │
    └─→ STATUS: READY_FOR_REVIEW ──→ Invoke quality reviewer
        (content embedded)              │
                                        ├─→ Grade A/PASS → Write file → done
                                        │
                                        └─→ Grade < A → REVIEW_FEEDBACK ──┐
                                                                          │
    ┌─────────────────────────────────────────────────────────────────────┘
    │
Fix issues
    │
    └─→ STATUS: READY_FOR_REVIEW ──→ Re-review (max 3 attempts)
```

### Why Parent-Orchestrated?

- **Subagent limitation**: Subagents cannot use the Task tool (cannot spawn quality reviewers)
- **No staging files**: Content is embedded in status block, eliminating file management
- **Centralized retry logic**: Parent command handles the 3-attempt limit consistently

### Quality Review Status Flow

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

The parent command:
1. Invokes quality reviewer with embedded content
2. If grade < A: Resumes creator with `REVIEW_FEEDBACK:`
3. If grade A: Writes file to final location

### Quality Grades

| Grade    | agent-reviewer                             | command-reviewer        |
|:---------|:-------------------------------------------|:------------------------|
| **A**    | All requirements, 0 critical, ≤2 warnings  | —                       |
| **B**    | All requirements, 0 critical, 3-5 warnings | —                       |
| **C**    | All requirements, 1-2 critical             | —                       |
| **D**    | Missing requirements OR 3+ critical        | —                       |
| **F**    | Missing 3+ requirements OR invalid         | —                       |
| **PASS** | —                                          | All checks pass         |
| **WARN** | —                                          | Passes with warnings    |
| **FAIL** | —                                          | Critical issues present |

**Acceptance criteria:**
- `agent-manager`: Only grade **A** is acceptable
- `command-manager`: Only **PASS** is acceptable

### Review Feedback Format

When quality review fails, parent resumes creator agent with:

```
REVIEW_FEEDBACK:
grade: {B|C|D|F}
critical_issues:
- Issue 1 at line X
- Issue 2 at line Y
warnings:
- Warning 1
- Warning 2
```

### Max 3 Attempts

After 3 failed quality reviews, the parent command reports to user:
- Final grade and remaining issues
- Manual intervention required

**Note**: There is no `STATUS: QUALITY_FAILED` from creator agents—the parent command handles retry limit enforcement.

---

## 11. Orchestration Patterns

### Status-Based Handoff (Recommended)

The most common and reliable pattern for multi-agent workflows. Agents output structured status blocks that parent agents/commands parse to determine next steps.

Sources: [PubNub Best Practices][pubnub], [wshobson/agents][wshobson], [Delegation Setup Gist][delegation-gist], [Agent Design Lessons][agent-design]

#### Status Block Format

```
STATUS: {COMPLETED|READY_FOR_NEXT|NEEDS_INPUT|READY_FOR_REVIEW}
key1: value1
key2: value2
summary: one-line description
```

#### Status Values

| Status             | Meaning                         | Parent Action                            |
|:-------------------|:--------------------------------|:-----------------------------------------|
| `COMPLETED`        | Task finished successfully      | Report to user, done                     |
| `READY_FOR_NEXT`   | Chain to another agent          | Invoke specified `next_agent`            |
| `NEEDS_INPUT`      | Requires user clarification     | Use `AskUserQuestion`, then resume       |
| `READY_FOR_REVIEW` | Content ready for quality check | Invoke quality reviewer, write if passed |

**Note**: `STATUS: READY_FOR_REVIEW` is used when subagents need quality review but cannot spawn reviewers themselves (Task tool not available to subagents). See §10 for details.

#### Example: Agent Chaining with Quality Review

```
agent-manager
├── STATUS: NEEDS_INPUT → AskUserQuestion → resume
└── STATUS: READY_FOR_REVIEW → invoke quality-reviewer
    ├── Grade A → write file → check slash_command
    │   ├── yes → invoke command-manager → quality review → write → done
    │   └── no → done
    └── Grade < A → resume with REVIEW_FEEDBACK (max 3x)
```

#### Implementation in Subagent

```markdown
## Output

Always end with a status block:

**If work is complete:**
```
STATUS: COMPLETED
result_path: {path}
summary: {description}
```

**If user clarification is needed:**
```
STATUS: NEEDS_INPUT
questions:
  1. QUESTION_KEY: Question text? [option1|option2 (recommended)|option3]
  2. ANOTHER_KEY: Another question? [yes|no]
summary: awaiting user clarification on {topic}
```

**If another agent should continue:**
```
STATUS: READY_FOR_NEXT
next_agent: {agent-name}
context: {what the next agent needs}
summary: {what was done}
```

**If content needs quality review (subagent cannot spawn reviewers):**
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
```

#### Implementation in Command

```markdown
## Workflow

1. Invoke subagent with Task tool
2. Parse status block from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with answers
   - `STATUS: READY_FOR_NEXT` → Invoke specified `next_agent` with context
   - `STATUS: READY_FOR_REVIEW` → Invoke quality reviewer, write if passed, resume with feedback if not
   - `STATUS: COMPLETED` → Report success to user, done
3. Repeat until final `STATUS: COMPLETED`

**CRITICAL**: For `NEEDS_INPUT`, you MUST use `AskUserQuestion` tool. Do NOT print questions as text.
```

### Pipeline Architecture (Alternative)

Chain agents through status flags in shared files:

```
pm-spec        → READY_FOR_ARCH
architect      → READY_FOR_BUILD
implementer    → DONE
```

Each agent reads status, does work, updates status.

> "A three-stage pipeline example: pm-spec → reads an enhancement, writes a working spec, sets status READY_FOR_ARCH. architect-review → validates design, produces ADR, sets status READY_FOR_BUILD. implementer-tester → implements code & tests, sets status DONE." — [PubNub Best Practices][pubnub]

### Human-in-the-Loop (HITL)

Use hooks to pause between agents:

`.claude/settings.json`:

```json
{
  "hooks": {
    "SubagentStop": [{
      "command": "echo 'Next: Use the architect agent on this task'"
    }]
  }
}
```

> "Chain via Hooks, Not Prompts. Register SubagentStop and Stop hooks to suggest next steps. This prevents runaway chains and forces deliberate human approvals." — [PubNub Best Practices][pubnub]

### Parallel Execution

Safe to parallelize when:

- Agents work on disjoint files
- No status dependencies
- Different slugs/tasks

> "Safe parallelization: Only parallelize disjoint slugs; flag file conflicts via architect/implementer reports." — [PubNub Best Practices][pubnub]

---

## 12. Context Management

### Why Subagents Help

| Problem                    | Solution                                    |
|----------------------------|---------------------------------------------|
| Main context bloated       | Subagent investigates, returns summary only |
| Irrelevant info persists   | Subagent's context is discarded after task  |
| Long tasks exhaust context | Multiple subagents preserve main thread     |

> "Subagents enable parallelization—you can spin up multiple subagents to work on different tasks simultaneously. They also help manage context by using their own isolated context windows, and only send relevant information back to the orchestrator." — [Claude Agent SDK Engineering Blog][sdk]

### Reduce and Delegate (R&D) Pattern

1. **Reduce**: Minimize redundant data in main context
2. **Delegate**: Assign investigation to subagents
3. **Summarize**: Subagent returns only relevant findings

> "The 'Reduce and Delegate' (R&D) framework optimizes context usage: Reduce—minimize unnecessary data within the context window. Delegate—assign specific tasks to sub-agents, allowing the primary agent to focus on core responsibilities." — [ClaudeCode101 Context Management][cc101]

### When to Use Subagents

- Early in conversations to verify details
- For investigation that would pollute main context
- When sifting through large amounts of information
- For parallelizable tasks

> "Use subagents strongly for complex problems. Telling Claude to use subagents to verify details or investigate particular questions, especially early in a conversation, tends to preserve context availability without much downside in terms of lost efficiency." — [Claude Code Best Practices][bp]

---

## 13. Debugging & Troubleshooting

| Issue                       | Cause                           | Fix                                      |
|-----------------------------|---------------------------------|------------------------------------------|
| Agent not invoked           | Description doesn't match task  | Make description more specific           |
| Agent has wrong tools       | `tools` field misconfigured     | Check comma-separated list               |
| Hooks not running           | Invalid JSON in settings        | Validate with `jq`                       |
| Agent does unexpected work  | Missing constraints in prompt   | Add explicit "do NOT" rules              |
| Context exhausted quickly   | Inherited all tools             | Restrict to needed tools only            |
| AskUserQuestion not working | Tool is filtered from subagents | Use parent relay pattern (§13.2)         |
| Task tool not working       | Tool unavailable to subagents   | Use parent orchestration pattern (§13.3) |

Source: [PubNub Best Practices][pubnub], [GitHub Issue #12890][gh-12890]

### 13.1 Iterative Refinement

1. Run agent on task
2. Note what went wrong vs. expected
3. Update system prompt with counter-examples
4. Version control agent files for history

> "Use iterative prompting to refine behavior: Supply context on failed actions (what vs. expected), explain desired outcome, pass in the .md config for Claude to suggest modifications." — [PubNub Best Practices][pubnub]

### 13.2 AskUserQuestion Limitation

**Known Bug**: `AskUserQuestion` is explicitly filtered out when spawning subagents at the system level, regardless of what you configure in the `tools:` field. ([GitHub Issue #12890][gh-12890])

This is a **regression introduced in v2.0.56** (worked in v2.0.55). Related issues track broader parent-child communication needs ([GitHub Issue #1770][gh-1770], [GitHub Issue #5812][gh-5812]).

#### Symptoms

- Subagent lists `AskUserQuestion` in tools but cannot use it
- Subagent outputs questions as text instead of interactive UI
- User cannot respond to subagent's questions

#### Workaround: Status-Based Relay Pattern

Since subagents cannot interact with users directly, use the status-based pattern for consistency:

```text
User ↔ Parent Agent ↔ Sub-Agent
```

**Step 1**: Subagent outputs `STATUS: NEEDS_INPUT` block:

```text
STATUS: NEEDS_INPUT
questions:
  1. MODEL: Which model? [haiku|sonnet (recommended)|opus]
  2. TOOLS: Suggested tools: Read, Grep, Glob. Add or remove? [accept|modify]
  3. PERMISSION: Permission mode? [default (recommended)|acceptEdits|bypassPermissions]
  4. LOCATION: Save location? [.claude/agents/ (recommended)|~/.claude/agents/]
  5. SLASH_COMMAND: Create slash command? [yes: /name|no]
summary: awaiting configuration choices
```

**Step 2**: Parent agent recognizes `NEEDS_INPUT` status and calls `AskUserQuestion` tool

**Step 3**: Parent agent resumes subagent with formatted answers:

```text
ANSWERS: MODEL=sonnet, TOOLS=Read,Grep,Glob, PERMISSION=default, LOCATION=.claude/agents/, SLASH_COMMAND=/myagent
```

#### Implementation in Subagent

```markdown
## Constraints

- **CANNOT use AskUserQuestion** — Tool is filtered at system level
- **MUST output STATUS: NEEDS_INPUT block** — Parent agent handles user interaction
- **MUST STOP after status block** — Wait for parent agent to resume with answers
```

#### Implementation in Slash Command

```markdown
## Workflow

1. Invoke subagent with Task tool
2. Parse status block from output:
   - `STATUS: NEEDS_INPUT` → Parse questions, use `AskUserQuestion` tool, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report success to user
   - `STATUS: READY_FOR_NEXT` → Invoke next agent
3. Repeat until final `STATUS: COMPLETED`

**CRITICAL**: You MUST use `AskUserQuestion` tool. Do NOT print questions as text.
```

This approach aligns with PubNub's HITL (Human-in-the-Loop) pattern: "If acceptance criteria are ambiguous, ask numbered questions and WAIT for human answers." ([PubNub Best Practices][pubnub])

> "A community response suggested an indirect approach: Tell the sub-agent to request the use of AskUserQuestion. The primary agent can then use the tool to propagate questions back to the user." — [GitHub Issue #12890][gh-12890]

### 13.3 Task Tool Limitation

**Subagents cannot spawn other subagents.** The Task tool (used to invoke subagents) is not available to subagents themselves. This is an architectural constraint, not a bug.

#### Symptoms

- Subagent attempts to call Task tool but tool is not available
- Subagent tries to invoke quality reviewer but nothing happens
- Subagent outputs instructions like "Use the Task tool to..." but cannot execute them

#### Architectural Impact

This limitation affects workflows that require subagents to chain other subagents:

| Workflow                    | Blocked Approach                  | Working Approach                   |
|:----------------------------|:----------------------------------|:-----------------------------------|
| Quality review integration  | Subagent invokes quality reviewer | Parent command orchestrates review |
| Multi-agent pipelines       | Subagent chains to next subagent  | Parent command chains agents       |
| Delegation within subagents | Subagent delegates to specialist  | Parent handles all delegation      |

#### Workaround: Parent-Orchestrated Pattern

Since subagents cannot spawn subagents, all multi-agent orchestration must happen at the parent level (slash commands or main conversation):

```
┌─────────────────────────────────────────────────────────────┐
│ Parent (Command or Main Conversation)                       │
│   • Has Task tool access                                    │
│   • Can spawn subagents                                     │
│   • Orchestrates multi-agent workflows                      │
│   • Handles quality review loops                            │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Subagent A      │  │ Subagent B      │  │ Quality Reviewer│
│ (no Task tool)  │  │ (no Task tool)  │  │ (no Task tool)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

#### Implementation Pattern

Subagent outputs status block signaling need for external action:

```markdown
## Output

**If work needs external action (quality review, next agent):**
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
```

Parent command parses status and orchestrates:

```markdown
## Workflow

1. Invoke creator subagent
2. Parse status block:
   - `STATUS: READY_FOR_REVIEW` → Invoke quality reviewer → write if passed
   - `STATUS: COMPLETED` → done
3. Handle quality fix loop if needed (max 3 attempts)
```

#### Key Insight

**Commands are the orchestration layer.** Design subagents to be single-purpose units that output structured status blocks. Commands parse these blocks and handle:
- User interaction (`AskUserQuestion`)
- Agent chaining (`Task` tool)
- Quality review loops
- File writing after approval

This separation of concerns makes workflows more maintainable and testable.

---

## 14. Advanced Patterns

### Definition of Done (DoD)

End each agent prompt with a checklist:

```markdown
## Done When

- [ ] All files modified are listed
- [ ] Verification command passed
- [ ] Progress tracker updated
- [ ] No TODOs left in code
```

> "Definition of Done per agent: Each agent prompt ends with a checklist; missing items block handoff." — [PubNub Best Practices][pubnub]

### Slug-Based Audit Trails

Tie all artifacts to a task slug:

```
tmp/tasks/251206-add-retry/
├── implementation_plan.md
├── working_notes.md
├── adr.md
└── status.txt    # READY_FOR_BUILD
```

> "Slug-based audit trails: Every enhancement gets a slug (e.g., `use-case-presets`) tied to queue status, working notes, and ADRs." — [PubNub Best Practices][pubnub]

### Multi-Model Integration

Route to external LLMs for specific checks via MCP:

```markdown
## After Implementation

Use MCP tool `external_review` to get GPT-5 review of the spec
```

> "Pattern A — MCP Bridge: Build lightweight MCP server calling preferred LLM; subagent invokes tool like `external_llm.reviewSlug()`." — [PubNub Best Practices][pubnub]

---

## 15. Community Resources

### Agent Collections

| Repository                               | Description                           |
|------------------------------------------|---------------------------------------|
| [awesome-claude-code-subagents][awesome] | 100+ production-ready agents          |
| [wshobson/agents][wshobson]              | 63 plugins, 15 workflow orchestrators |
| [claude-orchestration][orch]             | Multi-agent workflow plugin           |

### Official Documentation

- [Subagents Docs][docs]
- [Claude Code Best Practices][bp]
- [ClaudeLog Guides][clog]

---

## 16. Quick Start Checklist

Converting your prompt templates to subagents:

- [ ] Create `.claude/agents/` directory
- [ ] Add frontmatter to each prompt (name, description, tools)
- [ ] Set appropriate model (haiku for frequent, opus for complex)
- [ ] Restrict tools to minimum needed
- [ ] Add constraints section ("do NOT...")
- [ ] Include examples in system prompt
- [ ] Add verification/done criteria
- [ ] Test with `/agents` command
- [ ] Iterate based on actual behavior

---

## Sources

| Key                 | Source                                                           |
|---------------------|------------------------------------------------------------------|
| `[docs]`            | [Claude Code Subagents Documentation][docs]                      |
| `[bp]`              | [Claude Code Best Practices][bp]                                 |
| `[pubnub]`          | [Best Practices for Claude Code Subagents][pubnub]               |
| `[clog]`            | [ClaudeLog Custom Agents Guide][clog]                            |
| `[medianeth]`       | [Claude Code Frameworks & Sub-Agents 2025][medianeth]            |
| `[awesome]`         | [awesome-claude-code-subagents][awesome]                         |
| `[sdk]`             | [Claude Agent SDK Engineering Blog][sdk]                         |
| `[cc101]`           | [ClaudeCode101 Context Management][cc101]                        |
| `[wshobson]`        | [wshobson/agents][wshobson]                                      |
| `[orch]`            | [claude-orchestration][orch]                                     |
| `[arxiv-format]`    | [The Hidden Cost of Readability (arXiv)][arxiv-format]           |
| `[commonmark]`      | [CommonMark Specification][commonmark]                           |
| `[mdguide]`         | [Markdown Guide - Basic Syntax][mdguide]                         |
| `[cc-thinking]`     | [Claude Code Thinking Guide][cc-thinking]                        |
| `[ext-thinking]`    | [Extended Thinking Documentation][ext-thinking]                  |
| `[gh-12890]`        | [AskUserQuestion Bug - GitHub Issue #12890][gh-12890]            |
| `[gh-1770]`         | [Parent-Child Agent Communication - GitHub Issue #1770][gh-1770] |
| `[gh-5812]`         | [Context Bridging Between Agents - GitHub Issue #5812][gh-5812]  |
| `[agent-design]`    | [Agent Design Lessons from Claude Code][agent-design]            |
| `[cmd-guide]`       | [Claude Code Commands Guide](claude-code-commands-guide.md)      |
| `[delegation-gist]` | [Claude Code Sub-Agent Delegation Setup][delegation-gist]        |

[docs]: https://code.claude.com/docs/en/sub-agents
[bp]: https://www.anthropic.com/engineering/claude-code-best-practices
[pubnub]: https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/
[clog]: https://claudelog.com/mechanics/custom-agents/
[medianeth]: https://www.medianeth.dev/blog/claude-code-frameworks-subagents-2025
[awesome]: https://github.com/VoltAgent/awesome-claude-code-subagents
[sdk]: https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
[cc101]: https://www.claudecode101.com/en/tutorial/optimization/context-management
[wshobson]: https://github.com/wshobson/agents
[orch]: https://github.com/mbruhler/claude-orchestration
[arxiv-format]: https://arxiv.org/abs/2508.13666
[commonmark]: https://spec.commonmark.org/
[mdguide]: https://www.markdownguide.org/basic-syntax/
[cc-thinking]: https://stevekinney.com/courses/ai-development/claude-code-thinking
[ext-thinking]: https://platform.claude.com/docs/en/build-with-claude/extended-thinking
[gh-12890]: https://github.com/anthropics/claude-code/issues/12890
[gh-1770]: https://github.com/anthropics/claude-code/issues/1770
[gh-5812]: https://github.com/anthropics/claude-code/issues/5812
[agent-design]: https://jannesklaas.github.io/ai/2025/07/20/claude-code-agent-design.html
[delegation-gist]: https://gist.github.com/tomas-rampas/a79213bb4cf59722e45eab7aa45f155c
