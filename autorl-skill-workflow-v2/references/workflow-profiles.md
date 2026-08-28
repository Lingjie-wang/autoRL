# Workflow Profiles

## Shared Model

Use one shared workflow with two profiles. Do not maintain two duplicated
orchestrators.

```text
intake
  -> environment contract + independent verification
  -> task-grounded evidence
  -> strategy and experiment contracts
  -> training build + verification
  -> optional approved runtime
  -> evaluation
  -> result package
```

The environment and evidence branches may overlap when the task card already
contains enough environment semantics. Strategy is a join gate: both branches
must be accepted.

## Application Delivery

Trigger this profile when the user supplies custom environment code, a new
benchmark, an external simulator, or an application requirement whose primary
goal is a usable training package.

```text
RECEIVED
  -> CLARIFYING
  -> TASK_READY
  -> CONTEXT_COLLECTING
       -> environment onboarder
       -> environment verifier
       -> evidence retriever
  -> CONTEXT_READY
  -> STRATEGY_READY
  -> BUILDING
  -> CODE_VERIFIED
  -> PACKAGING
  -> COMPLETED
```

Optional runtime extension:

```text
CODE_VERIFIED
  -> PREFLIGHT_READY
  -> AWAITING_APPROVAL
  -> TRAINING_ACTIVE
  -> EVALUATING
  -> EVALUATION_READY
  -> PACKAGING
```

Default to delivery after code verification. Do not start a full run merely
because the user asked for "training code".

## Research Iteration

Trigger this profile when the user supplies a baseline, asks for reproduction or
improvement, or requires a scientific comparison.

```text
RECEIVED
  -> CLARIFYING
  -> TASK_READY
  -> CONTEXT_COLLECTING
       -> baseline audit
       -> environment contract/verification
       -> paper and code evidence
  -> CONTEXT_READY
  -> STRATEGY_READY
       -> freeze baseline comparison protocol
       -> freeze one candidate hypothesis
  -> BUILDING
  -> CODE_VERIFIED
  -> PREFLIGHT_READY
  -> AWAITING_APPROVAL
  -> TRAINING_ACTIVE
  -> EVALUATING
  -> EVALUATION_READY
  -> REVIEWING
       -> package, hold, rollback, or create child run
  -> PACKAGING
  -> COMPLETED
```

Baseline qualification is mandatory. If the baseline cannot be reproduced, mark
the comparison blocked or explicitly change the research claim. Do not treat a
different framework, budget, seed set, or evaluation cadence as the same
baseline without justification.

## Main Orchestrator Responsibilities

The main orchestrator:

- asks blocking questions
- selects the profile and stage graph
- initializes and transitions workflow state
- persists subagent prompts
- validates and accepts worker artifacts
- freezes strategy, approvals, and comparison protocol
- reconciles runtime state
- decides package, retry, rollback, or child-run routing
- writes the final result package

It does not perform evidence retrieval, environment implementation, environment
self-verification, or training-code implementation when those workers are
available.

## Worker Concurrency

Allowed:

- preliminary evidence retrieval in parallel with environment onboarding when
  environment semantics are already explicit
- independent read-only validation in parallel with unrelated static checks

Forbidden:

- strategy before environment and evidence are both accepted
- build before strategy is frozen
- full launch before preflight and exact approval
- supervisor-to-builder routing without a main-orchestrator state transition

## Iteration Model

An accepted artifact is immutable. Rework creates:

- a new stage attempt when the objective and experiment identity are unchanged
- a child run when code, reward, environment schema, hypothesis, baseline
  protocol, or scientific identity changes

Every child run records `parent_run_id`, `parent_checkpoint_id` when applicable,
and one bounded `change_set`.
