# Smoke Tests

Use smoke tests to prove wiring, not performance.

## Static Checks

Allowed under `generate_only`:

- files exist
- configs parse
- scripts expose `--help` or dry config validation if imports are local-only
- no forbidden paths or hidden dependency commands were added

## Dry-Run Checks

Allowed under `dry_run` when dependencies already exist:

- import selected framework
- construct environment
- inspect observation/action spaces
- reset environment
- take one safe step with a random or no-op action
- instantiate algorithm/model
- run one update step with synthetic or tiny data when safe

## Runtime Smoke Training

Allowed only when `runtime_allowed` and dependencies are satisfied:

- run a tiny number of environment steps or one short epoch
- use one seed unless the task explicitly asks for more
- write logs under the run directory
- stop before full training

## Report Template

Use this structure for `smoke_test_report.md`:

```markdown
# Smoke Test Report

## Status
- smoke_status: passed | partial | failed | skipped
- execution_boundary:
- framework:
- commands_run:

## Checks
| Check | Status | Evidence |
| --- | --- | --- |
| config_parse | ... | ... |
| import_framework | ... | ... |
| env_reset_step | ... | ... |
| algorithm_init | ... | ... |
| tiny_training | ... | ... |

## Failures
- command:
- error:
- likely_cause:
- smallest_next_fix:

## Notes
- performance_claims: none
- full_training_allowed: yes | no
```
