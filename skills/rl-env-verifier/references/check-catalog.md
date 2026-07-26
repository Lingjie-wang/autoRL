# Verification Check Catalog

Each check names the accident it catches. Tiers are cumulative.

## generate_only Tier

| Check | Catches |
| --- | --- |
| deliverables_exist | integration handed off with missing files |
| spec_parses / spec_required_fields | malformed or incomplete spec that downstream tooling would choke on |
| config_parses | unparseable construction config |

## dry_run Tier

| Check | Catches |
| --- | --- |
| adapter_imports | broken imports, missing dependencies in the isolated env |
| env_constructs | construction path broken despite files existing |
| observation_space_matches_declared | spec drift: adapter changed after spec extraction |
| action_space_matches_declared | same, on the action side |
| reset_contract | reset not returning (obs-in-space, info dict) |
| step_contract | wrong tuple arity (legacy Gym), obs escaping declared space, NaN/non-finite rewards, non-bool flags |
| episode_terminates | episodes that never end (missing terminated/truncated wiring) |
| seed_determinism | unseeded randomness sources — silent unreproducibility |
| close_safe | unsafe close/double-close; early warning for resource leaks |

Seed determinism method: two rollouts with identical seed and identically-seeded action sampling must produce byte-identical trajectories (observations, rewards, flags). Skip with a recorded reason when the spec declares `deterministic_under_seed: false`.

## runtime_allowed Tier

| Check | Catches |
| --- | --- |
| multi_episode_nan_sweep | NaN/Inf appearing only after many episodes or rare states |
| reward_bounds_observed | rewards outside declared/expected range at scale |
| construct_close_leak_cycle | resource leaks that surface at episode 50, not episode 1 (critical for external_simulator) |

## Extensions By Route

- `external_simulator`: add process-reaped-after-close, reconnect-after-crash behavior, startup timeout.
- `pettingzoo_parallel` / `pettingzoo_aec`: per-agent space containment, agent set stability across steps, action-mask validity (masked actions must be rejected or ignored as documented).

## Multi-Agent (pettingzoo_parallel) Tier

Run by `verify_parallel_env_template.py`; dispatched when `api_convention == "pettingzoo_parallel"`. Cumulative on top of generate_only.

| Check | Catches |
| --- | --- |
| possible_agents_match | declared agent id list drifted from the adapter |
| per_agent_spaces_match_declared | spec drift on any single agent's obs/action space |
| reset_dict_contract | reset not returning a dict keyed by active agents, or obs out of space |
| step_dict_contract | step dicts keyed wrong; obs/reward/flag violations for any agent |
| agent_set_monotonic_shrink | a dead agent "resurrecting" mid-episode (state-tracking bug) |
| episode_terminates | forgetting to drop done agents → episode never ends |
| action_masks_present | masks not surfaced at the declared location |
| reset_restores_agents | reset not restoring the full possible_agents set (episode 2 starts short-handed) |
| seed_determinism | unseeded native RNG — multi-agent trajectories unreproducible |

Proven on run 20260715-coin-arena-integration (2-agent grid, agents die on traps, per-agent masks): 14/14, and the termination check was self-tested by deleting the "drop done agents" line.

## EPyMARL (epymarl_multiagentenv) Tier

Run by `verify_epymarl_env_template.py`; dispatched when `api_convention == "epymarl_multiagentenv"`. Cumulative on top of generate_only.

| Check | Catches |
| --- | --- |
| env_info_fields | spec missing any of the 5 keys the trainer sizes networks from |
| multiagentenv_surface | a required pull-style getter missing or not callable |
| env_info_matches_declared | spec drift: adapter changed after spec extraction |
| obs_matches_env_info | `get_obs()` count/size disagreeing with advertised `n_agents`/`obs_shape` |
| state_matches_env_info | `get_state()` length disagreeing with advertised `state_shape` — silently corrupts the mixer network |
| avail_actions_matches_env_info | mask list length disagreeing with `n_actions` |
| every_agent_has_legal_action | a fully-masked agent, which deadlocks the runner |
| action_mask_source_honest | spec claiming native masks when the channel actually delivers all-legal padding |
| global_state_source_honest | spec claiming native centralized state when `get_state()` is byte-identical to concatenated observations |
| state_size_getter_agrees | `get_state_size()` disagreeing with actual `get_state()` length (gymma prefers `env.state_size` while still returning concatenated obs) |
| step_returns_finite_reward | NaN/Inf rewards; unknown step tuple arity (PyMARL 3-tuple vs EPyMARL 5-tuple) |
| episode_terminates_within_limit | missing terminated/truncated wiring, or a wrong declared `episode_limit` |
| seed_determinism | unseeded randomness; skipped-with-reason when the environment is legitimately non-reproducible (SMACv2) |
| close_safe | unreaped simulator child processes; unsafe double close |

The two `*_source_honest` checks are the reason this tier exists: EPyMARL's generic wrappers degrade masks and centralized state **silently**, so a spec that overclaims must be caught mechanically.

Proven on 4 runs (2026-07-26): `marl5-smacv1` 18/18, `marl5-smacv2` 17 passed + 1 honest skip, `marl5-mpe` 18/18, `marl5-vmas` 18/18. Self-tested by falsely declaring native masks + native state on MPE — both honesty checks failed as designed.

## Adding A Check

New checks enter this catalog with: name, tier, the accident it catches, and the smallest_fix wording. Update the matching verifier script (`verify_env_template.py` for single-agent, `verify_parallel_env_template.py` for multi-agent) in the same change — catalog and scripts must not drift apart.
