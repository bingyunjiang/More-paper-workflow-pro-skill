from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
import scripts.perform_skill_upgrade as upgrade


class PerformSkillUpgradeTest(unittest.TestCase):
    def test_reports_continue_when_git_pull_fails(self):
        def completed(args, returncode=0, stdout="", stderr=""):
            return subprocess.CompletedProcess(["git", *args], returncode, stdout, stderr)

        def fake_run(root, args, timeout=30):
            responses = {
                ("rev-parse", "HEAD"): completed(args, stdout="local\n"),
                ("symbolic-ref", "--quiet", "--short", "HEAD"): completed(args, stdout="main\n"),
                ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"): completed(args, stdout="origin/main\n"),
                ("status", "--porcelain", "--untracked-files=normal"): completed(args),
                ("fetch", "--quiet"): completed(args, returncode=1, stderr="network unavailable"),
            }
            return responses[tuple(args)]

        with mock.patch.object(upgrade, "run_git", side_effect=fake_run):
            payload = upgrade.build_result(ROOT)
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["upgraded"])
        self.assertTrue(payload["continue_with_current_version"])
        self.assertEqual(payload["reason"], "git_fetch_failed")
        self.assertIn("继续使用当前本地版本", payload["message"])

    def test_dirty_worktree_blocks_upgrade_before_network_access(self):
        def completed(args, returncode=0, stdout="", stderr=""):
            return subprocess.CompletedProcess(["git", *args], returncode, stdout, stderr)

        responses = [
            completed(["rev-parse", "HEAD"], stdout="local\n"),
            completed(["symbolic-ref"], stdout="main\n"),
            completed(["rev-parse"], stdout="origin/main\n"),
            completed(["status"], stdout=" M SKILL.md\n"),
        ]
        with mock.patch.object(upgrade, "run_git", side_effect=responses) as run_git:
            payload = upgrade.build_result(ROOT)
        self.assertEqual(payload["reason"], "dirty_worktree")
        self.assertEqual(run_git.call_count, 4)


if __name__ == "__main__":
    unittest.main()
