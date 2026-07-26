"""Independent verifier for EPyMARL MultiAgentEnv integrations.

Third verifier in the family, per the "EPyMARL MultiAgentEnv Convention"
section of references/env-adapter-contract.md. Dispatch rule: use this when
env_spec.json declares api_convention == "epymarl_multiagentenv".

Unlike the gymnasium/pettingzoo verifiers, this checks a PULL-style surface:
get_env_info() is the trainer's contract, so every shape it advertises must
match what the getters actually return. It also verifies the DECLARED
lossiness of the training channel (global_state.source, action_mask.source)
against observed behavior — EPyMARL's generic wrappers degrade silently.

Usage:
    python verify_epymarl_env_template.py --run-dir runs/<task-id> --boundary dry_run
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

DELIVERABLES = ["adapter.py", "env_config.json", "env_spec.json",
                "extract_spec.py", "smoke_rollout.py"]
SPEC_REQUIRED_FIELDS = ["env_id", "source_type", "api_convention", "env_info",
                        "global_state", "reward_structure", "action_mask",
                        "training_channel", "deterministic_under_seed",
                        "dependencies"]
ENV_INFO_KEYS = ["state_shape", "obs_shape", "n_actions", "n_agents",
                 "episode_limit"]
REQUIRED_METHODS = ["step", "reset", "get_obs", "get_obs_size", "get_state",
                    "get_state_size", "get_avail_actions",
                    "get_avail_agent_actions", "get_total_actions",
                    "get_env_info", "close"]

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


def flatdim(x):
    return int(np.asarray(x).size)


# ---------- generate_only tier ----------

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
           "epymarl spec fields present",
           "all present" if not missing else f"missing: {missing}",
           fix=f"add fields {missing} to extract_spec.py")
    if spec.get("api_convention") != "epymarl_multiagentenv":
        record("api_convention", "generate_only", "failed",
               "epymarl_multiagentenv", str(spec.get("api_convention")),
               fix="use the gymnasium or pettingzoo verifier for this spec")
        return None
    missing_info = [k for k in ENV_INFO_KEYS if k not in spec.get("env_info", {})]
    record("env_info_fields", "generate_only",
           "passed" if not missing_info else "failed",
           f"env_info has {ENV_INFO_KEYS}",
           "all present" if not missing_info else f"missing: {missing_info}",
           fix="emit the full get_env_info() dict in extract_spec.py")
    return spec


def load_adapter(integration_dir):
    sys.path.insert(0, str(integration_dir))
    try:
        import adapter
        record("adapter_imports", "dry_run", "passed", "import succeeds", "ok")
        return adapter
    except Exception as e:
        record("adapter_imports", "dry_run", "failed", "import succeeds",
               f"{type(e).__name__}: {e}",
               fix="fix imports/dependencies; import smac and smacv2 lazily, "
                   "never together (PySC2 DuplicateMapError)")
        return None


# ---------- dry_run tier ----------

def check_surface(env):
    missing = [m for m in REQUIRED_METHODS if not callable(getattr(env, m, None))]
    return record("multiagentenv_surface", "dry_run",
                  "passed" if not missing else "failed",
                  f"callable: {REQUIRED_METHODS}",
                  "all present" if not missing else f"missing/not callable: {missing}",
                  fix=f"implement {missing} on the adapter")


def check_env_info_consistency(env, spec):
    info = env.get_env_info()
    declared = spec["env_info"]
    drift = {k: (declared.get(k), info.get(k))
             for k in ENV_INFO_KEYS if declared.get(k) != info.get(k)}
    record("env_info_matches_declared", "dry_run",
           "passed" if not drift else "failed",
           json.dumps({k: declared.get(k) for k in ENV_INFO_KEYS}),
           "identical" if not drift else f"declared vs runtime: {drift}",
           fix="re-run extract_spec.py or fix adapter construction drift")
    return info


def check_shapes_self_consistent(env, info):
    obs = env.get_obs()
    state = env.get_state()
    n_agents, obs_shape = info["n_agents"], info["obs_shape"]
    state_shape, n_actions = info["state_shape"], info["n_actions"]

    record("obs_matches_env_info", "dry_run",
           "passed" if len(obs) == n_agents
           and all(flatdim(o) == obs_shape for o in obs) else "failed",
           f"get_obs() -> {n_agents} entries of flat size {obs_shape}",
           f"{len(obs)} entries, sizes {[flatdim(o) for o in obs]}",
           fix="fix get_obs()/get_obs_size() or the declared env_info")

    record("state_matches_env_info", "dry_run",
           "passed" if flatdim(state) == state_shape else "failed",
           f"get_state() flat size {state_shape}",
           f"flat size {flatdim(state)}",
           fix="fix get_state()/get_state_size() or the declared env_info")

    avail = env.get_avail_actions()
    lens_ok = (len(avail) == n_agents
               and all(len(a) == n_actions for a in avail))
    record("avail_actions_matches_env_info", "dry_run",
           "passed" if lens_ok else "failed",
           f"get_avail_actions() -> {n_agents} masks of length {n_actions}",
           f"{len(avail)} masks, lengths {[len(a) for a in avail]}",
           fix="fix get_avail_actions() or the declared n_actions")

    has_legal = all(int(np.sum(a)) > 0 for a in avail)
    record("every_agent_has_legal_action", "dry_run",
           "passed" if has_legal else "failed",
           "each agent has >= 1 legal action after reset",
           "all agents have legal actions" if has_legal
           else f"legal counts: {[int(np.sum(a)) for a in avail]}",
           fix="fix mask computation; a fully-masked agent deadlocks the runner")
    return avail


def check_declared_lossiness(env, spec, avail, info):
    """Declared channel lossiness must match observed behavior."""
    mask_src = spec["action_mask"].get("source", "none")
    all_legal = all(int(np.sum(a)) == info["n_actions"] for a in avail)
    if mask_src == "native":
        ok = not all_legal
        observed = ("masks constrain actions" if ok else
                    "every action legal for every agent — looks like padding, not native masks")
    elif mask_src in ("all_legal_padding", "none"):
        ok = True
        observed = f"declared lossy ({mask_src}); all_legal={all_legal}"
    else:
        ok, observed = False, f"unknown source {mask_src!r}"
    record("action_mask_source_honest", "dry_run",
           "passed" if ok else "failed",
           f"action_mask.source={mask_src}", observed,
           fix="set action_mask.source to all_legal_padding when the channel "
               "drops masks, or wire native masks through")

    state_src = spec["global_state"].get("source", "none")
    state = np.asarray(env.get_state()).reshape(-1)
    concat = np.concatenate([np.asarray(o).reshape(-1) for o in env.get_obs()])
    looks_concat = (state.size == concat.size
                    and np.allclose(state.astype(np.float64),
                                    concat.astype(np.float64)))
    if state_src == "native":
        ok = not looks_concat
        observed = ("state differs from concatenated obs" if ok else
                    "state is byte-identical to concatenated obs — that is obs_concat, not native")
    elif state_src == "obs_concat":
        ok = looks_concat
        observed = ("state equals concatenated obs, as declared" if ok else
                    f"declared obs_concat but state (size {state.size}) != concat (size {concat.size})")
    else:
        ok, observed = False, f"unknown source {state_src!r}"
    record("global_state_source_honest", "dry_run",
           "passed" if ok else "failed",
           f"global_state.source={state_src}", observed,
           fix="correct global_state.source in extract_spec.py to match reality")

    declared_size = spec["global_state"].get("shape")
    getter_size = flatdim(np.zeros(env.get_state_size())) if isinstance(
        env.get_state_size(), int) else flatdim(env.get_state_size())
    size_ok = (list(declared_size or []) == [int(state.size)]
               and getter_size == int(state.size))
    record("state_size_getter_agrees", "dry_run",
           "passed" if size_ok else "failed",
           f"global_state.shape={declared_size} == get_state_size() == len(get_state())",
           f"declared {declared_size}, get_state_size()={env.get_state_size()}, actual len {int(state.size)}",
           fix="reconcile get_state_size() with the actual get_state() length "
               "(gymma prefers env.state_size while returning concatenated obs)")


def sample_legal(env, n_agents, rng):
    acts = []
    for i in range(n_agents):
        mask = np.asarray(env.get_avail_agent_actions(i))
        legal = np.nonzero(mask)[0]
        acts.append(int(rng.choice(list(legal))) if legal.size else 0)
    return acts


def check_episode(env, info, rng):
    limit = info["episode_limit"]
    n_agents = info["n_agents"]
    steps, ended, step_ok = 0, False, True
    while steps <= limit + 5:
        out = env.step(sample_legal(env, n_agents, rng))
        if len(out) == 5:
            _, reward, terminated, truncated, _ = out
        elif len(out) == 3:  # original PyMARL signature
            reward, terminated, _ = out
            truncated = False
        else:
            step_ok = False
            break
        rewards = reward if isinstance(reward, (list, tuple, np.ndarray)) else [reward]
        if not all(math.isfinite(float(r)) for r in np.asarray(rewards).reshape(-1)):
            step_ok = False
        steps += 1
        if bool(terminated) or bool(truncated):
            ended = True
            break
    record("step_returns_finite_reward", "dry_run",
           "passed" if step_ok else "failed",
           "every step returns finite reward(s) and a known tuple arity",
           f"clean for {steps} steps" if step_ok else f"violation at step {steps}",
           fix="fix adapter step() return values / tuple arity")
    record("episode_terminates_within_limit", "dry_run",
           "passed" if ended and steps <= limit else "failed",
           f"episode ends within episode_limit={limit}",
           f"ended at step {steps}" if ended else f"no end after {steps} steps",
           fix="wire terminated/truncated, or correct the declared episode_limit")


def rollout_signature(adapter, config, seed, limit):
    env = adapter.make_env(config, seed=seed)
    try:
        env.reset(seed=seed) if _reset_takes_seed(env) else env.reset()
        info = env.get_env_info()
        rng = random.Random(seed)
        sig = [np.asarray(env.get_state()).reshape(-1).tobytes()]
        for _ in range(min(20, limit)):
            out = env.step(sample_legal(env, info["n_agents"], rng))
            terminated = bool(out[2]) if len(out) == 5 else bool(out[1])
            truncated = bool(out[3]) if len(out) == 5 else False
            sig.append((np.asarray(env.get_state()).reshape(-1).tobytes(),
                        terminated, truncated))
            if terminated or truncated:
                break
        return sig
    finally:
        env.close()


def _reset_takes_seed(env):
    import inspect
    try:
        return "seed" in inspect.signature(env.reset).parameters
    except (TypeError, ValueError):
        return False


def check_determinism(adapter, config, spec, limit):
    if not spec.get("deterministic_under_seed"):
        record("seed_determinism", "dry_run", "skipped",
               "spec declares deterministic_under_seed=false", "not checked")
        return
    seed = config.get("default_seed", 0)
    try:
        same = (rollout_signature(adapter, config, seed, limit)
                == rollout_signature(adapter, config, seed, limit))
    except Exception as e:
        record("seed_determinism", "dry_run", "failed",
               "two identical seeded rollouts comparable",
               f"{type(e).__name__}: {e}", fix="make repeated construction safe")
        return
    record("seed_determinism", "dry_run", "passed" if same else "failed",
           "identical state trajectory for identical seed and legal actions",
           "trajectories identical" if same else "trajectories diverged",
           fix="thread the seed into every randomness source, or declare "
               "deterministic_under_seed=false with a documented reason")


def check_close_safe(adapter, config):
    try:
        e = adapter.make_env(config, seed=config.get("default_seed", 0))
        e.close()
        e.close()  # double close must be safe
        record("close_safe", "dry_run", "passed",
               "construct/close cycles and double close are safe", "ok")
    except Exception as e:
        record("close_safe", "dry_run", "failed",
               "construct/close cycles and double close are safe",
               f"{type(e).__name__}: {e}",
               fix="guard close() for repeated calls; simulator-backed envs "
                   "must reap their child process")


def dry_run_checks(adapter, spec):
    config = adapter.load_config()
    seed = config.get("default_seed", 0)
    rng = random.Random(seed)

    try:
        env = adapter.make_env(config, seed=seed)
        record("env_constructs", "dry_run", "passed", "make_env succeeds", "ok")
    except Exception as e:
        record("env_constructs", "dry_run", "failed", "make_env succeeds",
               f"{type(e).__name__}: {e}",
               fix="fix construction path, env_config.json, or SC2PATH")
        return

    limit = spec["env_info"]["episode_limit"]
    try:
        check_surface(env)
        info = check_env_info_consistency(env, spec)
        env.reset(seed=seed) if _reset_takes_seed(env) else env.reset()
        avail = check_shapes_self_consistent(env, info)
        check_declared_lossiness(env, spec, avail, info)
        check_episode(env, info, rng)
        limit = info["episode_limit"]
    finally:
        env.close()

    check_determinism(adapter, config, spec, limit)
    check_close_safe(adapter, config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--boundary", choices=["generate_only", "dry_run"],
                        default="dry_run")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    integration_dir = run_dir / "artifacts" / "integration"
    report_path = run_dir / "verification_report.json"

    print(f"verifying {run_dir.name} (epymarl_multiagentenv) at boundary={args.boundary}")
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
        "api_convention": "epymarl_multiagentenv",
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
