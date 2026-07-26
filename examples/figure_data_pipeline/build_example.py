from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from figure_data_pipeline import (  # noqa: E402
    build_data,
    build_observations,
    build_spec_review,
    build_visualspec,
    confirm_spec,
    read_csv,
    review_template,
    sha256_file,
    validate_delivery,
    write_json,
)
from figure_evidence_pipeline import extract_color_lines, inspect_source  # noqa: E402
from render_visualspec_matplotlib import render_file  # noqa: E402


HERE = Path(__file__).resolve().parent


def main() -> int:
    source = HERE / "source-occluded.png"
    project = HERE / "figure-project.json"
    spec_dir = HERE / "spec"
    image = Image.new("RGB", (160, 100), "white")
    draw = ImageDraw.Draw(image)
    for x in range(20, 141):
        y = int(round(78 - 0.42 * (x - 20)))
        draw.point((x, y), fill="#cc2244")
        draw.point((x, y + 1), fill="#cc2244")
    # Synthetic legend occlusion: this hides real source pixels but does not
    # change the declared continuous physical topology.
    draw.rectangle((70, 48, 90, 67), fill="white", outline="#444444", width=1)
    draw.line((74, 54, 82, 54), fill="#cc2244", width=2)
    draw.text((84, 50), "A", fill="#222222")
    image.save(source)

    inspect_source(source, "line", project)
    build_spec_review(
        project,
        spec_dir,
        plot_bounds=(20, 15, 140, 82),
        x_anchors=[(20, 0), (140, 12)],
        y_anchors=[(78, 0), (28, 5)],
        series=[("response", "#cc2244")],
        curve_topology={"response": "continuous"},
        exclusion_regions=[(70, 48, 90, 67)],
    )
    confirmation = spec_dir / "spec-confirmation.json"
    confirm_spec(
        project,
        spec_dir / "figure-spec.json",
        spec_dir / "spec-review.png",
        confirmation,
        confirmation="explicit_user_confirmation",
    )
    extract_color_lines(
        project,
        HERE,
        plot_bounds=(20, 15, 140, 82),
        x_anchors=[(20, 0), (140, 12)],
        y_anchors=[(78, 0), (28, 5)],
        series=[("response", "#cc2244")],
        minimum_coverage=0.55,
        max_vertical_span_px=6,
        spec_confirmation_path=confirmation,
    )

    decisions = HERE / "review-decisions.json"
    review_template(HERE / "candidates.csv", HERE / "quality-assessment.json", confirmation, decisions)
    payload = json.loads(decisions.read_text(encoding="utf-8"))
    payload["review_status"] = "complete"
    payload["normal_batch"] = {"action": "accept", "user_reply": "继续"}
    payload["series_topology"]["response"]["confirmed_by_user"] = True
    for item in payload["anomaly_decisions"]:
        item["action"] = "accept"
        item["review_note"] = "synthetic regression: legend occlusion is evidence gap, not physical break"
    decisions.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    build_observations(HERE / "candidates.csv", HERE / "quality-assessment.json", decisions, HERE / "observations.csv")
    build_data(HERE / "observations.csv", decisions, HERE / "data.csv", HERE / "data.provenance.json")

    data_hash = sha256_file(HERE / "data.csv")
    for style in ("solid", "dashed", "dashdot"):
        styles = HERE / f"styles-{style}.json"
        style_record = {"color": "#cc2244", "line_style": style, "line_width_pt": 1.6}
        if style == "dashdot":
            style_record["marker"] = "o"
        write_json(styles, {"schema": "morepaper.figure_styles.v1", "series": {"response": style_record}})
        spec = HERE / f"visualspec-{style}.json"
        build_visualspec(HERE / "data.csv", HERE / "data.provenance.json", spec, styles_path=styles, width_mm=110, height_mm=72)
        render_file(spec, HERE / f"render-{style}")
        if sha256_file(HERE / "data.csv") != data_hash:
            raise RuntimeError("style change mutated data.csv")

    observations = read_csv(HERE / "observations.csv")
    data = read_csv(HERE / "data.csv")
    validation = validate_delivery(
        candidates_path=HERE / "candidates.csv",
        observations_path=HERE / "observations.csv",
        decisions_path=decisions,
        data_path=HERE / "data.csv",
        provenance_path=HERE / "data.provenance.json",
        visualspec_path=HERE / "visualspec-solid.json",
        render_manifest_path=HERE / "render-solid" / "render_manifest.json",
    )
    summary = {
        "schema": "morepaper.figure_gap_regression_example.v1",
        "synthetic_fixture": True,
        "source_occlusion": "legend rectangle hides a continuous line",
        "observation_evidence_breaks": sum(row["evidence_segment_break_before"] == "true" for row in observations),
        "formal_segment_breaks": sum(row["formal_segment_break_before"] == "true" for row in data),
        "data_sha256": data_hash,
        "data_row_count": len(data),
        "styles_rendered": ["solid", "dashed", "dashdot"],
        "style_invariance_verified": True,
        "render_stage_interpolation": False,
        "render_stage_bridging": False,
        "validation": validation,
    }
    write_json(HERE / "evidence-summary.json", summary)
    return 0 if validation["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
