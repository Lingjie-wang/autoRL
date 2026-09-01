---
name: rl-env-verifier
description: Independently verify an RL environment integration against the adapter contract and emit a machine-readable verification report. Use after rl-env-integrator or a hand-made integration produces deliverables in an AutoRL run directory, before algorithm implementation or training is allowed to rely on the environment.
---

# RL Environment Verifier

## Purpose

Act as the independent acceptance gate for an environment integration. Re-construct the environment through the adapter under test and check every claim in `env_spec.json` against runtime behavior, per [references/env-adapter-contract.md](../../references/env-adapter-contract.md). Emit `runs/<task-id>/verification_report.json` with a nonzero exit on failure so downstream stages can be gated mechanically.

This skill owns integration verification only. It proves the environment behaves as declared; it makes no claims about trainability or performance, and it must not fix integration code itself.

## Trust Model

- Do not reuse or trust the integrator's smoke results; re-derive all behavioral checks independently.
- Trust only `adapter.make_env(config)` for construction — the adapter is the product under test, and bypassing it (inline `gym.make`) would verify a different object than training will use.
- Verify claims, not intentions: the spec says what the env does; the verifier observes what it actually does.

## Inputs

Minimum viable inputs:

- run directory `runs/<task-id>/` containing `artifacts/integration/` deliverables
- `execution_boundary` for this verification pass

When `environment_reuse.json` exists, `artifacts/integration` may link to a
verified source run. Read through the link, keep its target immutable, and
write the current verification report in the current run.

Stop if deliverables are missing (report that as a `generate_only` failure, do not improvise), or if the boundary forbids the checks the task card demands.

## Workflow

### 1. Select The Tier

Match checks to `execution_boundary`:

- `generate_only`: deliverables exist, spec/config parse, required spec fields present. No environment code executed.
- `dry_run`: everything above, plus construction and behavioral checks.
- `runtime_allowed`: everything above, plus multi-episode NaN/Inf sweeps and repeated construct/close leak cycles.

Any loop that waits for an episode to end must carry an explicit step cap.
`env.spec.max_episode_steps` is `None` whenever truncation is internal to the
environment (ALE's frame limit, MiniGrid's `env.unwrapped.max_steps`), so it
cannot supply the bound. Hitting the cap is recorded as its own outcome, never
silently treated as "still running".

### 2. Run The Check Catalog

Read [check-catalog.md](references/check-catalog.md) for the full catalog, what accident each check catches, and multi-agent/external-simulator extensions.

Dispatch on `env_spec.json`'s `api_convention`:

- `gymnasium` (single-agent) → [verify_env_template.py](references/verify_env_template.py)

  ```bash
  python verify_env_template.py --run-dir runs/<task-id> --boundary runtime_allowed
  ```

  This is the only template implementing all three tiers, including
  `runtime_allowed` (multi-episode NaN sweep, reward-bound consistency, 10×
  construct/close cycles). It also enforces the single-agent descriptor fields
  (`observation_modality`, `action_type`, `goal_conditioned`,
  `randomness_sources`, `observed_reward_bounds`, `training_channel`).

  Three properties of this verifier exist because naive versions silently
  passed: observations are fingerprinted with a recursive `canonical_bytes()`
  rather than `repr()` (numpy abbreviates large arrays, so `repr` equality can
  match divergent trajectories); space reprs are compared with memory addresses
  normalized out (MiniGrid's `MissionSpace` embeds one); and rewards are
  type-checked as `numbers.Real` (`np.float32` is not a Python `float`).

- `pettingzoo_parallel` (multi-agent, simultaneous) → [verify_parallel_env_template.py](references/verify_parallel_env_template.py)

  ```bash
  python verify_parallel_env_template.py --run-dir runs/<task-id> --boundary dry_run
  ```

- `epymarl_multiagentenv` (pull-style MultiAgentEnv: SMAC, SMACv2, or anything routed through EPyMARL's gymma) → [verify_epymarl_env_template.py](references/verify_epymarl_env_template.py)

  ```bash
  python verify_epymarl_env_template.py --run-dir runs/<task-id> --boundary dry_run
  ```

The epymarl verifier adds two check families the other two cannot have: **env_info self-consistency** (`get_env_info()` is the trainer's sizing contract, so `len(get_state())`, `len(get_obs())`, and mask lengths must match what it advertises) and **declared-lossiness honesty** (`global_state.source` and `action_mask.source` are compared against observed behavior, catching a spec that claims native state/masks when the channel actually delivers concatenated observations and all-legal padding).

The parallel verifier adds multi-agent-only checks: per-agent space match, reset/step dict keys equal the active agent set, monotonic agent-set shrink (no resurrection), action masks present at the declared location, and reset restoring `possible_agents`. Both emit the same `verification_report.json` shape.

### 3. Self-Test The Verifier When It Changed

If the verifier script or check catalog was modified for this task, prove it still catches failures before trusting a green run: sabotage one spec field (e.g. flip a declared shape), confirm the corresponding check fails with exit code 1, then regenerate the spec via `extract_spec.py` and re-verify. A verifier that cannot fail is decoration, not verification.

For a reused integration, perform sabotage/self-testing only on an isolated
temporary copy. Never edit or regenerate files through the reuse link.

### 4. Report And Gate

`verification_report.json` follows [report-schema.md](references/report-schema.md): overall status, per-check records with expected/observed/smallest_fix, and `performance_claims: none`.

On failure, hand back to `skills/rl-env-integrator/` with the failed records; do not patch integration files from this skill. On pass, downstream implementation may rely on the environment.

## Output Rules

- Report path is fixed: `runs/<task-id>/verification_report.json`.
- Every failed check carries `expected`, `observed`, and `smallest_fix`.
- Checks that did not run are `skipped` with a reason, never omitted and never counted as passed.
- Exit code must reflect overall status (0 pass, nonzero fail) for mechanical gating.

## Anti-Patterns

- Do not round partial verification up to `passed`.
- Do not verify a hand-edited `env_spec.json`; if the spec was touched manually, require regeneration via `extract_spec.py` first.
- Do not construct the environment around the adapter.
- Do not modify a source run referenced by `environment_reuse.json`.
- Do not claim the environment is trainable because verification passed.
- Do not silently downgrade the tier (e.g. skip determinism because it is slow) without a `skipped` record.

## Handoff Wording

When verification passes:

```text
Environment verification passed: env=<env_id>, boundary=<tier>, checks=<passed>/<total>. Artifact: runs/<task-id>/verification_report.json. Downstream implementation may rely on this environment.
```

When verification fails:

```text
Environment verification failed: env=<env_id>, <n> failed checks (<check names>). Artifact: runs/<task-id>/verification_report.json. Route back to rl-env-integrator with the smallest_fix entries.
```
