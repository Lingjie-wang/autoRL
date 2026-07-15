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

## Unseeded Randomness Sources

- Symptom: `seed_determinism` verification fails intermittently; experiments unreproducible.
- Cause: some randomness (native RNG, action-space sampling, simulator internals) not threaded to the seed.
- Rule: seed the env via `reset(seed=...)` AND `action_space.seed(...)` in any rollout used for determinism claims; document unseedable sources and set `deterministic_under_seed: false`.
