# Claude Code Subagent Template

Comprehensive template for creating production-quality Claude Code subagent definitions.

---

## Quick Reference

| Section                | Required | When to Include                              |
|:-----------------------|:---------|:---------------------------------------------|
| Frontmatter            | ✅        | Always                                       |
| Role Statement         | ✅        | Always (first line after frontmatter)        |
| Expertise              | ✅        | Always (3-5 capabilities)                    |
| Modes of Operation     | ❌        | Agent has distinct operational modes         |
| Constraints            | ✅        | Always (use strong keywords)                 |
| Workflow               | ✅        | Always (numbered steps)                      |
| Decision Tree          | ❌        | Complex branching logic                      |
| Edge Cases             | ✅        | Always (MUST include uncertainty handling)   |
| Output Format          | ✅        | Always (concrete structure, not description) |
| Examples               | ✅        | Always (good + bad with tags)                |
| Density Rules          | 📋       | Recommended for agents producing text output |
| Done When              | ✅        | Always (4-6 measurable criteria)             |
| Known Issues           | ❌        | Reviewer/validator agents with runtime traps |
| Output (Status Blocks) | ❌        | Agent needs parent orchestration             |

---

## Template

````markdown
---
name: {kebab-case-name}
description: {What it does}. Use {PROACTIVELY|MUST BE USED|immediately after} {scenario 1}, {scenario 2}, or {scenario 3}. {Value proposition}.
tools: {Comma-separated list — see Tool Selection Reference}
model: {haiku|sonnet|opus}
---

You are a {specific role} specializing in {domain/capability in 5-10 words}.

## Expertise

- {Domain expertise 1 — concrete capability}
- {Domain expertise 2 — what this agent knows}
- {Domain expertise 3 — specific skill}

## Modes of Operation

{INCLUDE ONLY IF: Agent has 2+ distinct operational modes}

| Mode         | Trigger                    | Action                         |
|:-------------|:---------------------------|:-------------------------------|
| **{Mode 1}** | {Input pattern or keyword} | {What agent does in this mode} |
| **{Mode 2}** | {Input pattern or keyword} | {What agent does in this mode} |

## Constraints

- **{KEYWORD}** — {Explanation with rationale}
- **NEVER {action}** — {Why this is forbidden}
- **ALWAYS {action}** — {Why this is required}
- **ZERO {tolerance for X}** — {Consequence of violation}
- **MAXIMUM {limit}** — {What this means in practice}
- **NEVER assume** — If uncertain, output `STATUS: NEEDS_INPUT` block

## Workflow

1. {First action — specific, measurable, includes tool if applicable}
2. {Second action — builds on first}
3. {Third action — core work}
4. {Fourth action — verification or validation}
5. {Fifth action — output generation or handoff}

## Decision Tree

{INCLUDE ONLY IF: Workflow has complex conditional logic}

```text
{Condition to check}?
├─ YES → {Action or next decision}
│        └─ {Sub-condition}? → {Action}
└─ NO  → {Alternative action}
         └─ {Fallback} → {Final action}
```

## Edge Cases

- **Empty/missing input**: {Specific action — e.g., "Omit section entirely"}
- **Partial completion**: {What to do when blocked mid-task}
- **Multiple items**: {Batch vs sequential handling}
- **Security/privacy**: {How to handle sensitive data}
- **Uncertainty**: Output `STATUS: NEEDS_INPUT` block — never assume or guess

## Output Format

```markdown
# {Output Title}

## {Section 1}

{Concrete structure showing exact format}

## {Section 2}

{Another section with format specification}
```

## Examples

<example type="good">
<input>{Realistic scenario with sufficient context}</input>
<output>
{Complete, realistic output demonstrating all quality standards}
{Shows proper format, density, and completeness}
</output>
</example>

<example type="bad">
<input>{Common mistake scenario or edge case}</input>
<why_bad>
- {Specific problem 1 with explanation}
- {Specific problem 2 with explanation}
</why_bad>
<correct>
{What to do instead — concrete guidance}
</correct>
</example>

## Density Rules

{RECOMMENDED: Include for agents that produce text output}

| Bad                           | Good                          |
|:------------------------------|:------------------------------|
| {Verbose pattern with prose}  | {Dense pattern with key info} |
| {Another wordy example}       | {Concise equivalent}          |
| {Explanation instead of data} | {Data in structured format}   |

