"""Independent verifier for an environment integration (reusable template).

Usage:
    python verify_env_template.py --run-dir runs/<task-id> --boundary dry_run

Reads runs/<task-id>/artifacts/integration/ deliverables, re-constructs the
environment through the adapter under test, checks every claim in
env_spec.json against runtime behavior, writes
runs/<task-id>/verification_report.json, and exits nonzero on failure.

Check semantics live in check-catalog.md; keep the two in sync.
Proven against: gymnasium 1.3.0 — CartPole-v1 (run 20260715-cartpole-integration)
and the 5 single-agent envs of runs/20260726-sa5-* (LunarLander-v3,
HalfCheetah-v5, ALE/Pong-v5, MiniGrid-DoorKey-5x5-v0, FetchReach-v4).
"""

import argparse
import hashlib
import json
import math
import numbers
import re
import sys
from pathlib import Path

DELIVERABLES = ["adapter.py", "env_config.json", "env_spec.json",
                "extract_spec.py", "smoke_rollout.py"]
SPEC_REQUIRED_FIELDS = ["env_id", "source_type", "api_convention",
                        "observation_space", "action_space",
                        "episode_termination", "deterministic_under_seed",
                        "dependencies"]
# Required only for single-agent gymnasium specs; see env-adapter-contract.md
# "Single-Agent Descriptor Fields".
SPEC_DESCRIPTOR_FIELDS = ["observation_modality", "action_type",
                          "goal_conditioned", "randomness_sources",
                          "observed_reward_bounds", "training_channel"]

# Hard cap for any loop that waits for an episode to end. Environments that
# truncate internally report spec.max_episode_steps = None (ALE, MiniGrid), so
# the bound can never be derived from the spec alone.
STEP_CAP = 30_000

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
    missing_desc = [k for k in SPEC_DESCRIPTOR_FIELDS if k not in spec]
    record("spec_descriptor_fields", "generate_only",
           "passed" if not missing_desc else "failed",
           f"single-agent descriptor fields {SPEC_DESCRIPTOR_FIELDS} present",
           "all present" if not missing_desc else f"missing: {missing_desc}",
           fix=f"add fields {missing_desc} to extract_spec.py"
           if missing_desc else None)
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


_HEX_ADDR = re.compile(r" at 0x[0-9a-fA-F]+")


def normalize_repr(text):
    """Strip process-varying memory addresses from a space repr.

    MiniGrid's MissionSpace embeds the mission-generator function object, whose
    repr contains `at 0x7f74a3774e00`. That address differs on every process, so
    raw repr equality can never pass for any space holding a callable. Comparing
    normalized reprs keeps the check meaningful (structure still compared) while
    dropping the one part that is guaranteed to differ.
    """
    return _HEX_ADDR.sub(" at 0xADDR", text or "")


def space_matches(declared, runtime_space, name):
    ok = normalize_repr(declared.get("repr")) == normalize_repr(repr(runtime_space))
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


def canonical_bytes(obj, _depth=0):
    """Lossless-enough byte encoding of an arbitrary observation.

    Why not `repr()`: numpy abbreviates large arrays in repr (`[0 1 2 ... 9]`),
    so two genuinely different observations can share a repr and a determinism
    check built on it passes vacuously. Dict/tuple observations (MiniGrid,
    Fetch) have no `.tobytes()` and would fall into exactly that trap.

    Rules: dicts are key-sorted, arrays contribute raw bytes plus shape/dtype,
    other leaves fall back to repr (fine for scalars and strings, which repr
    faithfully).
    """
    if _depth > 8:
        return b"<depth-limit>"
    if hasattr(obj, "tobytes") and hasattr(obj, "shape"):  # ndarray-like
        header = f"arr:{obj.shape}:{obj.dtype}:".encode()
        return header + obj.tobytes()  # tobytes() copies; layout-independent
    if isinstance(obj, dict):
        return b"dict:" + b"|".join(
            k.encode() + b"=" + canonical_bytes(obj[k], _depth + 1)
            for k in sorted(obj))
    if isinstance(obj, (list, tuple)):
        return b"seq:" + b"|".join(
            canonical_bytes(v, _depth + 1) for v in obj)
    return f"lit:{obj!r}".encode()


