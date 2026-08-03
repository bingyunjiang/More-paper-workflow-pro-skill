import subprocess
import sys
import tempfile
import json
import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_step7_output.py"


class ValidateStep7OutputTest(unittest.TestCase):
    def run_validator(self, output_dir: Path, target_state: str | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), str(output_dir)]
        if target_state:
            command.extend(["--target-state", target_state])
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_fails_when_draft_skips_step7_artifact_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journal_paper_draft.md").write_text(
                "# 受力与变形特征\n\n这里直接写正文，但没有工件链。\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "evidence_closed")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_execution_card", result.stdout)
        self.assertIn("missing_citation_audit", result.stdout)
        self.assertIn("missing_figure_gate", result.stdout)
        self.assertIn("missing_mechanism_decision", result.stdout)

    def test_draft_ready_direct_entry_does_not_require_evidence_closure_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journal_paper_draft.md").write_text(
                "# 方法草稿\n\n当前段落仍需补充正式引文。\n",
                encoding="utf-8",
            )
            (out / "step7_execution_card.md").write_text(
                "# Step 7 Execution Card\n\n- target_state: draft_ready\n- figure_mode: skip\n- risk_status: citations_pending\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "draft_ready")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("completion_state: draft_ready", result.stdout)
        self.assertIn("draft_without_submission_style_citations", result.stdout)
        self.assertNotIn("missing_reviewer_scorecard", result.stdout)
        self.assertNotIn("missing_evidence_mapping", result.stdout)
        self.assertNotIn("missing_citation_audit", result.stdout)

    def test_formula_source_residue_blocks_draft_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journal_paper_draft.md").write_text(
                "# 方法草稿\n\n状态方程可表示为：\n\nT(omega), F_{i+1}, X_in\n",
                encoding="utf-8",
            )
            (out / "step7_execution_card.md").write_text(
                "# Step 7 Execution Card\n\n- target_state: draft_ready\n- figure_mode: skip\n- risk_status: citations_pending\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_equation", result.stdout)
        self.assertIn("plain_text_math_leak", result.stdout)

    def test_canonical_formula_passes_draft_ready_equation_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journal_paper_draft.md").write_text(
                "# 方法草稿\n\n状态方程可表示为：\n\n$$F_{i+1}(\\omega)=X_{\\mathrm{in}}$$\n",
                encoding="utf-8",
            )
            (out / "step7_execution_card.md").write_text(
                "# Step 7 Execution Card\n\n- target_state: draft_ready\n- figure_mode: skip\n- risk_status: citations_pending\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "draft_ready")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("equation_audit_status: pass", result.stdout)

    def test_passes_when_required_step7_artifacts_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journal_paper_draft.md").write_text(
                "# 受力与变形特征\n\n正文采用编号引文[1]（已读全文）。\n",
                encoding="utf-8",
            )
            (out / "step7_execution_card.md").write_text(
                "\n".join([
                    "# Step 7 Execution Card",
                    "- mechanism_trigger_decision: enter_mechanism_analysis",
                    "- figure_mode: skip",
                    "- risk_status: citations_checked",
                ]),
                encoding="utf-8",
            )
            (out / "evidence_matrix.md").write_text("# Evidence\n", encoding="utf-8")
            (out / "citation_audit.md").write_text("# Citation Audit\n", encoding="utf-8")
            (out / "figure_asset_check.md").write_text("# Figure Asset Check\n", encoding="utf-8")
            (out / "mechanism_cards.md").write_text("# Mechanism Cards\n", encoding="utf-8")
            (out / "mechanism_argument_plan.md").write_text("# Mechanism Argument Plan\n", encoding="utf-8")
            (out / "mechanism_claim_audit.md").write_text("# Mechanism Claim Audit\n", encoding="utf-8")
            self.write_reviewer_scorecard(out)
            result = self.run_validator(out)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STEP7_VALIDATION: pass", result.stdout)

    def test_fails_on_raw_zotero_key_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out)
            (out / "journal_paper_draft.md").write_text(
                "# 受力与变形特征\n\n壁厚减薄受相对弯曲半径影响 `99QWSQ5K`（已读全文）。\n",
                encoding="utf-8",
            )
            result = self.run_validator(out)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("raw_zotero_key_citations", result.stdout)
        self.assertIn("draft_without_submission_style_citations", result.stdout)

    def test_fails_on_raw_zotero_key_after_first_5000_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out)
            long_body = "背景说明。" * 1200
            (out / "journal_paper_draft.md").write_text(
                f"# 长章节\n\n正文采用编号引文[1]（已读全文）。\n\n{long_body}\n\n"
                "后文误留原始条目键 `99QWSQ5K`（已读全文）。\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "evidence_closed")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("raw_zotero_key_citations", result.stdout)

    def test_fails_when_mineru_assets_exist_without_figure_index_or_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_mode="post_write")
            (out / "figure_asset_check.md").write_text(
                "# Figure Asset Check\n\n- figure_mode: post_write\n- mineru_zip: available\n",
                encoding="utf-8",
            )
            (out / "journal_paper_draft.md").write_text(
                "# 受力与变形特征\n\n正文采用编号引文[1]（已读全文），但没有图位。\n",
                encoding="utf-8",
            )
            result = self.run_validator(out)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_figure_index", result.stdout)
        self.assertIn("missing_figure_marker", result.stdout)

    def test_passes_with_mineru_assets_figure_index_and_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_mode="post_write")
            (out / "figure_asset_check.md").write_text(
                "# Figure Asset Check\n\n- figure_mode: post_write\n- mineru_zip: available\n",
                encoding="utf-8",
            )
            (out / "figure_index.json").write_text(
                '{"records": [{"figure_id": "Fig. 1"}]}\n',
                encoding="utf-8",
            )
            (out / "journal_paper_draft.md").write_text(
                "# 受力与变形特征\n\n正文采用编号引文[1]（已读全文）。\n\n[[FIGURE:wall_thinning|source=99QWSQ5K|status=post_write]]\n",
                encoding="utf-8",
            )
            result = self.run_validator(out)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_figure_index_does_not_satisfy_asset_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_mode="post_write")
            (out / "figure_asset_check.md").write_text(
                "# Figure Asset Check\n\n- figure_mode: post_write\n- mineru_zip: available\n",
                encoding="utf-8",
            )
            (out / "figure_index.json").write_text(
                '{"records": []}\n',
                encoding="utf-8",
            )
            (out / "journal_paper_draft.md").write_text(
                "# 方法\n\n正文采用编号引文[1]（已读全文）。\n\n"
                "[[FIGURE:method|status=post_write]]\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_figure_index", result.stdout)

    def test_inserted_image_must_exist_and_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out)
            (out / "journal_paper_draft.md").write_text(
                "# 方法\n\n正文采用编号引文[1]（已读全文）。\n\n"
                "![图 1](figures/missing.png)\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_inserted_image", result.stdout)

    def write_minimum_artifacts(self, out: Path, figure_mode: str = "skip", figure_backend: str = "") -> None:
        backend_line = f"- figure_backend: {figure_backend}" if figure_backend else ""
        (out / "step7_execution_card.md").write_text(
            "\n".join([
                "# Step 7 Execution Card",
                "- mechanism_trigger_decision: enter_mechanism_analysis",
                f"- figure_mode: {figure_mode}",
                backend_line,
                "- risk_status: citations_checked",
            ]).replace("\n\n", "\n"),
            encoding="utf-8",
        )
        (out / "evidence_matrix.md").write_text("# Evidence\n", encoding="utf-8")
        (out / "citation_audit.md").write_text("# Citation Audit\n", encoding="utf-8")
        (out / "figure_asset_check.md").write_text(f"# Figure Asset Check\n\n- figure_mode: {figure_mode}\n", encoding="utf-8")
        (out / "mechanism_cards.md").write_text("# Mechanism Cards\n", encoding="utf-8")
        (out / "mechanism_argument_plan.md").write_text("# Mechanism Argument Plan\n", encoding="utf-8")
        (out / "mechanism_claim_audit.md").write_text("# Mechanism Claim Audit\n", encoding="utf-8")
        self.write_reviewer_scorecard(out)

    def test_reproduction_backend_requires_figure_evidence_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_backend="reproduction")
            (out / "journal_paper_draft.md").write_text(
                "# 方法\n\n当前复现图仍需登记。\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_figure_evidence_report", result.stdout)

    def test_near_pass_reproduction_requires_deviation_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_backend="reproduction")
            (out / "journal_paper_draft.md").write_text("# 方法\n\n当前复现图。\n", encoding="utf-8")
            (out / "figure_evidence_report.json").write_text(json.dumps({
                "schema_version": "figure-evidence.v1",
                "records": [{
                    "generation_backend": "reproduction",
                    "visualspec_path": "visualspec.json",
                    "reproduction_bundle": "figures/fig_1_bundle",
                    "manifest_path": "figures/fig_1_bundle/reproduction_manifest.json",
                    "reproduction_status": "semantic_near_pass",
                    "qa_profile": "semantic",
                    "verification_status": "pass",
                    "figure_asset_action": "redraw",
                    "figure_transform_authorization": "explicit_user_request",
                    "figure_risk_note": "",
                }],
            }), encoding="utf-8")
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_figure_deviation", result.stdout)

    def test_strict_reproduction_record_passes_draft_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_backend="reproduction")
            (out / "journal_paper_draft.md").write_text("# 方法\n\n当前复现图。\n", encoding="utf-8")
            (out / "figure_evidence_report.json").write_text(json.dumps({
                "schema_version": "figure-evidence.v1",
                "records": [{
                    "generation_backend": "reproduction",
                    "visualspec_path": "visualspec.json",
                    "reproduction_bundle": "figures/fig_1_bundle",
                    "manifest_path": "figures/fig_1_bundle/reproduction_manifest.json",
                    "reproduction_status": "semantic_strict_pass",
                    "qa_profile": "semantic",
                    "verification_status": "pass",
                    "figure_asset_action": "redraw",
                    "figure_transform_authorization": "explicit_user_request",
                    "figure_risk_note": "",
                }],
            }), encoding="utf-8")
            result = self.run_validator(out, "draft_ready")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("figure_backend: reproduction", result.stdout)

    def test_digitized_reproduction_rejects_unreviewed_candidate_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_backend="reproduction")
            (out / "journal_paper_draft.md").write_text("# 结果\n\n数字化结果。\n", encoding="utf-8")
            (out / "figure_evidence_report.json").write_text(json.dumps({
                "schema_version": "figure-evidence.v1",
                "records": [{
                    "generation_backend": "reproduction",
                    "visualspec_path": "visualspec.json",
                    "reproduction_bundle": "figures/fig_1_bundle",
                    "manifest_path": "figures/fig_1_bundle/reproduction_manifest.json",
                    "reproduction_status": "semantic_strict_pass",
                    "qa_profile": "semantic",
                    "verification_status": "pass",
                    "figure_asset_action": "digitize",
                    "figure_transform_authorization": "explicit_user_request",
                    "figure_risk_note": "",
                    "extraction_project_path": "figures/fig_1/figure_project.result.json",
                    "extraction_report_path": "figures/fig_1/extraction_report.json",
                    "extraction_status": "authorized_candidate",
                    "review_status": "not_reviewed",
                    "value_delivery_authorized": True
                }],
            }), encoding="utf-8")
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("digitization_status_authorization_conflict", result.stdout)

    def test_reproduction_requires_explicit_user_transform_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out, figure_backend="reproduction")
            (out / "journal_paper_draft.md").write_text(
                "# 结果\n\n原论文图片应直接插入。\n",
                encoding="utf-8",
            )
            (out / "figure_evidence_report.json").write_text(json.dumps({
                "schema_version": "figure-evidence.v1",
                "records": [{
                    "generation_backend": "reproduction",
                    "visualspec_path": "visualspec.json",
                    "reproduction_bundle": "figures/fig_1_bundle",
                    "manifest_path": "figures/fig_1_bundle/reproduction_manifest.json",
                    "reproduction_status": "semantic_strict_pass",
                    "qa_profile": "semantic",
                    "verification_status": "pass",
                    "figure_asset_action": "insert_original",
                    "figure_transform_authorization": "not_required",
                    "figure_risk_note": ""
                }],
            }), encoding="utf-8")
            result = self.run_validator(out, "draft_ready")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reproduction_without_transform_action", result.stdout)
        self.assertIn("figure_transform_not_explicitly_authorized", result.stdout)

    def write_reviewer_scorecard(self, out: Path, technical_soundness: int = 4) -> None:
        scores = {}
        for axis, score in {
            "originality": 3,
            "importance": 3,
            "technical_soundness": technical_soundness,
            "evidence_adequacy": 4,
            "readability_structure": 3,
        }.items():
            scores[axis] = {
                "score": score,
                "evidence_locations": ["full_document"],
                "reason": f"{axis} assessed against the anchored rubric",
            }
        (out / "reviewer_scorecard.json").write_text(
            json.dumps({
                "schema_version": "reviewer-scorecard.v1",
                "assessment_boundary": "full_document",
                "scores": scores,
                "critical_issues": [],
            }),
            encoding="utf-8",
        )

    def test_fails_when_reviewer_score_is_below_anchored_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out)
            self.write_reviewer_scorecard(out, technical_soundness=3)
            (out / "journal_paper_draft.md").write_text(
                "# 方法\n\n正文采用编号引文[1]（已读全文）。\n",
                encoding="utf-8",
            )
            result = self.run_validator(out, "evidence_closed")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reviewer_score_below_gate_technical_soundness", result.stdout)

    def test_evidence_closed_requires_current_hash_and_zero_unresolved_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.write_minimum_artifacts(out)
            draft = "# 方法\n\n正文采用编号引文[1]（已读全文）。\n"
            (out / "journal_paper_draft.md").write_text(draft, encoding="utf-8")
            digest = hashlib.sha256(draft.encode("utf-8")).hexdigest()
            scorecard_path = out / "reviewer_scorecard.json"
            scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
            scorecard["draft_sha256"] = digest
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")
            (out / "claim_evidence_audit.json").write_text(json.dumps({
                "schema_version": "claim-evidence-audit.v1",
                "draft_sha256": digest,
                "summary": {"unresolved_count": 0},
                "records": [{
                    "claim_segment_id": "S001", "claim_text": "正文", "claim_strength": "background",
                    "required_evidence": "abstract_ok", "support_grade": "background", "reading_depth": "full_text",
                    "evidence_anchor": "page:1", "downgrade_required": False, "recommended_action": "retain",
                    "resolution_status": "closed",
                }],
            }), encoding="utf-8")
            passed = self.run_validator(out, "evidence_closed")
            (out / "journal_paper_draft.md").write_text(draft + "新增句子。\n", encoding="utf-8")
            stale = self.run_validator(out, "evidence_closed")
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        self.assertIn("completion_state: evidence_closed", passed.stdout)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("stale_claim_evidence_audit", stale.stdout)


if __name__ == "__main__":
    unittest.main()
