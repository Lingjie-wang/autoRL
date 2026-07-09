# Orchestrator Report Template

Use this structure for `runs/<task-id>/orchestrator_report.md`.

```markdown
# AutoRL Mini Orchestration Report

## Status
- orchestration_status: complete | blocked_before_start | blocked_after_clarification | blocked_before_retrieval | blocked_after_retrieval | failed
- task_id:
- created_at:
- user_request:

## Stage Execution
| Stage | Executor | Prompt Path | Status | Output |
| --- | --- | --- | --- | --- |
| clarification | main_agent | n/a | ... | task_card.md |
| retrieval | retrieval_subagent | subagent_prompts/retrieval_prompt.md | ... | evidence_report.md |

## Clarification Gate
- status: pass | fail | skipped
- task_card:
- clarification_log:
- handoff_status:
- ambiguity_score:
- missing_or_invalid_fields:

## Retrieval Gate
- status: pass | fail | skipped
- evidence_report:
- retrieval_status:
- coverage:
- gaps:

## Artifact Chain
- task_card.md:
- evidence_report.md:
- optional_sidecars:

## Result
- handoff_worked: yes | no
- why:
- smallest_blocker:
- next_action:

## Notes
- subagent_limitations:
- main_thread_clarification_notes:
- tool_or_network_limitations:
- assumptions:
```
