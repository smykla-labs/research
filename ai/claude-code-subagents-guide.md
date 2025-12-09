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
Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch
```

Plus any MCP tools registered in settings. ([Subagents Docs][docs])

---

## 3. Tool Selection by Agent Type

| Agent Role        | Recommended Tools                       | Rationale            |
|-------------------|-----------------------------------------|----------------------|
| **Reviewer**      | `Read, Grep, Glob`                      | Read-only analysis   |
| **Researcher**    | `Read, Grep, Glob, WebFetch, WebSearch` | Gather information   |
| **Planner**       | `Read, Grep, Glob, Bash, Write`         | Investigate and doc  |
| **Implementer**   | `Read, Edit, Write, Bash, Grep, Glob`   | Create and execute   |
| **Documentation** | `Read, Write, Edit, Glob, WebFetch`     | Research and write   |

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

| Keyword                        | Approx. Budget   |
|--------------------------------|------------------|
| `think`                        | ~4,000 tokens    |
| `think hard` / `megathink`     | ~10,000 tokens   |
| `think harder` / `ultrathink`  | ~31,999 tokens   |

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

- [What NOT to do]
- [Scope limitations]

## Output Format

[Expected deliverable format]

## Examples

<example>
Input: [sample]
Output: [expected result]
</example>
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

---

## 7. Agent Invocation

### Automatic Delegation

Claude invokes agents based on `description` matching the current task. Strengthen triggers with keywords:

```yaml
description: Use PROACTIVELY after code changes to review for quality issues
```

```yaml
description: MUST BE USED when creating implementation specifications
```

```yaml
description: Use immediately after completing any coding task
```

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

## 8. Example Agents

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

## 9. Orchestration Patterns

### Pipeline Architecture

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

## 10. Context Management

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

## 11. Debugging & Troubleshooting

| Issue                      | Cause                          | Fix                            |
|----------------------------|--------------------------------|--------------------------------|
| Agent not invoked          | Description doesn't match task | Make description more specific |
| Agent has wrong tools      | `tools` field misconfigured    | Check comma-separated list     |
| Hooks not running          | Invalid JSON in settings       | Validate with `jq`             |
| Agent does unexpected work | Missing constraints in prompt  | Add explicit "do NOT" rules    |
| Context exhausted quickly  | Inherited all tools            | Restrict to needed tools only  |

Source: [PubNub Best Practices][pubnub]

### Iterative Refinement

1. Run agent on task
2. Note what went wrong vs. expected
3. Update system prompt with counter-examples
4. Version control agent files for history

> "Use iterative prompting to refine behavior: Supply context on failed actions (what vs. expected), explain desired outcome, pass in the .md config for Claude to suggest modifications." — [PubNub Best Practices][pubnub]

---

## 12. Advanced Patterns

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

## 13. Community Resources

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

## 14. Quick Start Checklist

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

| Key              | Source                                                 |
|------------------|--------------------------------------------------------|
| `[docs]`         | [Claude Code Subagents Documentation][docs]            |
| `[bp]`           | [Claude Code Best Practices][bp]                       |
| `[pubnub]`       | [Best Practices for Claude Code Subagents][pubnub]     |
| `[clog]`         | [ClaudeLog Custom Agents Guide][clog]                  |
| `[medianeth]`    | [Claude Code Frameworks & Sub-Agents 2025][medianeth]  |
| `[awesome]`      | [awesome-claude-code-subagents][awesome]               |
| `[sdk]`          | [Claude Agent SDK Engineering Blog][sdk]               |
| `[cc101]`        | [ClaudeCode101 Context Management][cc101]              |
| `[wshobson]`     | [wshobson/agents][wshobson]                            |
| `[orch]`         | [claude-orchestration][orch]                           |
| `[arxiv-format]` | [The Hidden Cost of Readability (arXiv)][arxiv-format] |
| `[commonmark]`   | [CommonMark Specification][commonmark]                 |
| `[mdguide]`      | [Markdown Guide - Basic Syntax][mdguide]               |
| `[cc-thinking]`  | [Claude Code Thinking Guide][cc-thinking]              |
| `[ext-thinking]` | [Extended Thinking Documentation][ext-thinking]        |

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
