from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from citation_audit import (  # noqa: E402
    CitationRef,
    extract_citations_from_manuscript,
    extract_dois_from_bib,
    score_citation_support,
)


class CitationAuditRegressionTest(unittest.TestCase):
    def test_repeated_reference_is_audited_at_every_claim_occurrence(self) -> None:
        manuscript = (
            "背景事实由文献支持[1]。\n\n"
            "该文献还证明了 CNT 导致 CDRX 并提升强度的因果机制[1]。\n\n"
            "# 参考文献\n[1] Author. Title. Journal. DOI: 10.1000/demo\n"
        )

        citations = extract_citations_from_manuscript(manuscript)

        self.assertEqual([1, 1], [item.index for item in citations])
        self.assertNotEqual(citations[0].claim_occurrence_id, citations[1].claim_occurrence_id)
        self.assertIn("背景事实", citations[0].claim_sentence)
        self.assertIn("因果机制", citations[1].claim_sentence)

    def test_grouped_marker_keeps_one_occurrence_per_reference(self) -> None:
        citations = extract_citations_from_manuscript("联合证据支持该结论[1, 2]。")
        self.assertEqual([1, 2], [item.index for item in citations])
        self.assertEqual(2, len({item.claim_occurrence_id for item in citations}))

    def test_doi_extraction_preserves_suffix_dots_and_common_forms(self) -> None:
        entries = {
            1: "DOI: 10.1016/j.msea.2025.123456.",
            2: "https://doi.org/10.1002/ente.202301205",
            3: "Bare DOI 10.1109/TPEL.2024.1234567]",
        }

        self.assertEqual(
            {
                1: "10.1016/j.msea.2025.123456",
                2: "10.1002/ente.202301205",
                3: "10.1109/TPEL.2024.1234567",
            },
            extract_dois_from_bib(entries),
        )

    def test_low_overlap_chinese_claim_needs_review_instead_of_false_negative(self) -> None:
        citation = CitationRef(
            1,
            "[1]",
            "热变形过程中，动态再结晶能够改善铝合金塑性。[1]",
            "",
            1,
        )
        abstract = "研究结果表明，铝合金在高温变形时发生动态再结晶，晶粒细化并使塑性得到改善。"

        result = score_citation_support(citation, abstract)

        self.assertEqual("⚠️ 无法判断", result.support_level)
        self.assertIn("不足以", result.reasoning)


if __name__ == "__main__":
    unittest.main()
