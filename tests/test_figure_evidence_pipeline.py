from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "scripts"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from scripts.figure_data_pipeline import (  # noqa: E402
    FigureDataError,
    build_data,
    build_observations,
    build_spec_review,
    build_visualspec,
    confirm_spec,
    migrate_legacy_digitized_lines,
    read_csv,
    review_template,
    sha256_file,
    validate_delivery,
    validate_visualspec_data_contract,
)
from scripts.figure_evidence_pipeline import (  # noqa: E402
    FigureEvidenceError,
    extract_color_bars,
    extract_color_lines,
    extract_color_scatter,
    inspect_source,
    validate_project,
)
from scripts.render_visualspec_matplotlib import render_file  # noqa: E402
from scripts.visualspec import validate_visualspec  # noqa: E402


class FigureEvidencePipelineTest(unittest.TestCase):
    BOUNDS = (10, 10, 110, 70)
    X_ANCHORS = [(10, 0), (110, 10)]
    Y_ANCHORS = [(65, 0), (25, 4)]
    SERIES = [("response", "#cc2244")]

    def _make_line_image(
        self,
        path: Path,
        *,
        gaps: list[tuple[int, int]] | None = None,
        dashed: bool = False,
        jpeg: bool = False,
    ) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        gaps = gaps or []
        for x in range(10, 111):
            if any(start <= x <= end for start, end in gaps):
                continue
            if dashed and (x - 10) % 10 >= 6:
                continue
            y = int(round(65 - 0.4 * (x - 10)))
            draw.point((x, y), fill="#cc2244")
            draw.point((x, y + 1), fill="#cc2244")
        image.save(path, quality=78 if jpeg else None)

    def _make_scatter_image(self, path: Path) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        for x, y in [(25, 55), (55, 40), (90, 25)]:
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#2266cc")
        image.save(path)

    def _make_bar_image(self, path: Path) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        for box in [(20, 45, 32, 70), (50, 30, 62, 70), (80, 18, 92, 70)]:
            draw.rectangle(box, fill="#22aa66")
        image.save(path)

    def _confirm(
        self,
        root: Path,
        project: Path,
        *,
        series: list[tuple[str, str]] | None = None,
        topology: str = "continuous",
        y_anchors: list[tuple[float, float]] | None = None,
    ) -> Path:
        review = root / "spec"
        series = series or self.SERIES
        build_spec_review(
            project,
            review,
            plot_bounds=self.BOUNDS,
            x_anchors=self.X_ANCHORS,
            y_anchors=y_anchors or self.Y_ANCHORS,
            series=series,
            curve_topology={name: topology for name, _ in series},
        )
        confirmation = review / "spec-confirmation.json"
        confirm_spec(
            project,
            review / "figure-spec.json",
            review / "spec-review.png",
            confirmation,
            confirmation="explicit_user_confirmation",
        )
        return confirmation

    def _extract(
        self,
        root: Path,
        *,
        gaps: list[tuple[int, int]] | None = None,
        dashed: bool = False,
        jpeg: bool = False,
        topology: str = "continuous",
    ) -> tuple[Path, Path, Path]:
        source = root / ("source.jpg" if jpeg else "source.png")
        project = root / "figure-project.json"
        output = root / "evidence"
        self._make_line_image(source, gaps=gaps, dashed=dashed, jpeg=jpeg)
        inspect_source(source, "line", project)
        confirmation = self._confirm(root, project, topology=topology)
        extract_color_lines(
            project,
            output,
            plot_bounds=self.BOUNDS,
            x_anchors=self.X_ANCHORS,
            y_anchors=self.Y_ANCHORS,
            series=self.SERIES,
            minimum_coverage=0.45,
            max_vertical_span_px=6,
            color_tolerance=90 if jpeg else 36,
            spec_confirmation_path=confirmation,
        )
        return project, confirmation, output

    def _review_and_build(
        self,
        output: Path,
        confirmation: Path,
        *,
        topology: str = "continuous",
    ) -> tuple[Path, Path, Path, Path]:
        candidates = output / "candidates.csv"
        quality = output / "quality-assessment.json"
        decisions = output / "review-decisions.json"
        review_template(candidates, quality, confirmation, decisions)
        payload = json.loads(decisions.read_text(encoding="utf-8"))
        payload["review_status"] = "complete"
        payload["normal_batch"] = {"action": "accept", "user_reply": "继续"}
        payload["series_topology"]["response"]["confirmed_by_user"] = True
        payload["series_topology"]["response"]["curve_topology"] = topology
        for item in payload["anomaly_decisions"]:
            item["action"] = "accept"
        if topology == "segmented":
            first_break = next(
                row["candidate_id"]
                for row in read_csv(candidates)
                if row["evidence_segment_break_before"] == "true"
            )
            payload["series_topology"]["response"]["formal_break_before_candidate_ids"] = [first_break]
        decisions.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        observations = output / "observations.csv"
        data = output / "data.csv"
        provenance = output / "data.provenance.json"
        build_observations(candidates, quality, decisions, observations)
        build_data(observations, decisions, data, provenance)
        return candidates, decisions, observations, data

    def test_inspect_without_chart_type_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "figure-project.json"
            self._make_line_image(source)
            payload = inspect_source(source, None, project)
            self.assertEqual(payload["routing"]["status"], "needs_chart_type_confirmation")
            self.assertEqual(payload["review_status"], "not_started")
            self.assertFalse(payload["routing"]["value_delivery_authorized"])
            self.assertEqual(validate_project(project)["status"], "pass")
            schema = json.loads((ROOT / "schemas" / "figure-project-v1.schema.json").read_text(encoding="utf-8"))
            jsonschema.validate(payload, schema)

    def test_candidate_extraction_never_materializes_visualspec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, output = self._extract(root)
            report = json.loads((output / "extraction_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["extraction_status"], "candidate_ready")
            self.assertEqual(report["review_status"], "not_reviewed")
            self.assertFalse(report["value_delivery_authorized"])
            self.assertTrue((output / "candidates.csv").is_file())
            self.assertTrue((output / "quality-assessment.json").is_file())
            self.assertFalse((output / "visualspec.json").exists())
            self.assertFalse((output / "digitized_lines.csv").exists())

    def test_occlusion_gap_is_evidence_not_formal_break_and_render_is_continuous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, confirmation, output = self._extract(root, gaps=[(50, 58)])
            _, _, observations, data = self._review_and_build(output, confirmation)
            observation_rows = read_csv(observations)
            data_rows = read_csv(data)
            self.assertTrue(any(row["evidence_segment_break_before"] == "true" for row in observation_rows))
            self.assertTrue(any(row["evidence_segment_break_before"] == "true" for row in data_rows))
            self.assertFalse(any(row["formal_segment_break_before"] == "true" for row in data_rows))
            spec = output / "visualspec.json"
            build_visualspec(data, output / "data.provenance.json", spec)
            payload = json.loads(spec.read_text(encoding="utf-8"))
            self.assertEqual(1, len(payload["panels"][0]["plots"]))
            render_file(spec, output / "render-solid")
            self.assertTrue((output / "render-solid" / "render.png").is_file())

    def test_dashed_pixels_remain_continuous_data_and_any_line_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, confirmation, output = self._extract(root, dashed=True)
            _, _, observations, data = self._review_and_build(output, confirmation)
            self.assertTrue(any(row["evidence_segment_break_before"] == "true" for row in read_csv(observations)))
            before_hash = sha256_file(data)
            before_rows = data.read_bytes()
            for style in ("solid", "dashed", "dashdot"):
                styles = output / f"styles-{style}.json"
                style_record = {"line_style": style, "color": "#cc2244"}
                if style == "dashdot":
                    style_record["marker"] = "o"
                styles.write_text(json.dumps({"schema": "morepaper.figure_styles.v1", "series": {"response": style_record}}) + "\n", encoding="utf-8")
                spec = output / f"visualspec-{style}.json"
                build_visualspec(data, output / "data.provenance.json", spec, styles_path=styles)
                render_file(spec, output / f"render-{style}")
                rendered_style = json.loads(spec.read_text())["panels"][0]["plots"][0]["style"]
                self.assertEqual(style, rendered_style["line_style"])
                if style == "dashdot":
                    self.assertEqual("o", rendered_style["marker"])
                self.assertEqual(before_hash, sha256_file(data))
                self.assertEqual(before_rows, data.read_bytes())

    def test_jpeg_short_gap_is_resolved_by_formal_data_not_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, confirmation, output = self._extract(root, gaps=[(62, 68)], jpeg=True)
            _, _, observations, data = self._review_and_build(output, confirmation)
            provenance = json.loads((output / "data.provenance.json").read_text())
            self.assertTrue(any(row["evidence_segment_break_before"] == "true" for row in read_csv(observations)))
            self.assertFalse(any(row["formal_segment_break_before"] == "true" for row in read_csv(data)))
            self.assertFalse(provenance["render_stage_interpolation"])
            self.assertFalse(provenance["render_stage_bridging"])

    def test_segmented_physical_curve_preserves_formal_break(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, confirmation, output = self._extract(root, gaps=[(45, 65)], topology="segmented")
            _, _, _, data = self._review_and_build(output, confirmation, topology="segmented")
            data_rows = read_csv(data)
            self.assertEqual(1, sum(row["formal_segment_break_before"] == "true" for row in data_rows))
            spec = output / "visualspec.json"
            build_visualspec(data, output / "data.provenance.json", spec)
            self.assertEqual(2, len(json.loads(spec.read_text())["panels"][0]["plots"]))

    def test_pre_extraction_and_hash_gates_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "project.json"
            self._make_line_image(source)
            inspect_source(source, "line", project)
            with self.assertRaisesRegex(FigureEvidenceError, "spec_not_confirmed"):
                extract_color_lines(project, root / "out", plot_bounds=self.BOUNDS, x_anchors=self.X_ANCHORS, y_anchors=self.Y_ANCHORS, series=self.SERIES)
            confirmation = self._confirm(root, project)
            Image.new("RGB", (120, 80), "black").save(source)
            with self.assertRaisesRegex(FigureEvidenceError, "source SHA-256 mismatch"):
                extract_color_lines(project, root / "out", plot_bounds=self.BOUNDS, x_anchors=self.X_ANCHORS, y_anchors=self.Y_ANCHORS, series=self.SERIES, spec_confirmation_path=confirmation)

    def test_project_or_spec_change_invalidates_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "figure.png"
            project = root / "project.json"
            self._make_line_image(source)
            inspect_source(source, "line", project)
            confirmation = self._confirm(root, project)
            payload = json.loads(project.read_text(encoding="utf-8"))
            payload["chart"]["chart_type_verified"] = False
            project.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(FigureEvidenceError, "project_spec_changed"):
                extract_color_lines(project, root / "out", plot_bounds=self.BOUNDS, x_anchors=self.X_ANCHORS, y_anchors=self.Y_ANCHORS, series=self.SERIES, spec_confirmation_path=confirmation)

    def test_review_and_visualspec_rejection_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, confirmation, output = self._extract(root, gaps=[(50, 58)])
            candidates = output / "candidates.csv"
            quality = output / "quality-assessment.json"
            decisions = output / "review-decisions.json"
            review_template(candidates, quality, confirmation, decisions)
            with self.assertRaisesRegex(FigureDataError, "ordinary candidates"):
                build_observations(candidates, quality, decisions, output / "observations.csv")
            with self.assertRaisesRegex(FigureDataError, "review-decisions.json is required"):
                build_data(output / "observations.csv", output / "missing.json", output / "data.csv", output / "data.provenance.json")
            fake_candidate_spec = output / "candidate-visualspec.json"
            fake_candidate_spec.write_text(json.dumps({"schema": "scientificfigure.visualspec.v2", "figure": {"size_mm": [100, 70], "dpi": 300}, "data_contract": {"kind": "formal_data_csv", "path": "candidates.csv"}, "panels": [{"id": "p", "bbox_normalized": [0.1, 0.1, 0.8, 0.8], "source_strategy": "digitized_raster", "plots": []}]}) + "\n")
            self.assertEqual("failed", validate_visualspec_data_contract(fake_candidate_spec)["status"])
            delivery = validate_delivery(candidates_path=candidates, observations_path=output / "missing-observations.csv", decisions_path=decisions, data_path=output / "missing-data.csv", provenance_path=output / "missing-provenance.json", visualspec_path=fake_candidate_spec)
            self.assertEqual("working", delivery["delivery_status"])
            self.assertNotEqual("formal_data_ready", delivery["extraction_status"])

    def test_candidate_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, confirmation, output = self._extract(root)
            decisions = output / "review-decisions.json"
            review_template(output / "candidates.csv", output / "quality-assessment.json", confirmation, decisions)
            with (output / "candidates.csv").open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            with self.assertRaisesRegex(FigureDataError, "candidates hash mismatch"):
                build_observations(output / "candidates.csv", output / "quality-assessment.json", decisions, output / "observations.csv")

    def test_legacy_digitized_lines_migrates_to_candidate_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "digitized_lines.csv"
            legacy.write_text(
                "series,x,y,x_px,y_px,uncertainty_x,uncertainty_y,status\n"
                "response,0,1,10,20,0.1,0.1,visible_color_supported\n"
                "response,1,2,11,19,0.1,0.1,visible_color_supported\n",
                encoding="utf-8",
            )
            output = root / "candidates.csv"
            report = migrate_legacy_digitized_lines(
                legacy,
                output,
                source_sha256="a" * 64,
                spec_sha256="b" * 64,
            )
            self.assertEqual("candidate_only_not_reviewed", report["status"])
            self.assertFalse(report["formal_data_authorized"])
            self.assertFalse(report["visualspec_authorized"])
            self.assertEqual(2, len(read_csv(output)))

    def test_scatter_and_bar_extractors_are_candidate_only(self) -> None:
        for grammar in ("scatter", "simple_bar"):
            with self.subTest(grammar=grammar), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "source.png"
                project = root / "project.json"
                output = root / "out"
                series = [("samples", "#2266cc")] if grammar == "scatter" else [("bars", "#22aa66")]
                (self._make_scatter_image if grammar == "scatter" else self._make_bar_image)(source)
                inspect_source(source, grammar, project)
                confirmation = self._confirm(root, project, series=series, y_anchors=[(70, 0), (10, 6)])
                kwargs = dict(project_path=project, output_dir=output, plot_bounds=self.BOUNDS, x_anchors=self.X_ANCHORS, y_anchors=[(70, 0), (10, 6)], series=series, spec_confirmation_path=confirmation)
                report = extract_color_scatter(**kwargs) if grammar == "scatter" else extract_color_bars(**kwargs, baseline_pixel=70)
                self.assertEqual("candidate_ready", report["extraction_status"])
                self.assertFalse(report["value_delivery_authorized"])
                self.assertTrue((output / "candidates.csv").is_file())
                self.assertFalse((output / "visualspec.json").exists())


if __name__ == "__main__":
    unittest.main()
