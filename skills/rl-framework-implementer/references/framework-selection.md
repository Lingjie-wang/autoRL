# RL Framework Selection

Use this guide after reading task/evidence/decision artifacts and inspecting the workspace.

## Selection Order

Prefer routes in this order:

1. Existing project framework and conventions.
2. Framework explicitly selected in `decision_packet` or `executor_brief`.
3. Framework supported by the strongest codebase evidence in `evidence_report.md`.
4. Maintained standard library that fits the environment and algorithm family.
5. Minimal native implementation when the algorithm is simple and framework setup is heavier than the task.
6. Advisory-only plan when dependencies, simulator, hardware, or approvals block implementation.

## Common Fit Patterns

Single-agent classic/Gymnasium/MuJoCo:

- Stable-Baselines3 for fast PPO/SAC/TD3/DQN baselines.
- CleanRL for readable single-file baselines and educational reproducibility.
- Tianshou or TorchRL when custom collectors, buffers, or training loops matter.
- RLlib when distributed rollout or production-style scaling is required.

Custom Gymnasium-compatible environments:

- Write or validate the env adapter first.
- Use Stable-Baselines3 or Tianshou for first runnable baselines when spaces are standard.
- Use a native PyTorch loop only when the algorithm or interface is too custom for a library.

Multi-agent environments:

- PettingZoo-compatible tasks: consider RLlib, Tianshou, MARLlib, or a maintained MARL stack.
- SMAC/StarCraft-style tasks: consider PyMARL, EPyMARL, or evidence-backed repo candidates.
- Prefer benchmark-native baselines when exact comparability matters.

Offline RL:

- Prefer libraries or repos that explicitly support dataset loading, behavior cloning, and offline evaluation.
- Do not invent dataset format assumptions; block if dataset source/schema is missing.

Imitation learning:

- Use an imitation-learning library or a small BC/GAIL implementation only when demonstrations and evaluation protocol are clear.

External simulators:

- Build a thin adapter/wrapper first.
- Verify simulator startup and one-step interaction before algorithm work.
- Avoid installing heavyweight simulator stacks without explicit approval.

## Choosing Clone Vs Dependency Vs Native Code

Use package dependency when:

- the framework is maintained and installable
- the algorithm is standard
- the environment interface is compatible
- license and dependency risk are acceptable

Clone a repo when:

- evidence identifies official paper code or benchmark baseline
- exact reproducibility matters
- the repo cannot be consumed as a normal package
- user approves clone target and licensing risk

Write native code when:

- the environment/task is small
- the algorithm is simple enough to implement safely
- dependency/network policy blocks installs
- project conventions already have most infrastructure

## Required Rationale

`implementation_plan.md` must state:

- selected framework route
- alternatives considered
- why the route fits the environment and algorithm
- evidence refs used
- license/dependency risks
- what is implemented now vs deferred
