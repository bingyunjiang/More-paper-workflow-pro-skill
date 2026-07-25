from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import jsonschema
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from scripts.figure_evidence_pipeline import (
    FigureEvidenceError,
    extract_color_bars,
    extract_color_lines,
    extract_color_scatter,
    inspect_source,
    main,
    validate_project,
)
from scripts.visualspec import validate_visualspec


class FigureEvidencePipelineTest(unittest.TestCase):
    def _make_line_image(self, path: Path) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        for x in range(10, 111):
            y = int(round(65 - 0.4 * (x - 10)))
            draw.point((x, y), fill="#cc2244")
            draw.point((x, y + 1), fill="#cc2244")
        image.save(path)

    def _make_scatter_image(self, path: Path) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        for x, y in [(25, 55), (55, 40), (90, 25)]:
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#2266cc")
        image.save(path)

    def _make_bar_image(self, path: Path) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 45, 32, 70), fill="#22aa66")
        draw.rectangle((50, 30, 62, 70), fill="#22aa66")
        draw.rectangle((80, 18, 92, 70), fill="#22aa66")
        image.save(path)

    def test_inspect_without_chart_type_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            self._make_line_image(source)

            payload = inspect_source(source, None, project)

            self.assertEqual(payload["routing"]["status"], "needs_chart_type_confirmation")
            self.assertFalse(payload["routing"]["value_delivery_authorized"])
            self.assertEqual(validate_project(project)["status"], "pass")
            schema = json.loads(
                (ROOT / "schemas" / "figure-project-v1.schema.json").read_text(
                    encoding="utf-8"
                )
            )
            jsonschema.validate(payload, schema)

    def test_candidate_line_extraction_writes_evidence_and_visualspec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            output = root / "evidence"
            self._make_line_image(source)
            inspect_source(source, "line", project)

            report = extract_color_lines(
                project,
                output,
                plot_bounds=(10, 10, 110, 70),
                x_anchors=[(10, 0), (110, 10)],
                y_anchors=[(65, 0), (25, 4)],
                series=[("response", "#cc2244")],
                minimum_coverage=0.95,
                max_vertical_span_px=4,
                overlay_review_status="accepted",
            )

            self.assertTrue(report["value_delivery_authorized"])
            self.assertEqual(report["extraction_status"], "authorized_candidate")
            self.assertTrue((output / "digitized_lines.csv").is_file())
            self.assertTrue((output / "digitization_overlay.png").is_file())
            self.assertTrue((output / "extraction_report.json").is_file())
            visualspec = json.loads((output / "visualspec.json").read_text(encoding="utf-8"))
            self.assertEqual(validate_visualspec(visualspec), [])

    def test_overlay_review_gate_blocks_visualspec_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            output = root / "evidence"
            self._make_line_image(source)
            inspect_source(source, "line", project)

            report = extract_color_lines(
                project,
                output,
                plot_bounds=(10, 10, 110, 70),
                x_anchors=[(10, 0), (110, 10)],
                y_anchors=[(65, 0), (25, 4)],
                series=[("response", "#cc2244")],
                minimum_coverage=0.95,
                max_vertical_span_px=4,
            )

            self.assertFalse(report["value_delivery_authorized"])
            self.assertEqual(report["extraction_status"], "needs_review")
            self.assertIsNone(report["artifacts"]["visualspec"])
            self.assertTrue((output / "digitization_overlay.png").is_file())

    def test_low_coverage_does_not_materialize_visualspec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            output = root / "evidence"
            self._make_line_image(source)
            inspect_source(source, "line", project)

            report = extract_color_lines(
                project,
                output,
                plot_bounds=(10, 10, 110, 70),
                x_anchors=[(10, 0), (110, 10)],
                y_anchors=[(65, 0), (25, 4)],
                series=[("absent", "#22cc44")],
            )

            self.assertFalse(report["value_delivery_authorized"])
            self.assertEqual(report["extraction_status"], "not_extracted")
            self.assertIsNone(report["artifacts"]["visualspec"])
            self.assertFalse((output / "visualspec.json").exists())

    def test_source_hash_mismatch_blocks_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            self._make_line_image(source)
            inspect_source(source, "line", project)
            Image.new("RGB", (120, 80), "black").save(source)

            with self.assertRaises(FigureEvidenceError):
                extract_color_lines(
                    project,
                    root / "evidence",
                    plot_bounds=(10, 10, 110, 70),
                    x_anchors=[(10, 0), (110, 10)],
                    y_anchors=[(65, 0), (25, 4)],
                    series=[("response", "#cc2244")],
                )

    def test_scatter_extraction_requires_overlay_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scatter.png"
            project = root / "project.json"
            output = root / "evidence"
            self._make_scatter_image(source)
            inspect_source(source, "scatter", project)

            pending = extract_color_scatter(
                project,
                output,
                plot_bounds=(10, 10, 110, 70),
                x_anchors=[(10, 0), (110, 10)],
                y_anchors=[(70, 0), (10, 6)],
                series=[("samples", "#2266cc")],
            )
            accepted = extract_color_scatter(
                project,
                output,
                plot_bounds=(10, 10, 110, 70),
                x_anchors=[(10, 0), (110, 10)],
                y_anchors=[(70, 0), (10, 6)],
                series=[("samples", "#2266cc")],
                overlay_review_status="accepted",
            )

            visualspec = json.loads(
                (output / "visualspec.json").read_text(encoding="utf-8")
            )

        self.assertEqual("needs_review", pending["extraction_status"])
        self.assertFalse(pending["value_delivery_authorized"])
        self.assertEqual("authorized_candidate", accepted["extraction_status"])
        self.assertTrue(accepted["value_delivery_authorized"])
        self.assertEqual([], validate_visualspec(visualspec))

    def test_bar_and_histogram_route_extracts_visible_rectangles(self) -> None:
        for chart_type in ("simple_bar", "grouped_bar", "histogram"):
            with self.subTest(chart_type=chart_type), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "bars.png"
                project = root / "project.json"
                output = root / "evidence"
                self._make_bar_image(source)
                inspect_source(source, chart_type, project)

                report = extract_color_bars(
                    project,
                    output,
                    plot_bounds=(10, 10, 110, 70),
                    x_anchors=[(10, 0), (110, 10)],
                    y_anchors=[(70, 0), (10, 6)],
                    series=[("bars", "#22aa66")],
                    baseline_pixel=70,
                    overlay_review_status="accepted",
                )
                visualspec = json.loads(
                    (output / "visualspec.json").read_text(encoding="utf-8")
                )
                rows = (output / "digitized_bars.csv").read_text(
                    encoding="utf-8"
                ).splitlines()

            self.assertTrue(report["value_delivery_authorized"])
            self.assertEqual(4, len(rows))
            self.assertEqual([], validate_visualspec(visualspec))

    def test_bar_route_refuses_nonzero_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bars.png"
            project = root / "project.json"
            self._make_bar_image(source)
            inspect_source(source, "simple_bar", project)
            with self.assertRaises(FigureEvidenceError):
                extract_color_bars(
                    project,
                    root / "evidence",
                    plot_bounds=(10, 10, 110, 70),
                    x_anchors=[(10, 0), (110, 10)],
                    y_anchors=[(70, 5), (10, 11)],
                    series=[("bars", "#22aa66")],
                    baseline_pixel=70,
                )

    def test_cli_runs_two_stage_review_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            output = root / "evidence"
            self._make_line_image(source)

            with redirect_stdout(io.StringIO()):
                inspect_code = main([
                    "inspect",
                    "--input", str(source),
                    "--chart-type", "line",
                    "--output-project", str(project),
                ])
                pending_code = main([
                    "extract-line",
                    "--project", str(project),
                    "--plot-bounds", "10,10,110,70",
                    "--x-anchor", "10,0",
                    "--x-anchor", "110,10",
                    "--y-anchor", "65,0",
                    "--y-anchor", "25,4",
                    "--series", "response=#cc2244",
                    "--minimum-coverage", "0.95",
                    "--max-vertical-span-px", "4",
                    "--output-dir", str(output),
                ])
                accepted_code = main([
                    "extract-line",
                    "--project", str(project),
                    "--plot-bounds", "10,10,110,70",
                    "--x-anchor", "10,0",
                    "--x-anchor", "110,10",
                    "--y-anchor", "65,0",
                    "--y-anchor", "25,4",
                    "--series", "response=#cc2244",
                    "--minimum-coverage", "0.95",
                    "--max-vertical-span-px", "4",
                    "--overlay-review", "accepted",
                    "--output-dir", str(output),
                ])

            self.assertEqual(inspect_code, 0)
            self.assertEqual(pending_code, 3)
            self.assertEqual(accepted_code, 0)
            self.assertTrue((output / "visualspec.json").is_file())


if __name__ == "__main__":
    unittest.main()
