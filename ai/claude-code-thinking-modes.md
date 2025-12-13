# Claude Code Thinking Modes

> Understanding and using extended thinking for complex reasoning tasks

**Research Date**: 2025-12-07

---

## Overview

Extended thinking (also called "thinking mode") gives Claude enhanced reasoning capabilities for complex tasks. When enabled, Claude creates `thinking` content blocks where it outputs internal reasoning step-by-step before delivering a final response.

**Key insight**: Claude Code has special keywords (`think`, `megathink`, `ultrathink`) that activate extended thinking with varying token budgets. These keywords **only work in Claude Code CLI**—not in web chat or API.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Getting Started](#getting-started)
3. [Keyword Hierarchy](#keyword-hierarchy)
4. [Configuration Methods](#configuration-methods)
5. [Cost & Performance](#cost--performance)
6. [Best Practices](#best-practices)
7. [Supported Models](#supported-models)
8. [Limitations](#limitations)
9. [Troubleshooting](#troubleshooting)
10. [Technical Details](#technical-details)
11. [Sources](#sources)

---

## Quick Reference

### When to Use Extended Thinking

| Use Extended Thinking ✅                 | Skip Extended Thinking ⏭️            |
|:----------------------------------------|:-------------------------------------|
| Complex architectural decisions         | Simple documentation and comments    |
| Intricate debugging (multi-layer bugs)  | Code formatting and style fixes      |
| Implementation planning for features    | Quick refactoring and minor cleanups |
| Understanding complex codebases         | Information lookup and retrieval     |
| Evaluating tradeoffs between approaches | Fast prototyping and rapid iteration |
| Math/logic requiring step verification  | Cost-sensitive work                  |
| Security analysis and vulnerabilities   | Straightforward, well-defined tasks  |

### Keyword Cheat Sheet

| Level       | Keywords                     | Budget         | Use For                               |
|:------------|:-----------------------------|:---------------|:--------------------------------------|
| **Basic**   | `think`                      | ~4,000 tokens  | Simple debugging, small tasks         |
| **Medium**  | `think hard`, `megathink`    | ~10,000 tokens | Architecture, complex bugs            |
| **Maximum** | `think harder`, `ultrathink` | ~31,999 tokens | Deep analysis, multi-component design |

**Cost warning**: `ultrathink` can consume 8x more tokens than `think`—use progressively.

---

## Getting Started

### Quick Start (5 Seconds)

Add one of these keywords to your prompt:

```text
think about this bug and suggest a fix
```

```text
ultrathink how to architect this feature
```

That's it. Claude Code will intercept the keyword and activate extended thinking.

### Typical Workflow

1. **Start with no keyword** for simple tasks
2. **Use `think`** if the initial response misses nuances
3. **Escalate to `megathink`** for architectural decisions
4. **Reserve `ultrathink`** for deep analysis requiring maximum reasoning

### Checking If It's Working

When extended thinking is active, you'll see:

- Italic gray text showing Claude's internal reasoning
- Longer response times (2-10x depending on complexity)
- Higher token counts in `/cost` output

---

## Keyword Hierarchy

### Claude Code-Specific Keywords

Claude Code has a preprocessor that intercepts specific keywords and maps them to thinking token budgets. **These keywords ONLY work in Claude Code CLI**—not in web chat or direct API usage.

| Level       | Keywords                                                                                                                    | Token Budget   |
|:------------|:----------------------------------------------------------------------------------------------------------------------------|:---------------|
| **Basic**   | `think`                                                                                                                     | ~4,000 tokens  |
| **Medium**  | `think about it`, `think a lot`, `think deeply`, `think hard`, `think more`, `megathink`                                    | ~10,000 tokens |
| **Maximum** | `think harder`, `think intensely`, `think longer`, `think really hard`, `think super hard`, `think very hard`, `ultrathink` | ~31,999 tokens |

### How Detection Works

The system employs "automatic lexical detection integrated into the engine" that analyzes prompt content in real-time. A parsing function converts trigger expressions into corresponding token allocations.

From deobfuscated source code analysis (November 2025):

```javascript
if (B.includes("think")) return 4000
// Medium keywords return 10000
// Maximum keywords return 31999
```

### November 2025 Update

According to deobfuscation analysis of the Claude Code bundle, **only certain keywords still trigger extended reasoning**. The tiered structure above remains active and verified.

---

## Configuration Methods

### Method 1: Prompt Keywords (Recommended for Claude Code)

**Easiest approach**: Include keywords like `think`, `ultrathink` directly in your prompt text.

```text
think about the edge cases in this authentication flow
```

**Pros**: Simple, no configuration needed
**Cons**: Only works in Claude Code CLI

---

### Method 2: Environment Variable

Set `MAX_THINKING_TOKENS` in `~/.claude/settings.json`:

```json
{
  "env": {
    "MAX_THINKING_TOKENS": "10000"
  }
}
```

**Pros**: Persistent across sessions
**Cons**: Global setting affects all prompts

---

### Method 3: API Configuration (Direct API Usage)

For direct API usage outside Claude Code, add a `thinking` object to your request:

```json
{
  "model": "claude-sonnet-4-5",
  "max_tokens": 16000,
  "thinking": {
    "type": "enabled",
    "budget_tokens": 10000
  },
  "messages": ["..."]
}
```

**Pros**: Fine-grained control per request
**Cons**: Requires API integration, keywords don't work

---

### Method 4: Tab Key Toggle (Claude Code)

In Claude Code CLI, press `Tab` to cycle through modes:

```
Normal → Auto-Accept → Plan Mode
```

**Note**: This changes interaction mode, not thinking budget directly.

---

## Token Budget Guidelines

### Recommended Budgets by Task

| Task Complexity | Budget         | Use Case                              | Example                               |
|:----------------|:---------------|:--------------------------------------|:--------------------------------------|
| Simple          | Skip thinking  | Quick fixes, formatting               | "Fix this typo"                       |
| Medium          | 5,000 tokens   | Simple debugging, small features      | "Debug why this test fails"           |
| Complex         | 10,000 tokens  | Architecture, complex bugs            | "Design API for user authentication"  |
| Very Complex    | 16,000+ tokens | Deep analysis, multi-component design | "Analyze security of this system"     |
| Intensive       | 32,000+ tokens | Use batch processing API              | "Refactor entire module architecture" |

### Budget Constraints

| Constraint                 | Value                                               |
|:---------------------------|:----------------------------------------------------|
| **Minimum budget**         | 1,024 tokens                                        |
| **Maximum budget**         | 128,000 tokens (Claude 3.7+)                        |
| **Relation to max_tokens** | `budget_tokens` < `max_tokens` (except interleaved) |
| **Recommended ratio**      | Set `budget_tokens` to 40%-60% of `max_tokens`      |

---

## Cost & Performance

### Token Billing

⚠️ **Critical**: You are charged for **full thinking tokens**, not the summarized output shown.

| Aspect                      | Detail                                                     |
|:----------------------------|:-----------------------------------------------------------|
| **Billing basis**           | Full internal reasoning tokens, not visible summary        |
| **Token count mismatch**    | Billed output tokens ≠ visible token count                 |
| **Claude 4 behavior**       | Thinking is summarized for display, but you pay for full   |
| **Previous turn caching**   | Thinking blocks count as input tokens when cached          |

### Example Cost Impact

```text
Prompt: "ultrathink how to optimize this algorithm"

Visible output: 500 tokens
Actual thinking: 25,000 tokens
Billed output: 25,500 tokens (50x higher than visible!)
```

### Response Time Impact

| Factor                   | Impact                                 |
|:-------------------------|:---------------------------------------|
| **Typical slowdown**     | 2-10x longer processing time           |
| **Streaming threshold**  | Required when `max_tokens` > 21,333    |
| **Large budgets (32k+)** | Use batch processing to avoid timeouts |

### Cache Behavior

- ❌ Changing thinking parameters invalidates message cache breakpoints
- ✅ System prompts and tools remain cached despite thinking parameter changes
- 💡 Consider 1-hour cache duration for long-running sessions

---

## Best Practices

### Progressive Escalation Strategy

**Don't start with `ultrathink`**—escalate progressively:

```text
1. First attempt: No keyword
2. If inadequate: Add "think"
3. If still inadequate: Use "think hard" or "megathink"
4. Last resort: Use "ultrathink" for maximum reasoning
```

### Plan Before Code Workflow

For complex features, use the "think + plan" workflow:

```text
Step 1: "think hard about the architecture for this feature"
Step 2: Review the thinking output and plan
Step 3: Implement without thinking keywords (faster execution)
```

### Cost Monitoring

- Use `/cost` command regularly to track token consumption
- Set budget alerts if your provider supports them
- Compare costs with and without thinking for your use case

### Model Selection

| Model          | When to Use                               |
|:---------------|:------------------------------------------|
| **Haiku 4.5**  | Simple tasks, cost-sensitive work         |
| **Sonnet 4.5** | Balanced complexity (default)             |
| **Opus 4.5**   | Maximum reasoning depth, complex analysis |

**Tip**: Opus 4.5 with thinking is the most capable but also most expensive—reserve for truly complex problems.

---

## Supported Models

Extended thinking is supported in:

| Model                          | Model ID                     | Thinking Output | Interleaved | Block Preservation |
|:-------------------------------|:-----------------------------|:----------------|:------------|:-------------------|
| Claude Opus 4.5                | `claude-opus-4-5-20251101`   | Summarized      | Yes (beta)  | Yes (default)      |
| Claude Opus 4.1                | `claude-opus-4-1-20250805`   | Summarized      | Yes (beta)  | Not preserved      |
| Claude Opus 4                  | `claude-opus-4-20250514`     | Summarized      | Yes (beta)  | Not preserved      |
| Claude Sonnet 4.5              | `claude-sonnet-4-5-20250929` | Summarized      | Yes (beta)  | Not preserved      |
| Claude Sonnet 4                | `claude-sonnet-4-20250514`   | Summarized      | Yes (beta)  | Not preserved      |
| Claude Haiku 4.5               | `claude-haiku-4-5-20251001`  | Summarized      | Yes (beta)  | Not preserved      |
| Claude Sonnet 3.7 (deprecated) | `claude-3-7-sonnet-20250219` | Full output     | No          | Not preserved      |

### Feature Differences

- **Thinking Output**: Claude 4+ summarizes thinking for display; 3.7 shows full output
- **Interleaved Thinking**: Claude 4+ can reason between tool calls (beta feature)
- **Block Preservation**: Only Opus 4.5+ preserves thinking blocks by default

---

## Limitations

### Platform-Specific Limitations

| Limitation                 | Description                                                  |
|:---------------------------|:-------------------------------------------------------------|
| **Claude Code Only**       | Keywords like `ultrathink` ONLY work in Claude Code CLI      |
| **English Only**           | Keywords must be in English—synonyms in other languages fail |
| **No Temperature Control** | Thinking isn't compatible with `temperature` or `top_k`      |
| **No Pre-filling**         | Cannot pre-fill responses when thinking is enabled           |
| **No Forced Tool Use**     | Thinking isn't compatible with forced tool use               |

### Common Issues

**Issue**: Keyword doesn't trigger thinking
**Cause**: Using outside Claude Code CLI (e.g., web chat)
**Solution**: Use API configuration method instead

**Issue**: Token count way higher than expected
**Cause**: Using `ultrathink` when `think` would suffice
**Solution**: Use progressive escalation strategy

---

## Troubleshooting

| Problem                              | Likely Cause                             | Solution                                         |
|:-------------------------------------|:-----------------------------------------|:-------------------------------------------------|
| Keyword not working                  | Not using Claude Code CLI                | Use API configuration or switch to Claude Code   |
| Unexpectedly high token costs        | `ultrathink` when simpler level suffices | Start with `think`, escalate only if needed      |
| Response timeout                     | Budget too high (32k+) for streaming     | Use batch processing API or reduce budget        |
| Cache invalidation                   | Changed thinking parameters              | Keep thinking settings consistent within session |
| Non-English keyword doesn't work     | Keywords must be English                 | Use English keywords or API configuration        |
| `budget_tokens` > `max_tokens` error | Budget exceeds max                       | Set `budget_tokens` to 40%-60% of `max_tokens`   |

---

## Technical Details

### How Claude Code Implements Thinking

Claude Code has a preprocessing layer that:

1. Intercepts prompts before sending to the model
2. Matches keywords against regular expressions
3. Sets corresponding token budgets programmatically
4. Sends the modified request to Claude API

This is a **hard-coded feature** in Claude Code's `cli.js` bundle, not an inherent model capability.

### Keyword Detection Implementation

From deobfuscated source code (November 2025):

```javascript
function detectThinkingLevel(prompt) {
  if (prompt.includes("think harder") ||
      prompt.includes("ultrathink") ||
      prompt.includes("think really hard")) {
    return 31999;
  }
  if (prompt.includes("think hard") ||
      prompt.includes("megathink") ||
      prompt.includes("think deeply")) {
    return 10000;
  }
  if (prompt.includes("think")) {
    return 4000;
  }
  return 0; // No extended thinking
}
```

**Key insight**: Detection is literal string matching—keywords must be exact (case-insensitive).

---

## Summary

**Extended thinking trades speed and cost for reasoning depth.** Use it strategically:

- **Start simple**: Most tasks don't need extended thinking
- **Escalate progressively**: `think` → `megathink` → `ultrathink`
- **Monitor costs**: Thinking tokens can be 8x+ your visible output
- **Plan before code**: Use thinking for planning, then execute without it
- **Know your tools**: Keywords only work in Claude Code CLI

**Remember**: More thinking isn't always better—match the thinking level to task complexity.

---

## Sources

### Official Documentation

- [Anthropic Extended Thinking Documentation](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Claude's Extended Thinking Announcement](https://www.anthropic.com/news/visible-extended-thinking)
- [AWS Bedrock Extended Thinking](https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-extended-thinking.html)
- [Extended Thinking Practical Settings](https://claude-ai.chat/guides/extended-thinking/)
- [How to Use Claude 4 Extended Thinking](https://www.cometapi.com/how-to-use-claude-4-extended-thinking/)

### Community Resources

- [What is UltraThink in Claude Code - ClaudeLog](https://claudelog.com/faqs/what-is-ultrathink/)
- [The Ultrathink Mystery - ITECS Blog](https://itecsonline.com/post/the-ultrathink-mystery-does-claude-really-think-harder)
- [Ultrathink is a Claude Code Magic Word - Hacker News](https://news.ycombinator.com/item?id=43739997)
- [Think, Megathink, Ultrathink Decoded - SmartNested](https://smartnested.com/think-megathink-ultrathink-claude-codes-power-keywords-decoded/)
- [Claude Code Ultrathink Secret Prompt - wenaidev](https://www.wenaidev.com/blog/en/claude-code-ultrathink-secret-prompt)
- [Claude Code Thinking - Steve Kinney](https://stevekinney.com/courses/ai-development/claude-code-thinking)
- [Claude Extended Thinking Guide - GitHub Gist](https://gist.github.com/intellectronica/58571dda3581eec3e17a77741e8c858a)
- [What Still Works in Claude Code Nov 2025 - Level Up Coding](https://levelup.gitconnected.com/what-still-works-in-claude-code-nov-2025-ultrathink-tab-and-plan-mode-2ade26f7f45c)
- [Claude Code Thinking Levels - GoatReview](https://goatreview.com/claude-code-thinking-levels-think-ultrathink/)
- [Unlocking Claude Code's Hidden Thinking Levels - mauricioacosta.dev](https://www.mauricioacosta.dev/blog/claude-code-thinking-levels-ultrathink)
- [Claude Code: The Missing Manual - Arthur Clune](https://clune.org/posts/claude-code-manual/)
- [Claude Code Prompts & Tool Definitions - AI Engineer Guide](https://aiengineerguide.com/blog/claude-code-prompt/)

### Simon Willison's Coverage

- [Claude Code Best Practices Analysis](https://simonwillison.net/2025/Apr/19/claude-code-best-practices/)
- [Claude 3.7 Sonnet Extended Thinking](https://simonwillison.net/2025/Feb/25/llm-anthropic-014/)
- [Claude 3.7 Extended Thinking Substack](https://simonw.substack.com/p/claude-37-sonnet-extended-thinking)

### GitHub Issues

- [BUG: Extended Thinking fails on non-English synonyms - Issue #1284](https://github.com/anthropics/claude-code/issues/1284)
- [BUG: max_tokens must be greater than thinking.budget_tokens - Issue #8756](https://github.com/anthropics/claude-code/issues/8756)
