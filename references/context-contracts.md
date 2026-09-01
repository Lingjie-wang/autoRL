# Context Contracts

## Three Context Types

### LLM/Executor Context

Small, task-focused context used in executor briefs.

Include:

- task card
- environment/model/runtime contracts
- selected evidence refs
- artifact contract
- validation commands
- constraints and forbidden actions

Exclude:

- full traces
- full prompt history
- recursive handoff packets
- raw logs
- full retention matrix

### Audit/Debug Context

Compact but richer context for debugging workflow behavior.

Include:

- context digest hashes
- compact handoff packet
- compact shared context digest
- retention summary
- artifact paths
- failure reasons

Exclude:

- full raw prompt bodies unless explicitly debugging prompt construction
- recursive input payloads

### Internal Working Context

Full in-memory context used by the orchestrator or human operator.

May include:

- normalized shared context
- full retention audit
- full evidence objects
- intermediate decision payloads
- trace metadata

Do not pass this whole object to an executor.

## Required Context Packet Fields

Use these keys when available:

- `original_user_utterance`
- `environment_spec`
- `model_requirements`
- `metrics_contract`
- `artifact_contract`
- `runtime_capability`
- `runtime_contract_digest`
- `environment_adaptation_packet`
- `environment_interface_contract`
- `environment_reuse_policy`
- `environment_reuse_ref`
- `context_preflight`
- `evidence_source_context`
- `implementation_evidence_bridge`
- `candidate_decision_context`
- `agent_decision_context`
- `state_feedback_context`
- `feedback_handoff_context`
- `execution_boundary`
- `risk_flags`

## Retention Summary

Pass a summary to LLMs and executors:

```yaml
field_retention_ok: true | false
retention_risk_flags: []
expected_field_count: integer
retained_field_count: integer
risky_fields:
  - field: name
    carriers: []
    missing_from: []
full_fields_omitted: true
```

Keep the full `fields` matrix audit-only.

## Handoff Packet

Use handoff packets as a compact stage history, not as the state store.

Allowed fields:

- `original_user_utterance`
- `clarification_transcript`
- `agent_decisions`
- `evidence_artifacts`

Agent decisions should store input refs and hashes, not full recursive inputs.
