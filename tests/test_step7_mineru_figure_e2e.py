from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_deep_read_cards import build_cards  # noqa: E402
from build_figure_asset_check import build_asset_check, render_markdown  # noqa: E402
from mineru_zip_assets import scan_mineru_zip  # noqa: E402
from resolve_figure_refs import resolve_figure_refs  # noqa: E402
from validate_step7_output import validate  # noqa: E402


class Step7MinerUFigureE2ETest(unittest.TestCase):
    def test_mineru_zip_to_original_figure_ready_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "LLM-for-Zotero-MinerU-cache-ATT123.zip"
            image_buffer = io.BytesIO()
            Image.new("RGB", (20, 12), "#2266cc").save(image_buffer, format="PNG")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(
                    "_llm_source.json",
                    json.dumps(
                        {
                            "parentItemKey": "ITEM123",
                            "attachmentKey": "ATT123",
                            "sourceFilename": "temperature-study.pdf",
                        }
                    ),
                )
                zf.writestr(
                    "full.md",
                    "# Results\n\nThe temperature distribution is reported in Figure 2.\n",
                )
                zf.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "sections": [
                                {
                                    "heading": "Results",
                                    "figures": [
                                        {
                                            "label": "Fig. 2",
                                            "path": "images/figure-2.png",
                                            "caption": "Temperature distribution",
                                            "page": 4,
                                        }
                                    ],
                                }
                            ]
                        }
                    ),
                )
                zf.writestr("images/figure-2.png", image_buffer.getvalue())

            mapping = root / "mapping.json"
            mapping.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "record_id": "record-1",
                                "citekey": "author2024",
                                "title": "Temperature Study",
                                "chapter_id": "2.1",
                                "zotero_item_key": "ITEM123",
                                "paper_card": {
                                    "evidence_role": "experiment",
                                    "reading_depth": "full_text",
                                    "content_fit": "direct",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            figure_index = root / "figure_index.json"
            scan_mineru_zip(archive, figure_index, root / "figures", False)
            cards_json = root / "deep_read_cards.json"
            build_cards(
                mapping_json=mapping,
                section_id="2.1",
                section_title="Results",
                max_records=5,
                output_json=cards_json,
                output_md=root / "deep_read_cards.md",
                fulltext_json=None,
                notes_json=None,
                prepared_pdf_artifacts=None,
                figure_index=str(figure_index),
                mineru_zips=[str(archive)],
                figures_dir=root / "figures",
            )

            source_draft = root / "source.md"
            source_draft.write_text(
                "# Results\n\nThe observed field is summarized below.\n\n"
                "[图: temperature distribution]\n",
                encoding="utf-8",
            )
            draft = root / "journal_paper_draft.md"
            resolve_figure_refs(
                draft_path=source_draft,
                cards_paths=[str(cards_json)],
                figure_index_path=str(figure_index),
                output_path=draft,
            )

            asset_check = build_asset_check(
                mineru_zips=[archive],
                figure_index=figure_index,
                image_dirs=[root / "figures"],
                pdfs=[],
                figure_action="auto",
                figure_mode="auto",
                transform_authorization="not_required",
            )
            (root / "figure_asset_check.json").write_text(
                json.dumps(asset_check),
                encoding="utf-8",
            )
            (root / "figure_asset_check.md").write_text(
                render_markdown(asset_check),
                encoding="utf-8",
            )
            (root / "step7_execution_card.md").write_text(
                "# Step 7 Execution Card\n\n"
                "- target_state: draft_ready\n"
                "- figure_mode: auto_insert\n"
                "- figure_backend: not_applicable\n"
                "- risk_status: citations_pending\n",
                encoding="utf-8",
            )

            findings, summary = validate(root, "draft_ready")
            report = json.loads(
                (root / "figure_resolution_report.json").read_text(encoding="utf-8")
            )
            inserted = [
                path
                for path in (root / "figures").glob("*.png")
                if path.is_file()
            ]

        self.assertEqual("pass", summary["status"], findings)
        self.assertEqual(1, report["resolved_count"])
        self.assertEqual(1, len(inserted))
        self.assertEqual(
            report["records"][0]["source_image_sha256"],
            report["records"][0]["materialized_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
