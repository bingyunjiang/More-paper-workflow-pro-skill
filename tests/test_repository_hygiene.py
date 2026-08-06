from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_markdown_links
import check_offline_packages
import check_doc_contracts


class RepositoryHygieneTest(unittest.TestCase):
    def test_markdown_relative_links_resolve(self):
        self.assertEqual(check_markdown_links.scan(), [])

    def test_offline_package_manifest_matches_cache(self):
        self.assertEqual(check_offline_packages.check_manifest(), [])
        self.assertEqual(check_offline_packages.check_manifest(strict=True), [])
        self.assertFalse(
            any(path.name.endswith((".tar.gz", ".zip")) for path in check_offline_packages.iter_package_paths())
        )

    def test_document_contracts_are_structured(self):
        self.assertEqual(check_doc_contracts.check(), [])
        inventory = check_doc_contracts.inventory()
        self.assertEqual(inventory["main_step_document_count"], 8)
        self.assertEqual(inventory["step5_route_phases"], ["Phase 1", "Phase 2", "Phase 3", "Phase 4"])
        self.assertGreaterEqual(inventory["python_script_count"], 1)
        self.assertGreaterEqual(inventory["publisher_config_count"], 1)


if __name__ == "__main__":
    unittest.main()
