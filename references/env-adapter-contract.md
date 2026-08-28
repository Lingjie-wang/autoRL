# Environment Adapter Contract

Defines what "an RL environment is integrated" means in this workflow. The integration skill produces these deliverables; the verification skill checks them. Both must agree on this contract, so changes here require updating both skills.

## Adapter Standard

Every integrated environment must expose the Gymnasium API:

- `observation_space` and `action_space` declared as `gymnasium.spaces` objects
- `reset(seed=..., options=...) -> (observation, info)`
- `step(action) -> (observation, reward, terminated, truncated, info)`
- `close()`
- deterministic reproduction: same seed and same action sequence produce the same trajectory, or the adapter documents why not (e.g. external simulator with internal randomness)

Multi-agent environments follow the PettingZoo `ParallelEnv` or `AECEnv` convention instead. The `env_spec.json` must state which convention applies.

## Integration Routes By Source Type

Matches `environment_spec.type` in the task card:

- `official_benchmark`: environment already ships a Gymnasium-compatible interface. Adapter is thin or identity; integration work is registration, config, spec extraction, and verification.
- `custom_env`: user-provided environment code without standard interface. Adapter wraps it into the Gymnasium API and declares spaces explicitly.
- `external_simulator`: environment lives behind a process/network boundary. Adapter owns lifecycle (launch, connect, teardown) and must document failure modes and cleanup.

## Deliverables

An integration is complete when all of these exist:

```text
runs/<task-id>/artifacts/integration/
  adapter.py            # or package; identity shim allowed for official_benchmark
  env_config.json       # construction kwargs, ids, paths, version pins (JSON: stdlib-parseable, matches repo JSON artifacts)
  env_spec.json         # machine-readable spec, schema below
  extract_spec.py       # generates env_spec.json from the constructed env (spec must never be hand-written)
  smoke_rollout.py      # standalone script: construct, reset, N random steps
runs/<task-id>/integration_report.md
```

Plus, produced by the verification skill:

```text
runs/<task-id>/verification_report.json
```

## env_spec.json Schema

```json
{
  "env_id": "CartPole-v1",
  "source_type": "official_benchmark | custom_env | external_simulator",
  "api_convention": "gymnasium | pettingzoo_parallel | pettingzoo_aec",
  "observation_space": "repr of the space, with dtype and shape",
  "action_space": "repr of the space, with dtype and shape",
  "reward_range": [null, null],
  "episode_termination": "how episodes end, including truncation limit",
  "deterministic_under_seed": true,
  "dependencies": ["gymnasium>=0.29"],
  "notes": "known quirks, e.g. action masking, non-standard info keys"
}
```

Space fields must be extracted from the constructed environment, not hand-written from documentation.

### Single-Agent Descriptor Fields

A space `repr` alone does not tell a downstream consumer whether it is looking
at 17 float64 features or a 210x160x3 uint8 frame, nor what a real trainer will
actually receive. These fields are required for `api_convention: "gymnasium"`:

```json
{
  "observation_modality": "vector | image | dict | hybrid",
  "action_type": "discrete | continuous | multi_discrete | multi_binary",
  "goal_conditioned": false,
  "randomness_sources": ["initial state sampling", "sticky actions p=0.25"],
  "observed_reward_bounds": [-1.0, 1.0],
  "training_channel": "native | sb3_atari_wrapper | sb3_imgobs_wrapper | sb3_multiinput",
  "lossy_notes": ["what the training channel drops relative to the raw env"]
}
```

- `observation_modality`: `dict` when the observation space is a `Dict`;
  `hybrid` when a `Dict` mixes image and vector leaves.
- `randomness_sources`: every source that affects a trajectory, including ones
  that survive seeding (ALE sticky actions are stochastic per step but
  reproducible under a fixed seed — say so explicitly).
- `observed_reward_bounds`: measured min/max over the extraction rollout.
  `reward_range` left the core Gymnasium API in 1.x, so declared bounds are
  usually absent; observed bounds are what the `reward_bounds_observed` check
  compares against, and they are a floor on the true range, never a proof of it.