## Done When

- [ ] {Primary deliverable exists/completed}
- [ ] {Quality criterion met}
- [ ] {Verification step passed}
- [ ] {Output requirements satisfied}
- [ ] {No violations of constraints}

## Output

{INCLUDE ONLY IF: Agent is orchestrated by parent command/agent}

Always end with a status block:

**Task completed:**
```text
STATUS: COMPLETED
result: {what was produced}
location: {where it was saved/output}
summary: {one-line description}
```

**Needs user input:**
```text
STATUS: NEEDS_INPUT
questions:
  1. {KEY}: {Question}? [{option1}|{option2 (recommended)}|{option3}]
summary: awaiting {what information}
```

**Ready for next step:**
```text
STATUS: READY_FOR_REVIEW
artifact_name: {name}
content:
~~~markdown
{embedded content}
~~~
summary: {ready for what}
```
````

---

## Frontmatter Reference

### Required Fields

| Field         | Format           | Purpose                                      |
|:--------------|:-----------------|:---------------------------------------------|
| `name`        | `kebab-case`     | Unique identifier for the agent              |
| `description` | Natural language | Determines when Claude invokes automatically |

### Optional Fields

| Field            | Values                                        | Default   | Purpose                    |
|:-----------------|:----------------------------------------------|:----------|:---------------------------|
| `tools`          | Comma-separated tool names                    | All tools | Restrict to minimum needed |
| `model`          | `haiku`, `sonnet`, `opus`                     | `sonnet`  | Cost/capability tradeoff   |
| `permissionMode` | `default`, `acceptEdits`, `bypassPermissions` | `default` | Control approval flow      |

### Description Formula

High-quality descriptions follow this pattern:

```text
{What the agent does}. Use {TRIGGER KEYWORD} {scenario 1}, {scenario 2}, or {scenario 3}. {Value proposition}.
```

**Trigger Keywords** (include at least one):

| Keyword                 | Strength  | Use When                                       |
|:------------------------|:----------|:-----------------------------------------------|
| `Use PROACTIVELY`       | Strong    | Agent should auto-invoke in matching scenarios |
| `MUST BE USED`          | Strongest | Critical workflow step, never skip             |
| `Use immediately after` | Strong    | Post-action trigger                            |
| `Use when`              | Medium    | Conditional invocation                         |

**Good description:**

```yaml
description: Reviews code for bugs and security issues. Use PROACTIVELY after writing code, before commits, or during PR review. Prevents defects from reaching production.
```

**Bad description:**

```yaml
description: Helps with code analysis
```

Problems: No trigger keyword, single vague scenario, no value proposition.

### Tool Selection Reference

| Agent Type    | Recommended Tools                       | Rationale                 |
|:--------------|:----------------------------------------|:--------------------------|
| Reviewer      | `Read, Grep, Glob`                      | Read-only analysis        |
| Researcher    | `Read, Grep, Glob, WebFetch, WebSearch` | Information gathering     |
| Planner       | `Read, Grep, Glob, Bash, Write`         | Investigate and document  |
| Implementer   | `Read, Edit, Write, Bash, Grep, Glob`   | Create and execute        |
| Documentation | `Read, Write, Edit, Glob, WebFetch`     | Research and write        |
| Handover      | `Read, Grep, Glob, Bash, Write`         | Extract context and write |

**Note**: Do NOT include `AskUserQuestion` — it's filtered from subagents at the system level. Use `STATUS: NEEDS_INPUT` pattern instead.

### Model Selection Reference

| Model    | Use Case                                          | Cost/Speed        |
|:---------|:--------------------------------------------------|:------------------|
| `haiku`  | Simple, frequent-use, well-defined tasks          | Fastest, cheapest |
| `sonnet` | Balanced complexity, most agents, default choice  | Standard          |
| `opus`   | Complex analysis, deep reasoning, orchestration   | Most capable      |

---

## Section Guidelines

### Role Statement

**Format**: Single sentence, first line after frontmatter.

**Pattern**: `You are a {specific role} specializing in {domain/capability}.`

**Good:**

```markdown
You are a session context preservation specialist capturing everything needed for seamless session continuity.
```

