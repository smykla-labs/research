---
allowed-tools: Read, Grep, Glob
argument-hint: <file-path|@file>
description: Review slash command quality against the commands guide
model: haiku
---

Use the command-quality-reviewer agent to validate slash command files.

$ARGUMENTS

## Constraints

- **NEVER assume** input type — detect explicitly via frontmatter check
- **NEVER pass** file paths to reviewer — always extract and pass full content
- **ZERO tolerance** for hallucination — verify file read before proceeding

## Context

Commands Guide: @ai/claude-code-commands-guide.md

## Workflow

### Step 1: Determine Input Type

`$ARGUMENTS` may contain either:
- **File path**: e.g., `.claude/commands/foo.md` → Read the file first
- **Inline content**: e.g., `@.claude/commands/foo.md` expands to actual content → Use directly

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

Invoke **command-quality-reviewer** with the Task tool:
- **MUST include**: Full file content in `~~~markdown` fences
- **MUST include**: The Commands Guide from context above
- Format the prompt as:
  ```
  Review this command definition:

  ~~~markdown
  {actual file content here}
  ~~~
  ```

**If reviewer outputs STATUS: NEEDS_INPUT**:
- Parse questions from output
- Use `AskUserQuestion` tool to collect answers
- Resume reviewer with `ANSWERS: KEY=value, KEY=value`

### Step 4: Report Results

Agent will output structured findings:
- Summary (PASS/WARN/FAIL)
- Critical issues (must fix)
- Warnings (should fix)
- Info (consider)
- Checklist results
- Recommendations

Report results to user with actionable next steps.

**CRITICAL**: NEVER invoke the reviewer without actual file content. Passing just a path allows hallucination.

## Edge Cases

- **Empty input**: Report error — command requires a file path or inline content
- **File not found**: Report error immediately with the missing path
- **Relative vs absolute paths**: Detect both, resolve to full content
- **Malformed frontmatter**: If starts with `---` but YAML invalid, treat as inline content
- **Uncertainty about input format**: Use detection rules (frontmatter check) — never guess

## Done When

- [ ] Input type detected (file path vs. inline content)
- [ ] File read successfully (if path) — verify before proceeding
- [ ] Full content extracted and passed to reviewer (zero paths, zero references)
- [ ] Review results reported to user with actionable recommendations
- [ ] Quality findings displayed with severity levels
