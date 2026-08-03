from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_polish_fidelity import audit_fidelity  # noqa: E402


class PolishFidelityAuditTest(unittest.TestCase):
    def test_passes_low_risk_language_cleanup(self):
        payload = audit_fidelity(
            "在25 °C条件下，该方法可能使效率提高12%[3]。",
            "在25 °C条件下，该方法可能将效率提高12%[3]。",
        )
        self.assertEqual(payload["summary"]["status"], "pass")

    def test_fails_when_numeric_value_or_qualifier_changes(self):
        payload = audit_fidelity(
            "在25 °C条件下，该方法可能使效率提高12%[3]。",
            "该方法证明效率提高15%[3]。",
        )
        rule_ids = {item["rule_id"] for item in payload["issues"]}
        self.assertEqual(payload["summary"]["status"], "fail")
        self.assertIn("protected_span.numeric_unit", rule_ids)
        self.assertIn("meaning_drift.evidence_qualifier", rule_ids)
        self.assertIn("claim_strength.new_strengthening_language", rule_ids)

    def test_warns_when_responsibility_subject_changes(self):
        payload = audit_fidelity("该研究报告了这一结果。", "本文报告了这一结果。")
        self.assertEqual(payload["summary"]["status"], "warn")
        self.assertEqual(payload["summary"]["warning_count"], 1)

    def test_formula_signature_drift_is_a_hard_failure(self):
        payload = audit_fidelity(
            "传递函数为 $T(\\omega)=F_{i+1}(\\omega)$。",
            "传递函数为 $T(\\omega)=F_i(\\omega)$。",
        )
        rule_ids = {item["rule_id"] for item in payload["issues"]}

        self.assertEqual(payload["summary"]["status"], "fail")
        self.assertIn("protected_span.equation_signature", rule_ids)

    def test_fails_when_evidence_placeholder_is_removed(self):
        payload = audit_fidelity("该结论仍需核验。[待补证据: 参数来源]", "该结论已经明确。")
        rule_ids = {item["rule_id"] for item in payload["issues"]}
        self.assertEqual(payload["summary"]["status"], "fail")
        self.assertIn("argument_fidelity.evidence_placeholder", rule_ids)

    def test_fails_when_paragraph_argument_units_collapse(self):
        before = "第一段讨论问题。\n\n第二段说明方法。\n\n第三段报告结果。\n\n第四段讨论限制。"
        after = "问题、方法、结果与限制合并说明。"
        payload = audit_fidelity(before, after)
        rule_ids = {item["rule_id"] for item in payload["issues"]}
        self.assertEqual(payload["summary"]["status"], "fail")
        self.assertIn("argument_fidelity.paragraph_collapse", rule_ids)


if __name__ == "__main__":
    unittest.main()
