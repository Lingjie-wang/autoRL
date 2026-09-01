# Artifact Contracts

## Standard Output Layout

For each AutoRL run or migration task, prefer:

```text
run-or-task/
  task_card.md
  clarification_log.md
  task_card.json              # optional structured mirror
  context_packet.json
  evidence_report.md
  paper_candidates.jsonl      # optional structured mirror
  codebase_candidates.jsonl   # optional structured mirror
  evidence_packet.json        # optional structured mirror
  decision_packet.json
  executor_brief.yaml
  implementation_plan.md
  dependency_plan.md
  smoke_test_report.md
  integration_report.md       # when an environment was integrated; see references/env-adapter-contract.md
  reuse_search.json            # optional deterministic environment-reuse lookup
  environment_reuse.json       # when a verified integration is reused
  install_log.md              # optional when installs/clones happen
  run_config.json             # optional implementation config
  verification_report.json
  result_package.json
  artifacts/
```

Use fewer files for small tasks, but keep names stable when files exist.

## Task Card

`task_card.md` is the canonical executor-facing artifact. It should be written for Codex or Claude Code to read directly: concise prose, explicit assumptions, clear constraints, and stable section headings.

`task_card.json` is optional. Use it only when deterministic validation, indexing, or downstream non-LLM tooling needs a structured mirror.

Required:

- `user_goal`
- `task_mode`
- `intent`
- `domain`
- `execution_boundary`
- `environment_spec`
- `algorithm_direction`
- `success_criteria`
- `missing_context`
- `assumptions`
- `ambiguity_score`
- `handoff_status`

For tasks produced by `rl-task-clarifier`, `handoff_status` is `ready` only when the ambiguity score is `<= 0.15` and no blocking field remains unresolved.

## Clarification Log

Required when the intake stage asks follow-up questions:

- original user request
- question rounds
- user answers
- answer source for each response: fixed choice, custom text, or inferred from prior context
- confirmed facts
- assumptions
- blocked fields
- final ambiguity score
- next stage recommendation

## Evidence Report And Packet

`evidence_report.md` is the canonical LLM-facing artifact for evidence retrieval. It should be concise Markdown that a Codex or Claude Code executor can read directly before strategy decision.

Optional JSON/JSONL sidecars mirror the report for indexing, dashboards, or deterministic validation.

Required in the report or its structured mirror:

- `retrieval_status`
- `coverage`
- `input_task_card`
- `search_date`
- `evidence_items`
- `evidence_coverage`
- `gaps`
- `next_stage`

Evidence item required fields:

- `evidence_id`
- `source_type`
- `claim`
- `why_needed`
- `confidence`

## Decision Packet

Required:

- `supported`
- `route`
- `selected_strategy`
- `algorithm_selection_mode`
- `evidence_refs`
- `implementation_mode`
- `risks`
- `next_action`

## Executor Artifacts

`implementation_plan.md`, `dependency_plan.md`, and `smoke_test_report.md` are the preferred Markdown artifacts when implementation uses `rl-framework-implementer`.

Implementation plan required fields:

- selected framework or implementation route
- evidence refs or decision refs used
- files added or changed
- algorithm/environment wiring
- commands to run
- deferred work and risks

Dependency plan required fields:

- selected dependency or repository
- proposed commands
- target paths
- approval status
- version or commit pins when known
- install/download risks

Smoke test report required fields:

- smoke status
- execution boundary
- commands run
- checks performed
- failures and smallest next fix

Native renderer mode may produce:

- `run_config.json`
- generated training script
- static verification report

Runtime runspec mode may produce:

- `planned_runspec.json`
- runtime adapter invocation
- runtime setup diagnostics
- telemetry/control path contract

Advisory mode may produce:

- design memo
- experiment plan
- evidence-backed recommendations

## Verification Report

Required:

- `status`
- `checks`
- `commands_run`
- `artifacts_checked`
- `boundary_compliance`
- `evidence_ref_compliance`
- `failures`
- `next_action`

## Environment Reuse Receipt

Required when `artifacts/integration` references another run:

- `mode: reused`
- source run and source artifact root
- environment id, source type, API convention, and training channel
- hashes of the referenced integration artifacts
- source and required verification boundaries
- whether current-run re-verification is required

The source run is immutable. Downstream stages use the current run's
`artifacts/integration` path and must not edit through it.

## Result Package

Required:

- `status`
- `summary`
- `artifact_paths`
- `verification_status`
- `evidence_refs`
- `risks`
- `next_action`

Do not include full executor prompts or raw trace logs in the result package.
