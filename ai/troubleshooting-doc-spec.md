# Troubleshooting Documentation Specification

> Guidelines for writing clear, actionable troubleshooting guides that get users back to work fast

**Synthesized from runbook best practices and technical writing research (2025)**

---

## Overview

Troubleshooting documentation must solve problems, not explain them. Readers arrive frustrated and want one thing: **a working system**. This specification provides a structure that minimizes time-to-resolution while maintaining completeness.

**Key insight**: Google research shows structured runbooks produce a **3x improvement in Mean Time To Resolution (MTTR)** compared to ad-hoc troubleshooting. This applies to all troubleshooting documentation—not just incident runbooks.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Core Principles](#core-principles)
3. [Document Structure](#document-structure)
4. [Writing Rules](#writing-rules)
5. [Common Anti-Patterns](#common-anti-patterns)
6. [Quality Checklist](#quality-checklist)
7. [Example Template](#example-template)
8. [Sources](#sources)

---

## Quick Reference

### Document Structure at a Glance

```text
1. Problem        ─ What's broken (1-2 sentences)
2. Am I Affected? ─ Quick diagnostic to confirm the issue
3. Solution       ─ How to fix it (copy-pasteable commands)
4. Root Cause     ─ Why it happens (for understanding)
5. References     ─ External links, issue trackers
```

**Order matters**: Solution comes BEFORE root cause explanation. Readers want to fix first, understand later.

### The 5 A's Framework

| Principle         | What It Means                                            | Test It With                                    |
|:------------------|:---------------------------------------------------------|:------------------------------------------------|
| **Actionable**    | Every step is a command or clear action, not a paragraph | Can I copy-paste this?                          |
| **Accessible**    | Scannable in seconds; reader finds what they need fast   | Can I find the fix in under 10 seconds?         |
| **Accurate**      | Current, verified information matching real behavior     | Did I test this recently?                       |
| **Authoritative** | Single source of truth; no conflicting guidance          | Is there contradictory info elsewhere?          |
| **Adaptable**     | Easy to update as systems evolve                         | Can I update one section without rewriting all? |

### Writing Checklist

- [ ] Problem statement is 1-3 sentences
- [ ] Diagnostic comes before solution
- [ ] Solution comes before explanation
- [ ] All commands are copy-pasteable
- [ ] No redundant sections
- [ ] No "Key Takeaways" or summary

---

## Core Principles

### Reader-First Philosophy

Readers arrive with a problem. They want to:

1. **Confirm** they have the issue described
2. **Fix** it with minimal reading
3. **Understand** why (optional, for those who want depth)

Structure documents in that exact order.

### The MTTR Imperative

> Google estimates that structured runbooks produce roughly a **3x improvement in MTTR** compared to ad-hoc troubleshooting.

Every design decision in this spec optimizes for reducing Mean Time To Resolution:

- Diagnostic first → confirms reader has the right doc
- Solution before explanation → gets system working faster
- Copy-pasteable commands → eliminates transcription errors
- No redundancy → reduces search time

### Information Hierarchy

| Priority | Section             | Reader Type                           |
|:---------|:--------------------|:--------------------------------------|
| Highest  | Problem & Diagnosis | Everyone (needs to confirm relevance) |
| High     | Solution            | Users who just want it fixed          |
| Medium   | Root Cause          | Users who want to understand          |
| Low      | References          | Users investigating deeper issues     |

---

## Document Structure

### Required Sections (Order Matters)

#### 1. Problem

**Purpose**: Immediate context in one glance.

**Requirements**:

- Maximum 2-3 sentences
- State what's broken and what effect it has
- No background, history, or preamble

**Format**:

```markdown
## Problem

<!-- One sentence stating what's broken and observable symptom -->
<!-- Optional: One sentence on impact or when it occurs -->
```

**Example**:

```markdown
## Problem

Claude Code's Bash tool generates bash syntax but executes commands using `$SHELL` inherited from the terminal. If your terminal uses Fish or zsh, commands fail with syntax errors.
```

**Anti-patterns**:

- ❌ Long history of how the issue was discovered
- ❌ Multiple paragraphs of context
- ❌ Starting with "Background" or "Overview"

---

#### 2. Am I Affected?

**Purpose**: Reader confirms they have this specific problem before reading further.

**Requirements**:

- Single diagnostic command or check (prefer copy-pasteable)
- Clear interpretation table or list
- Symptoms grouped by severity/type if multiple exist

**Format**:

````markdown
## Am I Affected?

Run this command:

```bash
# diagnostic command
```

Interpret the result:

| Output           | Status     | Action                |
|:-----------------|:-----------|:----------------------|
| <!-- value 1 --> | ✅ No issue | No action             |
| <!-- value 2 --> | ⚠️ Warning | <!-- fix -->          |
| <!-- value 3 --> | ❌ Critical | Follow solution below |
````

**Example**:

````markdown
## Am I Affected?

Check your shell:

```bash
echo $SHELL
```

Interpret the result:

| Output      | Status     | Action                     |
|:------------|:-----------|:---------------------------|
| `/bin/bash` | ✅ No issue | No action needed           |
| `/bin/zsh`  | ⚠️ Partial | Commands may fail randomly |
| `/bin/fish` | ❌ Critical | Follow solution below      |
````

**Alternative format** (for symptom-based diagnosis):

```markdown
## Am I Affected?

You're affected if you see any of these symptoms:

- ❌ **Critical**: Bash commands fail with syntax errors
- ⚠️ **Warning**: Variables expand incorrectly
- ✅ **Normal**: Commands execute successfully
```

---

#### 3. Solution

**Purpose**: Fix the problem with minimal cognitive load.

**Requirements**:

- Comes BEFORE root cause explanation
- Copy-pasteable commands/configs
- Multiple paths if different environments need different fixes
- Verification steps at the end

**Format**:

````markdown
## Solution

<!-- One sentence summary of the fix -->

### <!-- Environment/Method 1 -->

```bash
# copy-pasteable commands
```

### <!-- Environment/Method 2 -->

```bash
# alternative commands
```

### Verify

```bash
# verification command
```

Expected output:

```text
<!-- expected output confirming fix -->
```
````

**Example**:

````markdown
## Solution

Configure Claude Code to use Bash explicitly instead of inheriting `$SHELL`.

### Option 1: Global Setting (Recommended)

Add to `~/.claude/settings.json`:

```json
{
  "bashPath": "/bin/bash"
}
```

### Option 2: Project Setting

Add to `.claude/settings.json`:

```json
{
  "bashPath": "/bin/bash"
}
```

### Verify

Restart Claude Code and run:

```bash
echo "Test successful"
```

Expected: Command completes without errors.
````

**Anti-patterns**:

- ❌ Explanation before solution
- ❌ Commands requiring user modification (use placeholders sparingly)
- ❌ Steps that are paragraphs instead of commands

---

#### 4. Root Cause

**Purpose**: Explain why the problem occurs (for those who want understanding).

**Requirements**:

- Single, consolidated explanation
- Diagrams or flow visualization if complex
- No redundancy with other sections

**Format**:

```markdown
## Root Cause

<!-- Explanation of why the problem occurs, including:

1. What component/behavior causes it
2. Why the design works this way
3. What triggers the failure condition

Optional: Diagram or flow chart for complex interactions -->
```

**Example**:

```markdown
## Root Cause

Claude Code's Bash tool generates commands using Bash syntax but delegates execution to the shell specified in `$SHELL`. This design allows Claude to use the user's preferred shell, but creates a mismatch when:

1. The LLM generates Bash-specific syntax (e.g., `[[`, `${var//pattern/replacement}`)
2. The terminal shell is Fish/zsh with incompatible syntax
3. The shell interpreter fails to parse the Bash-specific constructs

The tool assumes `$SHELL` is Bash-compatible, which is often false in modern development environments where Fish and zsh dominate.
```

**Anti-patterns**:

- ❌ Multiple sections explaining the same thing ("Why This Happens", "Root Cause", "Background", "Technical Details")
- ❌ Repeating information from Problem or Solution sections
- ❌ Speculation about how to fix it (that belongs in Solution)

---

#### 5. References

**Purpose**: External resources, issue trackers, related documentation.

**Requirements**:

- Links to upstream issues/PRs if applicable
- Related documentation
- No inline links scattered throughout (consolidate here)

**Format**:

```markdown
## References

- [Issue #123: Shell compatibility bug](https://github.com/org/repo/issues/123)
- [Documentation: Configuring bashPath](https://docs.example.com/config)
- [Related: Fish shell incompatibilities](https://example.com/fish)
```

---

## Writing Rules

### Commands

| Do ✅                              | Don't ❌                        |
|:----------------------------------|:-------------------------------|
| Copy-pasteable verbatim           | Require reader modification    |
| Include comments for clarity      | Assume command is self-evident |
| Show expected output when helpful | Leave reader guessing          |
| Use full paths for clarity        | Rely on PATH assumptions       |
| Test before publishing            | Hope it works                  |

**Example**:

```bash
# Good ✅
echo $SHELL  # Shows your current shell

# Bad ❌
Check your shell variable (run the appropriate command for your system)
```

### Prose

| Do ✅                              | Don't ❌                              |
|:----------------------------------|:-------------------------------------|
| Short sentences (15-20 words)     | Long, compound sentences             |
| Active voice ("Run this command") | Passive voice ("This should be run") |
| One idea per paragraph            | Multiple concepts interleaved        |
| Lead with action                  | Lead with explanation                |

### Tables vs. Lists vs. Prose

| Content Type                    | Format           | Example                   |
|:--------------------------------|:-----------------|:--------------------------|
| Comparisons, status, key-values | Tables           | Diagnostic interpretation |
| Sequential steps                | Numbered lists   | Installation instructions |
| Non-sequential items            | Bullet lists     | Symptoms list             |
| Complex explanations            | Short paragraphs | Root cause explanation    |

### Emphasis and Visual Cues

| Pattern       | Use For                        | Example                          |
|:--------------|:-------------------------------|:---------------------------------|
| **Bold**      | Key terms, important status    | **Critical**, **Warning**        |
| `backticks`   | Commands, file paths, env vars | `$SHELL`, `/bin/bash`            |
| ✅ ⚠️ ❌        | Status indicators in tables    | ✅ No issue, ❌ Critical           |
| > Blockquotes | Important callouts or quotes   | > Warning: This deletes all data |

---

## Common Anti-Patterns

### ❌ Redundancy

**Problem**: Same information repeated across multiple sections.

**Symptoms**:

- "Root Cause" and "Why This Happens" sections with overlapping content
- "Solution" and "Prevention" sections that are nearly identical
- "Key Takeaways" that summarizes what's already in the document

**Fix**: Consolidate into single authoritative sections. Delete redundant sections entirely.

**Example of redundancy**:

```markdown
❌ Bad: Multiple overlapping sections
## Why This Happens
<!-- Explanation A -->

## Root Cause
<!-- Same explanation, slightly different wording -->

## Technical Details
<!-- Same explanation again, more verbose -->
```

```markdown
✅ Good: Single consolidated section
## Root Cause
<!-- Clear, complete explanation once -->
```

---

### ❌ Explanation Before Action

**Problem**: Long background/context before the reader can do anything.

**Symptoms**:

- Page of explanation before first command
- Root cause before solution
- History lesson before diagnostic

**Fix**: Reorder to Problem → Diagnosis → Solution → Explanation.

**Example**:

```markdown
❌ Bad order:
1. Background (3 paragraphs)
2. History of the issue
3. Root cause explanation
4. Solution (finally!)

✅ Good order:
1. Problem (2 sentences)
2. Am I Affected? (diagnostic)
3. Solution (fix it now)
4. Root Cause (understand later)
```

---

### ❌ Scattered Diagnostics

**Problem**: Diagnostic steps spread across multiple sections.

**Symptoms**:

- "Quick Check" in one section
- "Detailed Check" elsewhere
- "System Investigation" in another

**Fix**: Consolidate into single "Am I Affected?" section with progressive checks (quick → detailed if needed).

---

### ❌ Non-Actionable Steps

**Problem**: Steps that are paragraphs instead of commands.

**Symptoms**:

- "You may need to check your configuration"
- "Consider whether your system uses..."
- Instructions requiring interpretation

**Fix**: Every step should be a concrete action.

**Example**:

```markdown
❌ Non-actionable:
You may want to check if your shell is configured correctly.

✅ Actionable:
Run `echo $SHELL` to check your shell.
```

---

### ❌ Token Waste Narratives

**Problem**: Describing impact/consequences at length.

**Symptoms**:

- "Impact Analysis" sections explaining how bad the problem is
- Detailed cost calculations
- Failure cascade descriptions

**Fix**: The problem statement conveys severity. If additional warning is needed, one sentence suffices.

**Example**:

```markdown
❌ Token waste:
This issue can have severe consequences for your workflow. Commands
will fail, causing frustration and lost productivity. Over time, this
can lead to hundreds of wasted hours and significant token costs as
the system retries failed commands.

✅ Concise:
Commands fail with syntax errors, breaking workflows.
```

---

### ❌ Takeaway Sections

**Problem**: Summarizing everything that was just said.

**Symptoms**:

- "Key Takeaways" at end
- "Summary" that repeats all sections
- "TL;DR" that's still too long

**Fix**: Delete entirely. A well-structured document IS the takeaway.

---

## Quality Checklist

### Before Publishing

**Structure**:

- [ ] Problem statement is 1-3 sentences
- [ ] "Am I Affected?" comes before solution
- [ ] Solution comes before root cause explanation
- [ ] No redundant sections covering same information
- [ ] No "Key Takeaways" or summary section
- [ ] References are consolidated at the end

**Content**:

- [ ] All commands are copy-pasteable
- [ ] Verification steps included after solution
- [ ] Root cause is single consolidated explanation
- [ ] No explanation before action
- [ ] Diagnostic has clear pass/fail criteria

**Style**:

- [ ] Active voice throughout
- [ ] Sentences under 20 words on average
- [ ] Tables used for comparisons/status
- [ ] Lists used for sequential/parallel items
- [ ] Visual cues (✅/❌/⚠️) used consistently

### Self-Review Questions

1. Can a reader fix the problem without reading past "Solution"?
2. Is there any content that appears in two places?
3. Would a frustrated reader at 3 AM find this helpful?
4. What can be deleted without losing essential information?
5. Does every section serve a distinct purpose?
6. Did I test all commands before publishing?

---

## Example Template

Use this as a starting point:

````markdown
# <!-- Issue Name -->

## Problem

<!-- 1-2 sentences: what's broken and observable symptom -->

## Am I Affected?

Run this command:

```bash
# diagnostic command
```

Interpret the result:

| Output           | Status     | Action                |
|:-----------------|:-----------|:----------------------|
| <!-- value 1 --> | ✅ No issue | No action needed      |
| <!-- value 2 --> | ❌ Critical | Follow solution below |

## Solution

<!-- One sentence summary -->

### <!-- Method 1 -->

```bash
# copy-pasteable commands
```

### Verify

```bash
# verification command
```

Expected: <!-- expected output -->

## Root Cause

<!-- Explanation of why this happens -->

## References

- <!-- Link to issue -->
- <!-- Link to documentation -->
````

---

## Sources

### Runbook Best Practices

- [Rootly: Incident Response Runbooks][rootly] - Templates and structure
- [IncidentHub: Runbook Best Practices][incidenthub] - The 5 A's framework
- [Christian Emmer: Incident Runbook Template][emmer] - Section structure, Google MTTR research

### Technical Writing

- [Boot.dev: Practical Patterns for Technical Writing][bootdev] - Writing guidelines, anti-patterns
- [Write the Docs: Software Documentation Guide][writethedocs] - Community standards

### Documentation Anti-Patterns

- [ACM: Anti-Patterns in End-User Documentation][acm] - Academic research on documentation failures
- [IEEE: Linguistic Anti-Patterns in Software][ieee] - Misleading documentation patterns

### General Best Practices

- [Atlassian: Software Documentation Best Practices][atlassian] - Proactive problem-solving
- [Technical Writer HQ: Good Documentation Practices][techwriter] - 2025 guidelines

---

## Version History

| Date       | Version | Changes               |
|:-----------|:--------|:----------------------|
| 2025-12-09 | 1.1     | Enhanced structure    |
| 2025-12-03 | 1.0     | Initial specification |

[rootly]: https://rootly.com/incident-response/runbooks
[incidenthub]: https://blog.incidenthub.cloud/The-No-Nonsense-Guide-to-Runbook-Best-Practices
[emmer]: https://emmer.dev/blog/an-effective-incident-runbook-template/
[bootdev]: https://blog.boot.dev/clean-code/practical-patterns-for-technical-writing/
[writethedocs]: https://www.writethedocs.org/guide/index.html
[acm]: https://dl.acm.org/doi/10.1145/3147704.3147726
[ieee]: https://ieeexplore.ieee.org/document/6498467/
[atlassian]: https://www.atlassian.com/blog/loom/software-documentation-best-practices
[techwriter]: https://technicalwriterhq.com/documentation/good-documentation-practices/
