# AI Agent Prompt Engineering Specification

> Best practices and guidelines for writing effective AI agent prompts.
> Synthesized from Anthropic, OpenAI, and industry research (2024-2025).

## Table of Contents

1. [Core Principles](#core-principles)
2. [Prompt Structure](#prompt-structure)
3. [Formatting Guidelines](#formatting-guidelines)
4. [Agent-Specific Patterns](#agent-specific-patterns)
5. [Advanced Techniques](#advanced-techniques)
6. [Anti-Patterns](#anti-patterns)
7. [Quality Checklist](#quality-checklist)
8. [References](#references)

---

## Core Principles

### 1. Context Engineering Over Prompting

Context is a finite resource with diminishing returns. Goal: **minimum high-signal tokens that maximize desired outcome**.

| Principle              | Description                                                            |
|:-----------------------|:-----------------------------------------------------------------------|
| Start minimal          | Begin with minimal prompt, add instructions based on observed failures |
| Progressive disclosure | Allow agents to discover context through exploration                   |
| Just-in-time retrieval | Fetch information dynamically vs. pre-loading everything               |

### 2. Clarity Over Complexity

- **Explicit > Implicit**: State exactly what you want; never assume inference
- **Simple language**: Avoid jargon; use action verbs (Write, Analyze, Create)
- **Focused scope**: One clear objective per prompt or section

### 3. Specificity Without Over-Engineering

```text
Balance point:
├─ Too vague: "Create analytics dashboard"
├─ Optimal: "Create analytics dashboard with user metrics, date filtering, CSV export"
└─ Over-engineered: 500-word specification for simple task
```

### 4. Show, Don't Tell

Examples > Descriptions. One concrete example clarifies what paragraphs of rules cannot.

**Important**: Modern models (Claude 4.x) pay close attention to example details. Ensure examples match desired behavior exactly.

---

## Prompt Structure

### Required Sections (Order Matters)

1. **Role/Identity** — Who the agent is (brief, single sentence)
2. **Constraints** — Critical rules, non-negotiable boundaries
3. **Workflow/Process** — Step-by-step execution flow
4. **Output Specification** — Expected format, structure, content
5. **Edge Cases** — How to handle ambiguity, errors, blockers

### Recommended Template Structure

```markdown
You are {role}. {one-sentence purpose}.

CRITICAL CONSTRAINTS:
- {non-negotiable rule 1}
- {non-negotiable rule 2}

SUCCESS CRITERIA:
- {measurable outcome 1}
- {measurable outcome 2}

WORKFLOW:
1. {step with specific action}
2. {step with specific action}
3. {step with specific action}

EDGE CASES:
- **{scenario}**: {action to take}

OUTPUT:
{format specification or example}

---

{CONTEXT/INPUT placeholder}
```

### Information Positioning

Models attend to information in this order:

1. **User message** (highest attention)
2. **Beginning of system prompt**
3. **End of system prompt**
4. **Middle sections** (lowest attention)

**Implication**: Place critical instructions in user message or prompt beginning/end.

---

## Formatting Guidelines

### Structure Choice: XML vs. Markdown

| Format   | Best For                                  | Trade-offs                               |
|:---------|:------------------------------------------|:-----------------------------------------|
| XML      | Complex prompts, tool definitions, Claude | +15% tokens, clearer boundaries          |
| Markdown | Readability, simple prompts, GPT models   | Fewer tokens, human-friendly             |
| Hybrid   | Best of both                              | Mix headers (MD) + data delimiters (XML) |

**Recommendation**: Use Markdown headers for sections, XML tags for data/examples.

### XML Tag Best Practices

- Consistent naming across prompt (`<context>` not `<ctx>` then `<context>`)
- Self-documenting names (`<user_input>` not `<ui>`)
- Always close tags
- Nest for hierarchy when needed

```xml
<examples>
  <example type="good">
    <input>...</input>
    <output>...</output>
  </example>
</examples>
```

### Markdown Best Practices

- Use headers to create scannable sections
- Bullet lists for parallel items
- Tables for structured comparisons
- Code blocks for examples/templates
- Bold for emphasis on key terms

### Emphasis Patterns

| Pattern     | Use For                       | Example                  |
|:------------|:------------------------------|:-------------------------|
| **Bold**    | Key terms, important concepts | **NEVER** commit secrets |
| CAPS        | Critical warnings (sparingly) | CRITICAL: Do not proceed |
| `backticks` | Code, commands, file paths    | Run `make test`          |

---

## Agent-Specific Patterns

### Memory Management

LLMs are stateless. Explicitly manage:

| Memory Type      | Implementation                                       |
|:-----------------|:-----------------------------------------------------|
| Short-term       | In-context: conversation history, current state      |
| Long-term        | External: files (NOTES.md), vector stores, databases |
| Structured notes | To-do lists, progress trackers, session handovers    |

### Tool Design

Tools must be:
- **Unambiguous**: Clear when to use each tool (no overlap)
- **Token-efficient**: Return concise, relevant information
- **Error-robust**: Return error messages, not exceptions
- **Self-documenting**: Include descriptions, parameters, examples

```markdown
## Tool: read_file

**Purpose**: Read contents of a file from the filesystem
**Parameters**:
  - `path` (required): Absolute path to file
  - `lines` (optional): Number of lines to read (default: all)
**Returns**: File contents as string, or error message
**Example**: `read_file("/src/main.py", lines=50)`
```

### Planning vs. Execution Modes

Separate planning from execution to reduce errors:

```text
PLAN MODE:
├─ Gather context
├─ Ask clarifying questions
├─ Outline approach
└─ Wait for approval

EXECUTE MODE:
├─ Follow approved plan
├─ Single task at a time
├─ Verify after each step
└─ Report completion
```

### Error Handling

Return descriptive errors; models self-correct better than crash recovery:

```text
✗ raise Exception("Invalid parameter")
✓ return "Error: parameter 'count' must be positive integer, got -5"
```

---

## Advanced Techniques

### Chain of Thought (CoT)

Request step-by-step reasoning for complex tasks.

| Implementation | When to Use                                   |
|:---------------|:----------------------------------------------|
| Zero-shot      | Add "Think step-by-step" for simple reasoning |
| Guided         | Define specific reasoning stages              |
| Structured     | Use tags: `<thinking>`, `<answer>`            |

**Warning**: CoT can reduce performance on simple tasks by overcomplicating.

### Few-Shot Prompting

Provide 1-3 diverse, canonical examples.

```markdown
## Examples

<example>
Input: "Fix the login bug"
Output: Branch name: fix/login-authentication-failure
</example>

<example>
Input: "Add dark mode support"
Output: Branch name: feat/add-dark-mode-toggle
</example>
```

**Rules**:

- Start with 1 example; add more only if needed
- Diverse examples > many similar examples
- Examples must perfectly match desired behavior

### Prompt Chaining

Break complex tasks into sequential prompts where output feeds next input.

```text
Prompt 1: Analyze requirements → Summary
Prompt 2: Summary → Design document
Prompt 3: Design document → Implementation plan
```

**Trade-off**: Latency ↑, Accuracy ↑

### Response Prefilling

Start the model's response to enforce format:

```markdown
Respond with valid JSON only. Begin your response with: {
```

### Permission to Express Uncertainty

Explicitly allow "I don't know" to prevent hallucination:

```markdown
If information is insufficient, state what's missing rather than guessing.
```

---

## Anti-Patterns

### ❌ Avoid These

| Anti-Pattern         | Problem                      | Fix                             |
|:---------------------|:-----------------------------|:--------------------------------|
| Vague instructions   | Generic responses            | Add specificity, examples       |
| Negative framing     | "Don't use X" less effective | Say what TO do instead          |
| Overloaded prompts   | Multiple unrelated tasks     | One focused task per prompt     |
| Edge case stuffing   | Bloated, brittle prompts     | Curate diverse examples instead |
| Tool overlap         | Agent confusion              | Distinct, unambiguous tools     |
| No iteration         | Suboptimal results           | Test, refine, repeat            |
| Role over-assignment | Over-constrained responses   | Be explicit about perspective   |
| Context assumption   | Missing information          | State all relevant context      |

### ❌ Common Mistakes

1. **Assuming shared context** — State everything explicitly
2. **Placeholders in output** — "rest of code remains same" → write full code
3. **One-shot mindset** — Iterate on prompts
4. **Length = quality** — Concise + clear > long + thorough
5. **Technique overload** — Use only what's needed

---

## Quality Checklist

### Before Finalizing a Prompt

- [ ] **Clear role**: Agent identity defined in first sentence
- [ ] **Explicit constraints**: Non-negotiable rules stated upfront
- [ ] **Success criteria**: Measurable outcomes defined
- [ ] **Workflow steps**: Concrete, actionable sequence
- [ ] **Edge cases**: Blockers, ambiguity, errors handled
- [ ] **Output format**: Structure specified or exemplified
- [ ] **No assumptions**: All necessary context provided
- [ ] **Tested**: Run against diverse inputs

### Self-Review Questions

1. Can a fresh agent execute this without clarification?
2. What happens if input is malformed/missing?
3. Are instructions specific enough to avoid interpretation?
4. Is there anything this prompt assumes but doesn't state?
5. Does every section serve a purpose?

---

## References

### Primary Sources

- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Claude: Best Practices for Prompt Engineering](https://www.claude.com/blog/best-practices-for-prompt-engineering)
- [Anthropic: Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Prompting Guide: LLM Agents](https://www.promptingguide.ai/research/llm-agents)

### Supplementary Sources

- [Augment Code: 11 Prompting Techniques for Better AI Agents](https://www.augmentcode.com/blog/how-to-build-your-agent-11-prompting-techniques-for-better-ai-agents)
- [PromptHub: Prompt Engineering for AI Agents](https://www.prompthub.us/blog/prompt-engineering-for-ai-agents)
- [Lakera: Ultimate Guide to Prompt Engineering](https://www.lakera.ai/blog/prompt-engineering-guide)
- [IBM: Prompt Engineering Techniques](https://www.ibm.com/think/topics/prompt-engineering-techniques)

### Format-Specific

- [SSW Rules: XML vs Markdown for AI Prompts](https://www.ssw.com.au/rules/ai-prompt-xml/)
- [Algorithm Unmasked: Claude XML vs Markdown](https://algorithmunmasked.com/2025/05/14/mastering-claude-prompts-xml-vs-markdown-formatting-for-optimal-results/)

---

## Version History

| Date       | Version | Changes               |
|:-----------|:--------|:----------------------|
| 2025-12-09 | 1.0.1   | Table formatting      |
| 2025-12-03 | 1.0     | Initial specification |
