from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

import scripts.validate_skill_package as package_validator
import scripts.build_skill_package as package_builder


class ManifestAndPluginContractsTest(unittest.TestCase):
    def test_top_level_manifest_routes_all_eight_steps(self):
        text = (ROOT / "manifest.yaml").read_text(encoding="utf-8")
        allowed = set(package_validator.yaml_axis_allowed(text, "step"))
        routes = package_validator.yaml_mapping(text, "step_routes")
        self.assertEqual(len(allowed), 8)
        self.assertEqual(allowed, set(routes))
        for target in routes.values():
            self.assertTrue((ROOT / target).is_file(), target)

    def test_step7_modes_and_operations_match_public_contract(self):
        manifest = (ROOT / "manifest.step7.yaml").read_text(encoding="utf-8")
        entry = (ROOT / "agents" / "step_7_entry.md").read_text(encoding="utf-8")
        writing_modes = (ROOT / "references" / "writing-modes.md").read_text(encoding="utf-8")
        modes = set(package_validator.yaml_axis_allowed(manifest, "mode"))
        operations = set(package_validator.yaml_axis_allowed(manifest, "operation"))
        self.assertEqual(modes, package_validator.PUBLIC_STEP7_MODES)
        self.assertEqual(operations, package_validator.STEP7_OPERATIONS)
        self.assertEqual(modes, set(package_validator.yaml_mapping(manifest, "mode_routes")))
        self.assertEqual(operations, set(package_validator.yaml_mapping(manifest, "operation_routes")))
        for mode in modes:
            self.assertIn(f"`{mode}`", entry)
            self.assertIn(f"`{mode}`", writing_modes)
        for operation in operations:
            self.assertIn(f"`{operation}`", writing_modes)

    def test_root_is_self_contained_codex_plugin(self):
        plugin = ROOT / ".codex-plugin" / "plugin.json"
        entry = ROOT / "skills" / "more-paper-workflow" / "SKILL.md"
        self.assertTrue(plugin.is_file())
        self.assertTrue(entry.is_file())
        self.assertIn("../../SKILL.md", entry.read_text(encoding="utf-8"))
        self.assertNotIn("agents/step_*.md", (ROOT / "SKILL.md").read_text(encoding="utf-8"))
        for runtime_path in package_validator.STEP_RUNTIME_PATHS:
            self.assertIn(runtime_path, entry.read_text(encoding="utf-8"))
            self.assertTrue((ROOT / runtime_path).is_file(), runtime_path)
        self.assertFalse(
            (ROOT / "plugins" / "more-paper-workflow" / ".codex-plugin" / "plugin.json").exists()
        )

    def test_full_package_structure_validation_passes(self):
        result = package_validator.scan_skill(ROOT)
        self.assertEqual(result["status"], "ok", result["failures"])

    def test_step7_always_load_stays_lightweight(self):
        manifest = (ROOT / "manifest.step7.yaml").read_text(encoding="utf-8")
        always_load = package_validator.yaml_top_level_sequence(manifest, "always_load")
        self.assertLessEqual(len(always_load), 4)
        self.assertNotIn("references/equation-writing-contract.md", always_load)
        self.assertIn("conditional_load:", manifest)

    def test_step7_all_manifest_markdown_targets_exist(self):
        manifest = (ROOT / "manifest.step7.yaml").read_text(encoding="utf-8")
        targets = package_validator.manifest_markdown_targets(manifest)
        self.assertGreaterEqual(len(targets), 20)
        for target in targets:
            self.assertTrue((ROOT / target).is_file(), target)

    def test_security_scan_rejects_local_codex_config_and_author_paths(self):
        failures = []
        local_path = "/" + "Users" + "/" + "Bing" + "/.local/bin/zotero-mcp"
        api_key_name = "ZOTERO" + "_API_KEY"
        package_validator.scan_text_security(
            f'{api_key_name} = "real-looking-token"\ncommand = "{local_path}"\n',
            ".codex/config.toml",
            failures,
        )
        codes = {failure["code"] for failure in failures}
        self.assertIn("local_codex_config_present", codes)
        self.assertIn("committed_secret_value", codes)
        self.assertIn("author_local_path", codes)

    def test_security_scan_allows_documented_placeholders(self):
        failures = []
        api_key_name = "ZOTERO" + "_API_KEY"
        library_id_name = "ZOTERO" + "_LIBRARY_ID"
        package_validator.scan_text_security(
            f'{api_key_name} = "your_key_here"\n{library_id_name} = "${{{library_id_name}}}"\n',
            "docs/ZOTERO_MCP_SETUP.md",
            failures,
        )
        self.assertEqual([], failures)

    def test_zip_validation_rejects_missing_step7_runtime_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            built = package_builder.build_package(ROOT, temp_root / "complete.zip")
            broken = temp_root / "missing-step7.zip"
            with zipfile.ZipFile(built, "r") as source, zipfile.ZipFile(broken, "w") as target:
                for info in source.infolist():
                    if info.filename.endswith("/agents/step_7_writing.md"):
                        continue
                    target.writestr(info, source.read(info.filename))

            result = package_validator.scan_zip(broken)

        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any(
                failure["code"] == "missing_required_zip_entry"
                and failure.get("target") == "/agents/step_7_writing.md"
                for failure in result["failures"]
            ),
            result,
        )

    def test_zip_validation_rejects_plugin_entry_that_escapes_package_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            built = package_builder.build_package(ROOT, temp_root / "complete.zip")
            broken = temp_root / "escaped-entry.zip"
            with zipfile.ZipFile(built, "r") as source, zipfile.ZipFile(broken, "w") as target:
                for info in source.infolist():
                    payload = source.read(info.filename)
                    if info.filename.endswith("/skills/more-paper-workflow/SKILL.md"):
                        payload = payload.replace(b"../../SKILL.md", b"../../../SKILL.md")
                    target.writestr(info, payload)

            result = package_validator.scan_zip(broken)

        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any(
                failure["code"] == "invalid_zip_canonical_skill_reference"
                and failure.get("target") == "../../../SKILL.md"
                for failure in result["failures"]
            ),
            result,
        )


if __name__ == "__main__":
    unittest.main()
