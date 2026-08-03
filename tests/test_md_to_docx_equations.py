import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from equation_guard import audit_paths  # noqa: E402


@unittest.skipUnless(shutil.which("pandoc"), "pandoc is required for DOCX equation transfer tests")
class MarkdownToDocxEquationTest(unittest.TestCase):
    def run_conversion(self, markdown: str) -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory]:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        source = root / "paper.md"
        output = root / "paper.docx"
        source.write_text(markdown, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "md_to_docx.py"), str(source), "-o", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return result, output, temp_dir

    def test_canonical_markdown_math_becomes_native_word_equations(self):
        result, output, temp_dir = self.run_conversion(
            "# 方法\n\n输入为 $X_{\\mathrm{in}}$。\n\n"
            "$$F_{i+1}(\\omega)=T(\\omega)X_{\\mathrm{in}}$$\n"
        )
        try:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.is_file())
            audit, _ = audit_paths([output])
            self.assertEqual(audit["summary"]["status"], "pass", audit["findings"])
            self.assertGreaterEqual(audit["summary"]["native_math_count"], 2)
        finally:
            temp_dir.cleanup()

    def test_plain_text_math_is_blocked_before_docx_delivery(self):
        result, output, temp_dir = self.run_conversion(
            "# 方法\n\n状态方程可表示为：\n\nT(omega), F_{i+1}, X_in\n"
        )
        try:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Markdown 公式预检失败", result.stdout)
            self.assertFalse(output.exists())
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
