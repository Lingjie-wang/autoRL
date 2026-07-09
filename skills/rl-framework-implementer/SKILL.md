---
name: rl-framework-implementer
description: Set up the appropriate reinforcement-learning framework and implement an algorithm/environment training path from AutoRL artifacts. Use after task clarification, evidence retrieval, and strategy decision when Codex or Claude Code needs to inspect the workspace, choose or download an RL framework under approval gates, add adapters/configs/training/evaluation code, and run smoke tests without starting unapproved full training.
---

# RL Framework Implementer

## Purpose

Convert an evidence-backed AutoRL task into runnable implementation artifacts. The skill may inspect the workspace, choose a framework path, prepare dependency/download commands, implement environment adapters or algorithm glue code, and run bounded smoke tests.

This skill owns implementation setup only. It must not invent paper evidence, silently choose a strategy that contradicts `decision_packet`, run full training without `runtime_allowed`, or install/clone/download anything without the required approval.

## Inputs

Preferred inputs:

```text
runs/<task-id>/task_card.md
runs/<task-id>/evidence_report.md
runs/<task-id>/decision_packet.json
runs/<task-id>/executor_brief.yaml
```

Minimum viable inputs:

- ready `task_card.md`
- either `decision_packet` or an evidence report that explicitly allows evidence-backed framework/algorithm selection
- clear `execution_boundary`
- clear dependency policy
- allowed target directory or permission to write under `runs/<task-id>/artifacts/implementation/`

Stop if the task card is blocked, the implementation route is unsupported, or dependency/runtime permissions are unclear.

## Workflow

### 1. Read Inputs And Inspect Workspace

Read the task card, evidence report, decision packet, and executor brief when present. Then inspect the workspace for:

- existing Python/RL project structure
- package manager files
- existing environment wrappers
- existing training/evaluation entrypoints
- test commands and project conventions
- installed frameworks that can avoid new downloads

Prefer existing project patterns over introducing a new framework.

### 2. Choose The Framework Path

Read [framework-selection.md](references/framework-selection.md) before choosing.

Select one route:

- reuse an existing local framework/package
- use a maintained RL library as a dependency
- clone an external reference repo into `third_party/`
- write a minimal native implementation when a framework would be heavier than the task
- stop with an advisory implementation plan when runtime/download constraints block implementation

Record the rationale and evidence refs in `implementation_plan.md`.

### 3. Plan Dependencies And Approvals

Read [dependency-boundary.md](references/dependency-boundary.md) before any network, clone, or install action.

Write:

```text
runs/<task-id>/dependency_plan.md
```

The plan must list exact intended commands, target paths, version/commit pins when known, expected risks, rollback/cleanup notes, and whether approval is required.

Do not run `git clone`, `pip install`, `conda install`, large downloads, or full training until the task card and current approval policy allow it.

### 4. Implement The Algorithm Path

Read [implementation-artifacts.md](references/implementation-artifacts.md).

Implement the smallest runnable path that satisfies the task:

- environment adapter or registration
- training config
- algorithm selection/configuration
- training entrypoint
- evaluation entrypoint or metric collector
- logging/telemetry outputs
- smoke-test command

When adapting third-party code, call it as a dependency or inspect it as a reference. Do not copy substantial third-party source into project-owned files unless the license and user approval allow it.

### 5. Run Bounded Verification

Read [smoke-tests.md](references/smoke-tests.md).

Run only tests allowed by `execution_boundary`:

- `generate_only`: static checks and file existence only
- `dry_run`: imports, env construction, config validation, one-step rollout when safe
- `runtime_allowed`: short smoke training only before any full experiment

Write:

```text
runs/<task-id>/smoke_test_report.md
```

If a command fails, capture the command, failure, likely cause, and smallest next fix.

### 6. Emit Implementation Summary

Write:

```text
runs/<task-id>/implementation_plan.md
runs/<task-id>/dependency_plan.md
runs/<task-id>/smoke_test_report.md
```

Optional:

```text
runs/<task-id>/install_log.md
runs/<task-id>/run_config.json
runs/<task-id>/artifacts/implementation/
```

End with changed files, commands run, approval gates encountered, and next action.

## Output Rules

- Use Markdown for implementation/dependency/smoke-test reports.
- Keep framework choice evidence-backed and task-specific.
- Prefer small smoke tests over long training.
- Pin external repos by commit when cloning is approved.
- Keep downloaded third-party repos under `third_party/` or a user-approved location.
- Keep generated implementation files in the executor brief's allowed target, or under `runs/<task-id>/artifacts/implementation/` when no target is provided.
- Report partial implementation honestly when dependencies, GPU, simulator, license, or approvals block progress.

## Anti-Patterns

- Do not install a framework just because it is popular.
- Do not run `pip install` or `git clone` as part of "planning".
- Do not overwrite an existing training stack without checking local conventions.
- Do not run full training to prove implementation works unless explicitly allowed.
- Do not claim algorithm performance from smoke tests.
- Do not copy third-party code into this repo as if it were generated code.

## Handoff Wording

When implementation is usable:

```text
RL implementation path ready: framework=<name>, smoke_status=<passed|partial>. Artifacts: runs/<task-id>/implementation_plan.md, runs/<task-id>/dependency_plan.md, runs/<task-id>/smoke_test_report.md
```

When blocked:

```text
RL implementation blocked at <stage>: <smallest approval or missing dependency>. Artifact: runs/<task-id>/implementation_plan.md
```
