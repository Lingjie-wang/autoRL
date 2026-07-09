# Handoff Gates

Use these gates in the main orchestrator thread after main-thread clarification and after the retrieval child agent returns.

## Clarification Gate

Pass only when:

- `task_card.md` exists and is readable.
- `clarification_log.md` exists and is readable when follow-up questions were asked.
- `handoff_status` is `ready`.
- `ambiguity_score` is present and `<= 0.15`.
- The task card contains:
  - `task_mode`
  - `environment_type`
  - environment id/path or source
  - concrete `rl_task`
  - `algorithm_direction`
  - primary metric or success criteria
  - runtime boundary

Fail when:

- Any required field is absent.
- The main thread only summarized clarification without writing files.
- The card asks for downstream implementation before evidence retrieval.
- The card hides important uncertainty as an assumption.
- A ready card fills mandatory fields from prior run artifacts, local notes, or repository context without an explicit user confirmation for this run.
- Retrieval starts in the same assistant turn that asked a blocking/high-impact clarification question.

## Retrieval Gate

Pass when:

- `evidence_report.md` exists and is readable.
- `retrieval_status` is present.
- `coverage` is present.
- Task grounding agrees with `task_card.md`.
- The report includes at least one of:
  - paper candidates
  - codebase candidates
  - explicit gaps explaining why candidates could not be found
- The report includes risks and handoff notes.

Treat `retrieval_status: complete` or `partial` as acceptable for completing the mini workflow when the report names sources, candidates, or explicit gaps.

Treat `retrieval_status: blocked` as a valid report shape but not a successful chain. In that case, write `orchestration_status: blocked_after_retrieval`.

Fail when:

- The child agent claims it searched but provides no sources, candidates, or gaps.
- The report recommends cloning/installing/running without approval.
- The report chooses a final implementation plan instead of handing off to strategy decision.

## Stop Conditions

Stop the mini workflow and write `orchestrator_report.md` when:

- subagents are unavailable before retrieval starts
- clarification remains blocked after the main agent asks the smallest necessary user question
- the task card fails validation
- the retrieval report is missing or invalid
- a child agent attempted forbidden actions
