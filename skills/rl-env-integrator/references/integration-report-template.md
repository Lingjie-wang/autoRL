# Integration Report Template

Write to `runs/<task-id>/integration_report.md`:

```markdown
# Integration Report: <env_id>

## Status
- integration_status: complete | partial | blocked
- route: official_benchmark | custom_env | external_simulator
- api_convention: gymnasium | pettingzoo_parallel | pettingzoo_aec
- execution_boundary_used:

## Environment
- env_id:
- runtime: <isolated env name>, Python <pin>, <library>==<pin>

## Deliverables
| File | Purpose |
| --- | --- |
| artifacts/integration/adapter.py | single construction entrypoint `make_env(config)` |
| artifacts/integration/env_config.json | env id, kwargs, seed, pinned dependencies |
| artifacts/integration/extract_spec.py | generates env_spec.json from the live env |
| artifacts/integration/env_spec.json | extracted spec |
| artifacts/integration/smoke_rollout.py | random-policy rollout with contract checks |

## Smoke Result
- command:
- smoke_status: passed | pending | failed
- observed:

## Notes And Gotchas
- <every doc-vs-runtime mismatch, version pitfall, or API quirk discovered>

## Next Action
Run rl-env-verifier at <boundary> and emit verification_report.json.
```

Rules:

- `pending` is honest under `generate_only`; never report `passed` for checks that did not run.
- The gotchas section is mandatory even when empty (`- none`); it feeds known-pitfalls.md.
