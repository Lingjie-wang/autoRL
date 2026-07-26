"""Independent verifier for PettingZoo-ParallelEnv integrations.

Multi-agent counterpart of verify_env_template.py, per the multi-agent
tiers in references/env-adapter-contract.md. Dispatch rule: use this
when env_spec.json declares api_convention == "pettingzoo_parallel".

Usage:
    python verify_parallel_env_template.py --run-dir runs/<task-id> --boundary dry_run
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path

DELIVERABLES = ["adapter.py", "env_config.json", "env_spec.json",
                "extract_spec.py", "smoke_rollout.py"]
SPEC_REQUIRED_FIELDS = ["env_id", "source_type", "api_convention",
                        "possible_agents", "observation_spaces", "action_spaces",
                        "action_mask_location", "agents_can_terminate_early",
                        "episode_termination", "deterministic_under_seed",
                        "dependencies"]

results = []


def record(name, tier, status, expected, observed, fix=None):
    entry = {"check": name, "tier": tier, "status": status,
             "expected": expected, "observed": observed}
    if fix is not None and status == "failed":
        entry["smallest_fix"] = fix
    results.append(entry)
    print(f"  [{status.upper():7}] {name}" +
          ("" if status == "passed" else f": {observed}"))
    return status == "passed"


def check_files_exist(integration_dir):
    missing = [f for f in DELIVERABLES if not (integration_dir / f).exists()]
    return record("deliverables_exist", "generate_only",
                  "passed" if not missing else "failed",
                  "all integration deliverables present",
                  "all present" if not missing else f"missing: {missing}",
                  fix=f"produce missing files: {missing}")


def check_spec(integration_dir):
    try:
        spec = json.loads((integration_dir / "env_spec.json").read_text())
    except Exception as e:
        record("spec_parses", "generate_only", "failed",
               "env_spec.json is valid JSON", f"parse error: {e}",
               fix="regenerate spec via extract_spec.py")
        return None
    missing = [k for k in SPEC_REQUIRED_FIELDS if k not in spec]
    record("spec_required_fields", "generate_only",
           "passed" if not missing else "failed",
           "multi-agent spec fields present",
           "all present" if not missing else f"missing: {missing}",
           fix=f"add fields {missing} to extract_spec.py")
    if spec.get("api_convention") != "pettingzoo_parallel":
        record("api_convention", "generate_only", "failed",
               "pettingzoo_parallel",
               str(spec.get("api_convention")),
               fix="use verify_env_template.py for single-agent gymnasium specs")
        return None
    return spec


def load_adapter(integration_dir):
    sys.path.insert(0, str(integration_dir))
    try:
        import adapter
        record("adapter_imports", "dry_run", "passed", "import succeeds", "ok")
        return adapter
    except Exception as e:
        record("adapter_imports", "dry_run", "failed", "import succeeds",
               f"{type(e).__name__}: {e}", fix="fix imports/dependencies")
        return None


def pick_legal(env, agent, info, rng):
    mask = None
    if isinstance(info.get(agent), dict):
        mask = info[agent].get("action_mask")
    if mask is not None:
        legal = [i for i, ok in enumerate(mask) if ok]
        if legal:
            return rng.choice(legal)
    return env.action_space(agent).sample()


def rollout_signature(adapter, config, seed, max_turns):
    env = adapter.make_env(config)
    rng = random.Random(seed)
    obs, info = env.reset(seed=seed)
    sig = [sorted((a, o.tobytes() if hasattr(o, "tobytes") else repr(o))
                  for a, o in obs.items())]
    for _ in range(max_turns + 5):
        if not env.agents:
            break
        actions = {a: pick_legal(env, a, info, rng) for a in env.agents}
        obs, rew, term, trunc, info = env.step(actions)
        sig.append((sorted((a, o.tobytes() if hasattr(o, "tobytes") else repr(o))
                           for a, o in obs.items()),
                    sorted(rew.items()), sorted(term.items()), sorted(trunc.items())))
    env.close()
    return sig


def dry_run_checks(adapter, spec):
    config = adapter.load_config()
    seed = config.get("default_seed", 0)
    rng = random.Random(0)

    try:
        env = adapter.make_env(config)
        record("env_constructs", "dry_run", "passed", "make_env succeeds", "ok")
    except Exception as e:
        record("env_constructs", "dry_run", "failed", "make_env succeeds",
               f"{type(e).__name__}: {e}", fix="fix construction path/config")
        return

    try:
        declared_agents = spec["possible_agents"]
        record("possible_agents_match", "dry_run",
               "passed" if list(env.possible_agents) == declared_agents else "failed",
               str(declared_agents), str(list(env.possible_agents)),
               fix="re-run extract_spec.py or fix adapter agent ids")

        ok = True
        for a in declared_agents:
            if spec["observation_spaces"][a]["repr"] != repr(env.observation_space(a)):
                ok = False
            if spec["action_spaces"][a]["repr"] != repr(env.action_space(a)):
                ok = False
        record("per_agent_spaces_match_declared", "dry_run",
               "passed" if ok else "failed",
               "declared per-agent spaces equal runtime spaces",
               "all match" if ok else "at least one agent's space drifted",
               fix="re-run extract_spec.py or fix adapter construction drift")

        obs, info = env.reset(seed=seed)
        reset_ok = (set(obs) == set(env.agents)
                    and set(env.agents) <= set(declared_agents)
                    and all(env.observation_space(a).contains(obs[a]) for a in obs))
        record("reset_dict_contract", "dry_run",
               "passed" if reset_ok else "failed",
               "reset -> obs dict keyed by active agents, each obs in its space",
               f"keys={sorted(obs)}, active={sorted(env.agents)}",
               fix="fix adapter reset() dict construction")

        limit = spec["episode_termination"].get("truncated_at_steps") or 10_000
        step_ok, shrink_ok, mask_seen = True, True, False
        turns, ended = 0, False
        while env.agents and turns <= 10 * limit:
            prev = set(env.agents)
            actions = {a: pick_legal(env, a, info, rng) for a in env.agents}
            obs, rew, term, trunc, info = env.step(actions)
            for d in (rew, term, trunc, info):
                if set(d) != prev:
                    step_ok = False
            for a in prev:
                if a in obs and not env.observation_space(a).contains(obs[a]):
                    step_ok = False
                if not (isinstance(rew.get(a), (int, float)) and math.isfinite(rew[a])):
                    step_ok = False
                if not (isinstance(term.get(a), bool) and isinstance(trunc.get(a), bool)):
                    step_ok = False
            if not set(env.agents) <= prev:
                shrink_ok = False
            if any(isinstance(v, dict) and "action_mask" in v for v in info.values()):
                mask_seen = True
            turns += 1
            ended = not env.agents
        record("step_dict_contract", "dry_run",
               "passed" if step_ok else "failed",
               "per-step dicts keyed by stepping agents; obs in space; finite rewards; bool flags",
               f"clean for {turns} turns" if step_ok else f"violation within {turns} turns",
               fix="fix adapter step() dict conversion")
        record("agent_set_monotonic_shrink", "dry_run",
               "passed" if shrink_ok else "failed",
               "agents only leave mid-episode, never re-enter",
               "no resurrection observed" if shrink_ok else "agent re-entered mid-episode",
               fix="remove done agents from self.agents and never re-add before reset")
        record("episode_terminates", "dry_run",
               "passed" if ended and turns <= limit else "failed",
               f"all agents done within {limit} turns",
               f"ended at turn {turns}" if ended else f"no end after {turns} turns",
               fix="wire per-agent terminated/truncated in adapter")
        if spec.get("action_mask_location", "none") != "none":
            record("action_masks_present", "dry_run",
                   "passed" if mask_seen else "failed",
                   f"masks at {spec['action_mask_location']}",
                   "masks observed" if mask_seen else "no mask found where declared",
                   fix="surface masks at the declared location or set location to none")

        obs2, _ = env.reset(seed=seed)
        record("reset_restores_agents", "dry_run",
               "passed" if set(env.agents) == set(declared_agents) else "failed",
               "reset restores the full possible_agents set",
               f"active after reset: {sorted(env.agents)}",
               fix="reset self.agents from possible_agents in reset()")
    finally:
        env.close()

    if spec.get("deterministic_under_seed"):
        same = (rollout_signature(adapter, config, seed, limit)
                == rollout_signature(adapter, config, seed, limit))
        record("seed_determinism", "dry_run", "passed" if same else "failed",
               "identical multi-agent trajectory for identical seed and actions",
               "trajectories identical" if same else "trajectories diverged",
               fix="thread seed into every native randomness source, or declare "
                   "deterministic_under_seed=false with a documented reason")
    else:
        record("seed_determinism", "dry_run", "skipped",
               "spec declares deterministic_under_seed=false", "not checked")

    try:
        e2 = adapter.make_env(config)
        e2.close()
        e2.close()
        record("close_safe", "dry_run", "passed",
               "construct/close cycles and double close are safe", "ok")
    except Exception as e:
        record("close_safe", "dry_run", "failed",
               "construct/close cycles and double close are safe",
               f"{type(e).__name__}: {e}", fix="guard close() for repeated calls")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--boundary", choices=["generate_only", "dry_run"],
                        default="dry_run")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    integration_dir = run_dir / "artifacts" / "integration"
    report_path = run_dir / "verification_report.json"

    print(f"verifying {run_dir.name} (pettingzoo_parallel) at boundary={args.boundary}")
    check_files_exist(integration_dir)
    spec = check_spec(integration_dir)

    if args.boundary == "dry_run" and spec is not None:
        adapter = load_adapter(integration_dir)
        if adapter is not None:
            dry_run_checks(adapter, spec)

    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ("passed", "failed", "skipped")}
    overall = "passed" if counts["failed"] == 0 else "failed"
    report = {
        "task_id": run_dir.name,
        "contract": "references/env-adapter-contract.md",
        "api_convention": "pettingzoo_parallel",
        "verified_at_boundary": args.boundary,
        "overall_status": overall,
        "summary": counts,
        "checks": results,
        "performance_claims": "none",
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"overall: {overall} {counts} -> {report_path}")
    return 0 if overall == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
