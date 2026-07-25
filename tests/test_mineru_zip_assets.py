import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "mineru_zip_assets.py"


class MinerUZipAssetsTest(unittest.TestCase):
    def test_cli_generates_figure_index_and_copies_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "LLM-for-Zotero-MinerU-cache-8DYA42PB.zip"
            out = root / "figure_index.json"
            figures = root / "figures"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("_llm_source.json", json.dumps({
                    "parentItemKey": "AX5588SA",
                    "attachmentKey": "8DYA42PB",
                    "sourceFilename": "demo.pdf",
                }))
                zf.writestr("full.md", "# Demo\n\n![](images/fig-a.jpg)\n")
                zf.writestr("manifest.json", json.dumps({
                    "sections": [
                        {
                            "heading": "Results",
                            "page": 1,
                            "figures": [
                                {
                                    "label": "image-1",
                                    "path": "images/fig-a.jpg",
                                    "caption": "Figure 1 demo",
                                    "page": 1,
                                }
                            ],
                        }
                    ]
                }))
                zf.writestr("images/fig-a.jpg", b"fake-image")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--zip",
                    str(zip_path),
                    "--output",
                    str(out),
                    "--figures-dir",
                    str(figures),
                    "--copy-images",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertIn("FIGURES: 1", result.stdout)
        self.assertEqual(data["schema_version"], "figure-index.v1")
        self.assertEqual(data["records"][0]["source_item_key"], "AX5588SA")
        self.assertEqual(data["records"][0]["source_attachment_key"], "8DYA42PB")
        self.assertTrue(data["records"][0]["source_image_path"].endswith("::images/fig-a.jpg"))
        self.assertIn("figures/image-1-", data["records"][0]["local_image_path"])
        self.assertTrue(data["records"][0]["local_image_path"].endswith(".jpg"))


if __name__ == "__main__":
    unittest.main()
