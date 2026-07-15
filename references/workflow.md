# AutoRL Skill Workflow

## Purpose

Replace custom multi-agent execution with a skill-orchestrated workflow. The skill prepares context and contracts; Codex or Claude Code performs implementation, file edits, and tests.

## Stage 0: Request Intake

Output: `task_card`.

Use `skills/rl-task-clarifier/` when the request is underspecified. Its job is to ask repeated, prioritized question batches until the task ambiguity gate passes or the remaining blockers are explicit.

Required fields:

- `user_goal`: exact user request
- `domain`: `reinforcement_learning` or `unsupported`
- `intent`: `build`, `debug`, `review`, `migrate`, or `advisory`
- `task_mode`: `research_quality_improvement` or `application_new_env_algorithm`
- `environment_spec`: environment type (`official_benchmark`, `custom_env`, or `external_simulator`), environment id/path, and the concrete RL task
- `algorithm_direction`: rough algorithm family or explicit permission for evidence-backed selection
- `execution_boundary`: `generate_only`, `dry_run`, or `runtime_allowed`
- `missing_context`: concrete questions or blockers
- `assumptions`: bounded assumptions allowed for planning

Stop here if the request lacks task mode, environment objective, concrete RL task, algorithm direction, runtime boundary, or success criteria. Do not proceed to evidence retrieval or implementation while any blocking intake field is unresolved.

## Stage 1: Context Assembly

Output: `context_packet`.

Include only durable facts:

- environment spec: id, state/observation schema, action schema, reward signal
- model requirements: policy/value/world model constraints
- metrics contract: training and evaluation metrics
- runtime capability: adapter, entrypoints, install policy, artifact outputs
- control contract: allowed feedback/control actions and forbidden surfaces
- safety constraints: no reward rewriting, no hidden runtime execution, no unapproved dependency install

Keep raw logs, long prompts, source dumps, and full traces audit-only.

## Stage 2: Evidence Retrieval

Output: `evidence_report.md` and optional `evidence_packet`.

Use `skills/rl-evidence-retrieval/` after Stage 0/1 produces an actionable task card. Its job is to retrieve and synthesize paper and codebase evidence for the clarified RL task.

Primary artifact:

```text
runs/<task-id>/evidence_report.md
```

Optional structured sidecars:

```text
runs/<task-id>/paper_candidates.jsonl
runs/<task-id>/codebase_candidates.jsonl
runs/<task-id>/evidence_packet.json
```

Evidence categories:

- runtime capability evidence
- paper or method evidence
- code reference evidence
- task-context grounding evidence
- operational evidence from tests or diagnostics

Each evidence item must have:

- `evidence_id`
- `source_type`
- `claim`
- `why_needed`
- `path` or `url` when available
- `confidence`
- `limitations`

Stop here if the task card is not ready, search tools are unavailable, or codebase inspection would require unapproved cloning, dependency installation, or runtime execution. Produce a partial evidence report with explicit gaps instead of moving to strategy decision on hidden assumptions.

## Stage 3: Strategy Decision

Output: `decision_packet`.

Decide:

- whether the request is supported
- whether algorithm selection is user-specified or evidence-backed
- whether implementation should be native renderer, runtime runspec, adapter call, or advisory-only
- which evidence supports the selected route
- which risks remain

Do not produce code in this stage.

## Stage 4: Executor Brief

Output: `executor_brief`.

This is the only context the implementation executor should need. It must contain:

- task card
- selected route
- allowed files or target directory
- artifact contract
- exact implementation instructions
- forbidden actions
- tests to run
- expected output summary

Use [executor-protocol.md](executor-protocol.md) for the brief format.

## Stage 5: Implementation

Executor: Codex or Claude Code.

Use `skills/rl-env-integrator/` first when the task card names a concrete environment that must become constructible behind the adapter contract (`references/env-adapter-contract.md`). It emits `integration_report.md` plus `artifacts/integration/` deliverables, which `skills/rl-env-verifier/` gates in Stage 6 before training-oriented implementation relies on the environment.

Use `skills/rl-framework-implementer/` when implementation requires selecting or installing an RL framework, cloning a reference implementation, adding algorithm/environment wiring, or running bounded smoke tests.

Primary artifacts:

```text
runs/<task-id>/implementation_plan.md
runs/<task-id>/dependency_plan.md
runs/<task-id>/smoke_test_report.md
```

Optional artifacts:

```text
runs/<task-id>/install_log.md
runs/<task-id>/run_config.json
runs/<task-id>/artifacts/implementation/
```

The executor may:

- inspect files
- edit code
- generate configs/runspecs
- run local tests
- prepare dependency/download commands and run them only when approved
- produce patches and artifacts

The executor must not:

- invent evidence
- run real training unless `runtime_allowed`
- install dependencies without explicit approval
- copy third-party repository code into project-owned output

If dependency installation, cloning, simulator assets, or long training are required but unapproved, stop with a partial implementation plan and the smallest approval needed.

## Stage 6: Verification

Output: `verification_report`.

Use `skills/rl-env-verifier/` when Stage 5 produced an environment integration: it independently re-checks every `env_spec.json` claim against runtime behavior and emits `verification_report.json` with per-check expected/observed/smallest_fix records.

Check:

- artifact files exist
- schemas are valid
- runtime boundary was respected
- evidence refs appear in generated rationale
- tests passed or failures are explained
- no unsupported training claims are made

## Stage 7: Result Package

Output: `result_package`.

Include:

- concise user-facing summary
- artifact paths
- verification status
- evidence refs used
- remaining risks
- next recommended action

Avoid including full prompts, raw traces, full manifests, or recursive context.
