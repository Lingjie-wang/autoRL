# Single-Agent Environment Catalog

Verified integrations of single-agent environments behind the Gymnasium adapter
contract. Every row was measured on this machine (2026-07-26), not copied from
docs.

Runtime: conda env `sa5`, Python 3.11.15, gymnasium 1.3.0, numpy 2.4.6,
torch 2.13.0, stable-baselines3 2.9.0. No sudo, no system packages.

## Status

| Env | Modality | Action | Verification | Training smoke |
| --- | --- | --- | --- | --- |
| `LunarLander-v3` | vector | discrete | 15/15 | PPO COMPLETED |
| `HalfCheetah-v5` | vector | continuous | 15/15 | SAC COMPLETED |
| `ALE/Pong-v5` | image | discrete | 15/15 | PPO COMPLETED |
| `MiniGrid-DoorKey-5x5-v0` | dict (image+int+**text**) | discrete | 15/15 | PPO COMPLETED |
| `FetchReach-v4` | dict (**goal-conditioned**) | continuous | 15/15 | SAC COMPLETED |

All five verified at the `runtime_allowed` tier (the highest), which adds
multi-episode NaN sweeps, reward-bound checks, and 10× construct/close cycles on
top of the `dry_run` behavioral checks.

## Shapes And Episode Structure

| Env | Observation | Action | Episode ends | Step limit | Limit source |
| --- | --- | --- | --- | --- | --- |
| LunarLander-v3 | `Box(8,) float32` | `Discrete(4)` | terminated **and** truncated both reachable | 1000 | `spec.max_episode_steps` |
| HalfCheetah-v5 | `Box(17,) float64` | `Box(-1,1,(6,)) float32` | **truncation only** | 1000 | `spec.max_episode_steps` |
| ALE/Pong-v5 | `Box(0,255,(210,160,3)) uint8` | `Discrete(6)` | terminated (game to 21) | **27000** | ALE frames 108000 / frameskip 4 |
| MiniGrid-DoorKey-5x5-v0 | `Dict{image (7,7,3) uint8, direction Discrete(4), mission MissionSpace}` | `Discrete(7)` | terminated on goal, else truncated | **250** | `env.unwrapped.max_steps` |
| FetchReach-v4 | `Dict{observation (10,), achieved_goal (3,), desired_goal (3,)}` float64 | `Box(-1,1,(4,)) float32` | **truncation only** | 50 | `spec.max_episode_steps` |

Two of five report `spec.max_episode_steps = None` and truncate internally. Any
loop waiting for an episode to end needs its own cap.

## What A Trainer Actually Receives

Only 3 of 5 reach the trainer unmodified. This is the single-agent analogue of
the EPyMARL channel-lossiness table in `marl-environment-catalog.md`.

| Env | Channel | Trainer sees | Dropped / changed |
| --- | --- | --- | --- |
| LunarLander-v3 | `native` | `Box(8,) float32` | — |
| HalfCheetah-v5 | `native` | `Box(17,) float64` | — |
| ALE/Pong-v5 | `sb3_atari_wrapper` | `Box(0,255,(84,84,4)) uint8` | RGB→grayscale, 210×160→84×84, 4-frame stack, **rewards clipped to {−1,0,+1}** |
| MiniGrid-DoorKey-5x5-v0 | `sb3_flatobs_wrapper` | `Box(0,255,(2835,)) uint8` | image flattened (147) + mission one-hot **character**-encoded (2688); **`direction` dropped** |
| FetchReach-v4 | `sb3_multiinput` | the `Dict`, unchanged | no shape loss, but plain SAC treats `desired_goal` as an ordinary feature — goal structure unused without HER |

Pong's reward clipping is the one to remember when reading logs: a logged reward
is not the game score.

## Reward Types Are Not Uniform

`int` (MiniGrid), `np.float32` (FetchReach), `np.float64` (HalfCheetah) all
appear. `isinstance(r, (int, float))` accepts `np.float64` by accident and
**rejects `np.float32`**; the verifier uses `numbers.Real`.

## Reproducibility

