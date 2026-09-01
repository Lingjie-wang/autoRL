# RL Clarification Schema

Use this schema to score whether an RL task is clear enough for downstream AutoRL stages.

## Scoring

Each field has a weight. Sum unresolved weights and divide by total weight.

```text
ambiguity_score = unresolved_weight / total_weight
```

Gate:

- `0.00-0.15`: ready
- `0.16-0.30`: usable only with explicit assumptions
- `>0.30`: keep clarifying
- any unresolved `must` field: blocked unless the user explicitly approves an assumption

## Field Matrix

| Field | Need | Weight | Blocking rule |
| --- | --- | ---: | --- |
| `user_goal` | must | 8 | Block if the desired outcome is unknown. |
| `task_mode` | must | 9 | Block if research-quality-improvement vs application/new-environment execution is unclear. |
| `intent` | must | 5 | Block if build/debug/review/advisory cannot be inferred. |
| `execution_boundary` | must | 10 | Block if real training permission is unknown. |
| `environment_spec.environment_type` | must | 8 | Block if official/standard vs custom vs external simulator is unclear. |
| `environment_spec.id_or_path` | must | 10 | Block if no environment, benchmark, or env-building instruction exists. |
| `environment_spec.rl_task` | must | 7 | Block if the concrete behavior/task to learn or evaluate is unclear. |
| `environment_spec.observation_space` | should | 5 | Block only for custom env implementation. |
| `environment_spec.action_space` | should | 5 | Block only for custom env implementation or algorithm-sensitive tasks. |
| `environment_spec.reward_signal` | must | 8 | Block for custom envs; assumable for named benchmark envs. |
| `environment_spec.termination` | should | 4 | Block only when implementing an env wrapper. |
| `objective.primary_metric` | must | 8 | Block if success cannot be measured. |
| `success_criteria.threshold` | must | 8 | Block unless user explicitly asks for exploratory/advisory work. |
| `evaluation_protocol` | must | 7 | Block if train-only results could be mistaken for evaluation. |
| `baseline_or_comparator` | should | 4 | Assumable for first-pass training; high-impact for research claims. |
| `algorithm_direction` | must | 7 | Block if neither a rough algorithm family nor permission for evidence-backed selection is known. |
| `runtime_constraints.compute` | must | 6 | Block before running training; assumable for generate-only. |
| `runtime_constraints.budget` | should | 5 | Block if training cost may be substantial. |
| `dependency_policy` | must | 5 | Block if new installs may be needed and policy is unknown. |
| `artifact_expectations` | should | 3 | Assumable to code/config/metrics/report. |
| `approval_gates` | should | 3 | Assumable to ask before expensive training or dependency install. |
| `safety_constraints` | must | 4 | Block for real robots, finance, healthcare, or external systems. |

Total weight: 134.

## Safe Defaults

Use these only when they do not change cost, safety, or evaluation validity:

| Missing field | Default | Risk |
| --- | --- | --- |
| `intent` | `build` if user asks to train/create an agent | low |
| `domain` | `reinforcement_learning` | low |
| `artifact_expectations` | training config, script, telemetry, summary report | low |
| `approval_gates` | ask before dependency install, long training, remote spend | low |
| `environment_reuse` | `prefer_verified`; use `disabled` for clean-room workflow tests | low |
| `baseline_or_comparator` | simple canonical baseline for the environment family | medium |
| `runtime_constraints.budget` | smoke run only | medium |

Never silently default:

- `execution_boundary`
- `task_mode`
- `environment_spec.environment_type`
- `environment_spec.rl_task`
- `algorithm_direction` unless the user explicitly authorizes evidence-backed algorithm selection
- real-money cloud or remote GPU spend
- real-robot or external-system execution
- success metric and threshold
- custom reward definition
- dataset/source for offline RL

## RL-Specific Question Bank

Use these as templates, not as a fixed questionnaire.

Prefer the interactive choice templates in [choice-prompts.md](choice-prompts.md) for blocking fields. Use these open-ended questions only when the fixed choices do not fit or the user selects a custom option.

### Task Mode

- Is this mainly a research task to improve method/experiment/paper quality, or an application task to make an RL algorithm run in a new environment?
- If research-oriented, what quality is being improved: idea novelty, algorithm design, experiment rigor, baseline coverage, training stability, result analysis, or paper claims?
- If application-oriented, what concrete environment should be made runnable and what algorithm family should be tried first?

### Environment

