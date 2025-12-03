# Claude Code Using Wrong Shell

## Problem

Claude Code's Bash tool generates bash syntax but executes commands using `$SHELL` inherited from the terminal that launched it. If your terminal uses Fish, zsh, or another non-bash shell, commands occasionally fail with syntax errors—more frequently with Fish (~90%), less with zsh (~20%). Claude typically takes a few attempts to figure out workarounds like prefixing commands with `bash -c '...'` or rewriting in shell-agnostic syntax.

## Am I Affected?

Use `!echo $SHELL` in the CLI, or ask Claude to run this command:

```bash
echo $SHELL
```

| Result                                         | Status      |
|:-----------------------------------------------|:------------|
| `/bin/bash`                                    | ✅ No issue  |
| `/bin/zsh` or `/run/current-system/sw/bin/zsh` | ⚠️ Moderate |
| `/bin/fish` or `/opt/homebrew/bin/fish`        | ❌ Critical  |

### Symptoms by Shell

**Fish (Critical)** - ~90% of bash syntax fails:

- `name=$(command)` → `Unsupported use of '='`
- `arr=()` → syntax errors
- Command substitution broken

**Zsh (Moderate)** - ~20% of commands have subtle issues:

- `shopt` not found
- Different globbing behavior
- Array indexing starts at 1 (bash uses 0)

## Solution

Force `SHELL=/bin/bash` in the shell you use to launch Claude Code.

### Fish Users

```fish
# ~/.config/fish/config.fish
set --export SHELL /bin/bash
```

### Zsh Users

```bash
# ~/.zshenv (sourced for all zsh shells)
export SHELL=/bin/bash
```

### Bash Users (if SHELL points elsewhere)

```bash
# ~/.bashrc or ~/.bash_profile
export SHELL=/bin/bash
```

### Verification

```bash
# 1. Restart your shell
exec fish  # or: exec zsh, exec bash

# 2. Verify in your terminal
echo $SHELL  # Must show /bin/bash

# 3. Restart Claude Code completely (quit and reopen)

# 4. Verify in Claude Code
echo $SHELL  # Must show /bin/bash
```

## Root Cause

Claude Code inherits `$SHELL` from the parent process—the terminal shell you used to run `claude`. Despite the tool being named "Bash", it spawns shells using `$SHELL`, not `/bin/bash`.

```text
Your Terminal (Fish/Zsh)
    ↓ $SHELL=/opt/homebrew/bin/fish
Claude Code CLI
    ↓ inherits $SHELL
Bash Tool executes with $SHELL (Fish, not Bash)
    ↓
Bash syntax fails in Fish
```

## Known Limitations

No official fix available. Tracked in:

- [#7490][issue-7490] - Feature request to configure shell
- [#1630][issue-1630] - Shell config not loaded

> [!IMPORTANT]
> Setting `SHELL` in Claude Code's `settings.json` does **not** work—you must set it in your shell config.

[issue-7490]: https://github.com/anthropics/claude-code/issues/7490
[issue-1630]: https://github.com/anthropics/claude-code/issues/1630
