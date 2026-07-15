# Environment Description Checklist

What a "description + environment code" request must tell the integrator.
Code shows structure; only the description carries semantics. Items marked
**blocking** stop the integration with a concrete question when missing from
both description and code.

## Checklist

1. **Observation semantics** (blocking): what each field/dimension means,
   expected ranges, units. Needed to declare `observation_space` honestly.
2. **Action semantics** (blocking): encoding (discrete meanings or continuous
   bounds), what an out-of-range action should do.
3. **Reward semantics** (blocking): what the scalar means, sign convention
   (reward vs cost), rough scale. A cost must be negated or documented — never
   silently passed through as reward.
4. **Episode termination** (blocking): every natural end condition, and which
   ends are "task outcome" (`terminated`) vs "cut off" (`truncated`); step
   limit if any.
5. **Randomness sources**: what is random, where each RNG lives (instance
   attribute, module-level `random`/`np.random`, external process), and
   whether it can be seeded. Missing answer here is not blocking, but the
   adapter must then discover it by code inspection and the spec must record
   the determinism conclusion.
6. **Lifecycle**: construction arguments and defaults; any external process,
   asset, or file the env needs at runtime.
7. **Dependencies**: libraries and versions the env code imports.

## Rules

- Derive first, ask second: read the code before asking any question the code
  already answers.
- Code wins over description on facts (shapes, dtypes, return arity); the
  description wins on intent (what the reward means). Record every
  discrepancy in `integration_report.md` gotchas.
- One batch of questions, not a drip: collect all missing blocking items and
  ask them together.
