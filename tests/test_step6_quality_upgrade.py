import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_zotero_plan import (  # noqa: E402
    ATTACHMENT_STATES, ITEM_STATES, apply_duplicate_states, apply_pdf_assignment_conflicts,
    ensure_unique_record_ids,
    plan_fingerprint, stable_record_id,
)
from validate_step6_output import validate  # noqa: E402
from zotero_operation_journal import record_operation  # noqa: E402


class Step6QualityUpgradeTest(unittest.TestCase):
    def write_execution_fixture(self, root: Path, *, operation_plan: str = "plan-a", include_success: bool = True) -> None:
        record = {
            "record_id": "r1", "item_state": "imported", "attachment_state": "matched_attachment",
        }
        item_counts = {state: int(state == "imported") for state in sorted(ITEM_STATES)}
        attachment_counts = {state: int(state == "matched_attachment") for state in sorted(ATTACHMENT_STATES)}
        (root / "文献-Zotero架构对照.json").write_text(json.dumps({
            "artifact_type": "zotero_plan", "execution_mode": "local", "completion_state": "write_complete",
            "cp_zotero_write_confirmed": True, "plan_fingerprint": "plan-a", "records": [record],
            "state_counts": {"items": item_counts, "attachments": attachment_counts},
        }), encoding="utf-8")
        (root / "pdf-附件池索引.json").write_text("{}", encoding="utf-8")
        operation = {
            "event_id": "event-1", "operation_id": "op-1", "operation_type": "create_item",
            "target_id": "r1", "status": "success" if include_success else "failed",
            "plan_fingerprint": operation_plan,
        }
        (root / "zotero_execution_state.json").write_text(json.dumps({"operations": {"op-1": operation}}), encoding="utf-8")
        (root / "zotero_write_operations.jsonl").write_text(json.dumps(operation) + "\n", encoding="utf-8")

    def test_duplicate_doi_is_a_candidate_not_auto_merged(self):
        records = [
            {"record_id": "r1", "doi": "10.1000/demo", "title": "A", "authors": ["One"], "year": "2024", "item_state": "planned"},
            {"record_id": "r2", "doi": "10.1000/demo", "title": "A", "authors": ["One"], "year": "2024", "item_state": "planned"},
        ]
        apply_duplicate_states(records)
        self.assertEqual(records[1]["item_state"], "duplicate_candidate")
        self.assertEqual(records[1]["duplicate_of_record_id"], "r1")

    def test_record_id_is_stable_across_input_order(self):
        first = {"doi": "10.1000/demo", "citekey": "one2024", "title": "A", "authors": ["One"], "year": "2024"}
        second = {"source_id": "CNKI-1", "citekey": "two2023", "title": "B", "authors": ["Two"], "year": "2023"}
        ids_forward = {stable_record_id(item) for item in [first, second]}
        ids_reverse = {stable_record_id(item) for item in [second, first]}
        self.assertEqual(ids_forward, ids_reverse)

    def test_duplicate_doi_with_distinct_citekeys_has_distinct_record_ids(self):
        first = {"doi": "10.1000/demo", "citekey": "one2024", "title": "A"}
        second = {"doi": "10.1000/demo", "citekey": "two2024", "title": "A"}
        self.assertNotEqual(stable_record_id(first), stable_record_id(second))

    def test_exact_duplicate_records_get_non_self_referencing_ids(self):
        records = [
            {"record_id": "same", "doi": "10.1000/demo", "item_state": "planned"},
            {"record_id": "same", "doi": "10.1000/demo", "item_state": "planned"},
        ]
        ensure_unique_record_ids(records)
        apply_duplicate_states(records)
        self.assertEqual(records[1]["record_id"], "same-dup2")
        self.assertEqual(records[1]["duplicate_of_record_id"], "same")

    def test_plan_fingerprint_is_order_independent_and_state_sensitive(self):
        records = [
            {"record_id": "r2", "item_state": "planned", "attachment_state": "missing_attachment"},
            {"record_id": "r1", "item_state": "planned", "attachment_state": "matched_attachment"},
        ]
        self.assertEqual(plan_fingerprint(records, "Root"), plan_fingerprint(list(reversed(records)), "Root"))
        changed = [dict(item) for item in records]
        changed[0]["collection_path"] = ["Root", "Changed"]
        self.assertNotEqual(plan_fingerprint(records, "Root"), plan_fingerprint(changed, "Root"))

    def test_shared_pdf_is_attachment_conflict_for_all_records(self):
        records = [
            {"record_id": "r1", "pdf_path": "/tmp/shared.pdf", "attachment_state": "matched_attachment"},
            {"record_id": "r2", "pdf_path": "/tmp/shared.pdf", "attachment_state": "matched_attachment"},
        ]
        apply_pdf_assignment_conflicts(records)
        self.assertTrue(all(item["attachment_state"] == "attachment_conflict" for item in records))
        self.assertEqual(records[0]["shared_pdf_record_ids"], ["r1", "r2"])

    def test_operation_journal_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            operation = {"operation_type": "create_item", "target_id": "r1", "status": "success", "checkpoint_confirmed": True}
            first = record_operation(tmp, operation)
            second = record_operation(tmp, operation)
            lines = (Path(tmp) / "zotero_write_operations.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertFalse(first["skipped"])
        self.assertTrue(second["skipped"])
        self.assertEqual(len(lines), 1)

    def test_operation_journal_rejects_changed_payload_for_same_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {"operation_type": "create_item", "target_id": "r1", "status": "planned", "payload": {"title": "A"}}
            record_operation(tmp, base)
            with self.assertRaises(ValueError):
                record_operation(tmp, {**base, "payload": {"title": "B"}})

    def test_new_plan_fingerprint_gets_new_operation_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = {"operation_type": "create_item", "target_id": "r1", "status": "success"}
            first = record_operation(tmp, {**base, "plan_fingerprint": "plan-a"})
            second = record_operation(tmp, {**base, "plan_fingerprint": "plan-b"})
        self.assertNotEqual(first["operation_id"], second["operation_id"])

    def test_write_complete_requires_success_for_each_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_execution_fixture(root, include_success=False)
            findings, summary = validate(root)
        self.assertEqual(summary["status"], "fail")
        self.assertTrue(any(item.code == "records_without_successful_operation" for item in findings))

    def test_write_complete_rejects_stale_plan_operations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_execution_fixture(root, operation_plan="plan-old")
            findings, summary = validate(root)
        self.assertEqual(summary["status"], "fail")
        self.assertTrue(any(item.code == "stale_execution_operation" for item in findings))

    def test_write_complete_passes_with_current_successful_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_execution_fixture(root)
            findings, summary = validate(root)
        self.assertEqual(summary["status"], "pass", findings)

    def test_pdf_only_direct_entry_is_plan_ready_without_step5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            (pdf_dir / "unlinked.pdf").write_bytes(b"%PDF-1.4\n<< /Type /Page >>\n" + b"x" * 6000)
            result = subprocess.run([
                sys.executable, str(SCRIPTS / "build_zotero_plan.py"),
                "--pdf-dir", str(pdf_dir),
                "--output", str(root / "文献-Zotero架构对照.json"),
                "--review", str(root / "文献-Zotero架构对照.md"),
                "--pdf-index", str(root / "pdf-附件池索引.json"),
            ], capture_output=True, text=True, check=False)
            plan = json.loads((root / "文献-Zotero架构对照.json").read_text(encoding="utf-8"))
            findings, summary = validate(root)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(plan["direct_entry"])
        self.assertEqual(plan["execution_profile"], "plan-only")
        self.assertEqual(plan["completion_state"], "plan_ready")
        self.assertEqual(summary["status"], "pass", findings)

    def test_records_json_direct_entry_does_not_require_bib_or_step5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = root / "zotero_readonly_scan.json"
            records.write_text(json.dumps({"items": [{
                "id": "ITEM0001", "title": "Direct Zotero record", "DOI": "10.1000/direct",
                "author": [{"family": "Author"}], "year": "2025",
            }]}), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SCRIPTS / "build_zotero_plan.py"),
                "--records-json", str(records),
                "--output", str(root / "文献-Zotero架构对照.json"),
                "--review", str(root / "文献-Zotero架构对照.md"),
                "--pdf-index", str(root / "pdf-附件池索引.json"),
            ], capture_output=True, text=True, check=False)
            plan = json.loads((root / "文献-Zotero架构对照.json").read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(plan["records"][0]["item_state"], "planned")
        self.assertNotIn("文献库.bib", plan["blocking_missing"])


if __name__ == "__main__":
    unittest.main()
