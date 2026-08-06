from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


import scripts.release_acceptance as release_acceptance


class ReleaseAcceptanceDiagnosticsTest(unittest.TestCase):
    def test_fixed_environment_uses_isolated_matplotlib_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "mpl"
            env = release_acceptance.fixed_env(cache)
            self.assertEqual(env["MPLCONFIGDIR"], str(cache))
            self.assertTrue(cache.is_dir())
            self.assertEqual(env["MPLBACKEND"], "Agg")

    def test_failed_step_retains_stdout_and_stderr(self):
        result = release_acceptance.run_step(
            "demo",
            [
                sys.executable,
                "-c",
                "import sys; print('missing: demo'); print('detail', file=sys.stderr); sys.exit(2)",
            ],
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["returncode"], 2)
        self.assertEqual(result["stdout"], "missing: demo")
        self.assertEqual(result["stderr"], "detail")

    def test_environment_failure_exposes_missing_dependencies(self):
        result = {
            "name": "environment_preflight",
            "status": "failed",
            "stdout": '{"missing_required": ["skimage", "pypdf"]}',
        }
        self.assertEqual(
            release_acceptance.parse_environment_failure(result),
            ["skimage", "pypdf"],
        )

    def test_timeout_is_returned_as_structured_failure(self):
        result = release_acceptance.run_step(
            "slow-demo",
            [sys.executable, "-c", "import time; print('started', flush=True); time.sleep(2)"],
            timeout=1,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_type"], "timeout")
        self.assertEqual(result["timeout_seconds"], 1)
        self.assertIn("started", result["stdout"])

    def test_acceptance_metadata_has_runtime_and_offline_targets(self):
        metadata = release_acceptance.acceptance_metadata()
        self.assertIn("commit_sha", metadata)
        self.assertIn(metadata["worktree_dirty"], {True, False, None})
        self.assertIn("python_version", metadata)
        self.assertEqual(3, len(metadata["requirements_sha256"]))
        self.assertIn("target_platform", metadata["offline_manifest"])
        self.assertIn("target_python", metadata["offline_manifest"])

    def test_acceptance_metadata_degrades_when_git_and_manifest_unavailable(self):
        with patch.object(release_acceptance, "_git_sha", return_value=None), patch.object(
            release_acceptance, "_git_worktree_dirty", return_value=None
        ), patch.object(
            release_acceptance, "OFFLINE_MANIFEST", Path("/nonexistent/manifest.json")
        ):
            metadata = release_acceptance.acceptance_metadata()
        self.assertIsNone(metadata["commit_sha"])
        self.assertIsNone(metadata["worktree_dirty"])
        self.assertEqual("unknown", metadata["offline_manifest"]["target_platform"])

    def test_worktree_dirty_helper_preserves_clean_and_dirty_states(self):
        with patch.object(release_acceptance.subprocess, "run", return_value=type("R", (), {"returncode": 0, "stdout": ""})()):
            self.assertFalse(release_acceptance._git_worktree_dirty())
        with patch.object(release_acceptance.subprocess, "run", return_value=type("R", (), {"returncode": 0, "stdout": " M README.md\n"})()):
            self.assertTrue(release_acceptance._git_worktree_dirty())


if __name__ == "__main__":
    unittest.main()
