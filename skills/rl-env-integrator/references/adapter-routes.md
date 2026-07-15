# Adapter Routes By Environment Source Type

## official_benchmark

Environment already ships a Gymnasium-compatible interface (Gymnasium classic control, Atari via ALE, many Farama projects).

- Adapter is an identity shim: `make_env(config)` wraps `gym.make(config["env_id"], **config["make_kwargs"])`.
- The shim still matters: it is the single construction entrypoint that keeps spec extraction, smoke, verification, and training building the exact same object.
- Work concentrates in config pinning, spec extraction, and verification.

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

Follow PettingZoo `ParallelEnv` (simultaneous actions) or `AECEnv` (turn-based) instead of single-agent Gymnasium. Record `api_convention` in `env_spec.json`. Per-agent spaces and action masks (e.g. SMAC availability masks) go into the spec's notes until the contract grows dedicated fields.
