# Implementation Artifacts

Use this guide when writing code/configs for the selected framework path.

## Preferred Output Layout

When no target directory is specified in the executor brief, use:

```text
runs/<task-id>/
  implementation_plan.md
  dependency_plan.md
  install_log.md                 # when installs/clones happen
  smoke_test_report.md
  run_config.json
  artifacts/
    implementation/
      train.py
      evaluate.py
      env_adapter.py
      configs/
```

When the executor brief provides allowed targets, follow those targets and still write the run reports under `runs/<task-id>/`.

## Minimum Runnable Path

For a framework-based implementation, provide:

- environment creation or registration
- algorithm/model construction
- training config with seed and budget
- evaluation config and metrics
- logging path
- checkpoint path when runtime is allowed
- smoke-test command

For a native implementation, provide:

- clear algorithm class/function boundaries
- replay/buffer/collector abstractions only when needed
- deterministic seeding
- small config object or file
- minimal tests for tensor shapes, env step, and one update step

For an adapter-only implementation, provide:

- wrapper around observation/action/reward/done interfaces
- validation of spaces/schema
- one reset and one step check
- notes for unsupported simulator features

## Code Quality Rules

- Keep edits scoped to the requested implementation path.
- Follow local project style and entrypoint patterns.
- Use config files for hyperparameters instead of burying important values in code.
- Make smoke-test budgets tiny and visibly separate from real experiment budgets.
- Log metrics needed by the task card: return, success rate, loss, episode length, wall-clock, or custom metric.
- Keep evaluation distinct from training.
- Do not claim benchmark performance from smoke outputs.

## Required Implementation Plan

`implementation_plan.md` should include:

- selected framework/route
- files added or changed
- algorithm and environment wiring
- config and command examples
- approval gates encountered
- smoke-test scope
- what remains before real experiments
