from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_figures.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("generate_figures_backends", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
generate_figures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_figures)


class GenerateFiguresBackendTest(unittest.TestCase):
    def test_auto_routes_visualspec_to_reproduction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "visualspec.json"
            path.write_text(
                json.dumps({"schema": "scientificfigure.visualspec.v2", "figure": {}, "panels": []}),
                encoding="utf-8",
            )
            self.assertEqual(
                "reproduction",
                generate_figures.select_figure_backend("auto", spec_path=path),
            )

    def test_auto_routes_reference_image_to_reproduction(self) -> None:
        self.assertEqual(
            "reproduction",
            generate_figures.select_figure_backend("auto", source_path="source.png"),
        )

    def test_auto_preserves_legacy_quick_inputs(self) -> None:
        self.assertEqual("quick", generate_figures.select_figure_backend("auto"))

    def test_auto_routes_native_diagram_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagram.json"
            path.write_text(json.dumps({"schema_version": "morepaper.paper-diagram.v1"}), encoding="utf-8")
            self.assertEqual("diagram", generate_figures.select_figure_backend("auto", spec_path=path))

    def test_explicit_backend_overrides_detection(self) -> None:
        self.assertEqual(
            "quick",
            generate_figures.select_figure_backend(
                "quick", spec_path="visualspec.json", source_path="source.png"
            ),
        )

    def test_explicit_quick_visualspec_is_reported_as_conflict_by_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "visualspec.json"
            path.write_text(json.dumps({"schema": "scientificfigure.visualspec.v2"}), encoding="utf-8")
            import subprocess
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--backend", "quick", "--spec", str(path)],
                capture_output=True, text=True,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("backend/schema conflict", result.stderr)

    def test_explicit_diagram_backend_is_preserved(self) -> None:
        self.assertEqual("diagram", generate_figures.select_figure_backend("diagram", spec_path="anything.json"))

    def test_missing_dependencies_fail_without_fallback(self) -> None:
        args = type(
            "Args",
            (),
            {
                "spec": "visualspec.json",
                "transform_authorization": "explicit_user_request",
            },
        )()
        with patch.object(generate_figures, "missing_reproduction_dependencies", return_value=["scikit-image"]):
            with patch.object(generate_figures.subprocess, "call") as call:
                self.assertEqual(2, generate_figures.run_reproduction_backend(args))
                call.assert_not_called()

    def test_reproduction_arguments_are_forwarded(self) -> None:
        args = type(
            "Args",
            (),
            {
                "spec": "visualspec.json",
                "output": "bundle",
                "qa_profile": "semantic",
                "source": "source.png",
                "custom_renderer": "renderer.py",
                "require_strict": True,
                "transform_authorization": "explicit_user_request",
            },
        )()
        with patch.object(generate_figures, "missing_reproduction_dependencies", return_value=[]):
            with patch.object(generate_figures.subprocess, "call", return_value=0) as call:
                self.assertEqual(0, generate_figures.run_reproduction_backend(args))
        command = call.call_args.args[0]
        self.assertIn("run_reproduction.py", command[1])
        self.assertIn("--source", command)
        self.assertIn("--script", command)
        self.assertIn("--require-strict", command)
        self.assertIn("--transform-authorization", command)

    def test_reproduction_requires_explicit_transform_authorization(self) -> None:
        args = type(
            "Args",
            (),
            {
                "spec": "visualspec.json",
                "transform_authorization": None,
            },
        )()
        with patch.object(generate_figures.subprocess, "call") as call:
            self.assertEqual(2, generate_figures.run_reproduction_backend(args))
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
