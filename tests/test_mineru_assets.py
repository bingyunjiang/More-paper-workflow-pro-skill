from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mineru_assets import enumerate_mineru_assets, match_mineru_zip  # noqa: E402


class MinerUAssetsTest(unittest.TestCase):
    def _write_zip(
        self,
        path: Path,
        *,
        parent: str,
        attachment: str,
        source_filename: str,
        manifest: dict | None = None,
        full_md: str = "",
    ) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "_llm_source.json",
                json.dumps(
                    {
                        "parentItemKey": parent,
                        "attachmentKey": attachment,
                        "sourceFilename": source_filename,
                    }
                ),
            )
            if manifest is not None:
                archive.writestr("manifest.json", json.dumps(manifest))
            if full_md:
                archive.writestr("full.md", full_md)
            archive.writestr("images/fig-a.png", b"png-a")
            archive.writestr("images/fig-b.jpg", b"jpg-b")

    def test_manifest_full_md_and_images_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "LLM-for-Zotero-MinerU-cache-A.zip"
            self._write_zip(
                archive,
                parent="ITEM-A",
                attachment="ATT-A",
                source_filename="paper-a.pdf",
                manifest={
                    "sections": [
                        {
                            "heading": "Results",
                            "figures": [
                                {
                                    "label": "Figure 1",
                                    "path": "images/fig-a.png",
                                    "caption": "Temperature distribution",
                                    "page": 3,
                                }
                            ],
                        }
                    ],
                    "allFigures": [
                        {
                            "label": "Figure 1 duplicate",
                            "path": "images/fig-a.png",
                            "caption": "",
                        }
                    ],
                },
                full_md="![duplicate](images/fig-a.png)\n![Figure B](images/fig-b.jpg)\n",
            )
            assets = enumerate_mineru_assets(archive)

        self.assertEqual(2, len(assets))
        by_path = {item["internal_path"]: item for item in assets}
        self.assertEqual("manifest", by_path["images/fig-a.png"]["source_stage"])
        self.assertEqual("Temperature distribution", by_path["images/fig-a.png"]["caption"])
        self.assertEqual("full_md", by_path["images/fig-b.jpg"]["source_stage"])
        self.assertIn("::images/fig-a.png", by_path["images/fig-a.png"]["source_image_path"])

    def test_images_scan_is_last_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "LLM-for-Zotero-MinerU-cache-B.zip"
            self._write_zip(
                archive,
                parent="ITEM-B",
                attachment="ATT-B",
                source_filename="paper-b.pdf",
            )
            assets = enumerate_mineru_assets(archive)

        self.assertEqual({"images_scan"}, {item["source_stage"] for item in assets})
        self.assertEqual(2, len(assets))

    def test_exact_parent_item_key_wins_over_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrong = root / "wrong.zip"
            right = root / "right.zip"
            self._write_zip(
                wrong,
                parent="OTHER",
                attachment="ATT-1",
                source_filename="exact title paper.pdf",
            )
            self._write_zip(
                right,
                parent="ITEM-123",
                attachment="ATT-2",
                source_filename="unrelated-name.pdf",
            )
            matched = match_mineru_zip(
                {
                    "zotero_item_key": "ITEM-123",
                    "title": "Exact Title Paper",
                },
                [wrong, right],
            )

        self.assertEqual(right.resolve(), matched)


if __name__ == "__main__":
    unittest.main()
