# Environment Adapter Contract

Defines what "an RL environment is integrated" means in this workflow. The integration skill produces these deliverables; the verification skill checks them. Both must agree on this contract, so changes here require updating both skills.

## Adapter Standard

Every integrated environment must expose the Gymnasium API:

- `observation_space` and `action_space` declared as `gymnasium.spaces` objects
- `reset(seed=..., options=...) -> (observation, info)`
- `step(action) -> (observation, reward, terminated, truncated, info)`
- `close()`
- deterministic reproduction: same seed and same action sequence produce the same trajectory, or the adapter documents why not (e.g. external simulator with internal randomness)

Multi-agent environments follow the PettingZoo `ParallelEnv` or `AECEnv` convention instead. The `env_spec.json` must state which convention applies.

## Integration Routes By Source Type

Matches `environment_spec.type` in the task card:

- `official_benchmark`: environment already ships a Gymnasium-compatible interface. Adapter is thin or identity; integration work is registration, config, spec extraction, and verification.
- `custom_env`: user-provided environment code without standard interface. Adapter wraps it into the Gymnasium API and declares spaces explicitly.
- `external_simulator`: environment lives behind a process/network boundary. Adapter owns lifecycle (launch, connect, teardown) and must document failure modes and cleanup.

## Deliverables

An integration is complete when all of these exist:

```text
runs/<task-id>/artifacts/integration/
  adapter.py            # or package; identity shim allowed for official_benchmark
  env_config.json       # construction kwargs, ids, paths, version pins (JSON: stdlib-parseable, matches repo JSON artifacts)
  env_spec.json         # machine-readable spec, schema below
  extract_spec.py       # generates env_spec.json from the constructed env (spec must never be hand-written)
  smoke_rollout.py      # standalone script: construct, reset, N random steps
runs/<task-id>/integration_report.md
```

Plus, produced by the verification skill:

```text
runs/<task-id>/verification_report.json
```

## env_spec.json Schema

```json
{
  "env_id": "CartPole-v1",
  "source_type": "official_benchmark | custom_env | external_simulator",
  "api_convention": "gymnasium | pettingzoo_parallel | pettingzoo_aec",
  "observation_space": "repr of the space, with dtype and shape",
  "action_space": "repr of the space, with dtype and shape",
  "reward_range": [null, null],
  "episode_termination": "how episodes end, including truncation limit",
  "deterministic_under_seed": true,
  "dependencies": ["gymnasium>=0.29"],
  "notes": "known quirks, e.g. action masking, non-standard info keys"
}
```

Space fields must be extracted from the constructed environment, not hand-written from documentation.

## Verification Tiers

Checks are gated by `execution_boundary`, following the pattern in `skills/rl-framework-implementer/references/smoke-tests.md`:

- `generate_only`: deliverable files exist, `env_spec.json` parses and has all required fields, config parses.
- `dry_run`: import adapter, construct env, verify declared spaces match `observation_space`/`action_space` at runtime, `reset` returns an observation contained in the declared space, take random steps and check every return value's type/shape/containment, verify episodes can terminate, verify seed determinism over two identical rollouts, verify `close()` is safe.
- `runtime_allowed`: random-policy rollout over multiple full episodes checking for NaN/Inf in observations and rewards, reward magnitudes within `reward_range`, no resource leaks across repeated construct/close cycles.

Verification proves the environment behaves as declared. It makes no claims about trainability or performance.

## Failure Reporting

A failed check must record: the check name, the expected contract clause, the observed value, and the smallest suggested fix. Partial verification is reported honestly with explicit gaps, never rounded up to "passed".
