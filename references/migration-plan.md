# Migration Plan From Multi-Agent Codebase

## Goal

Move from custom Python agent executors to a skill-based workflow where Codex or Claude Code performs implementation and validation.

## Mapping Existing Nodes To Skill Stages

| Current node/agent | Skill-stage replacement | Executor responsibility |
| --- | --- | --- |
| ClarificationAgent | intake and task card | ask missing facts only when blocking |
| UnderstandingAgent | context assembly | parse user intent into task card |
| RouterAgent | decision support | classify supported route |
| RetrievalAgent | evidence packet | collect and rank evidence refs |
| DecisionAgent | strategy decision | choose implementation mode, no code |
| ResearchGuidanceAgent | optional evidence synthesis | summarize method constraints |
| CodeAgent / WriterAgent | executor brief + implementation | Codex/Claude edits files and generates artifacts |
| TrainingAgent | verification/preflight | validate boundary and runtime readiness |
| ReviewAgent | verification report | check artifacts against contracts |
| Save manifest | result package | compact user/debug outputs |

## Migration Sequence

1. Freeze current workflow behavior with focused tests.
2. Extract task card, context packet, evidence packet, decision packet, and executor brief schemas.
3. Replace LLM-to-LLM handoffs with file-backed stage artifacts.
4. Route implementation tasks to Codex or Claude Code using executor briefs.
5. Keep Python code only for deterministic normalization, validation, and artifact packaging.
6. Remove custom executor-like behavior from agent classes.
7. Keep full audit context out of executor prompts.

## What To Keep

Keep deterministic code for:

- context normalization
- evidence indexing
- runtime capability catalog
- schema validation
- artifact verification
- result packaging

## What To Remove Or Demote

Remove or demote:

- verbose final prompt storage in user-facing outputs
- recursive agent input snapshots
- LLM prompts that ask one agent to simulate another agent's job
- custom code executor logic where Codex/Claude can directly edit and test files
- full shared context in every prompt

## First Practical Cut

Implement one vertical workflow:

1. User asks for an RL adaptation.
2. Skill creates `task_card`, `context_packet`, and `executor_brief`.
3. Codex implements a small artifact or config change.
4. Skill validates artifacts and writes `result_package`.

Do not migrate all existing nodes at once.
