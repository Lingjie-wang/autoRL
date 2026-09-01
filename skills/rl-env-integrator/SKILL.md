---
name: rl-env-integrator
description: Reuse a compatible verified RL environment integration when available, or integrate the environment behind the standard adapter contract and produce verifiable deliverables. Use after task clarification when a concrete official benchmark, custom environment, or external simulator must become constructible, spec-documented, and smoke-tested before algorithm implementation or training.
---

# RL Environment Integrator

## Purpose

Make one concrete RL environment constructible through the standard adapter interface and emit the deliverables defined in [references/env-adapter-contract.md](../../references/env-adapter-contract.md): adapter, config, extracted spec, smoke script, and integration report.

This skill owns environment wiring only. It must not choose algorithms, write training loops, claim performance, or hand-write environment specs. Verification of the integration belongs to `skills/rl-env-verifier/`.

Normal use defaults to `environment_reuse: prefer_verified`. Clean-room workflow
tests must set `environment_reuse: disabled` so prior runs cannot answer the task.

## Inputs

Two accepted input forms:

**Form A — task card** (full AutoRL pipeline):

- a task card with a ready `environment_spec` (env id/path, source type, concrete RL task)
- clear `execution_boundary`
- clear dependency policy

**Form B — direct request** (description + environment code):

- the environment source code (file(s) or a path)
- a natural-language description covering the semantic checklist in
  [description-checklist.md](references/description-checklist.md) — the items
  code alone cannot reveal (observation/action semantics, reward meaning,
  termination rules, randomness sources)

For Form B, read the code first and derive everything derivable from it; use
the description only for semantics. If the description and the code disagree,
trust the code and record the discrepancy in the integration report. If a
blocking checklist item is missing from both, ask — do not guess.

Both forms need a target run directory `runs/<task-id>/`.

Optional reuse input:

- `environment_reuse`: `prefer_verified` (default) or `disabled`
- required API convention, training channel, and verification boundary
- construction config constraints when they affect environment semantics
- source files for custom environments, so reuse requires byte-identical code

Stop if the environment id/path is ambiguous, the source type is unknown, or dependency permissions are unclear. Route back to `skills/rl-task-clarifier/` instead of guessing.

## Workflow

### 1. Run The Reuse Gate

Before writing adapter code, run
[`scripts/find_reusable_integration.py`](scripts/find_reusable_integration.py).
Do not search runs manually or reuse on environment name alone.

Example for a custom environment:

```bash
python skills/rl-env-integrator/scripts/find_reusable_integration.py find \
  --runs-dir runs \
  --env-id ThermalChamber-v0 \
  --source-type custom_env \
  --api-convention gymnasium \
  --source-file incoming/thermal-chamber/env_code.py \
  --required-boundary dry_run \
  --output runs/<task-id>/reuse_search.json
```

The finder requires complete artifacts, a passing non-stale verification
report, matching metadata/config constraints, and matching source hashes when
provided. It returns `reusable`, `reusable_needs_verification`, `not_found`, or
`disabled`.

When reusable, link the verified integration into the new run without copying
or modifying the source run:

```bash
python skills/rl-env-integrator/scripts/find_reusable_integration.py link \
  --source-run runs/<source-run> \
  --target-run runs/<task-id> \
  --required-boundary dry_run
```

This creates `environment_reuse.json` and an
`artifacts/integration` symlink. Write the current run's
`integration_report.md` with `integration_status: reused` and the source run.
If `verification_required` is false, reuse the named source verification and
skip Steps 2-5. If true, keep the linked artifacts read-only and hand the new
run to `rl-env-verifier`; do not rebuild the adapter.

When status is `not_found` or reuse is disabled, continue below.

### 2. Classify The Integration Route

Read [adapter-routes.md](references/adapter-routes.md). Map `environment_spec.type` to a route:

- `official_benchmark`: identity or thin adapter; work is registration, config, spec extraction, verification
- `custom_env`: wrap user code into the Gymnasium API; declare spaces explicitly
- `external_simulator`: adapter owns process lifecycle; plan launch/teardown and failure cleanup

Multi-agent environments follow PettingZoo conventions; record which in `env_spec.json`.

### 3. Inspect The Runtime, Then Gate Dependencies

Check what already exists before proposing any install: Python version, package manager, existing envs/venvs, already-installed frameworks.

Write intended commands into `runs/<task-id>/dependency_plan.md` and wait for approval before running any install. Read [known-pitfalls.md](references/known-pitfalls.md) first — Python version choice and library version pins are the top failure source. Default to an isolated environment (conda env or venv) and pin Python 3.10/3.11 for RL-ecosystem wheel compatibility unless the task card says otherwise.

