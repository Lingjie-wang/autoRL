# Choice Prompt Templates

Use these option sets when the host can show interactive choices. If the host adds a free-form `Other` option automatically, provide only the fixed options listed here. If not, append `Other / custom: describe your case`.

Keep each popup to 1-3 questions. Ask the minimum set needed to unblock the next ambiguity gate.

## Task Mode

Question: `这次 AutoRL 需求主要是哪一类？`

Options:

1. `科研质量提升 (Recommended)` — Improve research content quality: method idea, experiment rigor, baselines, training stability, result analysis, or paper claims.
2. `项目应用: 新环境跑通算法` — Make an RL algorithm run and evaluate in a specified new environment.

Maps to:

- `research_quality_improvement`
- `application_new_env_algorithm`

## Environment Source

Question: `目标环境来自哪里？`

Options:

1. `官方/标准环境 (Recommended)` — Gymnasium, MuJoCo, Atari, Minigrid, PettingZoo, MetaWorld, D4RL, or similar maintained benchmark.
2. `自定义环境代码` — A local Python environment path, package, or wrapper already exists or needs to be created.
3. `外部模拟器/系统` — A simulator, robotics stack, game engine, or service needs an adapter.

Maps to:

- `official_benchmark`
- `custom_env`
- `external_simulator`

## RL Task Type

Question: `强化学习任务类型更接近哪一种？`

Options:

1. `在线 RL (Recommended)` — The agent interacts with the environment during training.
2. `离线 RL / 数据集训练` — Training uses a fixed dataset or logged trajectories.
3. `模仿学习 / 多智能体 / 安全约束` — The task is imitation, multi-agent, safety-constrained, or otherwise non-standard.

## Algorithm Direction

Question: `大致算法方向是什么？`

Options:

1. `标准 baseline 先跑通 (Recommended)` — Let the next stage choose a standard baseline from environment/task evidence.
2. `on-policy / policy gradient` — PPO, A2C, TRPO, MAPPO, or similar.
3. `off-policy / value or actor-critic` — SAC, TD3, DQN, Rainbow, or similar.

If offline RL, imitation learning, model-based RL, safe RL, or multi-agent RL is already implied, ask a follow-up or let the user choose custom text.

## Success Metric

Question: `成功主要看什么指标？`

Options:

1. `平均回报 (Recommended)` — Mean evaluation return over fixed episodes/seeds.
2. `成功率` — Task completion rate, common for manipulation/navigation.
3. `样本效率 / 稳定性` — Learning speed, variance across seeds, or training stability.

## Runtime Boundary

Question: `现在允许执行到什么程度？`

Options:

1. `只生成方案/代码 (Recommended)` — Generate task card, configs, or scripts without real training.
2. `dry run / smoke test` — Run only tiny checks for env wiring and script validity.
3. `允许真实训练` — Run training within stated compute and approval gates.

## Compute Budget

Question: `算力预算大致是什么？`

Options:

1. `本地 CPU/小规模 (Recommended)` — Start with smoke runs and small experiments.
2. `单张本地 GPU` — Use one GPU with explicit wall-time/step limits.
3. `远程/集群 GPU` — Requires approval before spending or queue submission.
