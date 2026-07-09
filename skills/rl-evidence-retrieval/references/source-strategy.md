# RL Evidence Source Strategy

Use this guide after loading `task_card.md` and before searching.

## Query Expansion

Build queries from task-card fields rather than generic RL keywords.

Environment axis:

- exact environment id or path
- framework family: Gymnasium, MuJoCo, Atari, Minigrid, PettingZoo, SMAC, MetaWorld, Isaac Gym, Brax, custom simulator name
- task aliases and benchmark suite aliases

Algorithm axis:

- explicit algorithm names from the task card
- family terms: on-policy, off-policy, actor-critic, value-based, offline RL, imitation learning, model-based RL, multi-agent RL, safe RL, exploration
- canonical baseline names when the user permits evidence-backed selection

Evaluation axis:

- primary metric and success criterion
- sample efficiency, success rate, return, regret, safety violation, wall-clock, robustness, transfer, generalization

Code axis:

- `GitHub`, `implementation`, `official code`, `baseline`, `example`, `Papers with Code`
- likely libraries: Stable-Baselines3, CleanRL, RLlib, Tianshou, TorchRL, Acme, JAX/Brax, MARLlib, PyMARL, EPyMARL

## Source Priority

Use available sources in this order, degrading gracefully when a source is unavailable:

1. Local project knowledge: task card, existing repos, `papers/`, `literature/`, notes, README files.
2. Paper databases: arXiv for preprints; Semantic Scholar/OpenAlex/Crossref-style metadata for exact titles, venues, DOI, citation metadata.
3. Paper-to-code sources: Papers with Code, author project pages, supplementary material.
4. Code hosts: GitHub/GitLab/Hugging Face Spaces or model repositories, official benchmark repos, library examples.
5. Broad web search for docs, issue threads, release notes, and environment-specific setup warnings.

## Recommended Search Batches

For application/new-environment tasks:

- `<environment> <algorithm family> reinforcement learning baseline`
- `<environment> RL GitHub implementation`
- `<environment> <metric> reinforcement learning paper`
- `<benchmark suite> examples <library name>`

For research-quality-improvement tasks:

- `<algorithm family> <environment family> state of the art reinforcement learning`
- `<metric> <environment> reinforcement learning sample efficiency`
- `<paper or method> ablation baseline reproduction`
- `<method> official implementation GitHub`

For custom environments:

- search by simulator/domain plus observation/action/reward style
- prefer algorithm-family evidence over exact environment matches
- look for wrapper examples and environment-interface risks

## Verification Discipline

- Verify exact title, authors, year, venue, DOI/arXiv id, and URL for recommended papers when possible.
- Verify code repository URL, license, last visible activity, installation surface, and whether the README/examples mention the relevant environment or algorithm.
- Mark uncertain fields as `unknown` or `[UNVERIFIED]`.
- Keep failed or weak searches in the report's `Gaps` section when they affect downstream decisions.

## Retrieval Boundary

Allowed:

- web/search queries
- metadata/API lookups
- read-only repository metadata and README inspection
- local file reads

Requires explicit approval:

- `git clone`
- dependency installation
- downloading large datasets or paper corpora
- running training/evaluation
- copying third-party source into project-owned code
