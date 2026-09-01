import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "rl-env-integrator" / "scripts" / "find_reusable_integration.py"
REQUIRED = ("adapter.py", "env_config.json", "env_spec.json", "extract_spec.py", "smoke_rollout.py")


class ReuseIntegrationTests(unittest.TestCase):
    def make_run(self, root: Path, *, status="passed", boundary="runtime_allowed") -> tuple[Path, Path]:
        run = root / "runs" / "source-run"
        artifacts = run / "artifacts" / "integration"
        artifacts.mkdir(parents=True)
        for name in REQUIRED:
            (artifacts / name).write_text("# fixture\n", encoding="utf-8")
        (artifacts / "env_config.json").write_text(
            json.dumps({"env_id": "Demo-v0", "source_type": "custom_env", "size": 4}),
            encoding="utf-8",
        )
        (artifacts / "env_spec.json").write_text(
            json.dumps(
                {
                    "env_id": "Demo-v0",
                    "source_type": "custom_env",
                    "api_convention": "gymnasium",
                    "training_channel": "native",
                }
            ),
            encoding="utf-8",
        )
        source = root / "env_code.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        (artifacts / "demo_env.py").write_bytes(source.read_bytes())
        report = run / "verification_report.json"
        report.write_text(
            json.dumps({"overall_status": status, "verified_at_boundary": boundary}),
            encoding="utf-8",
        )
        newest_artifact = max(path.stat().st_mtime for path in artifacts.iterdir())
        os.utime(report, (newest_artifact + 2, newest_artifact + 2))
        return run, source

    def run_cli(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_finds_verified_matching_custom_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, source = self.make_run(root)
            result = self.run_cli(
                "find",
                "--runs-dir", str(root / "runs"),
                "--env-id", "Demo-v0",
                "--source-type", "custom_env",
                "--api-convention", "gymnasium",
                "--source-file", str(source),
                "--required-boundary", "dry_run",
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "reusable")
            self.assertEqual(Path(payload["selected"]["run"]), run)

    def test_rejects_source_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, source = self.make_run(root)
            source.write_text("VALUE = 2\n", encoding="utf-8")
            result = self.run_cli(
                "find", "--runs-dir", str(root / "runs"), "--env-id", "Demo-v0",
                "--source-file", str(source), cwd=root,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "not_found")
            self.assertIn("source_hash_mismatch", payload["candidates"][0]["reasons"])

    def test_rejects_config_constraint_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_run(root)
            constraints = root / "constraints.json"
            constraints.write_text(json.dumps({"size": 8}), encoding="utf-8")
            result = self.run_cli(
                "find", "--runs-dir", str(root / "runs"), "--env-id", "Demo-v0",
                "--config-constraints", str(constraints), cwd=root,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "not_found")
            self.assertIn("config_constraints_mismatch", payload["candidates"][0]["reasons"])

    def test_disabled_policy_does_not_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_cli(
                "find", "--runs-dir", str(root / "missing"), "--env-id", "Demo-v0",
                "--policy", "disabled", cwd=root,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "disabled")
            self.assertEqual(payload["candidates"], [])

    def test_rejects_failed_or_stale_verification(self):
        for failure_mode in ("failed", "stale"):
            with self.subTest(failure_mode=failure_mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run, _ = self.make_run(root, status="failed" if failure_mode == "failed" else "passed")
                if failure_mode == "stale":
                    adapter = run / "artifacts" / "integration" / "adapter.py"
                    report_mtime = (run / "verification_report.json").stat().st_mtime
                    os.utime(adapter, (report_mtime + 2, report_mtime + 2))
                result = self.run_cli(
                    "find", "--runs-dir", str(root / "runs"), "--env-id", "Demo-v0", cwd=root,
                )
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "not_found")
                reason = (
                    "verification_not_passed"
                    if failure_mode == "failed"
                    else "verification_stale_artifacts_newer_than_report"
                )
                self.assertIn(reason, payload["candidates"][0]["reasons"])

    def test_links_without_copying_and_marks_reverification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_run, _ = self.make_run(root, boundary="generate_only")
            target_run = root / "runs" / "new-run"
            result = self.run_cli(
                "link",
                "--source-run", str(source_run),
                "--target-run", str(target_run),
                "--required-boundary", "dry_run",
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            link = target_run / "artifacts" / "integration"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (source_run / "artifacts" / "integration").resolve())
            receipt = json.loads((target_run / "environment_reuse.json").read_text())
            self.assertTrue(receipt["verification_required"])
            self.assertIn("demo_env.py", receipt["artifact_sha256"])


if __name__ == "__main__":
    unittest.main()
