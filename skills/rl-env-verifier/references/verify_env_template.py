"""Independent verifier for an environment integration (reusable template).

Usage:
    python verify_env_template.py --run-dir runs/<task-id> --boundary dry_run

Reads runs/<task-id>/artifacts/integration/ deliverables, re-constructs the
environment through the adapter under test, checks every claim in
env_spec.json against runtime behavior, writes
runs/<task-id>/verification_report.json, and exits nonzero on failure.

Check semantics live in check-catalog.md; keep the two in sync.
Proven against: gymnasium 1.3.0 (CartPole-v1, run 20260715-cartpole-integration).
"""

import argparse
import json
import math
import sys
from pathlib import Path

DELIVERABLES = ["adapter.py", "env_config.json", "env_spec.json",
                "extract_spec.py", "smoke_rollout.py"]
SPEC_REQUIRED_FIELDS = ["env_id", "source_type", "api_convention",
                        "observation_space", "action_space",
                        "episode_termination", "deterministic_under_seed",
                        "dependencies"]

results = []


def record(name, tier, status, expected, observed, fix=None):
    entry = {"check": name, "tier": tier, "status": status,
             "expected": expected, "observed": observed}
    if fix:
        entry["smallest_fix"] = fix
    results.append(entry)
    print(f"  [{status.upper():7}] {name}" +
          ("" if status == "passed" else f": {observed}"))
    return status == "passed"


# ---------- generate_only tier ----------

def check_files_exist(integration_dir):
    missing = [f for f in DELIVERABLES if not (integration_dir / f).exists()]
    return record("deliverables_exist", "generate_only",
                  "passed" if not missing else "failed",
                  f"all of {DELIVERABLES} under artifacts/integration/",
                  "all present" if not missing else f"missing: {missing}",
                  fix=f"produce missing files: {missing}" if missing else None)


def check_spec_parses(integration_dir):
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
           f"fields {SPEC_REQUIRED_FIELDS} present",
           "all present" if not missing else f"missing: {missing}",
           fix=f"add fields {missing} to extract_spec.py" if missing else None)
    return spec


# ---------- dry_run tier ----------

def load_adapter(integration_dir):
    sys.path.insert(0, str(integration_dir))
    try:
        import adapter
        record("adapter_imports", "dry_run", "passed",
               "import adapter succeeds", "ok")
        return adapter
    except Exception as e:
        record("adapter_imports", "dry_run", "failed",
               "import adapter succeeds", f"{type(e).__name__}: {e}",
               fix="fix import errors / missing dependencies in adapter.py")
        return None


def space_matches(declared, runtime_space, name):
    ok = declared.get("repr") == repr(runtime_space)
    detail_ok = True
    if "shape" in declared and list(getattr(runtime_space, "shape", []) or []) != declared["shape"]:
        detail_ok = False
    if "dtype" in declared and str(getattr(runtime_space, "dtype", None)) != declared["dtype"]:
        detail_ok = False
    if "n" in declared and int(getattr(runtime_space, "n", -1)) != declared["n"]:
        detail_ok = False
    return record(f"{name}_matches_declared", "dry_run",
                  "passed" if (ok and detail_ok) else "failed",
                  declared.get("repr"), repr(runtime_space),
                  fix=None if (ok and detail_ok) else
                  "re-run extract_spec.py or fix adapter construction drift")


def rollout_signature(adapter, config, seed, max_steps=200):
    """Deterministic trajectory fingerprint: same seed must reproduce it."""
    env = adapter.make_env(config)
    env.action_space.seed(seed)
    obs, _ = env.reset(seed=seed)
    sig = [obs.tobytes() if hasattr(obs, "tobytes") else repr(obs)]
    for _ in range(max_steps):
        obs, reward, terminated, truncated, _ = env.step(env.action_space.sample())
        sig.append((obs.tobytes() if hasattr(obs, "tobytes") else repr(obs),
                    float(reward), terminated, truncated))
        if terminated or truncated:
            break
    env.close()
    return sig


def dry_run_checks(adapter, spec):
    config = adapter.load_config()
    seed = config.get("default_seed", 0)

    try:
        env = adapter.make_env(config)
        record("env_constructs", "dry_run", "passed",
               "make_env(config) succeeds", "ok")
    except Exception as e:
        record("env_constructs", "dry_run", "failed",
               "make_env(config) succeeds", f"{type(e).__name__}: {e}",
               fix="fix construction path or env_config.json")
        return

    try:
        space_matches(spec["observation_space"], env.observation_space,
                      "observation_space")
        space_matches(spec["action_space"], env.action_space, "action_space")

        obs, info = env.reset(seed=seed)
        record("reset_contract", "dry_run",
               "passed" if env.observation_space.contains(obs) and isinstance(info, dict)
               else "failed",
               "reset -> (obs in declared space, info dict)",
               f"contains={env.observation_space.contains(obs)}, info={type(info).__name__}",
               fix="fix adapter reset() return values")

        step_ok, steps, done = True, 0, False
        limit = spec["episode_termination"].get("truncated_at_steps") or 10_000
        while not done and steps <= 10 * limit:
            obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
            if not (env.observation_space.contains(obs)
                    and isinstance(reward, (int, float)) and math.isfinite(reward)
                    and isinstance(terminated, bool) and isinstance(truncated, bool)):
                step_ok = False
            done = terminated or truncated
            steps += 1
        record("step_contract", "dry_run", "passed" if step_ok else "failed",
               "every step returns (obs in space, finite reward, bool, bool, info)",
               f"violation before step {steps}" if not step_ok else f"clean for {steps} steps",
               fix=None if step_ok else "fix adapter step() conversion")
        record("episode_terminates", "dry_run",
               "passed" if done and steps <= limit else "failed",
               f"episode ends within {limit} steps",
               f"ended at step {steps}" if done else f"no end after {steps} steps",
               fix=None if done else "wire terminated/truncated signals in adapter")
    finally:
        env.close()

    if spec.get("deterministic_under_seed"):
        same = (rollout_signature(adapter, config, seed)
                == rollout_signature(adapter, config, seed))
        record("seed_determinism", "dry_run", "passed" if same else "failed",
               "identical trajectory for identical seed and actions",
               "trajectories identical" if same else "trajectories diverged",
               fix=None if same else
               "thread seed into all randomness sources, or declare "
               "deterministic_under_seed=false with a documented reason")
    else:
        record("seed_determinism", "dry_run", "skipped",
               "spec declares deterministic_under_seed=false", "not checked")

    try:
        e2 = adapter.make_env(config)
        e2.close()
        e2.close()  # double close must be safe
        record("close_safe", "dry_run", "passed",
               "construct/close cycles and double close are safe", "ok")
    except Exception as e:
        record("close_safe", "dry_run", "failed",
               "construct/close cycles and double close are safe",
               f"{type(e).__name__}: {e}",
               fix="guard close() for repeated calls")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True,
                        help="runs/<task-id> directory containing artifacts/integration/")
    parser.add_argument("--boundary", choices=["generate_only", "dry_run"],
                        default="dry_run")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    integration_dir = run_dir / "artifacts" / "integration"
    report_path = run_dir / "verification_report.json"

    print(f"verifying {run_dir.name} at boundary={args.boundary}")
    check_files_exist(integration_dir)
    spec = check_spec_parses(integration_dir)

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
