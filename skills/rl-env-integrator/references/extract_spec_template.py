"""Template for extract_spec.py — copy to artifacts/integration/ and fill in.

Contract rule: every spec field must be derived from the LIVE environment, never
hand-copied from documentation. Docs lie; runtime does not.

Usage after filling in:
    python extract_spec.py

This template covers the full field set required by the verifier:
  - the 8 core fields (env_id, source_type, api_convention, spaces, etc.)
  - the 6 single-agent descriptor fields (observation_modality, action_type, ...)
See references/env-adapter-contract.md for the full schema.
"""

import json
import math
from pathlib import Path

# adapter.py must be in the same directory. Every consumer (spec extraction,
# smoke, verification, training) constructs through make_env to avoid drift.
from adapter import load_config, make_env

OUT = Path(__file__).parent / "env_spec.json"


# ── helpers ──────────────────────────────────────────────────────────────────

def describe_space(space):
    """Extract shape / dtype / n from a Gymnasium space at runtime."""
    d = {"repr": repr(space)}
    if hasattr(space, "shape") and space.shape is not None:
        d["shape"] = list(space.shape)
    if hasattr(space, "dtype") and space.dtype is not None:
        d["dtype"] = str(space.dtype)
    if hasattr(space, "n"):           # Discrete
        d["n"] = int(space.n)
    if hasattr(space, "spaces"):      # Dict
        d["spaces"] = {k: describe_space(v) for k, v in space.spaces.items()}
    return d


def measure_reward_bounds(env, config, n_episodes=10, step_cap=10_000):
    """Sample reward bounds over n_episodes FULL episodes.

    n_episodes must be >= the verifier's sweep (currently 5) so the declared
    floor is genuine. extraction and verification sample different action
    streams, so n=10 provides margin. See known-pitfalls.md:
    "observed_reward_bounds is a floor, not a range".
    """
    rewards = []
    for ep in range(n_episodes):
        obs, _ = env.reset(seed=config.get("default_seed", 0) + ep)
        env.action_space.seed(config.get("default_seed", 0) + ep)
        done, steps = False, 0
        while not done and steps < step_cap:
            obs, r, terminated, truncated, _ = env.step(env.action_space.sample())
            rewards.append(float(r))
            done = terminated or truncated
            steps += 1
    return [min(rewards), max(rewards)]


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    config = load_config()
    env = make_env(config)
    try:
        # ── 1. measure bounds before building the spec ─────────────────────
        # Use a step cap appropriate for your environment. ALE and MiniGrid
        # report spec.max_episode_steps = None and truncate internally — do NOT
        # rely on that attribute for the cap. See known-pitfalls.md.
        bounds = measure_reward_bounds(env, config,
                                       n_episodes=10,
                                       step_cap=config.get("episode_step_cap",
                                                           10_000))

        # ── 2. fill in the spec ────────────────────────────────────────────
        spec = {
            # ── core fields ────────────────────────────────────────────────
            "env_id": config["env_id"],
            "source_type": config["source_type"],   # official_benchmark | custom_env | external_simulator
            "api_convention": "gymnasium",

            # These two come from the live env object — never from docs.
            "observation_space": describe_space(env.observation_space),
            "action_space": describe_space(env.action_space),

            "reward_range": list(getattr(env, "reward_range", (None, None))),

            # Document how episodes end. Fill both fields; if one never fires,
            # say so explicitly (e.g. "never" for HalfCheetah terminated).
            "episode_termination": {
                "terminated": "TODO: what natural condition ends the task?",
                "truncated_at_steps": env.spec.max_episode_steps,
                # If spec.max_episode_steps is None, add:
                # "effective_step_limit": env.unwrapped.max_steps,  (MiniGrid)
                # or compute from ale kwargs:
                # "effective_step_limit_with_frameskip": frames // skip,  (ALE)
            },

            "deterministic_under_seed": True,  # change to False + document if not
            "dependencies": config["dependencies"],

            # ── single-agent descriptor fields (ALL required by verifier) ──
            #
            # observation_modality: what shape / type does obs have?
            #   "vector"  — flat ndarray (CartPole, HalfCheetah, LunarLander)
            #   "image"   — uint8 pixel array (Atari)
            #   "dict"    — gymnasium Dict space (MiniGrid, FetchReach)
            #   "hybrid"  — Dict mixing image and vector leaves
            "observation_modality": "TODO: vector | image | dict | hybrid",

            # action_type: what kind is the action space?
            #   "discrete"        — Discrete(n)
            #   "continuous"      — Box
            #   "multi_discrete"  — MultiDiscrete
            #   "multi_binary"    — MultiBinary
            "action_type": "TODO: discrete | continuous | multi_discrete | multi_binary",

            # goal_conditioned: does the observation contain an explicit goal
            # that changes episode-to-episode (e.g. FetchReach desired_goal)?
            "goal_conditioned": False,

            # randomness_sources: list every source that can affect trajectories.
            # Include sources that survive seeding (ALE sticky actions).
            # "deterministic_under_seed: True" does NOT mean no randomness —
            # it means the randomness is reproduced by the seed.
            "randomness_sources": [
                "TODO: initial state sampling",
                # "sticky actions p=0.25 (reproducible under seed)",  # Atari
                # "Gaussian noise on ...",                            # custom envs
            ],

            # observed_reward_bounds: MEASURED floor, not the documented range.
            # This will be wider than the hard reward_range for most envs.
            # The verifier checks that you did not invent numbers wider than
            # anything you actually measured.
            "observed_reward_bounds": bounds,

            # training_channel: what does the trainer actually receive?
            # The raw env, or a wrapper that transforms it?
            #   "native"               — env reaches the trainer unchanged
            #   "sb3_atari_wrapper"    — AtariWrapper + VecFrameStack
            #   "sb3_imgobs_wrapper"   — ImgObsWrapper (drops non-image keys)
            #   "sb3_flatobs_wrapper"  — FlatObsWrapper (MiniGrid)
            #   "sb3_multiinput"       — MultiInputPolicy over Dict
            #   (add your own as needed)
            "training_channel": "native",

            # lossy_notes: document what the channel drops or transforms.
            # This is the single-agent analogue of the EPyMARL channel-lossiness
            # table. An empty list is fine for native channels.
            "lossy_notes": [
                # "AtariWrapper: RGB->grayscale, resize to 84x84, rewards clipped to {-1,0,+1}",
                # "ImgObsWrapper: drops 'direction' and 'mission' from Dict obs",
            ],

            # notes: any other quirks worth recording (optional but encouraged)
            "notes": "",
        }

    finally:
        env.close()

    # Normalise the repr of spaces that embed memory addresses (e.g. MiniGrid's
    # MissionSpace). The verifier does the same normalisation, so this is for
    # human readability rather than correctness — the verifier does NOT compare
    # the repr in the JSON file, it compares against the live env.
    # (Nothing to do here; the verifier handles it.)

    OUT.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(json.dumps(spec, indent=2))


if __name__ == "__main__":
    main()
