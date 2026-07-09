---
name: autorl-mini-orchestrator
description: Orchestrate a small AutoRL skill-chain test where the main agent performs RL task clarification, validates task_card.md, then delegates evidence retrieval to one child agent and consolidates the Markdown artifacts without loading the skills globally.
---

# AutoRL Mini Orchestrator

## Purpose

Run a minimal two-stage AutoRL workflow as a controlled handoff test:

1. Main agent uses `skills/rl-task-clarifier/` to clarify the user request and produce `task_card.md`.
2. Main agent validates `task_card.md`.
3. Retrieval subagent uses `skills/rl-evidence-retrieval/` to produce `evidence_report.md`.
4. Main agent validates and summarizes the artifact chain.

This skill is an orchestrator only. It may perform the clarification stage in the main thread because that stage requires direct user interaction. It must not perform evidence retrieval, coding, cloning, dependency installation, or training itself.

## Preconditions

- Use this only when the user explicitly asks to test the AutoRL skill workflow or asks for subagent orchestration.
- Subagent support must be available before retrieval starts. If subagents are unavailable, stop with `orchestration_status: blocked_before_retrieval`; do not silently run retrieval in the main thread.
- Resolve skill paths relative to the workspace root:
  - `skills/rl-task-clarifier/SKILL.md`
  - `skills/rl-evidence-retrieval/SKILL.md`
- Use at most one child agent: the retrieval subagent.
- Do not allow child agents to spawn additional child agents.

## Workflow

### 1. Create A Run Directory

Choose a short stable task id:

```text
runs/<YYYYMMDD-short-topic>-mini-orchestration/
```

Expected files:

```text
runs/<task-id>/
  task_card.md
  clarification_log.md
  evidence_report.md
  orchestrator_report.md
  subagent_prompts/
    retrieval_prompt.md
```

### 2. Clarify In The Main Thread

Read and follow `skills/rl-task-clarifier/SKILL.md` in the main thread. Use the user's raw RL request as input, ask follow-up questions directly, and write:

```text
runs/<task-id>/task_card.md
runs/<task-id>/clarification_log.md
```

The main thread should keep clarification interactive and explicit:

- ask only blocking/high-impact questions
- record assumptions separately from confirmed facts
- stop before retrieval if the user has not resolved the clarification gate
- avoid spawning a child agent for clarification
- after asking any blocking/high-impact question batch, end the current turn and wait for a later user response before rewriting a ready task card or starting retrieval
- treat references such as "same task", "previous task", or "use that run" as unresolved until the user names an exact artifact path/run id or explicitly confirms the inferred field list in a later message
- do not use prior run artifacts, local notes, or repository context to satisfy mandatory clarification fields unless the user has explicitly approved those specific fields for this run

### 3. Validate The Task Card

Read [handoff-gates.md](references/handoff-gates.md) before validation.

Do not start retrieval unless `task_card.md` passes the clarification gate:

- file exists and is readable
- `handoff_status` is `ready`
- `ambiguity_score <= 0.15`
- task mode is present
- environment type, environment id/path, and concrete RL task are present
- algorithm direction is present
- objective/success criteria and runtime boundary are present

If the main thread asked a blocking/high-impact clarification question in the current assistant turn, validation must stop for that turn even if workspace artifacts appear to contain plausible answers. Continue only after a subsequent user message resolves the gate.

If validation fails, write `orchestrator_report.md` with `orchestration_status: blocked_after_clarification` and stop.

### 4. Spawn The Retrieval Subagent

Read [subagent-prompts.md](references/subagent-prompts.md). Write the filled retrieval prompt to:

```text
runs/<task-id>/subagent_prompts/retrieval_prompt.md
```

Spawn one child agent with that prompt. The child agent must:

- read the full `skills/rl-evidence-retrieval/SKILL.md`
- read the validated `task_card.md`
- write `evidence_report.md` into the same run directory
- optionally write structured mirrors if useful
- return only a compact status with artifact paths, retrieval status, coverage, and blockers

The child agent must not clone repositories, install dependencies, copy third-party code, or run training.

### 5. Validate The Evidence Report

Check:

- `evidence_report.md` exists and is readable
- `retrieval_status` is present
- `coverage` is present
- task grounding matches `task_card.md`
- paper candidates, codebase candidates, or explicit gaps are present
- risks and handoff notes are present

`retrieval_status: partial` can pass this mini workflow when the report explicitly explains unavailable tools, missing sources, or unresolved gaps.

### 6. Write The Orchestrator Report

Use [orchestrator-report-template.md](references/orchestrator-report-template.md).

The report is the main artifact for the test:

```text
runs/<task-id>/orchestrator_report.md
```

Include:

- run id and user request
- main-thread clarification status
- retrieval subagent status
- artifact paths
- gate results
- whether the handoff worked
- exact blocker if the chain stopped
- recommended next action

## Output Rules

- Keep the main thread focused on orchestration and validation.
- Prefer artifact paths over pasted child-agent output.
- Do not merge raw child-agent logs into the final answer.
- Treat file artifacts as source of truth over child-agent summaries.
- If a child agent summary claims success but the file is missing or invalid, mark the stage failed.

## Handoff Wording

When the full chain succeeds:

```text
Mini orchestration complete: clarification and retrieval artifacts passed validation. Report: runs/<task-id>/orchestrator_report.md
```

When it stops:

```text
Mini orchestration blocked at <stage>: <smallest blocker>. Report: runs/<task-id>/orchestrator_report.md
```
