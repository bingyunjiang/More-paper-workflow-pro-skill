from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_skill_package import build_package, should_include


class BuildSkillPackageTest(unittest.TestCase):
    def test_virtual_environments_and_local_caches_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "demo-skill"
            (root / "scripts").mkdir(parents=True)
            (root / "scripts" / "run.py").write_text("print('ok')\n", encoding="utf-8")
            excluded = [
                root / ".venv" / "lib" / "site-packages" / "demo.py",
                root / "venv" / "bin" / "python",
                root / "env" / "Lib" / "site-packages" / "demo.py",
                root / ".test-venv" / "lib" / "demo.py",
                root / ".ruff_cache" / "state.json",
                root / "paper-temp" / "download_manifest.json",
            ]
            for path in excluded:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("local-only\n", encoding="utf-8")

            archive_path = build_package(root, parent / "demo.zip")
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()

        self.assertIn("demo-skill/scripts/run.py", names)
        self.assertFalse(any("site-packages" in name for name in names))
        self.assertFalse(any(".test-venv" in name for name in names))
        self.assertFalse(any("/.venv/" in name or "/venv/" in name or "/env/" in name for name in names))
        self.assertFalse(any(".ruff_cache" in name for name in names))
        self.assertFalse(any("paper-temp" in name for name in names))

    def test_dot_test_prefix_is_rejected_even_outside_known_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            path = root / ".test-runtime" / "file.txt"
            path.parent.mkdir(parents=True)
            path.write_text("local-only\n", encoding="utf-8")
            self.assertFalse(should_include(path, root))


if __name__ == "__main__":
    unittest.main()
