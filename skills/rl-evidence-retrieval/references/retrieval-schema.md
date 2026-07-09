# RL Evidence Retrieval Schema

Use this schema when judging whether the evidence package is ready for strategy decision.

## Retrieval Status

Set one:

- `complete`: all high-priority axes were searched and at least one paper and one codebase candidate are usable or gaps are well justified.
- `partial`: some useful evidence exists, but a source, exact environment match, or code verification is missing.
- `blocked`: task card is not ready, network/search tools are unavailable, or required approval is missing.

## Paper Candidate Fields

Each paper candidate should capture:

| Field | Meaning |
| --- | --- |
| `paper_id` | Stable local id such as `P01`. |
| `title` | Exact title, or `[UNVERIFIED]` prefix if not confirmed. |
| `authors_year` | Compact author/year string. |
| `venue` | Venue or preprint source. |
| `url` | DOI, arXiv, publisher, or project page. |
| `algorithm` | Algorithm or method family. |
| `environment_match` | `exact`, `same_family`, `adjacent`, or `none`. |
| `metric_match` | `exact`, `compatible`, `weak`, or `unknown`. |
| `key_result` | One concise claim relevant to the task. |
| `code_url` | Repository/project link or `none_found`. |
| `verification` | `verified`, `partially_verified`, or `unverified`. |
| `relevance` | `high`, `medium`, or `low` for this task card. |
| `limitations` | Why it may not transfer or may be risky. |

## Codebase Candidate Fields

Each codebase candidate should capture:

| Field | Meaning |
| --- | --- |
| `repo_id` | Stable local id such as `C01`. |
| `name` | Repository or package name. |
| `url` | Source URL. |
| `source_role` | `official_paper_code`, `library_example`, `benchmark_baseline`, `third_party_reimplementation`, or `unknown`. |
| `algorithm_support` | Exact or likely algorithm support. |
| `environment_support` | Exact or likely environment support. |
| `license` | License if found, otherwise `unknown`. |
| `activity` | Recent visible maintenance status if available. |
| `install_risk` | `low`, `medium`, `high`, or `unknown`. |
| `reuse_plan` | Inspect only, adapt config, call as dependency, or not recommended. |
| `verification` | What was checked: README, examples, metadata, docs, issues, none. |
| `limitations` | Dependency, license, stale code, API mismatch, hardware, or benchmark mismatch risks. |

## Coverage Scoring

Use these labels instead of numeric overprecision:

| Dimension | Sufficient | Partial | Insufficient |
| --- | --- | --- | --- |
| Environment | Exact benchmark/env evidence exists. | Same family or wrapper evidence exists. | Only generic RL evidence exists. |
| Algorithm | Required family or accepted baseline is covered. | Adjacent family evidence exists. | No algorithm-relevant evidence. |
| Metric | Evaluation metric or close proxy appears. | Compatible but not identical metric. | No comparable metric. |
| Code | Reusable repo/library path identified. | Candidate exists but license/install/env support is unclear. | No credible code candidate. |
| Reproducibility | Setup and evaluation risks are known. | Some risks inspected. | Risks mostly unknown. |

Overall coverage:

- `sufficient`: no dimension is insufficient and code coverage is sufficient or partial with clear next inspection.
- `partial`: at least one dimension is insufficient, but recommendations can still guide the next stage.
- `insufficient`: environment or algorithm evidence is missing enough that strategy decision would be guesswork.

## Recommendation Rules

- Recommend at most 3 papers and 3 codebases.
- A high-citation paper is not automatically recommended unless it matches the task.
- A popular repo is not automatically recommended unless it matches environment, algorithm, and dependency boundary.
- If the best codebase is risky, recommend it as `inspect_first`, not `reuse`.
- If no code is credible, recommend implementing from a maintained library or writing a minimal baseline only after strategy decision.
