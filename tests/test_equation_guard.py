import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from equation_guard import audit_paths  # noqa: E402


class EquationGuardTest(unittest.TestCase):
    def audit_text(self, text: str, suffix: str = ".md") -> tuple[dict, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"draft{suffix}"
            path.write_text(text, encoding="utf-8")
            return audit_paths([path])

    def write_docx(self, path: Path, paragraph_xml: str) -> None:
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
            f"<w:body>{paragraph_xml}</w:body></w:document>"
        )
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document_xml)

    def test_canonical_markdown_equations_pass(self):
        text = r"""# 方法

传递函数可表示为：

$$
\begin{bmatrix}
F_{i+1}(\omega) \\
V_{i+1}(\omega)
\end{bmatrix}\tag{1}
$$

式（1）描述了频域状态，其中 $X_{\mathrm{in}}$ 为输入量。
"""
        audit, register = self.audit_text(text)

        self.assertEqual(audit["summary"]["status"], "pass", audit["findings"])
        self.assertGreaterEqual(register["record_count"], 2)

    def test_user_reported_plain_text_and_matrix_source_are_blocked(self):
        text = (
            "# 方法\n\n"
            "状态方程可表示为：\n\n"
            "T(omega), F_{i+1}, X_in\n"
            "\\begin{bmatrix}\n"
            "F_{i+1}(omega)" + "\\\n" +
            "V_{i+1}(omega)\n"
            "\\end{bmatrix}\n"
        )
        audit, _ = self.audit_text(text)
        codes = {finding["code"] for finding in audit["findings"]}

        self.assertEqual(audit["summary"]["status"], "fail")
        self.assertIn("missing_equation", codes)
        self.assertIn("plain_text_math_leak", codes)
        self.assertIn("matrix_source_leak", codes)
        self.assertIn("malformed_matrix_rows", codes)

    def test_slash_delimiters_are_rejected_for_markdown_delivery(self):
        audit, _ = self.audit_text(r"传递函数为 \(T(\omega)\)。" + "\n")
        codes = {finding["code"] for finding in audit["findings"]}

        self.assertIn("noncanonical_math_delimiter", codes)

    def test_missing_equation_after_cue_is_blocking(self):
        audit, _ = self.audit_text("# 方法\n\n目标函数为：\n\n这里只剩解释文字。\n")

        self.assertTrue(any(finding["code"] == "missing_equation" for finding in audit["findings"]))

    def test_code_blocks_are_not_treated_as_paper_math(self):
        text = r"""# 附录

示例源码：

```latex
\begin{bmatrix}
F_{i+1}(omega)\
V_{i+1}(omega)
\end{bmatrix}
```
"""
        audit, _ = self.audit_text(text)

        self.assertEqual(audit["summary"]["status"], "pass", audit["findings"])

    def test_docx_plain_text_math_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.docx"
            self.write_docx(path, "<w:p><w:r><w:t>T(omega), X_in</w:t></w:r></w:p>")
            audit, _ = audit_paths([path])

        codes = {finding["code"] for finding in audit["findings"]}
        self.assertIn("plain_text_math_leak", codes)
        self.assertEqual(audit["summary"]["native_math_count"], 0)

    def test_docx_native_omml_equation_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native.docx"
            self.write_docx(
                path,
                "<w:p><w:r><w:t>传递函数为：</w:t></w:r></w:p>"
                "<w:p><m:oMath><m:r><m:t>T(ω)</m:t></m:r></m:oMath></w:p>",
            )
            audit, register = audit_paths([path])

        self.assertEqual(audit["summary"]["status"], "pass", audit["findings"])
        self.assertEqual(audit["summary"]["native_math_count"], 1)
        self.assertEqual(register["record_count"], 1)

    def test_cli_writes_all_standard_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = root / "draft.md"
            draft.write_text("# 方法\n\n输入量为 $X_{\\mathrm{in}}$。\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "equation_guard.py"), str(draft), "--output-dir", str(root)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name in (
                "equation_audit.json",
                "equation_audit.md",
                "equation_register.json",
                "equation_register.md",
            ):
                self.assertTrue((root / name).is_file(), name)
            payload = json.loads((root / "equation_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["schema_version"], "equation-audit.v1")


if __name__ == "__main__":
    unittest.main()
