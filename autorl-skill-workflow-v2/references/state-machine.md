# State Machine

## Workflow States

| State | Meaning |
| --- | --- |
| `received` | Run created; intake not yet accepted. |
| `clarifying` | Main thread is resolving blocking fields. |
| `waiting_input` | User input is required; this is not a failure. |
| `task_ready` | Intake stage is accepted. |
| `context_collecting` | Environment and evidence workers are running. |
| `context_ready` | Environment verification and evidence are accepted. |
| `strategy_ready` | Strategy, experiment, and control contracts are frozen. |
| `building` | Training implementation is in progress. |
| `code_verified` | Build stage and bounded verification are accepted. |
| `awaiting_approval` | Exact launch or another privileged action needs approval. |
| `preflight_ready` | Launch plan and preflight are accepted. |
| `training_active` | An approved external training process is active. |
| `paused` | Training is deliberately paused at a recorded boundary. |
| `evaluating` | Frozen evaluation is in progress. |
| `evaluation_ready` | Evaluation artifacts are accepted. |
| `reviewing` | Main orchestrator decides package or next child run. |
| `packaging` | Result package is being produced. |
| `completed` | Result package is accepted; terminal. |
| `blocked` | A named external blocker prevents progress. |
| `failed` | Unrecoverable failure; terminal for this run. |
| `cancelled` | User or policy cancelled the run; terminal. |

Use `scripts/statectl.py`; do not edit `workflow_state.json` manually.

## Primary Transitions

```text
received -> clarifying
clarifying -> task_ready | waiting_input | cancelled
waiting_input -> clarifying | blocked | cancelled
task_ready -> context_collecting | cancelled
context_collecting -> context_ready | waiting_input | blocked | failed | cancelled
context_ready -> strategy_ready | blocked | cancelled
strategy_ready -> building | packaging | blocked | cancelled
building -> code_verified | blocked | failed | cancelled
code_verified -> preflight_ready | awaiting_approval | packaging | blocked | cancelled
awaiting_approval -> preflight_ready | blocked | cancelled
preflight_ready -> training_active | evaluating | packaging | blocked | failed | cancelled
training_active -> paused | evaluating | failed | cancelled
paused -> training_active | evaluating | blocked | failed | cancelled
evaluating -> evaluation_ready | failed | cancelled
evaluation_ready -> reviewing | packaging | failed
reviewing -> strategy_ready | packaging | blocked | cancelled
packaging -> completed | failed
```

`blocked` may resume only to a state named in its event payload. Terminal states
do not resume; create a child run instead.

## Stage Attempts

Each stage has attempts with the following local lifecycle:

```text
pending -> running -> produced -> validated -> accepted
                    \-> failed
          \-> blocked
```

Workers may produce files. Only deterministic validation plus the main
orchestrator may create the stage's `accepted.json`. A crash after `produced`
requires revalidation.

Accepted attempts are immutable. A changed input digest creates another attempt
and invalidates downstream acceptance until revalidated.

## Runtime Process State

Track the external process separately in `runtime/process_state.json`:

```text
ready -> launching -> running
running -> pause_requested -> paused
paused -> resuming -> running
running | paused -> stopping -> succeeded
running | paused -> recovering -> running | failed
launching | running | paused | recovering -> failed | cancelled
```

Workflow state and process state are not interchangeable. A monitoring agent
ending does not mean the training process ended.

## Supervisor Cycle State

Each scheduled supervision cycle is bounded and exits:

```text
observing
  -> diagnosing
  -> proposing
  -> policy_gate
  -> hold | request_approval | authorized
  -> apply_at_safe_boundary
  -> receipt
  -> cooldown
  -> evaluating
  -> done
```

The supervisor writes only the proposal. The deterministic guard writes the
authorization. A framework-specific actuator writes the receipt.

## Versioning And Recovery

- `workflow_state.version` is a compare-and-swap token.
- Every mutation requires `--expected-version`.
- A per-run file lock enforces one state writer.
- Every mutation appends a hash-chained event before updating the state
  projection.
- `statectl.py rebuild` reconstructs the projection from the event chain.
- A repeated operation id with the same payload is idempotent.
- Reusing an operation id with a different payload fails.

Run `scripts/validate_run.py` before resume and before packaging.
