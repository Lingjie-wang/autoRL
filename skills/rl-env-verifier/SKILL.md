---
name: rl-env-verifier
description: Independently verify an RL environment integration against the adapter contract and emit a machine-readable verification report. Use after rl-env-integrator (or any hand-made integration) produced deliverables under runs/<task-id>/artifacts/integration/, before algorithm implementation or training is allowed to rely on the environment.
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

Stop if deliverables are missing (report that as a `generate_only` failure, do not improvise), or if the boundary forbids the checks the task card demands.

## Workflow

### 1. Select The Tier

Match checks to `execution_boundary`:

- `generate_only`: deliverables exist, spec/config parse, required spec fields present. No environment code executed.
- `dry_run`: everything above, plus construction and behavioral checks.
- `runtime_allowed`: everything above, plus multi-episode NaN/Inf sweeps and repeated construct/close leak cycles.

### 2. Run The Check Catalog

Read [check-catalog.md](references/check-catalog.md) for the full catalog, what accident each check catches, and multi-agent/external-simulator extensions. Execute via [verify_env_template.py](references/verify_env_template.py):

```bash
python verify_env_template.py --run-dir runs/<task-id> --boundary dry_run
```

### 3. Self-Test The Verifier When It Changed

If the verifier script or check catalog was modified for this task, prove it still catches failures before trusting a green run: sabotage one spec field (e.g. flip a declared shape), confirm the corresponding check fails with exit code 1, then regenerate the spec via `extract_spec.py` and re-verify. A verifier that cannot fail is decoration, not verification.

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
