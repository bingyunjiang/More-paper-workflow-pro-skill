from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from paper_diagrams.engine import render_from_file
from paper_diagrams.model import DIAGRAM_TYPES, STYLE_IDS, DiagramSpecError, load_spec
from paper_diagrams.render import build_scene, publication_profile, render_svg
from unittest.mock import patch


def payload(diagram_type: str = "flowchart", style: str = "clean") -> dict:
    return {
        "schema_version": "morepaper.paper-diagram.v1",
        "figure_id": f"fig-{diagram_type.replace('_', '-')}",
        "diagram_type": diagram_type,
        "style": style,
        "title": "方法流程",
        "caption": "可审阅的原生论文流程图",
        "canvas": {"width": 1200, "height": 800},
        "nodes": [
            {"id": "input", "label": "输入数据", "order": 1},
            {"id": "model", "label_runs": [{"kind": "text", "value": "模型 "}, {"kind": "math", "value": "y=f(x)"}], "order": 2},
            {"id": "output", "label": "结果审阅", "order": 3},
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "model"},
            {"id": "e2", "source": "model", "target": "output"},
        ],
        "groups": [],
        "annotations": [{"id": "note-1", "label": "公式需通过 Step 7 契约"}],
    }


class PaperDiagramTest(unittest.TestCase):
    def write_spec(self, root: Path, value: dict) -> Path:
        path = root / "diagram.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_all_type_style_combinations_build_semantic_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for diagram_type in sorted(DIAGRAM_TYPES):
                for style in sorted(STYLE_IDS):
                    spec = load_spec(self.write_spec(root, payload(diagram_type, style)))
                    scene = build_scene(spec)
                    self.assertFalse([item for item in scene.findings if item["severity"] == "fail"], (diagram_type, style, scene.findings))
                    svg = render_svg(scene)
                    self.assertIn('class="node"', svg)
                    self.assertIn('data-node-id="input"', svg)
                    self.assertNotIn("<script", svg.lower())

    def test_engine_emits_svg_png_check_inspect_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = render_from_file(self.write_spec(root, payload()), root / "figures", inspect=True)
            for key in ("svg", "png", "check", "inspect", "evidence"):
                self.assertTrue(Path(result[key]).is_file(), key)
            check = json.loads(Path(result["check"]).read_text(encoding="utf-8"))
            self.assertEqual("pass", check["status"])
            evidence = json.loads(Path(result["evidence"]).read_text(encoding="utf-8"))
            self.assertEqual("diagram", evidence["records"][0]["generation_backend"])
            self.assertIn('class="math-run"', Path(result["svg"]).read_text(encoding="utf-8"))

    def test_minimal_style_is_print_black_white_with_scaled_typography(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            value = payload(style="minimal")
            value["canvas"] = {"width": 2000, "height": 1600}
            value["groups"] = [{"id": "method", "label": "方法", "node_ids": ["input", "model", "output"]}]
            spec = load_spec(self.write_spec(Path(tmp), value))
            scene = build_scene(spec)
            self.assertFalse([item for item in scene.findings if item["severity"] == "fail"], scene.findings)
            svg = render_svg(scene)
            self.assertEqual({"#000000", "#ffffff"}, set(re.findall(r"#[0-9a-fA-F]{6}", svg)))
            self.assertIn('data-group-id="method"><rect', svg)
            self.assertIn('fill="none" stroke="#000000"', svg)
            profile = publication_profile(spec)
            self.assertEqual("black_white_full_width", profile["mode"])
            self.assertEqual(30, profile["node_font_px"])
            self.assertGreaterEqual(profile["node_font_pt_at_180mm"], 7.0)

    def test_minimal_engine_report_records_publication_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = render_from_file(self.write_spec(root, payload(style="minimal")), root / "figures")
            check = json.loads(Path(result["check"]).read_text(encoding="utf-8"))
            profile = check["publication_profile"]
            self.assertTrue(profile["black_white_only"])
            self.assertTrue(profile["no_tinted_background"])
            self.assertEqual([170, 180], profile["recommended_width_mm"])
            self.assertLessEqual(profile["minimum_width_mm_for_7pt"], 165.0)

    def test_cjk_text_fails_closed_when_selected_font_lacks_glyphs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("font_discovery.pil_font_path_candidates", return_value=[Path("/tmp/no-font.ttf")]), patch(
                "font_discovery.font_supports_text", return_value=False
            ):
                with self.assertRaisesRegex(DiagramSpecError, "CJK text"):
                    render_from_file(self.write_spec(Path(tmp), payload()), Path(tmp) / "figures")

    def test_english_only_diagram_does_not_require_cjk_font(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            value = payload()
            value["title"] = "Method flow"
            for node in value["nodes"]:
                node.pop("label_runs", None)
                node["label"] = "Input" if node["id"] == "input" else "Model"
            value["annotations"] = []
            with patch("font_discovery.pil_font_path_candidates", return_value=[]):
                result = render_from_file(self.write_spec(Path(tmp), value), Path(tmp) / "figures")
            self.assertTrue(Path(result["svg"]).is_file())

    def test_unknown_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            value = payload()
            value["remote_template"] = "ignored"
            with self.assertRaisesRegex(DiagramSpecError, "unknown fields"):
                load_spec(self.write_spec(Path(tmp), value))

    def test_dangling_edge_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            value = payload()
            value["edges"][0]["target"] = "missing"
            with self.assertRaisesRegex(DiagramSpecError, "missing node"):
                load_spec(self.write_spec(Path(tmp), value))

    def test_unsupported_math_needs_author_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            value = payload()
            value["nodes"][0]["label"] = "$\\begin{matrix}1&2\\end{matrix}$"
            with self.assertRaises(DiagramSpecError) as raised:
                load_spec(self.write_spec(Path(tmp), value))
            self.assertTrue(raised.exception.needs_author_check)

    def test_external_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            value = payload()
            value["nodes"][0]["label"] = "https://example.invalid/payload"
            with self.assertRaisesRegex(DiagramSpecError, "external or executable"):
                load_spec(self.write_spec(Path(tmp), value))


if __name__ == "__main__":
    unittest.main()
