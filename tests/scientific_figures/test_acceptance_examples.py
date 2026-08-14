from __future__ import annotations

from .common import *


class AcceptanceExampleTests(ScientificFigureReproductionTestBase):
    def test_release_acceptance_official_line_plot_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "release_acceptance.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "release_acceptance.py"), "--json-out", str(report)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=240,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            payload = json.loads(report.read_text(encoding="utf-8"))
            expected_status = "pass" if payload["release_eligible"] else "diagnostic_pass"
            self.assertEqual(expected_status, payload["status"])
            self.assertEqual("pass", payload["diagnostic_status"])
            self.assertEqual("v1.0.28-20260814", payload["version"])
            self.assertEqual("semantic_strict_pass", payload["checks"]["official_example"])