- `training_channel` / `lossy_notes`: the single-agent analogue of the EPyMARL
  channel-lossiness table below. Most trainers do not consume the raw env — SB3
  needs `AtariWrapper` for pixels (grayscale, resize, frame-stack, reward clip)
  and cannot consume MiniGrid's text `mission` at all. Record what the
  trainer sees and what was dropped to get there.

## Verification Tiers

Checks are gated by `execution_boundary`, following the pattern in `skills/rl-framework-implementer/references/smoke-tests.md`:

- `generate_only`: deliverable files exist, `env_spec.json` parses and has all required fields, config parses.
- `dry_run`: import adapter, construct env, verify declared spaces match `observation_space`/`action_space` at runtime, `reset` returns an observation contained in the declared space, take random steps and check every return value's type/shape/containment, verify episodes can terminate, verify seed determinism over two identical rollouts, verify `close()` is safe.
- `runtime_allowed`: random-policy rollout over multiple full episodes checking for NaN/Inf in observations and rewards, reward magnitudes within `observed_reward_bounds`, no resource leaks across repeated construct/close cycles.

Verification proves the environment behaves as declared. It makes no claims about trainability or performance.

### Episode-Length Bounds Must Be Explicit

`env.spec.max_episode_steps` is `None` for environments that truncate
internally (ALE via `max_num_frames_per_episode`, MiniGrid via
`env.unwrapped.max_steps`). Any check that loops until an episode ends must
carry its own hard step cap and record "hit the cap without ending" as a
distinct outcome — never fall back to an effectively unbounded loop. The spec's
`episode_termination` records both the mechanism and the effective step limit,
whichever attribute it came from.

## Multi-Agent Environments (PettingZoo)

Multi-agent environments target the PettingZoo API instead of Gymnasium. Two conventions:

- `pettingzoo_parallel` (ParallelEnv): all agents act simultaneously; `step` takes and returns dicts keyed by agent id.
- `pettingzoo_aec` (AECEnv): agents act in turns via `agent_iter()`.

Prefer ParallelEnv for simultaneous-move environments (SMAC-style team play). Record the convention in `env_spec.json`.

### ParallelEnv Adapter Surface

- `possible_agents`: the full agent id list that can ever appear.
- `agents`: the currently-active agent ids (shrinks as agents terminate).
- `observation_space(agent)` / `action_space(agent)`: per-agent spaces (may be heterogeneous).
- `reset(seed=..., options=...) -> (obs_dict, info_dict)`: dicts keyed by active agent id.
- `step(action_dict) -> (obs, reward, terminated, truncated, info)`: five dicts keyed by active agent id.
- an agent is removed from `agents` on the step after its `terminated`/`truncated` is True.
- action masks (when actions are conditionally legal, e.g. SMAC) live in `info[agent]["action_mask"]` or the observation dict; declare where in the spec.

### env_spec.json Additions For Multi-Agent

```json
{
  "api_convention": "pettingzoo_parallel",
  "possible_agents": ["agent_0", "agent_1"],
  "max_num_agents": 2,
  "observation_spaces": {"agent_0": "repr...", "agent_1": "repr..."},
  "action_spaces": {"agent_0": "repr...", "agent_1": "repr..."},
  "homogeneous_agents": true,
  "action_mask_location": "info[agent]['action_mask'] | observation | none",
  "agents_can_terminate_early": true
}
```

Per-agent space fields (`observation_spaces`/`action_spaces`) replace the single `observation_space`/`action_space` for multi-agent specs. Extract them from the constructed environment, never hand-write.

### Multi-Agent Verification Tiers

Extends the single-agent tiers:

- `generate_only`: spec has `possible_agents`, per-agent space maps, `api_convention` set to a pettingzoo variant.
- `dry_run`: `reset` returns dicts keyed exactly by active agents; each agent's obs is in its declared space; `step` accepts an action dict and returns five dicts with matching keys; per-agent reward finite; per-agent terminated/truncated bool; agent set is stable or shrinks monotonically (no resurrection mid-episode); when action masks are declared, a masked-out action is rejected or handled as documented; episode ends (all agents done); seed determinism over identical rollouts.
- `runtime_allowed`: multi-episode NaN sweep across all agents; agent set returns to `possible_agents` on reset; no leaks over repeated construct/close.