### 4. Implement The Deliverables

Produce under `runs/<task-id>/artifacts/integration/`:

- `adapter.py`: expose `make_env(config)` as the single construction entrypoint. Every downstream consumer (spec extraction, smoke, verification, training) must construct through it. For environments that require `gym.register_envs(pkg)` before `gym.make` (ale-py, minigrid, gymnasium-robotics), call it **lazily inside `make_env`** behind a module-level flag — never at import time, so several adapters stay importable in one process.
- `env_config.json`: env id, construction kwargs, default seed, pinned dependencies, Python version. Add `episode_step_cap` when `spec.max_episode_steps` is `None` (ALE, MiniGrid) so `extract_spec.py` has a loop bound.
- `extract_spec.py`: builds the env through the adapter and writes `env_spec.json` from live object attributes. Never hand-write spec fields from documentation. **Start from [extract_spec_template.py](references/extract_spec_template.py)** — it contains all required fields with fill-in annotations.
- `smoke_rollout.py`: random-policy episodes checking declared-space containment, finite rewards, bool termination flags, and that episodes end. No performance claims.

#### Required spec fields

The verifier checks ALL of these. Missing any one causes `spec_descriptor_fields` to fail at `generate_only` tier — before the environment is even constructed.

Core fields (same as before):
`env_id`, `source_type`, `api_convention`, `observation_space`, `action_space`, `episode_termination`, `deterministic_under_seed`, `dependencies`

Single-agent descriptor fields (new since 2026-07-26):
`observation_modality`, `action_type`, `goal_conditioned`, `randomness_sources`, `observed_reward_bounds`, `training_channel`

`lossy_notes` is not required by the verifier but is expected in the spec to be honest about what a trainer receives vs what the raw env provides.

#### Episode-length bound

`env.spec.max_episode_steps` is `None` for environments that truncate internally (ALE via frame limit, MiniGrid via `env.unwrapped.max_steps`). `extract_spec.py` must carry its own loop bound — read `env.unwrapped.max_steps` or derive from ALE kwargs; never loop unboundedly. The `smoke_rollout.py` must do the same.

### 5. Extract The Spec And Run The Smoke Test

Allowed only under `dry_run` or `runtime_allowed`. Under `generate_only`, emit the scripts and report the spec/smoke steps as pending.

Default to `runtime_allowed` — it adds multi-episode NaN sweeps, reward-bound consistency, and 10× construct/close cycles for only a few minutes of cost. Only drop to `dry_run` when the environment is behind an external process with a long startup time (e.g. StarCraft II).

Run `extract_spec.py`, then `smoke_rollout.py`. If the smoke fails, capture command, error, likely cause, and smallest next fix; do not proceed to handoff with silent failures.

### 6. Write The Integration Report And Hand Off

Write `runs/<task-id>/integration_report.md` using [integration-report-template.md](references/integration-report-template.md): status, route, runtime pins, deliverable table, smoke result, gotchas discovered, next action.

Hand off to `skills/rl-env-verifier/` for independent verification. Integration is not "done" until verification passes.

## Output Rules

- All deliverables under `runs/<task-id>/artifacts/integration/`, report at `runs/<task-id>/integration_report.md`.
- A reused run instead contains `environment_reuse.json` plus a link at the
  same artifact path; downstream consumers use that path unchanged.
- Pin exact library versions and Python version in `env_config.json`.
- Record every discovered quirk (API differences, doc-vs-runtime mismatches) in the report's gotchas section — these feed back into [known-pitfalls.md](references/known-pitfalls.md).
- Keep adapter code free of algorithm or training logic.

## Anti-Patterns

- Do not hand-write `env_spec.json` from documentation; docs and runtime disagree (e.g. CartPole doc thresholds vs runtime `inf` velocity bounds).
- Do not reuse on `env_id` alone or copy old artifacts into a new run. Use the
  deterministic reuse gate and keep the source run read-only.
- Do not run `pip install`/`conda create` before the dependency plan is approved.
- Do not let scripts construct the environment around the adapter (`gym.make` inline) — construction drift makes verification meaningless.
- Do not treat a passing smoke rollout as verification; the independent verifier still runs.
- Do not claim the environment is trainable or performant from integration artifacts.

## Handoff Wording

When integration is ready for verification:

```text
Environment integration ready: env=<env_id>, route=<source_type>, smoke_status=<passed|pending|failed>. Artifacts: runs/<task-id>/artifacts/integration/, runs/<task-id>/integration_report.md. Next: rl-env-verifier.
```

When blocked:

```text
Environment integration blocked at <step>: <smallest approval or missing input needed>. Artifact: runs/<task-id>/dependency_plan.md
```
