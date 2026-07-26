# Known Integration Pitfalls

Append new entries as integrations discover them. Each entry: symptom, cause, rule.

## Python Version Too New

- Symptom: `pip install` fails building wheels, or imports crash on a fresh env.
- Cause: RL libraries lag latest Python; 3.13 lacks wheels for several RL stacks.
- Rule: pin Python 3.10/3.11 in the isolated env unless the task card requires otherwise. Record the pin in `env_config.json`.

## Documentation Lies About Spaces

- Symptom: verification fails containment or bounds checks that "should" pass per docs.
- Cause: doc tables describe termination thresholds, not the declared space (CartPole docs say ±4.8/±24°; the live space has `inf` velocity bounds).
- Rule: extract every spec field from the constructed environment. Never hand-copy from docs.

## Old Gym vs Gymnasium API

- Symptom: `ValueError: too many values to unpack`, or `done` used as one flag.
- Cause: legacy Gym used `step -> (obs, reward, done, info)` (4-tuple); Gymnasium uses a 5-tuple with `terminated`/`truncated` split, and `reset` returns `(obs, info)`.
- Rule: adapters always expose the Gymnasium 5-tuple. When wrapping legacy code, decide the terminated/truncated split explicitly.

## Removed/Deprecated Attributes

- Symptom: `AttributeError` on attributes older tutorials rely on.
- Cause: gymnasium 1.x removed `env.reward_range` from the core API, among others.
- Rule: read optional attributes with `getattr(..., default)`; record nulls in the spec rather than inventing values.

## SMAC + SMACv2 In One Process → DuplicateMapError

- Symptom: `pysc2.maps.lib.DuplicateMapError: Duplicate map found: 3m` on import.
- Cause: `smac` and `smacv2` both register map ids with PySC2 at import time.
- Rule: import either package **lazily inside the adapter constructor**, never at
  module top level, and never both in one process. EPyMARL does the same via
  dynamic registration (`src/envs/__init__.py`: `register_smac()` /
  `register_smacv2()`).

## MPE Moved Out Of PettingZoo

- Symptom: `ModuleNotFoundError: No module named 'pettingzoo.mpe'`.
- Cause: PettingZoo >= 1.25 removed the bundled MPE; it now ships as the
  standalone `mpe2` package.
- Rule: depend on `mpe2`. It is also a **lazy package** — scenarios exist only as
  submodules, so `getattr(mpe2, "simple_spread_v3")` raises AttributeError; use
  `importlib.import_module("mpe2.simple_spread_v3")`.

## numpy 2.x Breaks The SMAC/PySC2 Stack

- Symptom: import or runtime errors in pysc2/smac on a fresh env.
- Rule: pin `numpy<2` (1.26.4 verified) for any environment set including
  SMAC/SMACv2. Record the pin in `env_config.json`.

## sacred Needs pkg_resources

- Symptom: `ModuleNotFoundError: No module named 'pkg_resources'` when importing
  `sacred` (EPyMARL's experiment runner).
- Cause: fresh Python 3.11+ envs ship without setuptools.
- Rule: install `setuptools<81` alongside sacred.

## VMAS Returns Batched Torch Tensors

- Symptom: shapes are one dimension too large; `obs_shape` looks wrong.
- Cause: VMAS is vectorized — every return is a torch tensor shaped
  `(num_envs, ...)`.
- Rule: take batch element 0 and convert to flat numpy. Also note VMAS does not
  enforce an episode limit itself; EPyMARL wraps it in `TimeLimit`, so the
  adapter must count steps and raise `truncated`.

## numpy Scalars Break json.dump Of The Spec

- Symptom: `TypeError: Object of type int64 is not JSON serializable` when
  writing `env_spec.json`.
- Cause: `get_env_info()` values derived from Gymnasium spaces are `np.int64`.
- Rule: coerce with `int()` in `extract_spec.py` before serializing.

## SMACv2 Is Legitimately Non-Reproducible Per Episode

- Symptom: `seed_determinism` fails; identical seeds diverge right after reset.
- Cause: by design, `StarCraftCapabilityEnvWrapper.reset()` re-draws team
  composition and start positions from capability distributions that accept no
  seed; start positions are realized inside the StarCraft II engine, so seeding
  Python-side RNGs is **measured to be insufficient**.
- Rule: declare `deterministic_under_seed: false` with the reason in the spec
  rather than faking reproducibility. Evaluate over many episodes.

## EPyMARL: MPE Keys Unregistered After PettingZoo 1.25

- Symptom: the documented `env_args.key="pz-mpe-simple-spread-v3"` fails with
  `gymnasium.error.NameNotFound`, often suggesting an unrelated `vmas-*` key.
- Cause: `src/envs/pz_wrapper.py` builds `pz-*` registrations by globbing the
  installed `pettingzoo` package and imports via
  `pettingzoo.{family}.{env}`. PettingZoo 1.25 moved MPE into the standalone
  `mpe2` package, so no MPE key is ever registered.
- Rule: register `pz-mpe-*` keys from `mpe2` separately and parameterize the
  wrapper's module prefix. Note `mpe2` keeps env modules flat at the package
  root (`mpe2.simple_spread_v3`), so there is no family subpackage segment.
  Worked patch: `third_party/epymarl-run/src/envs/pz_wrapper.py`; see
  `runs/20260726-marl5-setup/training_smoke_report.md`.

## EPyMARL: smaclite Is A Hard Import For Every Environment

- Symptom: `ModuleNotFoundError: No module named 'smaclite'` when launching a
  completely unrelated environment; later `OSError: Could not load
  libspatialindex_c library`.
- Cause: `src/envs/__init__.py` imports `smaclite_wrapper` at module scope, so
  smaclite is mandatory regardless of the environment used. smaclite pulls
  `rtree`, which needs the native `libspatialindex_c`.
- Rule: install smaclite even for non-SMAClite runs, and satisfy the native
  library with `conda install -c conda-forge libspatialindex` (no sudo).

## Multi-Agent: Forgetting To Drop Done Agents

- Symptom: episodes never end; `episode_terminates` verification fails after
  many turns even though individual agents report done.
- Cause: the adapter computes per-agent `terminated`/`truncated` but never
  removes done agents from `self.agents`, so the "all agents done" loop
  condition is never reached.
- Rule: after building the per-agent flag dicts, drop done agents from
  `self.agents` (and never re-add before `reset`). Restore `possible_agents`
  in `reset`. Caught by the ParallelEnv verifier's `episode_terminates` and
  `agent_set_monotonic_shrink` checks.

## Multi-Agent: Stale Agent Keys In Step Dicts

- Symptom: `step_dict_contract` fails; downstream MARL trainer raises KeyError
  or trains on ghost agents.
- Cause: returning reward/obs/flag dicts keyed by the wrong agent set (e.g.
  `possible_agents` instead of the agents that just stepped, or keeping a dead
  agent's key).
- Rule: every per-step dict is keyed by exactly the agents that acted this
  step. Decide obs-for-dead-agents policy explicitly and document it.

## Unseeded Randomness Sources

- Symptom: `seed_determinism` verification fails intermittently; experiments unreproducible.
- Cause: some randomness (native RNG, action-space sampling, simulator internals) not threaded to the seed.
- Rule: seed the env via `reset(seed=...)` AND `action_space.seed(...)` in any rollout used for determinism claims; document unseedable sources and set `deterministic_under_seed: false`.
