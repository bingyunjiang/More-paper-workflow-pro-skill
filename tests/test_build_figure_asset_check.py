from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_figure_asset_check import build_asset_check  # noqa: E402


class FigureAssetCheckTest(unittest.TestCase):
    def test_generate_new_diagram_routes_to_native_backend(self) -> None:
        payload = build_asset_check(
            mineru_zips=[], figure_index=None, image_dirs=[], pdfs=[],
            figure_action="generate_new", figure_mode="auto",
            transform_authorization="not_required", figure_kind="diagram",
        )
        self.assertEqual("diagram", payload["figure_backend"])
        self.assertEqual("post_write", payload["figure_mode"])
        self.assertEqual("explicit_new_diagram_request", payload["routing_reason"])

    def test_mineru_assets_route_to_original_insertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "LLM-for-Zotero-MinerU-cache-A.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("_llm_source.json", "{}")
                zf.writestr("images/figure.png", b"image")
            payload = build_asset_check(
                mineru_zips=[archive],
                figure_index=None,
                image_dirs=[],
                pdfs=[],
                figure_action="auto",
                figure_mode="auto",
                transform_authorization="not_required",
            )

        self.assertEqual("ready", payload["status"])
        self.assertEqual("auto_insert", payload["figure_mode"])
        self.assertEqual("insert_original", payload["figure_asset_action"])
        self.assertEqual("not_applicable", payload["figure_backend"])

    def test_redraw_without_explicit_authorization_is_blocked(self) -> None:
        payload = build_asset_check(
            mineru_zips=[],
            figure_index=None,
            image_dirs=[],
            pdfs=[],
            figure_action="redraw",
            figure_mode="auto",
            transform_authorization="not_required",
        )
        self.assertEqual("blocked", payload["status"])
        self.assertIn(
            "figure_transform_requires_explicit_user_request",
            payload["errors"],
        )

    def test_nonempty_figure_index_is_an_original_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "figure_index.json"
            index.write_text(
                json.dumps({"records": [{"figure_id": "F1"}]}),
                encoding="utf-8",
            )
            payload = build_asset_check(
                mineru_zips=[],
                figure_index=index,
                image_dirs=[],
                pdfs=[],
                figure_action="auto",
                figure_mode="auto",
                transform_authorization="not_required",
            )
        self.assertTrue(payload["original_assets_available"])

    def test_pdf_only_routes_to_post_write_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            payload = build_asset_check(
                mineru_zips=[],
                figure_index=None,
                image_dirs=[],
                pdfs=[pdf],
                figure_action="auto",
                figure_mode="auto",
                transform_authorization="not_required",
            )
        self.assertEqual("post_write", payload["figure_mode"])
        self.assertEqual(
            "pdf_direct_candidate_pending_manual_check",
            payload["routing_reason"],
        )


if __name__ == "__main__":
    unittest.main()
