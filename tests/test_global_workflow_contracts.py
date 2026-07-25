from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_skill_package as package_validator  # noqa: E402
from validate_early_step_output import validate_step1, validate_step3  # noqa: E402
from workflow_run_envelope import validate_envelope  # noqa: E402


class GlobalWorkflowContractsTest(unittest.TestCase):
    def test_registry_matches_step3_step7_step8_manifests(self):
        registry = json.loads((ROOT / "schemas/workflow-contract-registry.json").read_text(encoding="utf-8"))
        for manifest_name, step, axes in [
            ("manifest.step3.yaml", "step3", ["base_workflow", "addons"]),
            (
                "manifest.step7.yaml",
                "step7",
                ["mode", "operation", "target_genre", "figure_mode", "figure_backend", "figure_asset_action"],
            ),
            (
                "manifest.step8.yaml",
                "step8",
                ["revision_scope", "language", "target_genre", "output_mode", "rewrite_scope", "rewrite_level"],
            ),
        ]:
            text = (ROOT / manifest_name).read_text(encoding="utf-8")
            for axis in axes:
                self.assertEqual(
                    set(package_validator.yaml_axis_allowed(text, axis)),
                    set(registry[step][axis]),
                    f"{manifest_name}:{axis}",
                )

    def test_step1_fatal_axis_overrides_green_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "研究主题.md"
            artifact.write_text(
                """---
user_profile: {stage: 开题, target: 期刊投稿}
topic:
  focused_topic: demo
  primary_rq: rq
  scope_boundaries: {in_scope: [a], out_of_scope: [b]}
  evaluation_metrics: [a, b, c]
  working_hypothesis: h
  falsification_condition: f
  minimum_viable_study: m
  topic_kill_criteria: [k]
interaction_record:
  answer_burden: minimal
  user_supplied: [direction]
  inferred: []
  assumed: []
  unresolved_blocking: []
  unresolved_nonblocking: []
evidence_calibration:
  status: unavailable
  sources_attempted: [openalex]
  queries: [demo]
  limitations: [offline]
pre_review:
  originality: {score: 5, signal: green, reason: ok}
  importance: {score: 5, signal: green, reason: ok}
  feasibility: {score: 1, signal: red, reason: fatal}
  literature_support: {score: 5, signal: green, reason: ok}
  method_readiness: {score: 5, signal: green, reason: ok}
  total_score: 21
  decision: green
  fatal_risks: []
---
""",
                encoding="utf-8",
            )
            errors = validate_step1(artifact)
        self.assertIn("pre_review.decision must be red for fatal axis/risk precedence", errors)

    def test_step3_composable_axes_and_plan_state_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "检索方案.json"
            artifact.write_text(
                json.dumps(
                    {
                        "plan_mode": "standard",
                        "plan_state": "not-a-state",
                        "base_workflow": "standard",
                        "addons": ["citation-expansion", "citation-expansion"],
                        "execution_context": "step3_planning",
                        "retrieval_language": "en",
                        "source_scope": ["openalex"],
                        "publication_year_range": {"from": 2020, "to": 2026},
                        "document_types": ["journal-article"],
                        "inclusion_criteria": ["relevant"],
                        "exclusion_criteria": ["irrelevant"],
                        "deduplication_plan": {"primary_key": "doi"},
                        "query_versions": [{"version": "v1"}],
                        "search_update_policy": {"rerun_before_submission": True},
                        "search_tasks": [
                            {
                                "id": "S1",
                                "rq_id": "RQ1",
                                "chapter_id": "ch1",
                                "evidence_type": "method",
                                "question_to_answer": "q",
                                "tier": "standard",
                                "framework": "concept_block",
                                "route": {"l1": ["openalex"]},
                                "query_blocks": [{"name": "object", "terms": ["a", "b"]}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_step3(artifact)
        self.assertIn("plan_state must be compiled, pilot_verified, or offline_unverified", errors)
        self.assertIn("addons must not contain duplicates", errors)

    def test_step2_baseline_is_not_overwritten_by_step7_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outline = root / "大纲关键词.md"
            style = root / "style_profile.md"
            evidence = root / "综述矩阵.csv"
            baseline = root / "section_blueprints.json"
            outline.write_text("# 大纲\n\n## 1. 绪论\n", encoding="utf-8")
            style.write_text("target_genre: thesis\n", encoding="utf-8")
            evidence.write_text("作者年份,核心发现,方法,贡献,可引用摘录,与我的主题关系\n", encoding="utf-8")
            baseline_payload = {
                "outline_state": "outline_baseline",
                "core_research_question_ids": ["RQ1"],
                "evidence_calibration": {"status": "unavailable"},
                "keyword_audit": [{"term": "demo"}],
                "sections": [
                    {
                        "section_id": "1",
                        "section_title": "绪论",
                        "section_function": "background",
                        "rq_ids": ["RQ1"],
                        "key_claims": ["baseline"],
                        "evidence_needed": ["context"],
                        "do_not_write": ["results"],
                    }
                ],
            }
            baseline.write_text(json.dumps(baseline_payload, ensure_ascii=False), encoding="utf-8")
            baseline_before = baseline.read_bytes()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/generate_section_blueprints.py"),
                    str(style),
                    str(outline),
                    "--evidence",
                    str(evidence),
                    "--baseline",
                    str(baseline),
                    "--output",
                    str(root),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(baseline.read_bytes(), baseline_before)
            derived = json.loads((root / "writing_blueprints.json").read_text(encoding="utf-8"))
        self.assertEqual(derived["blueprint_state"], "writing_derived")
        self.assertEqual(derived["sections"][0]["rq_ids"], ["RQ1"])
        self.assertEqual(len(derived["source_lineage"]["baseline_sha256"]), 64)

    def test_workflow_run_envelope_cli_is_atomic_and_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            artifact = root / "output.json"
            source.write_text("{}\n", encoding="utf-8")
            artifact.write_text("{}\n", encoding="utf-8")
            envelope = root / "search_run_manifest.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/workflow_run_envelope.py"),
                    "create",
                    "--project-root",
                    str(root),
                    "--output",
                    str(envelope),
                    "--step",
                    "4",
                    "--entry-mode",
                    "direct-query",
                    "--route-mode",
                    "direct_entry",
                    "--execution-profile",
                    "core",
                    "--input",
                    str(source),
                    "--artifact",
                    str(artifact),
                    "--domain-state",
                    "search_complete",
                    "--readiness",
                    "partial",
                    "--can-continue",
                    "--warning",
                    "degraded_source_coverage",
                    "--recommended-next-step",
                    "Step 5",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(envelope.read_text(encoding="utf-8"))
            self.assertEqual(validate_envelope(payload), [])
            self.assertFalse(list(root.glob(".search_run_manifest.json.*")))

    def test_step5_sources_and_order_remain_locked_and_serial(self):
        step5 = (ROOT / "agents/step_5_download.md").read_text(encoding="utf-8")
        router = (ROOT / "scripts/unified_download_router.py").read_text(encoding="utf-8")
        registry = json.loads((ROOT / "schemas/workflow-contract-registry.json").read_text(encoding="utf-8"))
        self.assertIn("英文默认顺序为 `2021 年及以前：Sci-Hub → OA fast → IEEE CDP / Generic CDP", step5)
        self.assertIn("中文条目先稳定排序为 CNKI → 万方", step5)
        self.assertIn("不得同时运行多个下载队列", step5)
        self.assertIn("--parallel-phase1 is deprecated and ignored", router)
        self.assertEqual(registry["step5"]["execution_policy"]["concurrency"], "serial")
        self.assertFalse(registry["step5"]["execution_policy"]["parallel_downloads_allowed"])

    def test_step8_strict_returns_nonzero_for_blocked_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "论文初稿.md").write_text("这里需要补文献，图表待补。", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_step8_ai_trace.py"),
                    "--project-root",
                    str(root),
                    "--strict",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
            self.assertIn("strict_status: blocked", result.stdout)
            self.assertFalse(list(root.glob(".revision_ledger.json.*")))


if __name__ == "__main__":
    unittest.main()