All five are deterministic under seed, including Pong — its sticky actions
(`repeat_action_probability=0.25`) are stochastic per step but reproduce exactly
under a fixed seed. That is recorded in each spec's `randomness_sources` so it
is not mistaken for nondeterminism.

## Verifier Defects This Set Exposed

The environments were the easy part. Four real defects in
`skills/rl-env-verifier/references/verify_env_template.py` surfaced only because
these five span modalities the earlier CartPole-only run never touched:

1. **`repr()`-based determinism hashing could false-pass.** `Dict` observations
   have no `.tobytes()` and fell back to `repr()`, which numpy abbreviates for
   large arrays — two divergent trajectories could share a signature. Proven with
   two 2000-element arrays differing at index 900 and identical reprs. Fixed with
   a recursive `canonical_bytes()`.
2. **`MissionSpace` repr embeds a memory address**, so declared-vs-runtime space
   comparison could never pass for any space holding a callable. Fixed by
   normalizing ` at 0x…`.
3. **`np.float32` rewards were rejected** by `isinstance(r, (int, float))`.
   Widened to `numbers.Real`.
4. **`runtime_allowed` tier was documented but unimplemented** — the script only
   accepted `generate_only|dry_run`. Now implemented, and all five run at it.

Plus a design correction: `reward_bounds_observed` initially failed healthy
environments because extraction and verification sample different action streams.
The check now catches specs claiming bounds *wider* than measured (invented
numbers) rather than penalising the verifier for finding more.

## Earlier Single-Agent Runs Brought Up To The Extended Contract

Adding the required descriptor fields turned three previously-green runs red,
because their specs predated the fields. Rather than leave them failing, their
`extract_spec.py` scripts were extended and the specs regenerated — never
hand-edited. All three now also verify at `runtime_allowed`, a higher tier than
they originally ran at:

| Run | Was | Now |
| --- | --- | --- |
| `runs/20260715-cartpole-integration` | `dry_run`, 12 checks | `runtime_allowed`, 15/15 |
| `runs/20260715-gridworld-integration` | `dry_run`, 12 checks | `runtime_allowed`, 15/15 |
| `runs/20260715-thermal-chamber-integration` | `dry_run`, 12 checks | `runtime_allowed`, 15/15 |

The thermal-chamber spec gained a genuine `lossy_notes` entry in the process: the
adapter negates the native cost to produce reward (raw cost preserved in
`info['cost']`), so a consumer reading reward alone sees a sign-flipped
objective. Nothing is lost, but it is now declared.

The `pettingzoo_parallel` and `epymarl_multiagentenv` runs use different verifier
templates and were unaffected; a full sweep across all 13 integrations in the repo
passes.

Self-tested destructively — falsified obs shape, invented reward bounds, and a
dropped descriptor field each produce the matching failed check and exit 1.

## Artifacts

```
runs/20260726-sa5-setup/dependency_plan.md          # exact install commands + versions
runs/20260726-sa5-setup/train_smoke.py              # SB3 end-to-end smoke
runs/20260726-sa5-setup/training_smoke_report.md    # results + the MiniGrid CnnPolicy failure
runs/20260726-sa5-setup/training_smoke_results.json
runs/20260726-sa5-lunarlander/                      # adapter, spec, smoke, reports
runs/20260726-sa5-halfcheetah/
runs/20260726-sa5-pong/
runs/20260726-sa5-minigrid/
runs/20260726-sa5-fetchreach/
```

## Reproduce

```bash
conda activate sa5

# verify one environment at the highest tier
python skills/rl-env-verifier/references/verify_env_template.py \
    --run-dir runs/20260726-sa5-minigrid --boundary runtime_allowed

# training smoke over all five
cd runs/20260726-sa5-setup && python train_smoke.py

# guided walkthrough of all five
bash demo_sa_envs.sh
```

## Not Claimed

Verification proves the environments behave as declared (spaces, episode
termination, reward finiteness, reproducibility, cleanup) and that a real trainer
can consume them. It does **not** claim any algorithm learns well on them: every
report carries `performance_claims: none`, and the training smoke runs
2000–4096 timesteps on purpose. Sparse-reward DoorKey in particular needs orders
of magnitude more than a smoke budget.
