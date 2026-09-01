# Integration Report Template

Write to `runs/<task-id>/integration_report.md`:

```markdown
# Integration Report: <env_id>

## Status
- integration_status: complete | reused | partial | blocked
- route: official_benchmark | custom_env | external_simulator
- api_convention: gymnasium | pettingzoo_parallel | pettingzoo_aec | epymarl_multiagentenv
- execution_boundary_used: runtime_allowed | dry_run | generate_only

## Reuse
- reuse_policy: prefer_verified | disabled
- reuse_status: reused | not_found | disabled
- source_run: runs/<source-run> | none
- source_verification: <path and boundary> | none
- verification_required: true | false

## Environment
- env_id:
- runtime: <isolated env name>, Python <pin>, <library>==<pin>
- role: one sentence on what this environment exercises (e.g. "first continuous action space in this set")

## Deliverables
| File | Purpose |
| --- | --- |
| artifacts/integration/adapter.py | single construction entrypoint `make_env(config)` |
| artifacts/integration/env_config.json | env id, kwargs, seed, pinned dependencies |
| artifacts/integration/extract_spec.py | generates env_spec.json from the live env |
| artifacts/integration/env_spec.json | extracted spec |
| artifacts/integration/smoke_rollout.py | random-policy rollout with contract checks |

## Measured Properties
| Property | Value |
| --- | --- |
| observation | `<space repr>` — modality `vector\|image\|dict\|hybrid` |
| action | `<space repr>` — type `discrete\|continuous` |
| episode end | `terminated` on ...; `truncated` at N |
| observed reward bounds | `[lo, hi]` over N full episodes |
| deterministic under seed | yes \| no (reason) |
| training channel | native \| sb3_atari_wrapper \| sb3_flatobs_wrapper \| ... |

## Channel Lossiness
<!-- Only fill when training_channel != "native". What does a trainer actually receive?
     Leave as "— (native, no loss)" for direct channels. -->
- what was dropped or transformed relative to the raw env

## Smoke Result
- command: `python smoke_rollout.py`
- smoke_status: passed | pending | failed
- observed: N episodes, steps/episode, return range

## Training Smoke
<!-- Optional but encouraged: algorithm, policy, timesteps, status, wall time.
     Proves the environment is consumable by a real trainer, not just the verifier.
     See runs/20260726-sa5-setup/train_smoke.py for the pattern. -->
- algo / policy:
- timesteps:
- status: COMPLETED | FAILED
- trainer received: `<obs space as the trainer saw it after wrappers>`

## Notes And Gotchas
- <every doc-vs-runtime mismatch, version pitfall, or API quirk discovered>
- <if spec.max_episode_steps is None, record where the real limit comes from>
- <if training_channel != native, record why and what the first-choice channel failed with>

## Next Action
Run rl-env-verifier at `runtime_allowed` and emit verification_report.json.
(Or `dry_run` only if the environment has a long external-process startup.)
```

Rules:

- For `integration_status: reused`, point the deliverable table at the linked
  artifact path and record the source run; do not copy its report text.
- `pending` is honest under `generate_only`; never report `passed` for checks that did not run.
- The gotchas section is mandatory even when empty (`- none`); it feeds known-pitfalls.md.
- "Measured Properties" and "Channel Lossiness" replace a blank spec dump — a reader should be able to understand the environment from the report without opening env_spec.json.
- Training smoke is separate from verification. A passing smoke does not replace the verifier; a passing verifier does not imply trainability.
