from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_skill_update.py"


class CheckSkillUpdateScriptTest(unittest.TestCase):
    def test_json_mode_reports_soft_prompt_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"XDG_CACHE_HOME": tmp}
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--json", "--force", "--no-network"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env={**env, "PATH": "/usr/bin:/bin"},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["enabled"])
        self.assertFalse(payload["skipped"])
        self.assertIn("update_available", payload)
        self.assertIn("should_prompt", payload)
        self.assertIn("suggested_action", payload)
        self.assertIn("messages", payload)
        self.assertEqual(payload["suggested_action"], "continue")
        self.assertFalse(payload["should_prompt"])
        self.assertEqual(payload["prompt_options"], [])
        self.assertEqual(payload["skill_version"], "v1.0.27-20260806")

    def test_parse_skill_version_reads_skill_metadata_body(self):
        import scripts.check_skill_update as check_skill_update

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text(
                "---\nname: demo\ndescription: demo\n---\n\n## Skill metadata\n\nversion: v9.9.9-20991231 (2099-12-31)\n",
                encoding="utf-8",
            )
            self.assertEqual(check_skill_update.parse_skill_version(root), "v9.9.9-20991231")

    def test_remote_version_comparison_uses_release_version_not_commit_difference(self):
        import scripts.check_skill_update as check_skill_update

        self.assertTrue(
            check_skill_update.remote_version_is_newer("v1.0.27-20260806", "v1.0.28-20260807")
        )
        self.assertFalse(
            check_skill_update.remote_version_is_newer("v1.0.27-20260806", "v1.0.27-20260806")
        )
        self.assertFalse(check_skill_update.remote_version_is_newer("v1.0.27-20260806", None))

    def test_read_remote_version_fetches_upstream_skill_metadata(self):
        import scripts.check_skill_update as check_skill_update

        responses = {
            ("ls-remote", "origin", "refs/heads/main"): "abcdef1234567890\trefs/heads/main",
            ("fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "origin", "refs/heads/main"): "",
            ("show", "abcdef1234567890:SKILL.md"): "## Skill metadata\n\nversion: v1.0.28-20260807 (2026-08-07)\n",
        }

        with mock.patch.object(
            check_skill_update,
            "run_git",
            side_effect=lambda root, args, timeout=5: responses[tuple(args)],
        ):
            head, version, status = check_skill_update.read_remote_version(ROOT, "origin", "main")

        self.assertEqual(head, "abcdef1234567890")
        self.assertEqual(version, "v1.0.28-20260807")
        self.assertEqual(status, "checked")

    def test_throttled_json_keeps_complete_prompt_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "more-paper-workflow" / "update-check.json"
            state_file.parent.mkdir(parents=True)
            state_file.write_text(json.dumps({"last_checked": time.time()}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--json", "--no-network"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env={"XDG_CACHE_HOME": tmp, "PATH": "/usr/bin:/bin"},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["skipped"])
        self.assertEqual(payload["reason"], "throttled")
        self.assertFalse(payload["should_prompt"])
        self.assertEqual(payload["prompt_options"], [])
        self.assertIn("remote_version", payload)

    def test_record_choice_snoozes_matching_remote_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"XDG_CACHE_HOME": tmp, "PATH": "/usr/bin:/bin"}
            first = subprocess.run(
                [sys.executable, str(SCRIPT), "--json", "--force", "--record-choice", "snooze_today"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            first_payload = json.loads(first.stdout)
            remote_head = first_payload.get("remote_head")

            if not remote_head or not first_payload.get("remote_update_available"):
                self.skipTest("remote HEAD not available in this environment")

            second = subprocess.run(
                [sys.executable, str(SCRIPT), "--json", "--force"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertTrue(second_payload["suppressed"])
            self.assertEqual(second_payload["suppress_reason"], "snoozed_for_today")
            self.assertFalse(second_payload["should_prompt"])

    def test_record_choice_bypasses_throttle_and_uses_cached_remote_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            state_file = cache_root / "more-paper-workflow" / "update-check.json"
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                json.dumps(
                    {
                        "last_checked": time.time(),
                        "last_prompted_remote_head": "abcdef1234567890",
                        "remote_head": "abcdef1234567890",
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--json",
                    "--no-network",
                    "--record-choice",
                    "snooze_today",
                    "--suppress-hours",
                    "2",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env={"XDG_CACHE_HOME": tmp, "PATH": "/usr/bin:/bin"},
            )
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["skipped"])
            self.assertEqual(payload["choice_recorded"], "snooze_today")
            self.assertEqual(state["suppressed_remote_head"], "abcdef1234567890")
            self.assertGreater(state["suppress_until"], state["last_choice_at"])

    def test_remote_has_update_ignores_local_ahead_of_known_remote_head(self):
        import scripts.check_skill_update as check_skill_update

        original = check_skill_update.run_git_status

        def fake_status(root, args, timeout=5):
            if args[:2] == ["cat-file", "-e"]:
                return 0
            if args == ["merge-base", "--is-ancestor", "remote", "local"]:
                return 0
            return 1

        try:
            check_skill_update.run_git_status = fake_status
            self.assertFalse(check_skill_update.remote_has_update(ROOT, "local", "remote"))
        finally:
            check_skill_update.run_git_status = original

    def test_remote_has_update_detects_local_behind_known_remote_head(self):
        import scripts.check_skill_update as check_skill_update

        original = check_skill_update.run_git_status

        def fake_status(root, args, timeout=5):
            if args[:2] == ["cat-file", "-e"]:
                return 0
            if args == ["merge-base", "--is-ancestor", "remote", "local"]:
                return 1
            if args == ["merge-base", "--is-ancestor", "local", "remote"]:
                return 0
            return 1

        try:
            check_skill_update.run_git_status = fake_status
            self.assertTrue(check_skill_update.remote_has_update(ROOT, "local", "remote"))
        finally:
            check_skill_update.run_git_status = original


if __name__ == "__main__":
    unittest.main()
