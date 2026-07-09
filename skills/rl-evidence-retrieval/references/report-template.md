# Evidence Report Template

Use this Markdown structure for `runs/<task-id>/evidence_report.md`.

```markdown
# AutoRL Evidence Report

## Retrieval Status
- retrieval_status: complete | partial | blocked
- coverage: sufficient | partial | insufficient
- search_date:
- input_task_card:
- next_stage: strategy_decision | stop_for_user
- reason:

## Task Grounding
- task_mode:
- environment:
- environment_type:
- rl_task:
- algorithm_direction:
- primary_metric:
- runtime_boundary:

## Search Plan
- paper_queries:
- codebase_queries:
- sources_used:
- sources_unavailable:

## Evidence Coverage
| Dimension | Status | Notes |
| --- | --- | --- |
| Environment | sufficient/partial/insufficient | ... |
| Algorithm | sufficient/partial/insufficient | ... |
| Metric | sufficient/partial/insufficient | ... |
| Code | sufficient/partial/insufficient | ... |
| Reproducibility | sufficient/partial/insufficient | ... |

## Paper Candidates
| ID | Paper | Venue/Year | Method | Env Match | Metric Match | Code | Verification | Relevance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | ... | ... | ... | ... | ... | ... | ... | ... |

## Codebase Candidates
| ID | Repo | Role | Algorithm | Env Support | License | Install Risk | Reuse Plan |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01 | ... | ... | ... | ... | ... | ... | ... |

## Recommended Evidence
- Best paper to follow:
- Best codebase to inspect:
- Best baseline path:
- Why this route fits the task:

## Risks And Gaps
- Missing environment evidence:
- Missing algorithm evidence:
- Unverified claims:
- License or dependency risks:
- Follow-up searches:

## Handoff Notes
- Evidence refs for decision stage:
- Do not do yet:
- Approval needed before:
```

Optional structured sidecars should mirror the report, not replace it.

`evidence_packet.json` should contain:

```json
{
  "retrieval_status": "complete",
  "coverage": "sufficient",
  "input_task_card": "runs/<task-id>/task_card.md",
  "search_date": "YYYY-MM-DD",
  "paper_refs": ["P01"],
  "codebase_refs": ["C01"],
  "evidence_items": [],
  "gaps": [],
  "next_stage": "strategy_decision"
}
```