**Bad:**

```markdown
You are a helpful AI assistant that can help with various tasks related to context management.
```

Problems: "helpful AI assistant" is generic, "various tasks" is vague.

### Expertise Section

**Purpose**: Establishes credibility and scope. Helps LLM understand what knowledge to apply.

**Format**: 3-5 bullet points, concrete capabilities.

**Good:**

```markdown
## Expertise

- Context distillation and density optimization
- Failed approach documentation with elimination rationale
- Architectural decision capture
- Investigation findings extraction
```

**Bad:**

```markdown
## Expertise

- Good at coding
- Can analyze things
- Helpful
```

Problems: Vague, non-specific, doesn't establish domain expertise.

### Constraints Section

**Purpose**: Non-negotiable rules that shape behavior. Most important section for reliability.

**Format**: `**KEYWORD** — {explanation}`

**Keywords and Their Use:**

| Keyword   | Use For               | Example                                       |
|:----------|:----------------------|:----------------------------------------------|
| `NEVER`   | Absolute prohibitions | **NEVER** assume — output STATUS: NEEDS_INPUT |
| `ALWAYS`  | Mandatory actions     | **ALWAYS** verify — run lint before commit    |
| `ZERO`    | No exceptions allowed | **ZERO** tolerance for secrets in code        |
| `MAXIMUM` | Upper limits          | **MAXIMUM** 60 lines — cut ruthlessly         |
| `ONLY`    | Scope restrictions    | **ONLY** modify plan file — no other files    |

**Mandatory Constraint** (every agent MUST include):

```markdown
- **NEVER assume** — If uncertain, output `STATUS: NEEDS_INPUT` block
```

### Workflow Section

**Purpose**: Step-by-step execution flow. Agent follows these in order.

**Format**: Numbered list, 3-7 steps, each specific and actionable.

**Good:**

```markdown
## Workflow

1. Parse input to determine mode (Create/Modify/Transform)
2. Read existing file if path provided
3. Extract key information (role, constraints, workflow)
4. Build agent definition following template structure
5. Validate against quality checklist
6. Output `STATUS: READY_FOR_REVIEW` with embedded content
```

**Bad:**

```markdown
## Workflow

1. Understand the task
2. Do the work
3. Return results
```

Problems: Steps are vague, not actionable, no verification.

### Edge Cases Section

**Purpose**: Handle unusual inputs and error conditions predictably.

**Format**: Bold scenario, colon, specific action.

**Mandatory Categories:**

| Category                | Why Required                               |
|:------------------------|:-------------------------------------------|
| **Empty/missing input** | Prevents errors on incomplete requests     |
| **Partial completion**  | Defines behavior when blocked mid-task     |
| **Multiple items**      | Clarifies batch vs sequential handling     |
| **Uncertainty**         | MANDATORY — triggers `STATUS: NEEDS_INPUT` |

**Good:**

```markdown
## Edge Cases

- **No failed approaches**: Omit section entirely (don't leave blank)
- **Session just started**: Minimal handover — stopping point + next steps only
- **Multiple task threads**: Output `STATUS: NEEDS_INPUT` to let user prioritize
- **Uncertainty about requirements**: Output `STATUS: NEEDS_INPUT` block — never assume
```

**Bad:**

```markdown
## Edge Cases

- Handle edge cases appropriately
- Use good judgment
```

Problems: No specific scenarios, no actions, relies on interpretation.

### Output Format Section

**Purpose**: Define exact structure of deliverable. LLMs follow examples better than descriptions.

**Format**: Concrete structure with placeholders, not prose description.

**Good:**

````markdown
## Output Format

```markdown
# Session Handover

## Session Context

{Goal}: {status}
{One-line summary — max 15 words}

## Failed Approaches

- Tried {X}: {why failed} → {elimination lesson}
```
````

**Bad:**

```markdown
## Output Format

The output should be a markdown document with appropriate sections covering the key information.
```

Problems: No structure, "appropriate sections" is vague, no format specification.

### Examples Section

**Purpose**: Show exact expected behavior. LLMs learn from pattern matching.

**Format**: XML tags with `type` attribute, realistic content.

**Structure:**

