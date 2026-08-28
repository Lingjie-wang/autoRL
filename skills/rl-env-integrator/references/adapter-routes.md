# Adapter Routes By Environment Source Type

## official_benchmark

Environment already ships a Gymnasium-compatible interface (Gymnasium classic control, Atari via ALE, many Farama projects).

- Adapter is an identity shim: `make_env(config)` wraps `gym.make(config["env_id"], **config["make_kwargs"])`.
- The shim still matters: it is the single construction entrypoint that keeps spec extraction, smoke, verification, and training building the exact same object.
- Work concentrates in config pinning, spec extraction, and verification.
- **Lazy registration**: `ale-py`, `minigrid`, and `gymnasium-robotics` only
  register their env ids when `gymnasium.register_envs(<pkg>)` runs. Call it
  inside `make_env` behind a module-level flag, never at import time, so several
  adapters stay importable in one process.
- Fill the single-agent descriptor fields (`observation_modality`, `action_type`,
  `goal_conditioned`, `randomness_sources`, `observed_reward_bounds`,
  `training_channel`, `lossy_notes`) from the live env plus the wrapper source.
  A space `repr` alone does not tell a consumer whether it faces 17 float64
  features or a 210×160×3 frame.
- Measure `observed_reward_bounds` over **at least as many full episodes as the
  verifier sweeps** (currently 5), and treat the result as a floor, not a range.

Worked examples: `runs/20260726-sa5-{lunarlander,halfcheetah,pong,minigrid,fetchreach}/`.
Overview with modalities, channels, and losses:
`references/single-agent-environment-catalog.md`.

## custom_env

User-provided environment code without a standard interface.

- Subclass `gymnasium.Env`; declare `observation_space`/`action_space` explicitly from the wrapped object's actual data (dtype and shape from real samples, not guesses).
- Map the native lifecycle to `reset(seed=...) -> (obs, info)` and `step(a) -> (obs, reward, terminated, truncated, info)`.
- Split "episode ended naturally" (`terminated`) from "cut off by step limit" (`truncated`). If the native env has one combined `done`, decide the split explicitly and document it in `env_spec.json` notes.
- Thread the seed into every randomness source the native env owns; if any source cannot be seeded, declare `deterministic_under_seed: false` with the reason.

## external_simulator

Environment behind a process or network boundary (StarCraft II for SMAC, robotics sims, game servers).

- Adapter owns lifecycle: launch/connect in construction, disconnect/kill in `close()`.
- `close()` must be idempotent and must reap the child process; verify with repeated construct/close cycles — leaks surface at episode 50, not episode 1.
- Document failure modes in the report: simulator not installed, port conflicts, license/asset requirements, startup latency.
- Construction requires assets/binaries: gate them through `dependency_plan.md` like any install.

## Multi-Agent Environments

Follow PettingZoo `ParallelEnv` (simultaneous actions) or `AECEnv` (turn-based) instead of single-agent Gymnasium. Record `api_convention` in `env_spec.json`. See the "Multi-Agent Environments (PettingZoo)" section of `references/env-adapter-contract.md` for the required surface, the extra `env_spec.json` fields (`possible_agents`, per-agent `observation_spaces`/`action_spaces`, `action_mask_location`, `agents_can_terminate_early`), and the multi-agent verification tier.

ParallelEnv adapter rules that differ from single-agent:

- `reset`/`step` speak dicts keyed by the CURRENTLY-ACTIVE agents, not lists or single values.
- Maintain `agents` (active) vs `possible_agents` (all). Drop an agent the step after its done flag is True; never re-add before `reset`. Restore the full set in `reset`.
- Split each agent's combined native `done` into per-agent `terminated` (task outcome) vs `truncated` (step/turn limit).
- Surface action masks at one declared location (`info[agent]["action_mask"]` is the default here) and record it in the spec.
- Verify with `skills/rl-env-verifier/references/verify_parallel_env_template.py`.

Worked example: `runs/20260715-coin-arena-integration/` — a legacy `setup/advance` dict env with dying agents and per-agent masks, wrapped without importing pettingzoo. If official conformance is required, gate a pettingzoo install and add `pettingzoo.test.parallel_api_test` as a runtime check.

## EPyMARL Family (PyMARL / EPyMARL, QMIX lineage)

When the target trainer is EPyMARL, the environment must end up as a pull-style `MultiAgentEnv` (`api_convention: "epymarl_multiagentenv"`). See the contract's "EPyMARL MultiAgentEnv Convention" section for the required surface and the extra spec fields.

Pick the channel by what the environment natively provides:

- **Direct wrapper** — the environment already speaks the dialect (SMAC, SMACv2, SMAClite). Thin shim; native masks and native centralized state survive. **Required** for any environment whose action legality matters.
- **`gymma`** — generic Gym-style multi-agent environments. Masks are dropped; `get_state()` becomes concatenated observations.
- **`pz_wrapper` → `gymma`** — PettingZoo sources (MPE). Same losses.
- **`vmas_wrapper` → `gymma`** — VMAS. Same losses.

Rules for this route:

- Reproduce the **real** channel, including its losses; do not build a better-than-real path, or the spec misrepresents what training receives.
- Detect `global_state.source` and `action_mask.source` from the live environment (compare `get_state()` against concatenated observations; check whether any action is actually masked out). Never assert them by hand.
- Set `SC2PATH` and any asset paths from `env_config.json`, not shell state.
- Import `smac` / `smacv2` lazily and never together (PySC2 `DuplicateMapError`).
- Normalize `step()` to the EPyMARL 5-tuple; upstream SMAC returns 3.

Worked examples: `runs/20260726-marl5-{smacv1,smacv2,mpe,vmas}/`. Overview of all verified environments with shapes, channels, and launch commands: `references/marl-environment-catalog.md`.
