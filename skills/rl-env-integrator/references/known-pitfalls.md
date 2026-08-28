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

## `spec.max_episode_steps` Is `None` For Internally-Truncating Envs

- Symptom: a verification loop waiting for an episode to end runs far longer
  than expected, or appears to hang.
- Cause: `env.spec.max_episode_steps` is `None` whenever truncation is internal
  rather than applied by a `TimeLimit` wrapper. `ALE/Pong-v5` truncates via
  `max_num_frames_per_episode=108000` with `frameskip=4` (27000 agent steps);
  `MiniGrid-DoorKey-5x5-v0` truncates via `env.unwrapped.max_steps=250`.
- Rule: never derive a loop bound from `max_episode_steps` alone. Carry an
  explicit cap (the verifier uses `STEP_CAP = 30000`) and record "hit the cap
  without ending" as a distinct outcome. Record the real limit and where it came
  from in the spec's `episode_termination`.

## Reward Types Are Not Uniform Across Environments

- Symptom: `step_contract` rejects a perfectly valid reward.
- Cause: `isinstance(r, (int, float))` looks exhaustive but is not.
  `np.float64` subclasses Python `float`, so it passes by accident —
  **`np.float32` does not** (FetchReach-v4 returns `np.float32`). MiniGrid
  returns a plain Python `int`. All three appear within one 5-environment set.
- Rule: type-check rewards with `numbers.Real`, and convert with `float(r)`
  before arithmetic or finiteness checks.

## Space `repr` Can Contain A Memory Address

- Symptom: `observation_space_matches_declared` fails with expected and observed
  that look identical to the eye.
- Cause: a space holding a callable renders its address.
  MiniGrid's `MissionSpace` reprs as
  `MissionSpace(<function DoorKeyEnv._gen_mission at 0x7f74a3774e00>, None)`;
  the address changes every process, so a spec extracted in one process can
  never repr-match a later verification run.
- Rule: normalize ` at 0x…` out of space reprs before comparing. Structure is
  still compared; only the guaranteed-to-differ part is dropped.

## `repr()` Is Not A Safe Observation Fingerprint

- Symptom: `seed_determinism` passes even when trajectories genuinely diverge.
- Cause: numpy **abbreviates** large arrays in `repr` (`[0 1 2 ... 9]`), so two
  different arrays can share one. Any fingerprint that falls back to `repr()`
  for observations without `.tobytes()` — i.e. every `Dict` observation — is
  vacuous. Demonstrated: two 2000-element arrays differing at index 900 have
  identical `repr()`.
- Rule: hash observations with a recursive canonical encoder — key-sorted dicts,
  `tobytes()` plus shape and dtype for arrays, `repr` only for scalars and
  strings. See `canonical_bytes()` in `verify_env_template.py`.

## `observed_reward_bounds` Is A Floor, Not A Range

- Symptom: `reward_bounds_observed` fails on a healthy environment because the
  verifier saw rewards outside the extracted bounds.
- Cause: extraction and verification sample **different action streams**, so the
  verifier legitimately discovers values extraction never hit. MiniGrid's goal
  reward only appears in a stream that actually reaches the goal — extraction
  measured `[0.0, 0.0]` over 10 episodes while the verifier saw `0.388`.
- Rule: treat `observed_reward_bounds` as a measured floor. The check should
  catch a spec claiming bounds **wider** than anything measured (invented
  numbers) and violations of a non-null hard `reward_range` — not the verifier
  finding more of a genuinely wider range.

## SB3's Default `CnnPolicy` Cannot Take Small Images

- Symptom: `RuntimeError: Calculated padded input size per channel: (7 x 7).
  Kernel size: (8 x 8). Kernel size can't be greater than actual input size`.
- Cause: SB3's `CnnPolicy` builds `NatureCNN`, whose first convolution is 8×8
  stride 4 — sized for 84×84 Atari frames. MiniGrid's egocentric view is 7×7,
  smaller than the kernel.
- Rule: for small-image environments use a flattening wrapper plus `MlpPolicy`,
  or pass a custom small-kernel extractor via `policy_kwargs`. Record which
  channel was used in the spec's `training_channel`.

## Wrapper Behavior Must Be Read From Source, Not Assumed

- Symptom: `lossy_notes` describes a loss the wrapper does not actually cause.
- Cause: wrapper names suggest their behavior and mislead. `FlatObsWrapper` in
  minigrid 3.1.0 does **not** drop the mission string — it one-hot
  **character**-encodes it and concatenates (2835 dims total) — and drops
  `direction` instead. `ImgObsWrapper` is the one that drops both.
- Rule: read the wrapper's `observation()` before writing `lossy_notes`. Same
  rule as spec extraction: docs and names lose to source.

## Registration Is Required Before `gym.make` For Several Farama Packages

- Symptom: `gymnasium.error.NameNotFound` for a package that is definitely
  installed.
- Cause: `ale-py`, `minigrid`, and `gymnasium-robotics` register their ids only
  when `gymnasium.register_envs(<pkg>)` is called.
- Rule: call it **lazily inside the adapter**, not at module import. Lazy
  registration keeps several adapters importable in one process (the same
  discipline SMAC/SMACv2 need for `DuplicateMapError`).

## ale-py Bundles ROMs Since 0.9

- Symptom: following older tutorials leads to an `AutoROM` install step,
  license prompts, or ROM-download failures.
- Rule: `ale-py >= 0.9` ships the ROMs. Depend on `ale-py` alone; no `AutoROM`,
  no download step, no license interaction.