```markdown
<example type="good">
<input>{Realistic scenario}</input>
<output>
{Complete output showing all standards}
</output>
</example>

<example type="bad">
<input>{Common mistake}</input>
<why_bad>
- {Specific problem 1}
- {Specific problem 2}
</why_bad>
<correct>
{What to do instead}
</correct>
</example>
```

**Rules:**

- At least 1 good example with complete input/output
- At least 1 bad example with specific problems and fixes
- Examples should be realistic, not trivial
- Good examples demonstrate ALL quality standards

### Density Rules Section

**Purpose**: Show how to compress verbose patterns into dense, high-signal text.

**Format**: Two-column table, Bad vs Good.

**Example:**

```markdown
## Density Rules

| Bad                                   | Good                          |
|:--------------------------------------|:------------------------------|
| "We attempted X but unfortunately..." | "Tried X: failed due to Y"    |
| 20-line code block                    | `func(a,b) → filtered result` |
| "/Users/dev/Projects/.../file.md"     | `.claude/agents/file.md`      |
```

### Done When Section

**Purpose**: Clear completion criteria. Prevents premature completion.

**Format**: Checkbox list, 4-6 measurable criteria.

**Good:**

```markdown
## Done When

- [ ] Document is MAXIMUM 60 lines (hard limit)
- [ ] All items pass SKIP test
- [ ] Saved to `.claude/sessions/YYMMDD-handover-{slug}.md`
- [ ] Copied to clipboard via `pbcopy`
```

**Bad:**

```markdown
## Done When

- [ ] Task is complete
- [ ] Output looks good
```

Problems: Not measurable, "looks good" is subjective.

### Known Issues Section

**Purpose**: Document subtle runtime failures or patterns that look correct but fail. Used by reviewer agents to detect issues and creator agents to avoid them.

**When to include**: Reviewer/validator agents that check for specific patterns, or creator agents that need to avoid known pitfalls.

**Format**: H3 header with `ID: descriptive name`, followed by labeled fields.

**Required fields:**

| Field       | Purpose                                       |
|:------------|:----------------------------------------------|
| **Detect**  | Pattern to look for (what triggers detection) |
| **Problem** | Why this fails (detailed explanation)         |
| **Fix**     | The correct approach (solution)               |

**Optional fields:**

| Field        | Purpose                               |
|:-------------|:--------------------------------------|
| **Severity** | Critical/Warning/Info (for reviewers) |
| **Example**  | Concrete code showing the issue       |
| **Verify**   | Command to test the fix works         |

**Structure:**

```markdown
## Known Issues

Subtle runtime failures. These patterns look correct but fail at runtime.

### {ID}: {descriptive name}

**Detect**: {pattern to look for — use backticks for code}

**Problem**: {Detailed explanation of why this fails. Include what happens at runtime.}

**Fix**: {The correct approach. Use backticks for code.}
```

**Good:**

```markdown
## Known Issues

Subtle runtime failures. These patterns look correct but fail at runtime.

### BASH001: awk brackets as character class

**Detect**: `awk -v b="[$var]" '$0 ~ b'`

**Problem**: Brackets in the variable become a regex character class. Instead of matching literal `[foo]`, it matches any single character: `f`, `o`, or `o`.

**Fix**: Use `index($0, b)` for literal string matching instead of regex.

### BASH002: double-escaped patterns in bash -c

**Detect**: `\\[`, `\\]`, `\\$` inside single-quoted `bash -c '...'`

**Problem**: Inside single quotes, `\\` becomes a literal backslash character, not an escape sequence. This causes awk/grep syntax errors at runtime.

**Fix**: Use single backslash: `\[`, `\]`, `\$`.
```

**Bad:**

```markdown
<pitfall id="BASH001">
**Pattern**: `awk -v b="[$var]"`
**Problem**: brackets issue
**Fix**: use index
</pitfall>
```

Problems: Mixes XML with Markdown, inconsistent field names ("Pattern" vs "Detect"), explanation too brief.

**Relationship with Anti-Pattern Detection:**

| Section                | Purpose                   | Format                               |
|:-----------------------|:--------------------------|:-------------------------------------|
| Anti-Pattern Detection | Quick reference checklist | Table: Pattern, Detection, Severity  |
| Known Issues           | Detailed explanations     | H3 headers with Detect, Problem, Fix |

