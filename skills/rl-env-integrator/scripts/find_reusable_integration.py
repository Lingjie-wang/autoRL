#!/usr/bin/env python3
"""Find and link verified AutoRL environment integrations.

The finder is deliberately conservative: a candidate must have complete
artifacts, a passing verification report, matching requested metadata, and no
artifact newer than that report.  Custom environment requests may additionally
require byte-identical source files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = (
    "adapter.py",
    "env_config.json",
    "env_spec.json",
    "extract_spec.py",
    "smoke_rollout.py",
)
BOUNDARY_RANK = {"generate_only": 0, "dry_run": 1, "runtime_allowed": 2}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_subset(expected: Any, observed: Any) -> bool:
    """Return whether expected is a recursive subset of observed."""
    if isinstance(expected, dict):
        return isinstance(observed, dict) and all(
            key in observed and is_subset(value, observed[key])
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return expected == observed
    return expected == observed


def verification_status(report: dict[str, Any]) -> str:
    return str(report.get("overall_status", report.get("status", ""))).lower()


def inspect_candidate(
    run_dir: Path,
    *,
    env_id: str,
    source_type: str | None,
    api_convention: str | None,
    training_channel: str | None,
    config_constraints: dict[str, Any],
    source_hashes: list[str],
    required_boundary: str,
) -> dict[str, Any]:
    artifact_root = run_dir / "artifacts" / "integration"
    report_path = run_dir / "verification_report.json"
    reasons: list[str] = []

    missing = [name for name in REQUIRED_ARTIFACTS if not (artifact_root / name).is_file()]
    if missing:
        reasons.append("missing_artifacts:" + ",".join(missing))
    if not report_path.is_file():
        reasons.append("missing_verification_report")
    if reasons:
        return {"run": str(run_dir), "eligible": False, "reasons": reasons}

    try:
        config = load_json(artifact_root / "env_config.json")
        spec = load_json(artifact_root / "env_spec.json")
        report = load_json(report_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "run": str(run_dir),
            "eligible": False,
            "reasons": [f"invalid_json:{exc}"],
        }

    if config.get("env_id") != env_id or spec.get("env_id") != env_id:
        reasons.append("env_id_mismatch")
    if source_type and (
        config.get("source_type") != source_type or spec.get("source_type") != source_type
    ):
        reasons.append("source_type_mismatch")
    if api_convention and spec.get("api_convention") != api_convention:
        reasons.append("api_convention_mismatch")
    if training_channel and spec.get("training_channel") != training_channel:
        reasons.append("training_channel_mismatch")
    if config_constraints and not is_subset(config_constraints, config):
        reasons.append("config_constraints_mismatch")
    if verification_status(report) != "passed":
        reasons.append("verification_not_passed")

    artifact_files = [
        path
        for path in artifact_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]
    artifact_mtime = max(path.stat().st_mtime for path in artifact_files)
    if artifact_mtime > report_path.stat().st_mtime + 1e-6:
        reasons.append("verification_stale_artifacts_newer_than_report")

    if source_hashes:
        candidate_hashes = {
            sha256_file(path)
            for path in artifact_root.rglob("*")
            if path.is_file()
            and path.name not in REQUIRED_ARTIFACTS
            and "__pycache__" not in path.parts
        }
        if not all(source_hash in candidate_hashes for source_hash in source_hashes):
            reasons.append("source_hash_mismatch")

    observed_boundary = str(report.get("verified_at_boundary", "generate_only"))
    if observed_boundary not in BOUNDARY_RANK:
        reasons.append("unknown_verification_boundary")
        observed_boundary = "generate_only"
    verification_required = (
        BOUNDARY_RANK[observed_boundary] < BOUNDARY_RANK[required_boundary]
    )

    return {
        "run": str(run_dir),
        "artifact_root": str(artifact_root),
        "eligible": not reasons,
        "reasons": reasons,
        "env_id": spec.get("env_id"),
        "source_type": spec.get("source_type"),
        "api_convention": spec.get("api_convention"),
        "training_channel": spec.get("training_channel"),
        "verified_at_boundary": observed_boundary,
        "required_boundary": required_boundary,
        "verification_required": verification_required,
        "verification_report": str(report_path),
        "verification_mtime_ns": report_path.stat().st_mtime_ns,
    }


def write_json(path: Path | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def command_find(args: argparse.Namespace) -> int:
    if args.policy == "disabled":
        write_json(
            args.output,
            {"schema_version": 1, "policy": "disabled", "status": "disabled", "candidates": []},
        )
        return 0

    runs_dir = args.runs_dir.resolve()
    config_constraints = load_json(args.config_constraints) if args.config_constraints else {}
    source_hashes = [sha256_file(path.resolve()) for path in args.source_file]
    excluded = args.exclude_run.resolve() if args.exclude_run else None
    candidates: list[dict[str, Any]] = []

    if runs_dir.is_dir():
        for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
            if excluded and run_dir.resolve() == excluded:
                continue
            if (run_dir / "environment_reuse.json").exists():
                continue
            try:
                peek_config = load_json(run_dir / "artifacts" / "integration" / "env_config.json")
                peek_spec = load_json(run_dir / "artifacts" / "integration" / "env_spec.json")
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if peek_config.get("env_id") != args.env_id and peek_spec.get("env_id") != args.env_id:
                continue
            candidate = inspect_candidate(
                run_dir,
                env_id=args.env_id,
                source_type=args.source_type,
                api_convention=args.api_convention,
                training_channel=args.training_channel,
                config_constraints=config_constraints,
                source_hashes=source_hashes,
                required_boundary=args.required_boundary,
            )
            candidates.append(candidate)

    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    eligible.sort(
        key=lambda candidate: (
            not candidate["verification_required"],
            BOUNDARY_RANK[candidate["verified_at_boundary"]],
            candidate["verification_mtime_ns"],
        ),
        reverse=True,
    )
    selected = eligible[0] if eligible else None
    if selected:
        status = "reusable_needs_verification" if selected["verification_required"] else "reusable"
    else:
        status = "not_found"

    for candidate in candidates:
        candidate.pop("verification_mtime_ns", None)
    if selected:
        selected.pop("verification_mtime_ns", None)
    write_json(
        args.output,
        {
            "schema_version": 1,
            "policy": args.policy,
            "status": status,
            "query": {
                "env_id": args.env_id,
                "source_type": args.source_type,
                "api_convention": args.api_convention,
                "training_channel": args.training_channel,
                "required_boundary": args.required_boundary,
                "config_constraints": config_constraints,
                "source_sha256": source_hashes,
            },
            "selected": selected,
            "candidates": candidates,
        },
    )
    return 0


def command_link(args: argparse.Namespace) -> int:
    source_run = args.source_run.resolve()
    target_run = args.target_run.resolve()
    if source_run == target_run:
        raise SystemExit("source and target run must differ")

    spec = load_json(source_run / "artifacts" / "integration" / "env_spec.json")
    candidate = inspect_candidate(
        source_run,
        env_id=str(spec["env_id"]),
        source_type=str(spec.get("source_type")) if spec.get("source_type") else None,
        api_convention=str(spec.get("api_convention")) if spec.get("api_convention") else None,
        training_channel=str(spec.get("training_channel")) if spec.get("training_channel") else None,
        config_constraints={},
        source_hashes=[],
        required_boundary=args.required_boundary,
    )
    if not candidate["eligible"]:
        raise SystemExit("source run is not reusable: " + ", ".join(candidate["reasons"]))

    source_artifacts = source_run / "artifacts" / "integration"
    target_artifacts_dir = target_run / "artifacts"
    target_link = target_artifacts_dir / "integration"
    target_run.mkdir(parents=True, exist_ok=True)
    target_artifacts_dir.mkdir(parents=True, exist_ok=True)
    relative_target = os.path.relpath(source_artifacts, target_artifacts_dir)
    if target_link.is_symlink():
        if os.path.realpath(target_link) != str(source_artifacts):
            raise SystemExit(f"existing integration link points elsewhere: {target_link}")
    elif target_link.exists():
        raise SystemExit(f"target integration path already exists: {target_link}")
    else:
        target_link.symlink_to(relative_target, target_is_directory=True)

    artifact_hashes = {
        str(path.relative_to(source_artifacts)): sha256_file(path)
        for path in sorted(source_artifacts.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    receipt = {
        "schema_version": 1,
        "mode": "reused",
        "source_run": os.path.relpath(source_run, Path.cwd()),
        "source_artifact_root": os.path.relpath(source_artifacts, Path.cwd()),
        "env_id": candidate["env_id"],
        "source_type": candidate["source_type"],
        "api_convention": candidate["api_convention"],
        "training_channel": candidate["training_channel"],
        "artifact_sha256": artifact_hashes,
        "source_verification_report": os.path.relpath(
            source_run / "verification_report.json", Path.cwd()
        ),
        "source_verified_at_boundary": candidate["verified_at_boundary"],
        "required_boundary": args.required_boundary,
        "verification_required": candidate["verification_required"],
        "immutability": "source run is referenced read-only; do not edit through the symlink",
    }
    write_json(target_run / "environment_reuse.json", receipt)
    write_json(args.output, {"status": "linked", "receipt": receipt})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    find_parser = subparsers.add_parser("find", help="find a compatible verified integration")
    find_parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    find_parser.add_argument("--env-id", required=True)
    find_parser.add_argument("--source-type")
    find_parser.add_argument("--api-convention")
    find_parser.add_argument("--training-channel")
    find_parser.add_argument(
        "--required-boundary", choices=tuple(BOUNDARY_RANK), default="generate_only"
    )
    find_parser.add_argument("--config-constraints", type=Path)
    find_parser.add_argument("--source-file", type=Path, action="append", default=[])
    find_parser.add_argument("--exclude-run", type=Path)
    find_parser.add_argument("--policy", choices=("prefer_verified", "disabled"), default="prefer_verified")
    find_parser.add_argument("--output", type=Path)
    find_parser.set_defaults(handler=command_find)

    link_parser = subparsers.add_parser("link", help="reference a reusable integration from a new run")
    link_parser.add_argument("--source-run", type=Path, required=True)
    link_parser.add_argument("--target-run", type=Path, required=True)
    link_parser.add_argument(
        "--required-boundary", choices=tuple(BOUNDARY_RANK), default="generate_only"
    )
    link_parser.add_argument("--output", type=Path)
    link_parser.set_defaults(handler=command_link)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
