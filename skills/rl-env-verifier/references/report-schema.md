# Verification Report Schema

`runs/<task-id>/verification_report.json`:

```json
{
  "task_id": "20260715-cartpole-integration",
  "contract": "references/env-adapter-contract.md",
  "verified_at_boundary": "generate_only | dry_run | runtime_allowed",
  "overall_status": "passed | failed",
  "summary": {"passed": 11, "failed": 0, "skipped": 0},
  "checks": [
    {
      "check": "observation_space_matches_declared",
      "tier": "dry_run",
      "status": "passed | failed | skipped",
      "expected": "the contract clause or declared value",
      "observed": "what runtime actually showed",
      "smallest_fix": "present only on failure"
    }
  ],
  "performance_claims": "none"
}
```

Rules:

- `overall_status` is `failed` if any check failed; `skipped` never fails the run but must carry a reason in `observed`.
- `expected`/`observed` must contain concrete values, not "mismatch" — the reader should diagnose from the record alone.
- `smallest_fix` is directed at whoever fixes the integration (human or rl-env-integrator rerun).
- `performance_claims: none` is a standing field: this report never certifies trainability.
- Exit code of the producing script mirrors `overall_status` for mechanical gating.
