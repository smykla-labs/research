# Claude Code Extensibility Guide

Comprehensive guide to Skills, Subagents, Slash Commands, and MCP in Claude Code.

---

## Quick Reference: The Four Extension Mechanisms

| Mechanism          | Location            | Invocation       | Context         | Primary Use Case                      |
|:-------------------|:--------------------|:-----------------|:----------------|:--------------------------------------|
| **Skills**         | `.claude/skills/`   | Automatic        | Main window     | Complex workflows with multiple files |
| **Subagents**      | `.claude/agents/`   | Automatic/Manual | Isolated window | Specialized autonomous tasks          |
| **Slash Commands** | `.claude/commands/` | Manual (`/cmd`)  | Main window     | Quick prompts, orchestration          |
| **MCP Servers**    | External process    | Automatic        | N/A (tools)     | External integrations                 |

---

## 1. Skills

### What Are Skills?

**Skills** are modular capabilities packaged as directories containing a `SKILL.md` file plus optional supporting files. They extend Claude's functionality with specialized knowledge, workflows, and tools.

**Key Characteristics:**

- **Model-invoked**: Claude automatically activates Skills based on context and the Skill's description
- **Directory-based**: Each Skill is a directory with `SKILL.md` + optional resources
- **Progressive loading**: Supporting files are loaded on-demand, not upfront
- **Shareable**: Project Skills (`.claude/skills/`) are shared via git

### Skill Locations

```
~/.claude/skills/           # Personal (available everywhere)
.claude/skills/             # Project (shared via git)
plugins/*/skills/           # Plugin-provided
```

### SKILL.md Structure

```yaml
---
name: my-skill-name
description: What the skill does and when to use it
allowed-tools: Read, Grep, Glob  # Optional - restricts tools
---

# My Skill Name

## Instructions

Step-by-step guidance for Claude.

## Examples

Concrete usage examples.
```

### Frontmatter Fields

| Field           | Required | Constraints                           |
|:----------------|:---------|:--------------------------------------|
| `name`          | Yes      | Lowercase, hyphens only; max 64 chars |
| `description`   | Yes      | Max 1024 chars; must include trigger  |
| `allowed-tools` | No       | Comma-separated tool names            |

### When to Use Skills

**Use Skills for:**

- Complex workflows requiring multiple files (scripts, templates, references)
- Capabilities Claude should discover automatically
- Knowledge that benefits from progressive file disclosure
- Team-shared domain expertise

**Don't use Skills for:**

- Simple prompts (use Slash Commands)
- Autonomous tasks needing isolated context (use Subagents)
- External API integrations (use MCP)

### Creating a Skill

**Step 1: Create directory structure**

```bash
# Personal Skill
mkdir -p ~/.claude/skills/code-reviewer
touch ~/.claude/skills/code-reviewer/SKILL.md

# Project Skill (team-shared)
mkdir -p .claude/skills/code-reviewer
touch .claude/skills/code-reviewer/SKILL.md
```

**Step 2: Write SKILL.md**

```markdown
---
name: code-reviewer
description: Reviews code for quality, security, and best practices. Use when reviewing code, analyzing PRs, or checking code quality.
allowed-tools: Read, Grep, Glob
---

# Code Reviewer

## Instructions

1. Identify files to review using Glob
2. Read file contents using Read
3. Search for patterns using Grep
4. Analyze for:
   - Security vulnerabilities
   - Performance issues
   - Code style violations
   - Best practice adherence
5. Provide prioritized feedback

## Review Categories

- **Critical**: Security holes, data loss risks
- **Warning**: Performance issues, maintainability
- **Info**: Style suggestions, minor improvements
```

**Step 3: Add supporting files (optional)**

```
.claude/skills/code-reviewer/
├── SKILL.md
├── checklists/
│   ├── security.md
│   └── performance.md
└── examples/
    └── review-output.md
```

### Skill Example: PDF Processing

```
~/.claude/skills/pdf-processor/
├── SKILL.md
├── FORMS.md
└── scripts/
    └── fill_form.py
```

```markdown
---
name: pdf-processor
description: Process PDF files - extract text, fill forms, merge documents. Use when working with PDF files, forms, or document extraction.
---

# PDF Processor

## Capabilities

- Extract text and tables from PDFs
- Fill PDF forms programmatically
- Merge multiple PDFs
- Split PDFs by page range

## Instructions

1. Identify the PDF operation needed
2. Read reference files for specific guidance:
   - Form filling: See FORMS.md
3. Use scripts in `scripts/` for automation
4. Validate output before returning
```

---

## 2. Subagents

