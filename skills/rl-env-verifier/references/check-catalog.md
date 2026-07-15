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

## Adding A Check

New checks enter this catalog with: name, tier, the accident it catches, and the smallest_fix wording. Update `verify_env_template.py` in the same change — catalog and script must not drift apart.