- Is the environment an official/standard benchmark, a custom environment, or an external simulator that needs an adapter?
- Is the target an existing Gymnasium/MuJoCo/Atari/Minigrid/PettingZoo environment, a custom Python env, or a simulator that needs a wrapper?
- If custom, what are the observation shape/type, action space, reward, and done condition?
- Is this online RL, offline RL from a dataset, imitation learning, or multi-agent RL?
- What exact behavior should the policy learn or improve in this environment?

### Objective And Metrics

- What is the primary success metric: average return, success rate, regret, safety violation rate, sample efficiency, or wall-clock speed?
- What threshold counts as success, and over how many seeds/evaluation episodes?
- Should AutoRL optimize for final performance, sample efficiency, robustness, stability, or reproducibility?

### Runtime Boundary

- May the workflow run real training now, or should it only generate code/configs?
- What compute is allowed: CPU, one local GPU, remote GPU, or a fixed cluster queue?
- What are the max training steps, wall-clock time, and dependency-install policy?

### Algorithm And Evidence

- What rough algorithm direction do you want: PPO/SAC/TD3/DQN, offline RL, imitation learning, model-based RL, multi-agent RL, safe RL, exploration-focused RL, or evidence-backed standard baseline selection?
- Are any algorithms required or forbidden?
- Should the system prefer simple standard baselines first, or search recent papers before choosing?
- Are there existing codebases, checkpoints, logs, or baselines that must be reused?

### Artifacts

- What should the final package include: runnable code, config files, plots, telemetry, checkpoints, report, or a PR?
- Should the workflow pause before long training, before changing algorithms, or before spending remote compute?

## Output Example

Prefer Markdown for the executor-facing task card:

```markdown
# AutoRL Task Card

## Gate Status
- handoff_status: ready
- ambiguity_score: 0.10
- next_stage: context_assembly
- reason: Environment, metric, threshold, and runtime boundary are actionable.

## User Goal
Train an RL agent for Gymnasium CartPole-v1.

## Task Mode
- mode: application_new_env_algorithm
- rationale: The user wants an agent trained and evaluated in a named benchmark environment.

## Confirmed Facts
- Environment type: official benchmark
- Environment: Gymnasium CartPole-v1
- RL task: balance the pole for as long as possible
- Algorithm direction: evidence-backed standard baseline selection is allowed
- Execution boundary: runtime_allowed
- Primary metric: mean_eval_return

## Assumptions
- Use evidence-backed algorithm selection in the next stage.
- Exact wall-clock budget is unspecified; run a smoke test first and ask before full training.

## Blocked Or Missing Context
- None blocking.

## RL Environment
- environment_type: official_benchmark
- id_or_path: CartPole-v1
- source: Gymnasium
- rl_task: balance the pole by applying left/right cart forces

## Algorithm Direction
- rough_family_or_policy: evidence-backed standard baseline selection
- required_algorithms: none
- forbidden_algorithms: none
- selection_notes: Prefer a simple standard baseline unless evidence retrieval indicates otherwise.

## Objective And Success Criteria
- primary_metric: mean_eval_return
- threshold: 475
- evaluation_protocol: 10 evaluation episodes

## Runtime Constraints
- compute: local
- dependency_policy: ask_before_install

## Expected Artifacts
- training script
- config
- telemetry
- summary report
```

Optional structured mirror:

```yaml
handoff_status: ready
ambiguity_score: 0.10
confirmed_facts:
  task_mode: application_new_env_algorithm
  environment_type: official_benchmark
  environment: Gymnasium CartPole-v1
  rl_task: balance the pole
  algorithm_direction: evidence-backed standard baseline selection
  execution_boundary: runtime_allowed
  primary_metric: mean_eval_return
assumptions:
  - Use a simple standard baseline unless evidence retrieval finds a stronger reason to choose another algorithm.
blocked_fields: []
missing_context:
  - Exact wall-clock budget not provided; defaulting to smoke run first, then ask before full training.
task_card:
  user_goal: Train an RL agent for CartPole-v1.
  domain: reinforcement_learning
  intent: build
  task_mode: application_new_env_algorithm
  execution_boundary: runtime_allowed
  environment_spec:
    environment_type: official_benchmark
    id_or_path: CartPole-v1
    source: Gymnasium
    rl_task: balance the pole by applying left/right cart forces
  algorithm_direction:
    rough_family_or_policy: evidence-backed standard baseline selection
    required_algorithms: []
    forbidden_algorithms: []
  objective:
    primary_metric: mean_eval_return
  success_criteria:
    threshold: 475
    eval_episodes: 10
  runtime_constraints:
    compute: local
    dependency_policy: ask_before_install
next_stage_recommendation:
  stage: context_assembly
  reason: Environment, metric, threshold, and runtime boundary are actionable.
```