### What Are Subagents?

**Subagents** are specialized AI assistants with their own isolated context window. They're invoked via the Task tool and return only a summary to the main conversation.

**Key Characteristics:**

- **Isolated context**: Prevents pollution of main conversation
- **Custom system prompt**: Domain-specific instructions
- **Scoped tool access**: Least-privilege permissions
- **Model selection**: Haiku/Sonnet/Opus tradeoffs

### Subagent Locations

```
.claude/agents/           # Project-level (higher priority)
~/.claude/agents/         # User-level (global)
```

### Subagent Structure

```markdown
---
name: agent-name
description: When and why to use this agent
tools: Read, Grep, Glob           # Optional - inherits all if omitted
model: sonnet                     # Optional - sonnet|opus|haiku
permissionMode: default           # Optional
---

You are a [role] specializing in [domain].

## Workflow

1. First action
2. Second action
3. Verification

## Constraints

- **NEVER** — absolute prohibition
- **ALWAYS** — mandatory action

## Output Format

Expected deliverable format.
```

### When to Use Subagents

**Use Subagents for:**

- Complex investigation that would pollute main context
- Parallelizable tasks
- Specialized tool access (e.g., read-only reviewers)
- Tasks requiring extended reasoning (Opus model)

**Don't use Subagents for:**

- Quick prompts (use Slash Commands)
- Tasks needing conversation context (use Skills or Commands)
- Simple file operations (too much overhead)

### Subagent Limitations

Two critical limitations affect architecture:

1. **AskUserQuestion filtered**: Subagents cannot use this tool directly
2. **Task tool unavailable**: Subagents cannot spawn other subagents

**Implication**: All user interaction and multi-agent orchestration must happen at the parent level (Commands or main conversation).

### Creating a Subagent

**Step 1: Create agent file**

```bash
mkdir -p .claude/agents
touch .claude/agents/code-reviewer.md
```

**Step 2: Write agent definition**

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
2. Analyze modified files for issues
3. Provide prioritized feedback

## Review Checklist

- Code clarity and readability
- No duplicated code
- Proper error handling
- No exposed secrets
- Adequate test coverage

## Constraints

- **NEVER modify** — Read-only analysis only
- **ALWAYS prioritize** — Critical issues first

## Output Format

**Critical** (must fix):
- [Issue with file:line and fix suggestion]

**Warnings** (should fix):
- [Issue with rationale]

**Suggestions** (consider):
- [Improvement opportunity]

## Done When

- [ ] All changed files reviewed
- [ ] Issues categorized by severity
- [ ] Actionable suggestions provided
```

### Tool Selection by Role

| Agent Role    | Recommended Tools                       |
|:--------------|:----------------------------------------|
| Reviewer      | `Read, Grep, Glob`                      |
| Researcher    | `Read, Grep, Glob, WebFetch, WebSearch` |
| Planner       | `Read, Grep, Glob, Bash, Write`         |
| Implementer   | `Read, Edit, Write, Bash, Grep, Glob`   |

### Model Selection

| Model      | Use Case                         | Cost/Speed            |
|:-----------|:---------------------------------|:----------------------|
| **Haiku**  | Lightweight, frequent-use agents | 3x cheaper, 2x faster |
| **Sonnet** | Balanced complexity (default)    | Standard              |
| **Opus**   | Complex analysis, deep reasoning | Most capable          |

---

## 3. Slash Commands

### What Are Slash Commands?

**Slash Commands** are user-invoked shortcuts stored as Markdown files. When you type `/command-name`, Claude Code executes the prompt.

**Key Characteristics:**

- **Explicit invocation**: User types `/command` to trigger
- **Runs in main context**: Results persist in conversation
- **Parameterizable**: `$ARGUMENTS`, `$1`, `$2`
- **Dynamic context**: Pre-execute bash commands (`!`backtick``)

### Command Locations

```
.claude/commands/         # Project-level (shared via git)
~/.claude/commands/       # User-level (personal)
```

### Command Structure

```markdown
---
allowed-tools: Bash(git:*), Read, Write
argument-hint: <file-path|@file>
description: What this command does
model: haiku
---

Purpose statement.

$ARGUMENTS

## Context

- Current branch: !`git branch --show-current`
- Status: !`git status --short`

## Workflow

