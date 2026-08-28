---
name: autorl-skill-workflow-v2
description: Orchestrate a file-backed, skill-based AutoRL workflow for either delivering runnable RL code from a custom or new environment or iterating scientifically from an existing baseline. Use when Codex must coordinate environment onboarding, independent verification, evidence retrieval, training implementation, guarded experiment execution, telemetry supervision, checkpoint recovery, evaluation, and result packaging without building a custom agent executor.
---

# AutoRL Skill Workflow V2

## Purpose

Run the two workflows shown in `image.png` as one shared, recoverable process:

- `application_delivery`: turn environment code plus an RL requirement into a
  verified environment contract, evidence-backed implementation, and runnable
  training package. Do not start a full experiment by default.
- `research_iteration`: reproduce and improve a baseline under a frozen
  comparison protocol, supervise approved training, and derive bounded child
  runs without mutating the evidence trail.

Codex is the main orchestrator and native implementation executor. Do not build
another LLM runtime, long-lived agent daemon, or hidden shared-memory state.

## Operating Rules

1. Treat files as the source of truth. Child summaries are hints only.
2. Keep machine control in JSON and append-only JSON events. Use Markdown for
   human and LLM handoffs, never as a runtime control source.
3. Give each stage one writer. Only the main orchestrator writes workflow state,
   strategy decisions, approvals, and the result package.
4. Spawn bounded child agents with explicit skill paths. A child must not spawn
   another child.
5. Validate and accept a stage artifact before any downstream stage consumes it.
   A worker reporting success does not pass a gate.
6. Never overwrite an accepted attempt. Changed inputs create a new attempt or a
   child run with lineage.
7. Separate observation, proposal, authorization, and action application.
   Monitoring agents never change a live run directly.
8. Preserve the baseline protocol, reward semantics, environment interface,
   evaluation seeds, and success criteria during an active research run.

## Read First

- Read [workflow-profiles.md](references/workflow-profiles.md) to select a
  profile and stage graph.
- Read [state-machine.md](references/state-machine.md) before creating or
  resuming a run.
- Read [artifact-contracts.md](references/artifact-contracts.md) before writing
  stage outputs.
- Read [approval-and-recovery.md](references/approval-and-recovery.md) before
  installs, training, checkpoint restoration, or resumption.
- Read [monitoring-contract.md](references/monitoring-contract.md) and
  [control-policy.md](references/control-policy.md) before supervised training.

## Authority Model

Resolve four independent permissions during intake:

- `build_boundary`: `generate_only`, `dry_run`, or `smoke_allowed`
- `experiment_authority`: `none`, `approval_required`, or
  `exact_run_approved`
- `control_authority`: `observe_only`, `manual_approval`, or `bounded_auto`
- `dependency_policy`: `forbidden`, `ask`, or `approved`

Do not infer full-training permission from permission to run imports, rollouts,
or smoke training. Bind `exact_run_approved` to the digest of the run plan,
budget, seeds, environment, code, and config. Any change invalidates it.

## Initialize A Run

Create a new run outside this skill directory:

```bash
python3 autorl-skill-workflow-v2/scripts/statectl.py init \
  --run-dir runs/<run-id> \
  --profile application_delivery \
  --goal "<user goal>" \
  --build-boundary dry_run \
  --experiment-authority none \
  --control-authority observe_only \
  --dependency-policy ask
```

Use `research_iteration` for baseline reproduction or improvement work. The
script creates the state store, immutable event history, stage directories,
runtime directories, and control directories.

## Workflow

### 1. Clarify And Classify

Keep clarification in the main thread. Produce an intake attempt containing
`task_card.json` and `task_card.md`.

Resolve:

- profile and user objective
- environment id, path, source, and RL semantics
- baseline path or reference for research work
- algorithm direction or permission for evidence-backed selection
- primary metric, threshold, seeds, and evaluation protocol
- build, experiment, control, and dependency authorities
- compute and spending budget
- checkpoint, stop, and expected artifact requirements

Stop in `waiting_input` when any field can change environment wiring, algorithm
selection, budget, permissions, or success evaluation.

### 2. Build The Context Gate

Run two bounded workers:

- Environment worker: read and follow
  `skills/autorl-onboard-environment/SKILL.md`.
- Evidence worker: read and follow
  `skills/autorl-retrieve-evidence/SKILL.md`.

For a custom or unverified environment, run the environment worker and then the
independent verifier at `skills/autorl-verify-environment/SKILL.md`. For a
research task with an existing verified environment contract, import it with
its digest and provenance instead of re-inventing it.