Known Issues provides **depth** for complex issues that need explanation. Anti-Pattern Detection provides **breadth** for quick scanning. They can reference each other by ID.

---

## Status Block Patterns

### When to Use STATUS Blocks

Use STATUS blocks when:

- Agent is invoked by a parent command (not directly by user)
- Agent needs user input but cannot use `AskUserQuestion` (filtered from subagents)
- Agent chains to another agent or needs quality review

### STATUS: NEEDS_INPUT

When agent needs clarification before proceeding:

```text
STATUS: NEEDS_INPUT
questions:
  1. {KEY}: {Question}? [{option1}|{option2 (recommended)}|{option3}]
  2. {KEY}: {Question}? [{option1}|{option2}]
summary: awaiting {what information is needed}
```

**Rules:**

- Questions are numbered with unique KEYs
- Options in brackets, recommended marked with `(recommended)`
- Summary states what's being waited for
- **STOP after outputting** — wait for parent to resume with answers

**KEY Naming for Command Extraction:**

When commands are created for your agent, their Expected Questions section will extract keys verbatim from your `STATUS: NEEDS_INPUT` examples. To ensure accurate extraction:

- Use UPPERCASE, descriptive key names (e.g., `PRIORITY`, `TYPE`, `ACTION`)
- Keep keys consistent across all `STATUS: NEEDS_INPUT` examples in your agent
- Document ALL possible keys in Edge Cases section examples
- Include realistic options with clear defaults marked `(recommended)`

**Example — Well-documented keys:**

```text
## Edge Cases

- **Multiple threads**: Output `STATUS: NEEDS_INPUT`:
  ```
  STATUS: NEEDS_INPUT
  questions:
    1. PRIORITY: Which thread to capture? [current-task|planned-feature (recommended)|other]
  summary: awaiting thread selection
  ```
```

Commands will extract: `- **PRIORITY**: Which thread to capture (current-task|planned-feature|other)`

### STATUS: COMPLETED

When task is fully done:

```text
STATUS: COMPLETED
result: {what was produced}
location: {file path or "clipboard"}
summary: {one-line description of outcome}
```

### STATUS: READY_FOR_REVIEW

When agent output needs quality review (subagents cannot spawn reviewers):

```text
STATUS: READY_FOR_REVIEW
artifact_name: {name}
artifact_location: {target save location}
content:
~~~markdown
{full content embedded here}
~~~
summary: Ready for quality review
```

### STATUS: READY_FOR_NEXT

When chaining to another agent:

```text
STATUS: READY_FOR_NEXT
next_agent: {agent-name}
context: {what the next agent needs to know}
summary: {what was completed, what's next}
```

---

## Anti-Patterns

### Avoid These in Agent Definitions

| Anti-Pattern                | Problem                          | Fix                                    |
|:----------------------------|:---------------------------------|:---------------------------------------|
| Vague role                  | "helpful assistant" is generic   | Specific role + domain                 |
| Missing constraints         | Agent does unexpected work       | Add NEVER/ALWAYS rules                 |
| No examples                 | Inconsistent behavior            | Add good + bad examples                |
| Implicit assumptions        | Agent guesses wrong              | Make everything explicit               |
| Placeholder text            | `{something}` in final output    | All content must be real               |
| Negative-only framing       | "Don't do X" without alternative | "Instead of X, do Y"                   |
| `AskUserQuestion` in tools  | Filtered from subagents          | Use `STATUS: NEEDS_INPUT` pattern      |
| Single-scenario description | Weak trigger matching            | 2-3 scenarios + trigger keyword        |
| Value-less description      | User doesn't know when to use    | State the benefit                      |
| Prose output format         | "Output a good document"         | Show exact structure with placeholders |
| Unmeasurable Done When      | "Task is complete"               | Specific, verifiable criteria          |

### Common Mistakes by Agent Type

**Reviewer Agents:**

- Including `Write` or `Edit` tools (reviewers should be read-only)
- Missing grading rubric or severity levels
- Not citing line numbers in findings

**Creator Agents:**

- Not requesting user confirmation for design decisions
- Missing validation checklist
- No quality review handoff pattern

**Executor Agents:**

- Scope creep (doing more than one task)
- Not updating progress tracking
- Skipping verification steps

---

## Agent Type Patterns

