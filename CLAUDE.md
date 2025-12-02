# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Knowledge base and research artifacts for investigations, experiments, and learnings. Not a production codebase—primarily documentation and prompt templates.

## Structure

- `ai/prompts/` - Reusable AI agent prompt templates
  - `planning-agent.md` - Planning agent for creating implementation specs
  - `executor-agent.md` - Executor agent for single-task implementation
- `tmp/` - Temporary files and working directories (gitignored)

## Agent Workflow System

This repository contains a two-agent workflow system for structured development:

### Planning Agent (`ai/prompts/planning-agent.md`)

- **Purpose**: Investigate codebase and create comprehensive implementation plans
- **Output**: `tmp/tasks/YYMMDD-{task-slug}/implementation_plan.md`
- **Constraints**: Never implements changes, only plans
- **Key sections in output**:
  - Workflow Commands (lint, format, test)
  - Progress Tracker (checklist with NEXT pointer)
  - Technical Context (architecture, rationale, file paths)
  - Execution Plan (session-sized phases with 3-7 steps each)

### Executor Agent (`ai/prompts/executor-agent.md`)

- **Purpose**: Execute ONE task from implementation spec, then hand off
- **Constraints**: Single task only, stops at session boundary
- **Workflow**:
  1. Branch setup (confirms with user if unclear)
  2. Load spec and identify NEXT task
  3. Implement and verify (lint/test)
  4. Update Progress Tracker (mark done, update NEXT)
  5. Commit spec updates with implementation
- **Knowledge capture**: Updates CLAUDE.md or `.claude/session-{topic}.md` for insights
- **Commit/PR style**: Focus on WHAT/WHY, exclude phase numbers and task completion status

## Key Principles

- Task directory naming: `tmp/tasks/YYMMDD-{task-slug}/`
- Progress tracking: In-spec Progress Tracker with NEXT pointer
- Session boundaries: One task per executor session
- Context preservation: Specs must be self-contained for fresh sessions
- Blockers: Stop and ask user rather than assuming
