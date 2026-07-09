# Executor Protocol

## Principle

Codex or Claude Code is the implementation executor. The AutoRL skill gives it a precise brief and validation contract, then lets it use its native coding loop.

## Executor Brief Format

Use this structure:

```yaml
task_id: short-stable-id
mode: plan_only | implement | debug | review | migrate
execution_boundary: generate_only | dry_run | runtime_allowed
dependency_policy: generate_only | ask_before_install | approved_for_install | approved_for_clone
objective: one sentence
repo_or_workspace: path
allowed_targets:
  - path-or-directory
inputs:
  task_card_path: runs/<task-id>/task_card.md
  context_packet_path: runs/<task-id>/context_packet.json
  evidence_report_path: runs/<task-id>/evidence_report.md
  decision_packet: {}
  implementation_plan_path: runs/<task-id>/implementation_plan.md
artifact_contract:
  required_files: []
  optional_files: []
  schema_expectations: []
constraints:
  - no invented evidence
  - no real training unless runtime_allowed
  - no dependency install without approval
  - no repository clone without approval
approval_gates:
  dependency_install: ask | approved | forbidden
  repository_clone: ask | approved | forbidden
  full_training: ask | approved | forbidden
validation:
  commands: []
  checks: []
expected_response:
  - changed files
  - tests run
  - artifact paths
  - remaining risks
```

## Codex Usage

Use Codex when the task requires repository inspection, refactoring, test runs, or patches. Give it:

- the executor brief
- exact workspace path
- expected validation commands
- whether it may modify files

Codex should return a patch-oriented result and test evidence.

## Claude Code Usage

Use Claude Code similarly when the user prefers it or when it is the available executor. Give it the same executor brief. Do not rely on Claude-specific hidden state; all critical constraints must be in the brief.

## Context Budgeting

Pass compact context, not full workflow state.

Prefer:

- file paths
- evidence ids
- compact schema snippets
- test commands
- acceptance criteria

Avoid:

- full run manifests
- raw LLM messages
- complete telemetry logs
- recursive `shared_context`
- complete retention matrices

## Executor Output Requirements

Require the executor to report:

- `status`: `completed`, `blocked`, or `failed`
- `changed_files`
- `tests_run`
- `artifacts`
- `assumptions`
- `risks`
- `next_action`

If blocked, require the smallest missing fact or approval needed.
