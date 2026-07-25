from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_prompt_acceptance.py"
CASES = ROOT / "evals" / "prompt_acceptance.json"
sys.path.insert(0, str(ROOT / "scripts"))

import run_prompt_acceptance as prompt_eval  # noqa: E402


class PromptAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.payload = prompt_eval.load_cases(CASES)

    def test_case_file_has_bilingual_step_1_to_8_coverage(self):
        self.assertEqual(prompt_eval.validate_case_file(self.payload), [])
        self.assertEqual(len(self.payload["cases"]), 16)
        coverage = {
            (case["language"], case["expected_step"])
            for case in self.payload["cases"]
        }
        self.assertEqual(
            coverage,
            {
                (language, step)
                for language in {"zh", "en"}
                for step in {
                    "step1-topic",
                    "step2-outline",
                    "step3-search-plan",
                    "step4-search-execute",
                    "step5-download",
                    "step6-zotero",
                    "step7-writing",
                    "step8-polishing",
                }
            },
        )

    def test_deterministic_judge_accepts_complete_response(self):
        case = prompt_eval.find_case(self.payload, "zh-step7-writing")
        response = "\n".join(
            [*case["required_all"], *(group[0] for group in case["required_any"])]
        )
        self.assertEqual(prompt_eval.judge_response(case, response), [])

    def test_deterministic_judge_rejects_missing_and_forbidden_claims(self):
        case = prompt_eval.find_case(self.payload, "en-step5-download")
        failures = prompt_eval.judge_response(
            case,
            "selected_step: step5-download\nall PDFs have been downloaded",
        )
        self.assertTrue(any(item.startswith("missing_required:") for item in failures))
        self.assertIn("forbidden_claim:all PDFs have been downloaded", failures)

    def test_cli_records_three_runs_and_commit(self):
        case = prompt_eval.find_case(self.payload, "en-step1-topic")
        response = "\n".join(
            [*case["required_all"], *(group[0] for group in case["required_any"])]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for index in range(3):
                path = root / f"run-{index + 1}.txt"
                path.write_text(response, encoding="utf-8")
                paths.extend(["--response", str(path)])
            report_path = root / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--case",
                    case["id"],
                    "--host",
                    "codex",
                    "--commit",
                    "deadbeef",
                    *paths,
                    "--out",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(report["run_count"], 3)
        self.assertEqual(report["pass_count"], 3)
        self.assertTrue(report["consistent"])
        self.assertEqual(report["commit"], "deadbeef")
        self.assertTrue(all(run["raw_response"] == response for run in report["runs"]))


if __name__ == "__main__":
    unittest.main()
