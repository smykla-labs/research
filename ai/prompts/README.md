# AI Agent Prompts

Reusable prompt templates for AI agents and quick inline prompts for common workflows.

## Quick Prompts

Short, reusable prompts for inline use:

```
Use AskUserQuestion tool for these questions
```

## Complex Agent Prompts

- **`_template.md`** - Blank template for new prompts. Structure: Role → Constraints → Success Criteria → Edge Cases → Workflow → Output.
- **`planning-agent.md`** - Investigates codebase, produces implementation plan. Never implements. Output: `tmp/tasks/YYMMDD-{task-slug}/implementation_plan.md` with workflow commands, git config, technical context, and session-sized phases.
- **`executor-agent.md`** - Implements ONE task from spec, updates progress before verification, commits implementation only. Single task per session.
- **`prompt-author-agent.md`** - Creates/refines agent prompts following `ai/prompt-engineering-spec.md`. No placeholders in output.
- **`session-handover.md`** - Captures session context: failed approaches with rationale, environment constraints, architectural decisions, next steps. Dense technical format, clipboard-ready.
- **`worktree-manager.md`** - Creates git worktree at `../{project}-{branch}` with context transfer. Discovers remote/default-branch, symlinks relevant files, outputs `cd` command to clipboard.
