# MARL Environment Catalog

Verified integrations of multi-agent environments for the EPyMARL family.
Every row was measured on this machine (2026-07-26), not copied from docs.

Runtime: conda env `marl5`, Python 3.11.15, numpy 1.26.4, gymnasium 1.3.0.
Reference framework: `~/code/epymarl` (read-only; has uncommitted work).
StarCraft II 4.7G at `~/code/epymarl/3rdparty/StarCraftII`.

## Status

| Env | Scenario | Channel | Global state | Action mask | Seed-reproducible | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| SMAC v1 | `3m` | direct_wrapper | **native** [48] | **native** | yes | 18/18 |
| SMACv2 | `terran_5_vs_5` | direct_wrapper | **native** [120] | **native** | **no** (by design) | 17 + 1 honest skip |
| MPE | `simple_spread_v3` | pz_wrapper_gymma | obs_concat [54] | none | yes | 18/18 |
| VMAS | `balance` | vmas_wrapper_gymma | obs_concat [48] | none | yes | 18/18 |
| GRF | — | **no EPyMARL wrapper exists** | — | — | — | deferred |

## Shapes

| Env | n_agents | obs_shape | state_shape | n_actions | episode_limit |
| --- | --- | --- | --- | --- | --- |
| SMAC v1 `3m` | 3 | 30 | 48 | 9 | 60 |
| SMACv2 `terran_5_vs_5` | 5 | 82 | 120 | 11 | 200 |
| MPE `simple_spread_v3` | 3 | 18 | 54 | 5 | 25 |
| VMAS `balance` | 3 | 16 | 48 | 9 | 150 |

## Launch Commands (EPyMARL)

```bash
# SMAC v1
python src/main.py --config=qmix --env-config=sc2 with env_args.map_name=3m
# SMACv2
python src/main.py --config=qmix --env-config=sc2v2 with env_args.map_name=terran_5_vs_5
# MPE
python src/main.py --config=qmix --env-config=gymma with env_args.time_limit=25 env_args.key="pz-mpe-simple-spread-v3"
# VMAS
python src/main.py --config=qmix --env-config=gymma with env_args.time_limit=150 env_args.key="vmas-balance"
```

## Reading The Fidelity Columns

**Channel lossiness is the point of this table.** EPyMARL's generic `gymma` route
silently degrades two things that CTDE algorithms depend on:

- **global state**: `gymma.get_state()` returns `np.concatenate(obs)`. For MPE and
  VMAS there is no true centralized state — QMIX's mixer consumes a
  concatenated-observation substitute. Results from these environments are **not
  directly comparable** with SMAC/SMACv2 runs that provide native state.
- **action mask**: `gymma.get_avail_agent_actions()` returns all-legal padding
  with no path to real legality. An environment whose action legality matters
  **must** use a direct wrapper.

These properties are detected by each run's `extract_spec.py` (state compared
byte-wise against concatenated observations; masks checked for any masked-out
action) and enforced by the `*_source_honest` checks in
`skills/rl-env-verifier/references/verify_epymarl_env_template.py`.

## Artifacts

```
runs/20260726-marl5-setup/dependency_plan.md      # exact install commands + versions
runs/20260726-marl5-smacv1/                       # adapter, spec, smoke, reports
runs/20260726-marl5-smacv2/
runs/20260726-marl5-mpe/
runs/20260726-marl5-vmas/
references/grf-feasibility.md                     # why GRF is deferred
```

## Not Claimed

Verification proves the environments behave as declared (shapes, masks, episode
termination, reproducibility, cleanup). It does **not** claim any algorithm
trains well on them; every report carries `performance_claims: none`.