## EPyMARL MultiAgentEnv Convention

EPyMARL-family trainers (PyMARL/EPyMARL, the QMIX/VDN lineage) consume a **pull-style** interface rather than Gymnasium/PettingZoo push-style returns. Use `api_convention: "epymarl_multiagentenv"` when the adapter targets this surface directly (SMAC, SMACv2, SMAClite) or when documenting what a trainer will actually see through EPyMARL's own wrappers.

### Required Surface

```python
step(actions)            -> obss, reward, terminated, truncated, info   # EPyMARL; original PyMARL returned 3
reset(seed=None, options=None) -> obss, info
get_obs()                -> list of per-agent observations
get_obs_agent(i) / get_obs_size()
get_state() / get_state_size()          # centralized state for CTDE training
get_avail_actions() / get_avail_agent_actions(i)
get_total_actions()
close()
get_env_info()           -> {state_shape, obs_shape, n_actions, n_agents, episode_limit}
```

`get_env_info()` is the trainer's contract: it sizes networks and buffers before the first episode. Every shape it reports must match what the getters actually return.

### Additional env_spec.json Fields

These record what a training run will actually receive — not just what the environment nominally has. Verified against EPyMARL source (`src/envs/gymma.py`, `src/envs/smacv2_wrapper.py`).

```json
{
  "api_convention": "epymarl_multiagentenv",
  "env_info": {"state_shape": 120, "obs_shape": 82, "n_actions": 11, "n_agents": 5, "episode_limit": 200},
  "global_state": {
    "available": true,
    "source": "native | obs_concat | none",
    "shape": [120]
  },
  "reward_structure": {
    "kind": "team | per_agent",
    "epymarl_config": {"common_reward": true, "reward_scalarisation": "sum | mean"}
  },
  "action_mask": {
    "available": true,
    "source": "native | all_legal_padding | none"
  },
  "training_channel": "direct_wrapper | gymma | pz_wrapper_gymma | vmas_wrapper_gymma",
  "lossy_notes": ["what this channel silently drops"]
}
```

### Channel Lossiness Must Be Declared

EPyMARL offers several routes to `MultiAgentEnv`, and the generic ones degrade information **silently**:

| Channel | Global state | Action mask |
| --- | --- | --- |
| direct wrapper (SMAC, SMACv2, SMAClite) | native `get_state()` | native masks |
| `gymma` (generic Gym-style multi-agent) | `np.concatenate(obs)` — obs_concat | dropped; `get_avail_agent_actions` returns all-legal padding |
| `pz_wrapper` → `gymma` (PettingZoo) | obs_concat | dropped |
| `vmas_wrapper` → `gymma` (VMAS) | obs_concat | dropped |

Consequences the integrator must record, not discover later:

- An environment with meaningful action masks **must** use a direct wrapper; routing it through `gymma` discards legality and the agent will select illegal actions.
- CTDE algorithms (QMIX and relatives) consume `get_state()`. `obs_concat` is a substitute, not the real centralized state; results across native-state and concat-state environments are not directly comparable.
- `gymma`'s `get_state_size()` prefers an env-provided `state_size` attribute while `get_state()` still returns concatenated observations — declare the observed values for both, and flag any mismatch.

### Verification Tiers

- `generate_only`: spec contains `env_info`, `global_state`, `reward_structure`, `action_mask`, `training_channel`; all required getters exist on the adapter.
- `dry_run`: `get_env_info()` self-consistency (`len(get_state()) == state_shape`; `len(get_obs()) == n_agents` and each observation flattens to `obs_shape`; `len(get_avail_agent_actions(i)) == n_actions`); every agent has at least one legal action after reset; a full random-legal episode terminates within `episode_limit`; declared `global_state.source`/`action_mask.source` match observed behavior; seed determinism; `close()` safe.
- `runtime_allowed`: multi-episode NaN/Inf sweep over rewards and observations; repeated construct/close cycles (critical — each SMAC episode owns a StarCraft II process).

## Failure Reporting

A failed check must record: the check name, the expected contract clause, the observed value, and the smallest suggested fix. Partial verification is reported honestly with explicit gaps, never rounded up to "passed".
