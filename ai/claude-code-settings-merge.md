# Claude Code Settings Merge Behavior

> Understanding how Claude Code combines settings from multiple configuration files

## Overview

Claude Code **merges** settings files rather than overriding them. This means configuration from multiple sources combines intelligently, allowing you to:

- Set global defaults in user settings
- Add project-specific rules in project settings
- Override specific values in local settings
- Enforce policies via enterprise settings

**Key principle**: Lower-precedence files provide defaults; higher-precedence files add to or override specific values.

---

## Table of Contents

1. [Precedence Hierarchy](#precedence-hierarchy)
2. [Merge Rules](#merge-rules)
3. [Examples](#examples)
4. [Common Pitfalls](#common-pitfalls)
5. [When This Matters](#when-this-matters)
6. [Quick Reference](#quick-reference)

---

## Precedence Hierarchy

Settings are evaluated in this order (highest precedence first):

| Priority | Source                              | Location                          | Use Case                    |
|:---------|:------------------------------------|:----------------------------------|:----------------------------|
| 1        | Enterprise managed policies         | `managed-settings.json`           | Organization-wide policies  |
| 2        | Command line arguments              | CLI flags                         | One-time overrides          |
| 3        | Local project settings (gitignored) | `.claude/settings.local.json`     | Personal project tweaks     |
| 4        | Shared project settings (committed) | `.claude/settings.json`           | Team-wide project config    |
| 5        | User settings                       | `~/.claude/settings.json`         | Personal global defaults    |

---

## Merge Rules

### How Settings Combine

1. **Additive by default**: Settings from all levels combine
2. **Specific overrides**: Higher-precedence values replace lower-precedence values for the same key
3. **No implicit removal**: Unset values do NOT remove settings from lower-precedence files
4. **Deny always wins**: A `deny` rule at any level overrides `allow` rules at any other level

### Merge Behavior by Setting Type

| Setting Type  | Merge Behavior                                              |
|:--------------|:------------------------------------------------------------|
| `hooks`       | Merged by event type and matcher—all matching hooks execute |
| `permissions` | Allow lists merge; deny rules override conflicting allows   |
| `model`       | Higher precedence replaces lower (no merge)                 |
| `autoApprove` | Higher precedence replaces lower (no merge)                 |

---

## Examples

### Example 1: Hooks from Global Only

**Scenario**: Global hooks defined, local settings has no hooks section.

```jsonc
// ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "Bash", "hooks": ["echo 'Running bash'"] }]
  }
}
```

```jsonc
// .claude/settings.local.json
{
  "permissions": { "allow": ["Bash(npm run:*)"] }
}
```

**Result**: ✅ Hook runs

**Why**: Local file doesn't define `hooks`, so global hooks apply unchanged.

---

### Example 2: Hooks from Both Files

**Scenario**: Both global and local settings define hooks for different matchers.

```jsonc
// ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "Bash", "hooks": ["echo 'Global hook'"] }]
  }
}
```

```jsonc
// .claude/settings.local.json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "Write", "hooks": ["echo 'Local hook'"] }]
  }
}
```

**Result**: ✅ Both hooks run (merged)

**Why**: Hooks merge by event type and matcher. Different matchers coexist.

---

### Example 3: Permissions Merge

**Scenario**: Global and local settings both define allow lists.

```jsonc
// ~/.claude/settings.json
{
  "permissions": {
    "allow": ["Bash(git:*)", "Bash(npm test:*)"]
  }
}
```

```jsonc
// .claude/settings.local.json
{
  "permissions": {
    "allow": ["Bash(task build)"]
  }
}
```

**Result**: ✅ All three permissions allowed

**Allowed commands**:

- `Bash(git:*)` (from global)
- `Bash(npm test:*)` (from global)
- `Bash(task build)` (from local)

---

### Example 4: Deny Takes Precedence

**Scenario**: Global denies a command, local tries to allow it.

```jsonc
// ~/.claude/settings.json
{
  "permissions": {
    "deny": ["Bash(rm -rf:*)"]
  }
}
```

```jsonc
// .claude/settings.local.json
{
  "permissions": {
    "allow": ["Bash(rm -rf:*)"]  // Attempt to override
  }
}
```

**Result**: ❌ Still denied

**Why**: `deny` rules take precedence over `allow` rules at any level. This prevents accidental override of safety policies.

---

## Common Pitfalls

### ❌ Expecting Local Settings to "Reset" Global Settings

**Incorrect assumption**: Adding `.claude/settings.local.json` will disable global hooks.

**Reality**: Global settings remain active unless explicitly overridden for the same key.

**Solution**: If you want to disable global hooks for a project, explicitly define an empty hooks section:

```jsonc
// .claude/settings.local.json
{
  "hooks": {}  // Explicitly no hooks
}
```

---

### ❌ Assuming Allow Can Override Deny

**Incorrect assumption**: Local `allow` can override global `deny`.

**Reality**: `deny` always wins, regardless of precedence level.

**Solution**: Remove the `deny` rule from the higher-precedence source if you need to allow it in specific contexts.

---

### ❌ Not Understanding Additive Permissions

**Incorrect assumption**: Local permissions replace global permissions.

**Reality**: Permissions from all levels combine (except where `deny` conflicts with `allow`).

**Solution**: Think of settings as layers that stack, not as files that replace each other.

---

## When This Matters

### Use Case 1: Team Projects with Personal Preferences

**Setup**:

- `.claude/settings.json` (committed): Team-wide hooks and permissions
- `.claude/settings.local.json` (gitignored): Personal auto-approvals or additional permissions

**Benefit**: Team shares common config while individuals customize their workflow.

---

### Use Case 2: Global Defaults with Project Overrides

**Setup**:

- `~/.claude/settings.json`: Global hooks for all projects (e.g., shell command logging)
- `.claude/settings.json`: Project-specific permissions for build tools

**Benefit**: Consistent behavior across projects with project-specific extensions.

---

### Use Case 3: Security Policies

**Setup**:

- `managed-settings.json`: Enterprise denies dangerous commands (`rm -rf`, `curl | bash`)
- Lower-precedence files: Cannot override denies

**Benefit**: Enforce organization-wide safety policies that users cannot bypass.

---

## Quick Reference

### Mental Model

Think of settings as transparent layers stacked on top of each other:

```text
┌─────────────────────────────┐
│ Enterprise (managed)        │ ← Highest precedence
├─────────────────────────────┤
│ CLI arguments               │
├─────────────────────────────┤
│ Local project (.local.json) │
├─────────────────────────────┤
│ Shared project (.json)      │
├─────────────────────────────┤
│ User settings (~/.claude)   │ ← Lowest precedence
└─────────────────────────────┘
```

Settings combine from **bottom to top**. Each layer adds or overrides specific values from layers below.

### Key Rules

| Rule                  | Description                                                  |
|:----------------------|:-------------------------------------------------------------|
| **Merge, don't wipe** | Lower files provide defaults; higher files add/override      |
| **Deny always wins**  | `deny` at any level overrides `allow` at any other level     |
| **Hooks merge**       | All matching hooks from all levels execute                   |
| **Permissions merge** | Allow lists combine (unless conflicting with deny)           |
| **No implicit unset** | Omitting a key doesn't remove it from lower-precedence files |

### Troubleshooting

| Problem                        | Likely Cause                        | Solution                                   |
|:-------------------------------|:------------------------------------|:-------------------------------------------|
| Global hooks still running     | Local settings doesn't unset them   | Add `"hooks": {}` to local settings        |
| Permission unexpectedly denied | `deny` rule somewhere in the chain  | Search all settings files for `deny` rules |
| Setting not taking effect      | Lower-precedence file is being used | Check precedence order and file locations  |

---

## Summary

**Settings files merge—they don't override.** Understanding this behavior allows you to:

- Create layered configurations that combine intelligently
- Share team settings while preserving personal customizations
- Enforce security policies that cannot be bypassed
- Maintain global defaults while adding project-specific rules

**Remember**: Think additive, not replacement. Each settings file contributes to the final configuration.