1. Step one
2. Step two
```

### When to Use Slash Commands

**Use Slash Commands for:**

- Frequently used prompts
- Quick, well-defined tasks
- Orchestrating subagents
- Tasks needing conversation context

**Don't use Slash Commands for:**

- Complex multi-file workflows (use Skills)
- Isolated investigation (use Subagents)
- External integrations (use MCP)

### Creating a Slash Command

**Step 1: Create command file**

```bash
mkdir -p .claude/commands/git
touch .claude/commands/git/commit.md
```

**Step 2: Write command**

```markdown
---
allowed-tools: Bash(git:*)
argument-hint: [message]
description: Create a git commit with staged changes
---

Create a commit for the staged changes.

$ARGUMENTS

## Context

- Status: !`git status --short`
- Staged: !`git diff --cached --stat`
- Recent: !`git log --oneline -5`

## Constraints

- Follow conventional commits format
- Title ≤50 characters
- Include body if changes are complex
```

**Usage:**

```
/commit feat: add user authentication
```

### Command + Subagent Orchestration

Commands excel at orchestrating subagents, especially for handling user input:

```markdown
---
argument-hint: <file-or-description>
description: Review code using the code-reviewer agent
---

Use the code-reviewer agent.

$ARGUMENTS

## Workflow

1. **Invoke code-reviewer** with Task tool
2. **Parse status block** from output:
   - `STATUS: NEEDS_INPUT` → Use `AskUserQuestion`, resume with `ANSWERS:`
   - `STATUS: COMPLETED` → Report findings to user
3. **Repeat** until `STATUS: COMPLETED`

**CRITICAL**: For NEEDS_INPUT, use `AskUserQuestion` tool. Do NOT print questions.
```

---

## 4. MCP (Model Context Protocol)

### What Is MCP?

**MCP** is an open-source protocol for connecting Claude Code to external systems. It provides standardized access to:

- **Tools**: Executable functions (GitHub, Sentry, databases)
- **Resources**: Data sources accessible via `@` mentions
- **Prompts**: Reusable instruction templates

### MCP Architecture

```
┌─────────────────┐
│  Claude Code    │  ← MCP Host (Client)
│  (Client)       │
└────────┬────────┘
         │ JSON-RPC 2.0
┌────────▼────────┐
│  MCP Server     │  ← External process
│  (Provider)     │
└────────┬────────┘
         │
┌────────▼────────┐
│  Capabilities   │
│  • Tools        │
│  • Resources    │
│  • Prompts      │
└─────────────────┘
```

### Transport Types

| Transport | Use Case                  | Security            |
|:----------|:--------------------------|:--------------------|
| **HTTP**  | Cloud services (OAuth)    | Best for remote     |
| **Stdio** | Local processes           | Best for local      |
| **SSE**   | Deprecated (use HTTP)     | Legacy              |

### MCP Configuration

**Add a server:**

```bash
# HTTP (remote)
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# Stdio (local)
claude mcp add --transport stdio airtable \
  --env AIRTABLE_API_KEY=YOUR_KEY \
  -- npx -y airtable-mcp-server
```

**Configuration files:**

| Scope   | Location         | Use Case                    |
|:--------|:-----------------|:----------------------------|
| Local   | `~/.claude.json` | Personal, sensitive configs |
| Project | `.mcp.json`      | Team-shared via git         |
| User    | `~/.claude.json` | Personal, all projects      |

### When to Use MCP

**Use MCP for:**

- External service integrations (GitHub, Jira, Slack)
- Database connections
- Third-party APIs
- Custom tooling exposed as services

**Don't use MCP for:**

- Local file operations (use native tools)
- Simple prompts (use Slash Commands)
- Domain knowledge (use Skills or Subagents)

### Creating an MCP Server

**Python (FastMCP):**

```python
from mcp.server.fastmcp import FastMCP

server = FastMCP("weather-server")

@server.tool()
def get_weather(location: str, units: str = "celsius") -> str:
    """Get current weather for a location."""
    return f"Weather in {location}: 72°{units[0].upper()}"

@server.resource("weather://{location}")
def get_weather_data(location: str) -> str:
    """Get historical weather data."""
    return f"Historical data for {location}..."

if __name__ == "__main__":
    server.run()
```

**TypeScript (MCP SDK):**

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "weather-server",
  version: "1.0.0",
});

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: "get_weather",
    description: "Get weather for a location",
    inputSchema: {
      type: "object",
      properties: {
        location: { type: "string" }
      },
      required: ["location"]
    }
  }]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => ({
  content: [{ type: "text", text: `Weather in ${request.params.arguments.location}: 72°F` }]
}));

const transport = new StdioServerTransport();
await server.connect(transport);
```

---

## 5. Comparison Matrix

### Feature Comparison

