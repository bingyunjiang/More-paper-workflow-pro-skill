from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import check_environment as environment


class CheckEnvironmentCapabilityTest(unittest.TestCase):
    def test_core_does_not_require_figure_modules_or_fonts(self) -> None:
        with patch.object(environment, "module_version", return_value=None), patch.object(
            environment, "font_available", return_value=False
        ), patch.object(environment.shutil, "which", return_value=None):
            result = environment.check_environment("core")

        self.assertEqual("pass", result["status"])
        self.assertEqual({}, result["required_modules"])
        self.assertEqual("none", result["font_requirement"])
        self.assertFalse(result["cjk_ready"])

    def test_chinese_diagram_requires_cjk_font_only_for_that_capability(self) -> None:
        with patch.object(environment, "module_version", return_value="installed"), patch.object(
            environment, "font_available", return_value=False
        ), patch.object(environment.shutil, "which", return_value=None):
            result = environment.check_environment("chinese_diagram")

        self.assertEqual("failed", result["status"])
        self.assertIn("missing_cjk_font", result["blocking_reasons"])
        self.assertEqual([], result["missing_required"])

    def test_strict_reproduction_reports_only_its_missing_modules(self) -> None:
        def module_version(name: str):
            return None if name == "skimage" else "installed"

        with patch.object(environment, "module_version", side_effect=module_version), patch.object(
            environment, "font_available", return_value=True
        ), patch.object(environment.shutil, "which", return_value=None):
            result = environment.check_environment("strict_reproduction")

        self.assertEqual(["skimage"], result["missing_required"])
        self.assertIn("missing_module:skimage", result["blocking_reasons"])

    def test_docx_export_checks_pandoc_without_requiring_figure_stack(self) -> None:
        with patch.object(environment, "module_version", return_value=None), patch.object(
            environment, "font_available", return_value=False
        ), patch.object(environment.shutil, "which", return_value=None):
            result = environment.check_environment("docx_export")

        self.assertEqual({}, result["required_modules"])
        self.assertEqual(["pandoc"], result["missing_tools"])
        self.assertEqual("failed", result["status"])


if __name__ == "__main__":
    unittest.main()
