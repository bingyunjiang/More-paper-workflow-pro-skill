from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_reproduction.py"


class ReproductionAuthorizationTest(unittest.TestCase):
    def test_direct_cli_rejects_missing_explicit_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--spec",
                    str(root / "spec.json"),
                    "--out-dir",
                    str(root / "bundle"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("--transform-authorization", result.stderr)


if __name__ == "__main__":
    unittest.main()