Environment onboarding and preliminary retrieval may run concurrently only when
the task card already contains adequate environment semantics. Strategy still
waits for both accepted environment and evidence stages.

### 3. Freeze Strategy And Experiment Contracts

The main orchestrator writes:

- `strategy_decision.json`
- `experiment_contract.json`
- `control_contract.json`

For `application_delivery`, select the smallest maintained training path that
meets the requested interface and artifacts.

For `research_iteration`, freeze the baseline comparator, hypotheses, matched
seeds, budgets, evaluation cadence, checkpoint rules, and allowed differences.
Reproduce or audit the baseline before attributing an improvement.

The evidence worker does not choose the final strategy. The training builder
does not silently change it.

### 4. Build And Verify Training Code

Read and follow `skills/autorl-build-training/SKILL.md`. Give the worker only
accepted artifact paths, digests, allowed targets, and exact validation
commands.

Require:

- training and evaluation entrypoints
- pinned config and dependency surface
- checkpoint and resume hooks
- telemetry emitters matching the monitoring contract
- framework-specific control adapters for each enabled hot-reload action
- usage documentation, build manifest, and bounded smoke report

Do not accept build output until static or smoke verification passes at the
declared build boundary.

### 5. Preflight And Launch

Create a run plan with the exact command, working directory, environment,
config/code/environment digests, seeds, budget, output path, cadence, checkpoint
policy, and approval digest.

Run preflight before launch. Launch full training only when:

- environment, evidence, strategy, build, and preflight stages are accepted
- `experiment_authority` is `exact_run_approved`
- the current run-plan digest matches the approval
- no active launch lease already exists

Use a short canary before a long run. A canary proves integration and telemetry,
not performance.

### 6. Supervise With Bounded Cycles

Training and telemetry collection are external long-lived processes. Do not keep
a Codex turn or child agent alive for the life of training.

At configured environment-step or time intervals, invoke
`skills/autorl-supervise-training/SKILL.md` for one bounded cycle:

```text
observe -> diagnose -> propose -> deterministic guard
        -> hold | request approval | apply at safe boundary
        -> receipt -> cooldown -> re-observe
```

Run `scripts/guard_action.py` on every proposal. A framework-specific actuator
may consume only an unexpired `allow` authorization and must write a receipt.

### 7. Evaluate, Review, And Iterate

Evaluate with the frozen protocol. For research runs, compare baseline and
candidate using matched seeds, budget, cadence, and aggregation.

The main orchestrator chooses one:

- package the result
- hold for more evidence
- return to strategy with a new immutable attempt
- create a child run with one explicit hypothesis/change set
- stop or roll back according to the pre-approved control contract

Never edit an active run's code, reward, observation/action schema, success
criterion, or evaluation protocol. Such changes require a child run.

### 8. Package The Result

Write `result_package.json` and `result_package.md` using accepted artifacts
only. Include:

- final status and profile
- environment, code, config, and approval digests
- baseline/candidate lineage
- tests, runs, and evaluation evidence
- controls applied and checkpoint provenance
- limitations, unsupported claims, and next action

Do not claim learning performance from smoke tests or incomplete evaluations.

## State And Resume

Use the deterministic CLI for every workflow-state change:

```bash
python3 autorl-skill-workflow-v2/scripts/statectl.py show \
  --run-dir runs/<run-id>

python3 autorl-skill-workflow-v2/scripts/statectl.py transition \
  --run-dir runs/<run-id> \
  --expected-version <n> \
  --to <state> \
  --actor main_orchestrator \
  --reason "<why>"

python3 autorl-skill-workflow-v2/scripts/validate_run.py \
  --run-dir runs/<run-id>
```

On resume, validate the event chain and accepted artifact digests, then reconcile
the process heartbeat, launch token, last action authorization/receipt, and
checkpoint. When uncertain, fail closed; do not relaunch or reapply blindly.

## Subagent Handoffs

Read [subagent-handoffs.md](references/subagent-handoffs.md). Persist every child
prompt under the relevant attempt directory before spawning. Require the child
to return only status, output paths, blockers, and next gate. Validate the files
yourself.

## Non-Negotiable Boundaries

- No dependency install, clone, paid compute, or external asset download without
  the matching authority.
- No full training from `smoke_allowed` alone.
- No live code patching or reward/objective changes.
- No automatic action that is absent from the frozen control contract.
- No automatic rollback from a checkpoint below `resume_grade: exact`.
- No performance claim without a complete, comparable evaluation.
- No direct child-to-child handoff that bypasses the main state machine.
