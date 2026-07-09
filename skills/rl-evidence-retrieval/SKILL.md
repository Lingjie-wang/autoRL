---
name: rl-evidence-retrieval
description: Retrieve and synthesize reinforcement-learning paper and codebase evidence for an AutoRL task card. Use after RL task clarification when Codex or Claude Code needs relevant algorithms, benchmarks, prior results, reusable repositories, implementation risks, or evidence-backed next-step recommendations before planning or coding.
---

# RL Evidence Retrieval

## Purpose

Turn an execution-ready AutoRL `task_card.md` into a compact evidence package covering related papers, algorithms, benchmarks, and reusable codebases. The output should help the next stage choose a strategy without inventing claims or cloning/installing unapproved third-party code.

This skill owns evidence retrieval and synthesis only. It must not choose the final strategy, write training code, run experiments, clone repositories, or install dependencies unless the task card explicitly allows that action and the user has approved it.

## Inputs

Preferred input:

```text
runs/<task-id>/task_card.md
```

The task card should come from `rl-task-clarifier` or contain equivalent fields:

- task mode
- environment type, id/path, and concrete RL task
- algorithm direction or evidence-backed selection permission
- objective and success criteria
- runtime and dependency boundary

If the task card is missing, blocked, or ambiguous about environment/task/algorithm direction, stop and ask for clarification instead of retrieving broad generic papers.

## Workflow

### 1. Load The Task Card

Read the full `task_card.md`. Extract:

- environment names, aliases, and benchmark family
- RL setting: online, offline, imitation, model-based, multi-agent, safe RL, exploration, or other
- requested or forbidden algorithm families
- metrics and success thresholds
- runtime and dependency restrictions
- task mode: research-quality improvement vs application/new-environment execution

### 2. Build A Search Plan

Read [source-strategy.md](references/source-strategy.md) before searching.

Create queries from four axes:

- environment or benchmark names
- RL task behavior and metric
- algorithm family or selection policy
- code availability terms such as `GitHub`, `baseline`, `implementation`, `papers with code`, or library names

Prefer targeted multi-query retrieval over one broad query.

### 3. Retrieve Papers

Search enough sources to cover both recency and reliability:

- arXiv or paper-index search for recent preprints
- Semantic Scholar/OpenAlex/Crossref-style metadata when available for venue, DOI, citations, and exact title verification
- Papers with Code, project pages, or official paper repositories for implementation links
- local `papers/`, `literature/`, or existing project notes if present

For every paper candidate, verify exact title, venue/year, and URL when possible. If a claim cannot be verified, keep it only when useful and mark it `[UNVERIFIED]`.

### 4. Retrieve Codebase Candidates

Search for reusable repositories that match the task card. Prefer:

- official author repositories for selected papers
- maintained RL libraries with examples matching the environment class
- benchmark-specific baselines
- minimal reference implementations for smoke tests

Do not clone, install, or copy code in this stage. Inspect only metadata, README/docs, file lists, and license information that are safely available through search or read-only fetch tools.

### 5. Score Coverage And Risks

Read [retrieval-schema.md](references/retrieval-schema.md) before scoring.

Assess coverage along these dimensions:

- environment match
- algorithm match
- metric/evaluation match
- implementation availability
- reproducibility risk
- license and dependency risk

Mark gaps explicitly. Lack of evidence is a result, not a reason to hallucinate.

### 6. Emit The Evidence Package

Read [report-template.md](references/report-template.md) before writing output.

Write the canonical LLM-facing report as Markdown:

```text
runs/<task-id>/evidence_report.md
```

Optional structured sidecars:

```text
runs/<task-id>/paper_candidates.jsonl
runs/<task-id>/codebase_candidates.jsonl
runs/<task-id>/evidence_packet.json
```

Markdown is the source of truth for Codex or Claude Code. JSON/JSONL files are mirrors for indexing, dashboards, or deterministic validators.

## Output Rules

- Include search date and sources used.
- Separate confirmed facts, assumptions, and unverified candidates.
- Explain why each recommended paper or repo matters for this task.
- Include enough detail for a downstream executor to inspect the chosen repo or paper without repeating the full search.
- If network/search tools are unavailable, produce a partial report with `retrieval_status: blocked_or_partial` and the exact missing tool or approval.
- Never present a repository as reusable unless license, install surface, and task match have been at least inspected or explicitly marked unknown.

## Anti-Patterns

- Do not search for "reinforcement learning" generically when the task card has a specific environment or algorithm axis.
- Do not treat stars or citation counts as proof of task fit.
- Do not silently drop contradictory or weak evidence.
- Do not infer a paper has code unless a code URL is found.
- Do not proceed to implementation from this skill; hand off to strategy decision or executor-brief generation.

## Handoff Wording

When evidence retrieval is sufficient:

```text
Evidence retrieval complete: coverage=<sufficient|partial>. Recommended next stage: strategy_decision. Report: runs/<task-id>/evidence_report.md
```

When blocked or partial:

```text
Evidence retrieval partial: <missing source/tool/approval>. Usable evidence: <yes|no>. Report: runs/<task-id>/evidence_report.md
```
