import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lint_search_plan import lint_and_compile, run_pilot  # noqa: E402


class LintSearchPlanTest(unittest.TestCase):
    def test_compiles_queries_and_accepts_relevant_pilot(self):
        plan = {"search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"], "l2": ["cnki"]},
            "query_blocks": [
                {"name": "object", "terms": ["cold plate", "liquid cooling"]},
                {"name": "method", "terms": ["topology optimization", "shape optimization"]},
            ],
            "exclusion_terms": ["building"],
        }]}
        pilot = {"records": [
            {"search_task_id": "S1", "title": "Cold plate topology optimization"},
            {"search_task_id": "S1", "title": "Liquid cooling shape optimization"},
        ]}
        payload = lint_and_compile(plan, pilot)
        task = payload["tasks"][0]
        self.assertEqual(payload["summary"]["status"], "pass")
        self.assertIn("AND", task["compiled_queries"]["openalex"])
        self.assertEqual(task["source_compilation"]["openalex"]["compile_status"], "exact")
        self.assertEqual(task["source_compilation"]["cnki"]["compile_status"], "manual_required")
        self.assertEqual(task["pilot"]["status"], "ok")

    def test_detects_exclusion_collision_and_zero_result(self):
        plan = {"search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [{"name": "object", "terms": ["battery", "battery"]}],
            "exclusion_terms": ["battery"],
        }]}
        payload = lint_and_compile(plan, {"records": []})
        errors = payload["tasks"][0]["lint_errors"]
        self.assertEqual(payload["summary"]["status"], "fail")
        self.assertTrue(any("collision" in error for error in errors))
        self.assertIn("pilot_zero-result", errors)
        repair = payload["tasks"][0]["repair"]
        self.assertTrue(repair["required"])
        self.assertEqual(repair["repair_location"], "step3")
        self.assertFalse(repair["requires_prior_step_rerun"])

    def test_step3_direct_entry_repairs_inside_step3(self):
        plan = {"route_mode": "direct_entry", "search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [{"name": "object", "terms": ["battery", "energy storage"]}],
        }]}
        payload = lint_and_compile(plan, {"records": []})
        task = payload["tasks"][0]
        self.assertEqual(task["basis_origin"], "step3_reconstructed")
        self.assertEqual(task["repair"]["repair_location"], "step3")

    def test_step4_direct_entry_repairs_inside_step4(self):
        plan = {"execution_context": "step4_direct_entry", "route_mode": "direct_entry", "search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [{"name": "object", "terms": ["battery", "energy storage"]}],
        }]}
        task = lint_and_compile(plan, {"records": []})["tasks"][0]
        self.assertEqual(task["basis_origin"], "step4_reconstructed")
        self.assertEqual(task["repair"]["repair_location"], "step4")

    def test_pilot_requires_every_required_concept_block(self):
        plan = {"search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [
                {"name": "object", "terms": ["battery", "energy storage"]},
                {"name": "method", "terms": ["topology optimization", "shape optimization"]},
            ],
        }]}
        pilot = {"records": [{"search_task_id": "S1", "title": "Battery management review", "abstract": "Energy storage systems"}]}
        task = lint_and_compile(plan, pilot)["tasks"][0]
        self.assertEqual(task["pilot"]["status"], "concept_block_dropout")
        self.assertIn("method", task["pilot"]["dropped_required_blocks"])

    def test_pilot_uses_abstract_and_checks_seed_recall(self):
        plan = {"known_relevant_records": [{"doi": "10.1/seed", "title": "Seed paper"}], "search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [
                {"name": "object", "terms": ["cold plate", "liquid cooling"]},
                {"name": "method", "terms": ["topology optimization", "shape optimization"]},
            ],
        }]}
        pilot = {"records": [{
            "search_task_id": "S1", "doi": "10.1/seed", "title": "Seed paper",
            "abstract": "Cold plate design using topology optimization",
        }]}
        task = lint_and_compile(plan, pilot)["tasks"][0]
        self.assertEqual(task["pilot"]["status"], "ok")
        self.assertEqual(task["pilot"]["seed_recall"], 1.0)
        self.assertEqual(task["pilot"]["title_relevance_ratio"], 0.0)
        self.assertEqual(task["pilot"]["title_abstract_precision_proxy"], 1.0)

    def test_allows_single_canonical_term_with_reason(self):
        plan = {"search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [{
                "name": "standard", "terms": ["ISO 14040"],
                "single_canonical_term_reason": "Official standard identifier",
            }],
        }]}
        task = lint_and_compile(plan)["tasks"][0]
        self.assertNotIn("block_0_needs_two_unique_terms", task["lint_errors"])

    def test_uses_title_abstract_precision_threshold(self):
        plan = {"search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [{"name": "object", "terms": ["battery", "energy storage"]}],
            "pilot_acceptance_criteria": {"min_title_abstract_precision_proxy": 0.75},
        }]}
        pilot = {"records": [
            {"search_task_id": "S1", "title": "Battery review"},
            {"search_task_id": "S1", "title": "Unrelated record"},
        ]}
        task = lint_and_compile(plan, pilot)["tasks"][0]
        self.assertEqual(task["pilot"]["status"], "low_precision")

    def test_run_pilot_executes_first_routed_source_and_tags_results(self):
        calls = []

        def fake_search(query, limit, use_cache):
            calls.append((query, limit, use_cache))
            return [{"title": "Cold plate topology optimization"}]

        plan = {"search_tasks": [{
            "id": "S1", "route": {"l1": ["openalex"]},
            "query_blocks": [{"name": "object", "terms": ["cold plate", "liquid cooling"]}],
        }]}
        payload = run_pilot(plan, limit=5, search_functions={"openalex": fake_search})

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 5)
        self.assertFalse(calls[0][2])
        self.assertEqual(payload["records"][0]["search_task_id"], "S1")
        self.assertEqual(payload["records"][0]["pilot_source"], "openalex")


if __name__ == "__main__":
    unittest.main()
