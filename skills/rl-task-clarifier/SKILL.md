---
name: rl-task-clarifier
description: Iteratively clarify vague reinforcement-learning task requests into an execution-ready AutoRL task card with low ambiguity, using choice-style prompts when available. Use when a user asks AutoRL to solve, train, evaluate, debug, or design an RL agent/environment but has not fully specified environment, objective, constraints, success metrics, runtime boundary, compute budget, algorithm direction, or experiment acceptance criteria.
---

# RL Task Clarifier

## Purpose

Turn an underspecified RL request into a task card that another AutoRL stage or executor can use without guessing. Ask repeated, prioritized question batches until the ambiguity gate passes, then emit a compact clarified task card and handoff summary.

This skill owns only intake and clarification. It must not retrieve papers, choose algorithms, write training code, or start experiments.

## Operating Rules

- Treat "low perplexity" as **low task ambiguity**, not a language-model metric.
- Prefer one concise batch of high-value questions over many scattered turns.
- Ask at most 5 questions per turn.
- Prefer choice-style prompts for blocking intake fields. If the host supports an interactive choice UI, use it; otherwise render the same choices as a numbered Markdown list.
- Ask only questions whose answers can change algorithm choice, environment wiring, experiment budget, runtime permissions, or success evaluation.
- Use defaults only when the risk is low and mark each default as an assumption.
- Stop asking when all blocking fields are resolved and the ambiguity score is `<= 0.15`.
- If the user refuses or cannot answer after 3 rounds, produce a task card with explicit `blocked_fields`, `assumptions`, and `handoff_status: blocked_or_assumption_based`.
- After asking any blocking or high-impact question batch, stop the current assistant turn and wait for a later user response. Do not answer the questions from workspace context or continue into downstream stages in the same turn.
- Treat "same task", "previous task", "use the old one", and similar references as pointers, not confirmation. They may identify candidate fields, but mandatory fields remain unresolved until the user names an exact artifact/run or confirms the inferred field list in a later message.

## Minimum Intake Gates

Before asking lower-priority details, clarify these three fields:

1. **Task mode**: whether the request is research-oriented quality improvement (`research_quality_improvement`) or application-oriented algorithm execution in a new environment (`application_new_env_algorithm`).
2. **Environment and RL task**: whether the environment is official/standard, custom, or an external simulator; which environment to run; what the agent observes/actions/reward are; and what task behavior is being learned or evaluated.
3. **Algorithm direction**: the rough algorithm family or a user-approved evidence-backed selection policy, such as PPO/SAC/TD3/DQN, offline RL, imitation learning, model-based RL, multi-agent RL, safe RL, exploration-focused RL, or "choose a standard baseline after evidence retrieval."

## Choice UI Behavior

Use [choice-prompts.md](references/choice-prompts.md) for ready-made option sets.

When an interactive choice UI is available:

- Ask 1-3 choice questions per popup.
- Provide 2-3 fixed options per question.
- Put the recommended option first and label it as recommended.
- Do not include a fixed "Other" option if the host UI automatically adds a free-form custom option.
- If the host UI does not add a free-form option, add a final option named `Other / custom` and ask the user to describe their case.

When no interactive choice UI is available, render the same question as Markdown:

```text
请选择任务模式：
1. 科研质量提升（推荐：用于改进实验质量、算法想法、baseline、论文 claim）
2. 项目应用：新环境跑通算法（用于让某个环境先能训练/评估）
3. 其他 / 自定义：请直接描述你的情况
```

Record whether each answer came from a fixed option or custom text in `clarification_log.md`.

## Workflow

### 1. Parse The Initial Request

Extract candidate values for:

- task mode: research quality improvement or application/new-environment algorithm execution
- RL problem type
- environment type: official benchmark, custom env, or external simulator/adapter
- environment or benchmark
- concrete RL task behavior
- observation, action, reward, and termination interface
- rough algorithm family or selection policy
- training objective and success criteria
- evaluation protocol
- algorithm constraints or exclusions
- compute, wall-clock, and dependency limits
- execution boundary
- artifact expectations
- user approval requirements
- environment reuse policy when the request is a clean-room workflow test or
  explicitly requires or forbids prior integrations

Read [clarification-schema.md](references/clarification-schema.md) before scoring ambiguity or writing the final task card.

### 2. Score Ambiguity

Use the schema's field weights to compute:

```text
ambiguity_score = unresolved_weight / total_weight
```

Classify fields:

- `blocking`: missing value prevents safe downstream execution.
- `high_impact`: missing value can change algorithm, code, runtime, or evaluation.
- `assumable`: safe default exists; include the default in `assumptions`.
- `nice_to_have`: improves polish but should not block intake.

### 3. Ask A Question Batch

Build a batch from highest-impact unresolved fields.

Question style:

- Include why the question matters when the risk is non-obvious.
- Offer a recommended default only when it is genuinely safe.
- Group related fields into one question.
- Avoid asking the user to choose algorithm names unless the algorithm preference itself is part of the requirement.
- If using a prior artifact as candidate context, show the inferred high-impact fields and ask for explicit confirmation instead of marking them confirmed immediately.

Example:

```text
First popup:
1. Task mode: research quality improvement / application new-environment execution / custom
2. Environment source: existing benchmark / custom env path / simulator wrapper / custom
3. Algorithm direction: on-policy/off-policy standard baseline / offline or imitation / evidence-backed selection / custom

Second popup, only if still unresolved:
1. Success metric: average return / success rate / sample efficiency / custom
2. Runtime boundary: generate only / dry run / real training allowed / custom
```

### 4. Update The Clarification State

After each user answer:

- Fill resolved fields.
- Recompute `ambiguity_score`.
- Record assumptions separately from confirmed facts.
- Remove answered questions from `missing_context`.
- Ask the next batch only if the gate still fails.
- If the answer only partially resolves mandatory fields, keep the remaining mandatory fields blocking even when a plausible prior run or repository default exists.

Do not proceed to downstream AutoRL stages while any blocking field remains unresolved.

### 5. Pass The Readiness Gate

The request is ready when:

- all mandatory fields in the schema are either confirmed or explicitly assumed with low risk
- `task_mode` is known
- `execution_boundary` is known
- `success_criteria` is measurable
- `environment_spec.environment_type` is known
- `environment_spec` and the concrete RL task are actionable enough for an executor brief
- `algorithm_direction` is known, either as a rough family or as explicit permission for evidence-backed selection
- `ambiguity_score <= 0.15`
- no unresolved field can silently change safety, cost, or evaluation validity

### 6. Emit The Handoff

Write the canonical executor-facing handoff as Markdown. Codex and Claude Code should receive `task_card.md`, not a JSON blob, because the downstream executor is an LLM that benefits from concise prose, tables, and explicit assumptions.

Use this structure:

```markdown
# AutoRL Task Card

## Gate Status
- handoff_status: ready | blocked_or_assumption_based
- ambiguity_score: 0.00
- next_stage: context_assembly | evidence_retrieval | stop_for_user
- reason: ...

## User Goal
...

## Task Mode
- mode: research_quality_improvement | application_new_env_algorithm
- rationale:

## Confirmed Facts
- ...

## Assumptions
- ...

## Blocked Or Missing Context
- ...

## RL Environment
- environment_type: official_benchmark | custom_env | external_simulator
- id_or_path:
- source:
- rl_task:
- observation_space:
- action_space:
- reward_signal:
- termination:

## Algorithm Direction
- rough_family_or_policy:
- required_algorithms:
- forbidden_algorithms:
- selection_notes:

## Objective And Success Criteria
- primary_metric:
- threshold:
- evaluation_protocol:

## Runtime Constraints
- execution_boundary: generate_only | dry_run | runtime_allowed
- compute:
- budget:
- dependency_policy:
- environment_reuse: prefer_verified | disabled

## Expected Artifacts
- ...

## Approval Gates
- ...
```

If a deterministic validator or indexer needs structured data, also write an optional `task_card.json` mirror. The Markdown file remains the source of truth for executor handoff.

If writing files, prefer:

```text
runs/<task-id>/task_card.md
runs/<task-id>/clarification_log.md
runs/<task-id>/task_card.json  # optional structured mirror
```

## Anti-Patterns

- Do not ask generic questions such as "Can you provide more detail?"
- Do not ask for papers, algorithms, and code preferences before the environment and success criteria are clear.
- Do not convert uncertainty into hidden defaults.
- Do not claim the task is clear if evaluation is subjective or runtime permission is unknown.
- Do not continue into implementation just because the user sounds impatient; report the precise remaining blocker.
- Do not silently promote prior run contents to confirmed facts from phrases like "same task" unless the user identified the exact artifact or confirmed the copied field list.

## Handoff Wording

When the gate passes, end with a compact status:

```text
Clarification gate passed: ambiguity_score=<score>. The task is ready for <next_stage> because <reason>.
```

When the gate fails, end with:

```text
Clarification gate blocked: <N> blocking fields remain. Smallest next answer needed: <question>.
```