### Reviewer Pattern

```markdown
---
name: {thing}-reviewer
description: Reviews {thing} for {criteria}. Use PROACTIVELY after {creating thing}, before {committing}, or when {auditing}. Prevents {problem}.
tools: Read, Grep, Glob
model: haiku
---

You are a {thing} quality auditor specializing in {domain} validation.

## Expertise
## Constraints (read-only, no modifications)
## Quality Checklist (with checkboxes)
## Grading Rubric (A/B/C/D/F with criteria)
## Edge Cases
## Output Format (findings report with severity)
## Examples (good review, bad review)
## Done When
```

### Creator Pattern

```markdown
---
name: {thing}-creator
description: Creates {things}. Use PROACTIVELY when {trigger}. {Value}.
tools: Read, Write, Edit, Glob, Grep
model: sonnet
---

You are a {thing} architect specializing in {domain}.

## Expertise
## Modes of Operation (if applicable)
## Constraints (includes validation, user confirmation)
## Workflow (includes design decisions phase)
## Edge Cases (includes uncertainty handling)
## Output Format (the thing being created)
## Examples (good creation, bad creation)
## Done When
## Output (STATUS blocks for orchestration)
```

### Executor Pattern

```markdown
---
name: {task}-executor
description: Executes {task type}. Use when {trigger}. {Value}.
tools: Read, Edit, Write, Bash, Grep, Glob
model: sonnet
permissionMode: acceptEdits
---

You are a {task} execution specialist.

## Expertise
## Constraints (single task, verification required)
## Workflow (includes progress update, verification)
## Edge Cases (blockers, partial completion)
## Output Format
## Examples
## Done When (verification passed)
```

### Researcher Pattern

```markdown
---
name: {topic}-researcher
description: Investigates {topic}. Use when {trigger}. {Value}.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: haiku
---

You are a research specialist in {domain}.

## Expertise
## Constraints (no modifications, synthesis focus)
## Workflow (search, analyze, synthesize)
## Edge Cases (insufficient info, conflicting sources)
## Output Format (findings summary)
## Examples
## Done When
```

---

## Quality Checklist

Use this checklist before finalizing any agent definition.

### Frontmatter

- [ ] `name`: lowercase, kebab-case, unique, descriptive
- [ ] `description`: Has trigger keyword (PROACTIVELY/MUST BE USED)
- [ ] `description`: Lists 2-3 trigger scenarios
- [ ] `description`: States value proposition
- [ ] `tools`: Does NOT include `AskUserQuestion`
- [ ] `tools`: Minimal set for task (least privilege)
- [ ] `model`: Appropriate for complexity and frequency

### System Prompt

- [ ] Role statement: First line, specific domain, action-oriented
- [ ] Expertise: 3-5 concrete capabilities
- [ ] Constraints: Uses **BOLD** — em dash — explanation format
- [ ] Constraints: Has NEVER/ALWAYS/ZERO/MAXIMUM keywords
- [ ] Constraints: Includes uncertainty handling (`STATUS: NEEDS_INPUT`)
- [ ] Workflow: Numbered steps with verification
- [ ] Edge cases: Covers empty, partial, multiple, uncertainty
- [ ] Edge cases: Has `STATUS: NEEDS_INPUT` pattern
- [ ] Output format: Shows concrete structure, not description
- [ ] Examples: Good example with realistic input/output
- [ ] Examples: Bad example with `<why_bad>` and `<correct>` tags
- [ ] Done When: 4-6 measurable completion criteria

### Anti-Pattern Check

- [ ] No vague role ("helpful assistant", "AI that helps")
- [ ] No missing constraints section
- [ ] No implicit assumptions (everything explicit)
- [ ] No placeholder text (`{something}` in final output)
- [ ] No negative-only framing ("don't X" without "do Y instead")
- [ ] No `AskUserQuestion` in tools
- [ ] No single-scenario description
- [ ] No value-less description

---

## Version History

| Date       | Version | Changes                                          |
|:-----------|:--------|:-------------------------------------------------|
| 2025-12-12 | 1.2     | Added KEY naming guidance for command extraction |
| 2025-12-12 | 1.1     | Added Known Issues section for runtime traps     |
| 2025-12-12 | 1.0     | Initial template                                 |