---
name: autorl
description: Skill workflow for evidence-backed AutoRL planning and implementation with Codex or Claude Code as the executor. Use when converting a multi-agent AutoRL pipeline into skill-based workflows, designing RL environment-adaptation tasks, preparing executor briefs, generating or validating RL runtime artifacts, or migrating the current AutoRL codebase away from custom agent executors.
---

# AutoRL

## Core Rule

Treat Codex or Claude Code as the executor. Do not recreate an executor inside the workflow. Use this skill to structure the task, preserve the right context, create bounded handoffs, and define validation.

## Workflow

1. Classify the request:
   - **Plan only**: produce task card, evidence plan, executor brief, and validation checklist.
   - **Implement**: create or modify files, then run focused tests.
   - **Migrate workflow**: map existing agent nodes to skills and remove custom executor responsibilities.
   - **Debug artifact**: inspect run outputs, manifests, prompts, and context packets.

2. Build a task card before execution. Include:
   - user intent and exact RL environment objective
   - known facts vs assumptions
   - environment/model/runtime contracts
   - evidence requirements
   - execution boundary: generate-only, dry-run, or allowed runtime execution
   - validation criteria

3. Use stage contracts instead of agent personas:
   - intake and clarification: use `skills/rl-task-clarifier/` when the RL task is vague or the executor would need to guess environment, metric, budget, or runtime permissions
   - context assembly
   - evidence retrieval: use `skills/rl-evidence-retrieval/` after a task card is ready to collect paper and codebase evidence before strategy decisions
   - mini workflow testing: use `skills/autorl-mini-orchestrator/` when explicitly testing main-thread clarification followed by retrieval subagent handoff
   - strategy decision
   - executor brief
   - environment integration: use `skills/rl-env-integrator/` when a concrete environment must become constructible behind the adapter contract (`references/env-adapter-contract.md`) before algorithm work
   - implementation: use `skills/rl-framework-implementer/` when the task requires setting up an RL framework, adding algorithm/environment code, or running bounded implementation smoke tests
   - verification: use `skills/rl-env-verifier/` to independently verify environment integrations and emit `verification_report.json`
   - result package

4. Keep context bounded:
   - give the executor only the task card, relevant evidence refs, artifact contracts, and acceptance tests
   - keep full audit/debug context outside the executor prompt
   - use hashes, paths, and summaries for large intermediate artifacts

5. Validate before reporting success:
   - run the smallest meaningful tests first
   - verify produced artifacts against the task card
   - report unsupported or missing context explicitly

## References

Read only the files needed for the current task:

- [workflow.md](references/workflow.md): stage-by-stage AutoRL workflow.
- [executor-protocol.md](references/executor-protocol.md): how to brief Codex or Claude Code as the implementation executor.
- [context-contracts.md](references/context-contracts.md): what information passes between stages and what stays audit-only.
- [artifact-contracts.md](references/artifact-contracts.md): expected files, schemas, and validation outputs.
- [migration-plan.md](references/migration-plan.md): how to migrate the current multi-agent codebase into skills.
- [skills/rl-task-clarifier/SKILL.md](skills/rl-task-clarifier/SKILL.md): repeated RL task clarification and ambiguity gate.
- [skills/rl-evidence-retrieval/SKILL.md](skills/rl-evidence-retrieval/SKILL.md): RL paper/codebase retrieval and evidence report generation.
- [skills/autorl-mini-orchestrator/SKILL.md](skills/autorl-mini-orchestrator/SKILL.md): orchestration test for main-thread clarification followed by retrieval subagent handoff.
- [skills/rl-framework-implementer/SKILL.md](skills/rl-framework-implementer/SKILL.md): RL framework setup, algorithm implementation, dependency gating, and smoke tests.
- [references/env-adapter-contract.md](references/env-adapter-contract.md): what "an environment is integrated" means — adapter standard, deliverables, verification tiers.
- [skills/rl-env-integrator/SKILL.md](skills/rl-env-integrator/SKILL.md): integrate one environment behind the adapter contract and produce verifiable deliverables.
- [skills/rl-env-verifier/SKILL.md](skills/rl-env-verifier/SKILL.md): independent acceptance gate for environment integrations; emits verification_report.json.