def rollout_signature(adapter, config, seed, max_steps=200):
    """Deterministic trajectory fingerprint: same seed must reproduce it."""
    env = adapter.make_env(config)
    env.action_space.seed(seed)
    obs, _ = env.reset(seed=seed)
    h = hashlib.sha256()
    h.update(canonical_bytes(obs))
    steps = 0
    for _ in range(min(max_steps, STEP_CAP)):
        obs, reward, terminated, truncated, _ = env.step(env.action_space.sample())
        h.update(canonical_bytes(obs))
        h.update(f"|{float(reward)!r}|{terminated}|{truncated}".encode())
        steps += 1
        if terminated or truncated:
            break
    env.close()
    return f"{steps}:{h.hexdigest()}"


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

        step_ok, steps, done, violation = True, 0, False, None
        # Declared limit is advisory: ALE and MiniGrid report
        # spec.max_episode_steps = None and truncate internally. STEP_CAP is the
        # real bound, and hitting it is reported as its own outcome.
        limit = spec["episode_termination"].get("truncated_at_steps") or STEP_CAP
        bound = min(limit, STEP_CAP)
        while not done and steps < bound:
            obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
            if step_ok:
                # numbers.Real, not (int, float): np.float32 rewards (FetchReach)
                # are not Python floats, while MiniGrid returns a plain int.
                why = None
                if not env.observation_space.contains(obs):
                    why = "obs outside declared space"
                elif not isinstance(reward, numbers.Real):
                    why = f"reward type {type(reward).__name__} is not a real number"
                elif not math.isfinite(float(reward)):
                    why = f"non-finite reward {reward}"
                elif not isinstance(terminated, bool) or not isinstance(truncated, bool):
                    why = (f"flags not bool: terminated={type(terminated).__name__},"
                           f" truncated={type(truncated).__name__}")
                elif not isinstance(info, dict):
                    why = f"info is {type(info).__name__}, not dict"
                if why:
                    step_ok, violation = False, why
            done = terminated or truncated
            steps += 1
        record("step_contract", "dry_run", "passed" if step_ok else "failed",
               "every step returns (obs in space, finite real reward, bool, bool, dict)",
               f"{violation} at step {steps}" if not step_ok else f"clean for {steps} steps",
               fix=None if step_ok else "fix adapter step() conversion")
        record("episode_terminates", "dry_run",
               "passed" if done else "failed",
               f"episode ends within {bound} steps"
               + ("" if limit <= STEP_CAP else f" (declared limit {limit} exceeds cap)"),
               f"ended at step {steps}" if done
               else f"no end after {steps} steps (cap {bound})",
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


# ---------- runtime_allowed tier ----------

def runtime_allowed_checks(adapter, spec):
    config = adapter.load_config()
    seed = config.get("default_seed", 0)
    n_episodes = 5

    # multi_episode_nan_sweep + reward_bounds_observed
    nan_ok, bounds_ok = True, True
    nan_fail_ep = None
    declared_bounds = spec.get("observed_reward_bounds") or [None, None]
    obs_lo, obs_hi = (declared_bounds + [None, None])[:2]
    all_rewards = []
    for ep in range(n_episodes):
        try:
            env = adapter.make_env(config)
            env.action_space.seed(seed + ep)
            obs, _ = env.reset(seed=seed + ep)
            done = False
            steps = 0
            while not done and steps < STEP_CAP:
                obs, reward, terminated, truncated, _ = env.step(
                    env.action_space.sample())
                # NaN/Inf check on obs
                def _has_nonfinite(o):
                    if hasattr(o, "__iter__") and not isinstance(o, (str, bytes)):
                        try:
                            return any(not math.isfinite(float(v)) for v in
                                       (o.flat if hasattr(o, "flat") else o))
                        except (TypeError, ValueError):
                            return False
                    return False
                if isinstance(obs, dict):
                    nf = any(_has_nonfinite(v) for v in obs.values()
                             if hasattr(v, "flat"))
                else:
                    nf = _has_nonfinite(obs)
                if nf or not math.isfinite(float(reward)):
                    nan_ok = False
                    nan_fail_ep = ep
                all_rewards.append(float(reward))
                done = terminated or truncated
                steps += 1
            env.close()
        except Exception as ex:
            record("multi_episode_nan_sweep", "runtime_allowed", "failed",
                   "no NaN/Inf in obs or reward over 5 episodes",
                   f"exception at episode {ep}: {type(ex).__name__}: {ex}",
                   fix="fix env construction or adapter for repeated episodes")
            return
    record("multi_episode_nan_sweep", "runtime_allowed",
           "passed" if nan_ok else "failed",
           "no NaN/Inf in obs or reward over 5 episodes",
           "clean" if nan_ok else f"NaN/Inf at episode {nan_fail_ep}",
           fix=None if nan_ok else "trace NaN source; guard with np.nan_to_num only as last resort")
    if all_rewards:
        lo, hi = min(all_rewards), max(all_rewards)
        # `observed_reward_bounds` is a measured FLOOR on the true reward range
        # (contract: "a floor on the true range, never a proof of it"). The
        # verifier samples a DIFFERENT action stream than extraction did, so it
        # legitimately discovers wider values -- MiniGrid's goal reward only
        # appears in streams that actually reach the goal. Penalising that would
        # contradict the declared semantics.
        #
        # So this check catches the two things that are genuinely wrong:
        #   1. a spec claiming bounds WIDER than anything ever measured
        #      (inventing numbers instead of extracting them), and
        #   2. violation of a non-null hard `reward_range` declared by the env.
        problems = []
        if obs_lo is not None and obs_hi is not None:
            if obs_lo > lo and obs_hi < hi:
                pass  # floor narrower than observed: expected, not a defect
            if obs_lo < lo and obs_hi > hi:
                problems.append(
                    f"declared floor [{obs_lo}, {obs_hi}] is wider than anything "
                    f"observed [{lo:.4f}, {hi:.4f}] -- bounds look invented, "
                    "not measured")
        hard = spec.get("reward_range") or [None, None]
        hard_lo, hard_hi = (list(hard) + [None, None])[:2]
        if hard_lo is not None and lo < hard_lo:
            problems.append(f"reward {lo:.4f} below declared reward_range low {hard_lo}")
        if hard_hi is not None and hi > hard_hi:
            problems.append(f"reward {hi:.4f} above declared reward_range high {hard_hi}")
        widened = (obs_lo is not None and lo < obs_lo) or (obs_hi is not None and hi > obs_hi)
        observed_txt = (f"observed [{lo:.4f}, {hi:.4f}] over {n_episodes} full "
                        f"episodes ({len(all_rewards)} steps)"
                        + ("; wider than the declared floor, which is allowed "
                           "(different action stream)" if widened else ""))
        record("reward_bounds_observed", "runtime_allowed",
               "passed" if not problems else "failed",
               "observed rewards consistent with the declared floor "
               f"{declared_bounds} and any hard reward_range {hard}",
               observed_txt if not problems else "; ".join(problems),
               fix="re-measure observed_reward_bounds in extract_spec.py from a "
                   "live rollout instead of declaring them" if problems else None)

    # construct_close_leak_cycle
    try:
        for _ in range(10):
            e = adapter.make_env(config)
            e.reset(seed=seed)
            e.close()
        record("construct_close_leak_cycle", "runtime_allowed", "passed",
               "10 construct/reset/close cycles succeed without error", "ok")
    except Exception as ex:
        record("construct_close_leak_cycle", "runtime_allowed", "failed",
               "10 construct/reset/close cycles succeed without error",
               f"{type(ex).__name__}: {ex}",
               fix="ensure close() is idempotent and releases all resources")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True,
                        help="runs/<task-id> directory containing artifacts/integration/")
    parser.add_argument("--boundary",
                        choices=["generate_only", "dry_run", "runtime_allowed"],
                        default="dry_run")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    integration_dir = run_dir / "artifacts" / "integration"
    report_path = run_dir / "verification_report.json"

    print(f"verifying {run_dir.name} at boundary={args.boundary}")
    check_files_exist(integration_dir)
    spec = check_spec_parses(integration_dir)

    if args.boundary in ("dry_run", "runtime_allowed") and spec is not None:
        adapter = load_adapter(integration_dir)
        if adapter is not None:
            dry_run_checks(adapter, spec)
            if args.boundary == "runtime_allowed":
                runtime_allowed_checks(adapter, spec)

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