| Feature              | Skills          | Subagents   | Commands        | MCP            |
|:---------------------|:----------------|:------------|:----------------|:---------------|
| **Invocation**       | Automatic       | Auto/Manual | Manual (`/`)    | Automatic      |
| **Context**          | Main window     | Isolated    | Main window     | N/A            |
| **Multi-file**       | Yes             | No          | No              | N/A            |
| **Tool restriction** | `allowed-tools` | `tools:`    | `allowed-tools` | Server-defined |
| **Model selection**  | No              | Yes         | Yes             | N/A            |
| **User interaction** | Yes             | Via relay   | Yes             | Yes            |
| **Shareable**        | Git             | Git         | Git             | Config/Code    |
| **External systems** | No              | No          | No              | Yes            |

### Architecture Differences

```
Skills:
  User → Claude → [Skill activated by context] → Result in main window

Subagents:
  User → Claude → [Task tool] → [Isolated agent] → Summary returned

Commands:
  User → /command → [Prompt executed] → Result in main window

MCP:
  User → Claude → [MCP tool call] → [External server] → Tool result
```

### Use Case Matrix

| Scenario                          | Best Choice    | Why                              |
|:----------------------------------|:---------------|:---------------------------------|
| Quick commit message              | Command        | Simple, explicit, fast           |
| PDF form filling                  | Skill          | Complex, multi-file, automatic   |
| Code review                       | Subagent       | Isolated context, specialized    |
| GitHub integration                | MCP            | External API                     |
| Database queries                  | MCP            | External system                  |
| Research with web search          | Subagent       | Isolated, parallelizable         |
| Project-specific prompts          | Command        | Team-shared, explicit            |
| Complex workflow with scripts     | Skill          | Multi-file, progressive loading  |
| Orchestrating multiple agents     | Command        | Controls flow, handles input     |

---

## 6. Decision Framework

Use this flowchart to decide which mechanism to use:

```
START
  │
  ├─ Need external service? ──────────────────────────────────→ MCP
  │
  ├─ Need isolated context? ──────────────────────────────────→ Subagent
  │
  ├─ Multiple supporting files needed? ───────────────────────→ Skill
  │
  ├─ Explicit user invocation? ───────────────────────────────→ Command
  │
  ├─ Should activate automatically based on context? ────────→ Skill
  │
  ├─ Needs specialized model (Opus/Haiku)? ───────────────────→ Subagent
  │
  ├─ Quick, single-purpose prompt? ───────────────────────────→ Command
  │
  └─ Complex autonomous task? ────────────────────────────────→ Subagent
```

### Quick Decision Table

| I want to...                                     | Use      |
|:-------------------------------------------------|:---------|
| Run a quick, predefined prompt                   | Command  |
| Integrate with GitHub/Jira/Slack                 | MCP      |
| Have Claude automatically recognize a capability | Skill    |
| Delegate investigation without context pollution | Subagent |
| Share project-specific workflows with team       | Command  |
| Package complex domain knowledge                 | Skill    |
| Use a different model for specific tasks         | Subagent |
| Query external databases                         | MCP      |
| Orchestrate multiple specialized agents          | Command  |

---

## 7. Integration Patterns

### Skill + Subagent

Skills can reference subagents in their instructions:

```yaml
---
name: comprehensive-review
description: Full code review with architecture analysis
---

## Instructions

1. Use the code-reviewer agent for line-by-line analysis
2. Use the architecture-analyzer agent for structural review
3. Synthesize findings into actionable report
```

### Command + Subagent + MCP

Commands orchestrate complex workflows:

```yaml
---
description: Create PR with review and GitHub integration
---

## Workflow

1. **Use code-reviewer agent** to analyze changes
2. **Use GitHub MCP** to create PR
3. **Use reviewer-assignment MCP** to assign reviewers
4. Report PR URL to user
```

### Status-Based Orchestration

Standard pattern for multi-agent workflows:

```
Command
  │
  ├─→ Invoke agent-1
  │   └─→ STATUS: NEEDS_INPUT
  │       └─→ Command uses AskUserQuestion
  │           └─→ Resume agent-1 with ANSWERS:
  │
  ├─→ STATUS: READY_FOR_REVIEW
  │   └─→ Command invokes quality-reviewer
  │       └─→ Grade A → Write file → Done
  │       └─→ Grade < A → Resume with feedback
  │
  └─→ STATUS: COMPLETED → Report to user
```

---

## 8. Best Practices

### Naming Conventions

| Type     | Convention                     | Example                    |
|:---------|:-------------------------------|:---------------------------|
| Skill    | `lowercase-hyphen`             | `pdf-processor`            |
| Subagent | `role-based-name`              | `code-reviewer`            |
| Command  | `verb` or `noun`               | `commit`, `review`         |
| MCP      | `service-name`                 | `github`, `notion`         |

