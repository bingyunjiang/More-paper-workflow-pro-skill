from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "unified_download_router.py"


class Step5CliSmokeTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=30,
        )

    def test_help_is_available_without_network_or_browser(self):
        completed = self.run_cli("--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Unified PDF download router", completed.stdout)
        self.assertIn("--resume-login-checkpoint", completed.stdout)

    def test_english_dry_run_reports_route_without_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = self.run_cli(
                "--papers",
                "10.1016/j.est.2024.113105,10.1109/ACCESS.2024.3399912",
                "--output",
                tmp,
                "--dry-run",
            )
            manifest = json.loads((Path(tmp) / "download_manifest.json").read_text(encoding="utf-8"))
            preflight = json.loads((Path(tmp) / "preflight_summary.json").read_text(encoding="utf-8"))
            attempts_exist = (Path(tmp) / "download_attempts.jsonl").exists()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Total unique DOIs: 2", completed.stdout)
        self.assertIn("Routing summary:", completed.stdout)
        self.assertIn("[DRY RUN]", completed.stdout)
        self.assertEqual("dry_run", manifest["summary"]["execution_mode"])
        self.assertFalse(preflight["cdp"]["checked"])
        self.assertFalse(attempts_exist)

    def test_mixed_dry_run_reports_chinese_and_english_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chinese = root / "chinese.json"
            chinese.write_text(
                json.dumps([
                    {
                        "title": "中文论文",
                        "source": "cnki",
                        "doi": "cnki.demo",
                        "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=demo",
                    }
                ], ensure_ascii=False),
                encoding="utf-8",
            )
            completed = self.run_cli(
                "--papers",
                "10.1016/j.est.2024.113105",
                "--chinese-input",
                str(chinese),
                "--output",
                str(root / "out"),
                "--dry-run",
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Chinese papers: 1 total", completed.stdout)
        self.assertIn("Chinese CDP", completed.stdout)
        self.assertIn("[DRY RUN]", completed.stdout)

    def test_missing_resume_checkpoint_fails_before_browser_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-checkpoint.json"
            completed = self.run_cli(
                "--resume-login-checkpoint",
                str(missing),
                "--output",
                tmp,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("login checkpoint not found", completed.stdout)


if __name__ == "__main__":
    unittest.main()
