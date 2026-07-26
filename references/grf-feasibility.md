# GRF (Google Research Football) Integration Feasibility

Status: **deferred by decision**, not attempted. This note records what an
integration would require, so the work can be scoped rather than rediscovered.

## Why It Is Harder Than The Other Four

1. **EPyMARL has no GRF wrapper.** Verified by grep over the cloned repo
   (`third_party/epymarl`, commit `cbc38c0`): zero matches for `gfootball` or
   `football` in any `.py`, `.yaml`, or requirements file. The other four
   environments all have either a direct wrapper or a `gymma`-compatible route
   already written. GRF needs one authored from scratch.

2. **Native compilation with system-level dependencies.** `gfootball` (latest on
   PyPI: 2.10.2) builds a C++ game engine at install time. It needs system
   packages installed with **sudo apt**, typically:
   `build-essential cmake libgl1-mesa-dev libsdl2-dev libsdl2-image-dev
   libsdl2-ttf-dev libsdl2-gfx-dev libboost-all-dev libdirectfb-dev
   libst-dev mesa-utils libsdl-sge-dev python3-pip`.
   The other four required no sudo at all.

3. **Compatibility risk.** GRF's last release predates the Gymnasium migration;
   it targets the old OpenAI Gym API. Expect to write the Gym→Gymnasium
   conversion (5-tuple step, `reset(seed=...)`) in addition to the multi-agent
   conversion.

## What An Integration Would Involve

1. **Dependency plan + approval** for the apt packages (sudo) and `gfootball`.
2. **Adapter** targeting `api_convention: "epymarl_multiagentenv"`:
   - GRF's multi-agent mode exposes per-agent observations via
     `number_of_left_players_agent_controls`; map those to `get_obs()`.
   - Decide and document the reward: GRF offers `scoring` and
     `scoring,checkpoints`. Per-agent vs team must be declared in
     `reward_structure`.
   - No native action mask (all 19/21 actions always available) → declare
     `action_mask: {available: false, source: "none"}`.
   - No native centralized state → either use `obs_concat` (matching what a
     `gymma`-style route would produce) or derive a state from the raw
     representation and declare `source: "native"` with justification.
   - Episode limit from the scenario config; GRF episodes end on goal/out-of-time
     depending on scenario.
3. **Verification** with the existing
   `skills/rl-env-verifier/references/verify_epymarl_env_template.py` — no new
   verifier needed, the epymarl tier already covers this convention.
4. **EPyMARL registration** — since no wrapper exists upstream, either register
   the adapter as a Gym env consumable by `gymma`, or add a dedicated wrapper
   entry. Note that adding it inside `~/code/epymarl` conflicts with the rule of
   not modifying that checkout; prefer registering from our own package.

## Rough Scope

Roughly comparable to the other four combined: the apt/compile step is the main
unknown (build failures on Debian 13 with modern toolchains are common for this
package), and the wrapper is greenfield rather than a thin shim.

## Recommendation

Treat as its own task with its own dependency approval. Before starting, confirm
with the supervisor whether GRF is actually needed for the research target — the
four verified environments already cover the SMAC-family and the
particle/vectorized families that EPyMARL benchmarks use.