### Description Quality

**Good description (Skill):**

```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files, forms, or document extraction.
```

**Good description (Subagent):**

```yaml
description: Reviews code for quality and security. Use PROACTIVELY after writing or modifying code.
```

### Tool Restriction

Apply least-privilege principle:

| Role       | Tools                           |
|:-----------|:--------------------------------|
| Read-only  | `Read, Grep, Glob`              |
| Writer     | `Read, Edit, Write, Glob, Grep` |
| Full       | (omit to inherit all)           |

### Error Handling

**In Subagents:**

```markdown
## Edge Cases

- **Empty input**: Ask for clarification via STATUS: NEEDS_INPUT
- **File not found**: Report specific error, suggest alternatives
- **Uncertainty**: Output STATUS: NEEDS_INPUT — never guess
```

**In Commands:**

```markdown
**CRITICAL**: For NEEDS_INPUT, use `AskUserQuestion` tool. Do NOT print questions.
```

---

## 9. Quick Start Checklists

### Creating a Skill

- [ ] Create `.claude/skills/{name}/` directory
- [ ] Write `SKILL.md` with frontmatter
- [ ] Include `description` with trigger phrases
- [ ] Add `allowed-tools` if restricting access
- [ ] Add supporting files if needed
- [ ] Test: Ask Claude about the capability

### Creating a Subagent

- [ ] Create `.claude/agents/{name}.md`
- [ ] Add frontmatter: `name`, `description`, `tools`, `model`
- [ ] Write system prompt with Workflow section
- [ ] Add Constraints with strong keywords
- [ ] Add Edge Cases including uncertainty handling
- [ ] Add Done When checklist
- [ ] Test: Ask Claude to use the agent

### Creating a Slash Command

- [ ] Create `.claude/commands/{name}.md`
- [ ] Add frontmatter: `description`, `argument-hint`
- [ ] Include `$ARGUMENTS` for user input
- [ ] Add `allowed-tools` if using bash pre-execution
- [ ] Add Context section with `!`backtick`` if needed
- [ ] Test: Type `/command-name`

### Adding an MCP Server

- [ ] Choose transport: HTTP (remote) or Stdio (local)
- [ ] Run: `claude mcp add --transport {type} {name} {url-or-command}`
- [ ] Add environment variables with `--env`
- [ ] Authenticate if needed: `/mcp`
- [ ] Test: Ask Claude to use the integration

---

## 10. Troubleshooting

### Skill Not Activating

| Issue                  | Cause                    | Fix                              |
|:-----------------------|:-------------------------|:---------------------------------|
| Claude ignores Skill   | Vague description        | Add specific trigger phrases     |
| Wrong Skill activated  | Competing descriptions   | Make descriptions more distinct  |
| SKILL.md not found     | Wrong directory          | Check `~/.claude/skills/{name}/` |

### Subagent Issues

| Issue                  | Cause                    | Fix                              |
|:-----------------------|:-------------------------|:---------------------------------|
| Agent not invoked      | Description mismatch     | Make description more specific   |
| AskUserQuestion fails  | Tool filtered            | Use STATUS: NEEDS_INPUT relay    |
| Task tool fails        | Can't spawn subagent     | Use parent orchestration         |
| Wrong tools available  | `tools:` misconfigured   | Check comma-separated list       |

### Command Issues

| Issue                  | Cause                    | Fix                              |
|:-----------------------|:-------------------------|:---------------------------------|
| Command not in /help   | File not found           | Check `.claude/commands/`        |
| Arguments not passed   | Missing `$ARGUMENTS`     | Add `$ARGUMENTS` to content      |
| Bash pre-exec fails    | Missing `allowed-tools`  | Add `Bash(cmd:*)` to frontmatter |

### MCP Issues

| Issue                  | Cause                    | Fix                              |
|:-----------------------|:-------------------------|:---------------------------------|
| Server not connecting  | Wrong transport/URL      | Check `claude mcp list`          |
| Authentication failed  | OAuth not completed      | Run `/mcp` and authenticate      |
| Tools not appearing    | Server not started       | Check server logs                |
| Timeout errors         | Slow startup             | Set `MCP_TIMEOUT=30000`          |

---

## Sources

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Slash Commands Documentation](https://code.claude.com/docs/en/slash-commands)
- [MCP Documentation](https://modelcontextprotocol.io)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Subagents Guide](claude-code-subagents-guide.md) (local)
- [Commands Guide](claude-code-commands-guide.md) (local)