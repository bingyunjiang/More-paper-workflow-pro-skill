#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Publication-quality figure generator — reads data files and a manuscript or
figure specification to produce reviewable scientific charts.

Inspired by nature-figure (Yuan1z0825/nature-skills). Supports 10+ chart types,
multi-panel GridSpec layouts, and multi-format export (SVG/PDF/TIFF).

Usage:
  # Generate figures from manuscript placeholders
  python3 generate_figures.py 论文初稿.md --data data/ --output figures/

  # Generate figures from explicit specification JSON
  python3 generate_figures.py --spec figures.json --output figures/

  # List available chart types
  python3 generate_figures.py --list-types

  # Preview a color scheme
  python3 generate_figures.py --preview-colors pastel

  # Single figure test
  python3 generate_figures.py --test grouped_bar --output test.svg
"""
try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import json
import sys
import os
import re
import csv
import importlib.util
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_matplotlib_cache = Path(tempfile.gettempdir()) / "morepaper-matplotlib-cache"
_matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache))

# Import shared figure utilities
from figure_utils import (
    nature_style, get_palette, export_figure,
    grouped_bar, trend_line, heatmap, bubble_scatter,
    radar_chart, gridspec_figure,
    NATURE_RCPARAMS, NATURE_PASTEL_6,
)
from paper_diagrams import DIAGRAM_TYPES, STYLE_IDS, DiagramSpecError, is_diagram_spec
from paper_diagrams.engine import failure_report, render_from_file


# ── Chart Type Registry ──────────────────────────────────────────────────────

CHART_TYPES = {
    "grouped_bar": {
        "name": "分组柱状图",
        "function": "grouped_bar",
        "description": "多条件对比（如不同方法在不同指标上的表现）",
        "data_format": "categories + groups dict",
    },
    "stacked_bar": {
        "name": "堆叠柱状图",
        "function": "stacked_bar",
        "description": "组分占比对比",
        "data_format": "categories + groups dict",
    },
    "horizontal_bar": {
        "name": "水平柱状图",
        "function": "horizontal_bar",
        "description": "类别名较长时的对比（如文献分类统计）",
        "data_format": "categories + values",
    },
    "trend_line": {
        "name": "趋势折线图",
        "function": "trend_line",
        "description": "时间序列 / 参数扫描 / 随变量变化趋势",
        "data_format": "x list + y_series dict",
    },
    "heatmap_seq": {
        "name": "顺序热力图",
        "function": "heatmap",
        "description": "单方向强度分布（如温度场、浓度场）",
        "data_format": "2D array + row/col labels",
    },
    "heatmap_div": {
        "name": "发散热力图",
        "function": "heatmap_diverging",
        "description": "双向偏离分布（如 z-score、差异矩阵）",
        "data_format": "2D array + center value",
    },
    "bubble_scatter": {
        "name": "气泡散点图",
        "function": "bubble_scatter",
        "description": "三维变量关系（x-y-size）",
        "data_format": "x, y, sizes lists",
    },
    "radar_polar": {
        "name": "雷达图",
        "function": "radar_chart",
        "description": "多指标综合评估/多方案对比",
        "data_format": "categories + values dict",
    },
    "gridspec": {
        "name": "多面板组合图",
        "function": "gridspec_figure",
        "description": "复合图表（不同视角组合展示）",
        "data_format": "panel_specs list",
    },
    "fill_between": {
        "name": "填充区域图",
        "function": "fill_between",
        "description": "不确定带/包络线展示",
        "data_format": "x + y_mean + y_lower + y_upper",
    },
}


REPRODUCTION_DEPENDENCIES = {
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "Pillow": "PIL",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "scikit-image": "skimage",
    "pypdf": "pypdf",
}


def is_visualspec(path: str | os.PathLike[str] | None) -> bool:
    """Return whether a JSON input uses the scientificfigure VisualSpec schema."""
    if not path:
        return False
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    schema = payload.get("schema") if isinstance(payload, dict) else None
    return isinstance(schema, str) and schema.startswith("scientificfigure.visualspec.")


def select_figure_backend(
    requested: str,
    *,
    spec_path: str | os.PathLike[str] | None = None,
    source_path: str | os.PathLike[str] | None = None,
) -> str:
    """Resolve the CLI backend without weakening an explicit user choice."""
    if requested in {"quick", "reproduction", "diagram"}:
        return requested
    if source_path or is_visualspec(spec_path):
        return "reproduction"
    if is_diagram_spec(spec_path):
        return "diagram"
    return "quick"


def missing_reproduction_dependencies() -> list[str]:
    return [
        distribution
        for distribution, module in REPRODUCTION_DEPENDENCIES.items()
        if importlib.util.find_spec(module) is None
    ]


def run_reproduction_backend(args) -> int:
    if not args.spec:
        print("ERROR: reproduction backend requires --spec with a VisualSpec JSON file.", file=sys.stderr)
        return 2
    if getattr(args, "transform_authorization", None) != "explicit_user_request":
        print(
            "ERROR: reproduction requires --transform-authorization explicit_user_request.",
            file=sys.stderr,
        )
        return 2
    missing = missing_reproduction_dependencies()
    if missing:
        requirements = Path(__file__).resolve().parents[1] / "requirements-figures.txt"
        print(
            "ERROR: reproduction backend dependencies are missing: " + ", ".join(missing),
            file=sys.stderr,
        )
        print(
            f'Install them with: "{sys.executable}" -m pip install -r "{requirements}"',
            file=sys.stderr,
        )
        return 2

    command = [
        sys.executable,
        str(Path(__file__).with_name("run_reproduction.py")),
        "--spec",
        str(args.spec),
        "--out-dir",
        str(args.output),
        "--qa-profile",
        args.qa_profile,
        "--transform-authorization",
        "explicit_user_request",
    ]
    if args.source:
        command.extend(["--source", str(args.source)])
    if args.custom_renderer:
        command.extend(["--script", str(args.custom_renderer)])
    if args.require_strict:
        command.append("--require-strict")
    return subprocess.call(command)


# ── Figure Specification ─────────────────────────────────────────────────────

@dataclass
class FigureSpec:
    """Specification for one figure."""
    figure_id: str                # e.g., "fig_1"
    chart_type: str               # one of CHART_TYPES keys
    data_source: str              # path to CSV/TSV file
    title: str = ""
    caption: str = ""
    x_column: str = ""
    y_columns: list[str] = field(default_factory=list)
    group_column: str = ""
    xlabel: str = ""
    ylabel: str = ""
    palette: str = "pastel"
    figsize: tuple = None
    panel_layout: tuple = None    # (nrows, ncols) for gridspec
    panel_labels: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=lambda: ["svg"])


def load_data_csv(path: str) -> dict:
    """Load figure data from a CSV file. Returns a dict with column arrays."""
    data = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, val in row.items():
                if key not in data:
                    data[key] = []
                try:
                    data[key].append(float(val))
                except (ValueError, TypeError):
                    data[key].append(val.strip() if val else "")
    return data


def load_spec_json(path: str) -> list[FigureSpec]:
    """Load figure specifications from a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    specs = []
    for item in raw:
        specs.append(FigureSpec(
            figure_id=item.get("figure_id", f"fig_{len(specs)+1}"),
            chart_type=item.get("chart_type", "grouped_bar"),
            data_source=item.get("data_source", ""),
            title=item.get("title", ""),
            caption=item.get("caption", ""),
            x_column=item.get("x_column", ""),
            y_columns=item.get("y_columns", []),
            group_column=item.get("group_column", ""),
            xlabel=item.get("xlabel", ""),
            ylabel=item.get("ylabel", ""),
            palette=item.get("palette", "pastel"),
            figsize=tuple(item["figsize"]) if "figsize" in item else None,
            panel_layout=tuple(item["panel_layout"]) if "panel_layout" in item else None,
            panel_labels=item.get("panel_labels", []),
            formats=item.get("formats", ["svg"]),
        ))
    return specs


def extract_figure_placeholders(md_text: str) -> list[dict]:
    """Extract figure references from a manuscript to auto-generate specs.

    Looks for patterns like:
    - [图1] or [图 1]
    - [Figure 1] or [Fig. 1]
    - <!-- figure: grouped_bar, data=results.csv -->
    """
    placeholders = []

    # Markdown comments with figure specs
    comment_pattern = re.compile(
        r'<!--\s*figure:\s*(\w+),\s*data=([^\s,]+)(?:,\s*title=(.+?))?\s*-->',
    )
    for match in comment_pattern.finditer(md_text):
        placeholders.append({
            "chart_type": match.group(1),
            "data_source": match.group(2),
            "title": match.group(3) or "",
        })

    # Inline figure references: [图1], [图 1], [Figure 1]
    fig_ref = re.compile(r'\[(?:图|Figure|Fig\.?)\s*(\d+)\]')
    for match in fig_ref.finditer(md_text):
        fig_num = int(match.group(1))
        # Check if not already captured by comment pattern
        if not any(p.get("_fig_ref") == fig_num for p in placeholders):
            placeholders.append({
                "_fig_ref": fig_num,
                "_marker": match.group(0),
                "chart_type": "grouped_bar",  # Default — user must specify
                "data_source": f"data/fig_{fig_num}.csv",
            })

    return placeholders


# ── Figure Generation ────────────────────────────────────────────────────────

def generate_figure(spec: FigureSpec, output_dir: str) -> list[str]:
    """Generate a single figure from its specification.

    Returns list of output file paths.
    """
    # Load data
    data = {}
    if spec.data_source and os.path.exists(spec.data_source):
        data = load_data_csv(spec.data_source)
    elif spec.data_source:
        print(f"   ⚠️ 数据文件未找到: {spec.data_source}")
        return []

    with nature_style(cjk=False):
        fig = None

        if spec.chart_type == "grouped_bar":
            categories = data.get(spec.x_column, [])
            groups = {}
            for ycol in spec.y_columns:
                if ycol in data:
                    groups[ycol] = data[ycol]
            if categories and groups:
                if isinstance(categories[0], (int, float)):
                    categories = [str(c) for c in categories]
                fig = grouped_bar(
                    categories, groups,
                    ylabel=spec.ylabel, xlabel=spec.xlabel,
                    figsize=spec.figsize,
                    palette=get_palette(len(groups), spec.palette),
                )

        elif spec.chart_type == "trend_line":
            x = data.get(spec.x_column, [])
            y_series = {}
            for ycol in spec.y_columns:
                if ycol in data:
                    y_series[ycol] = data[ycol]
            if x and y_series:
                fig = trend_line(
                    x, y_series,
                    xlabel=spec.xlabel, ylabel=spec.ylabel,
                    figsize=spec.figsize,
                    palette=get_palette(len(y_series), spec.palette),
                )

        elif spec.chart_type in ("heatmap_seq", "heatmap_div"):
            # Data should be loaded as 2D matrix
            row_labels = data.get("row_label", [])
            col_labels = [k for k in data if k not in ("row_label",)]
            matrix = []
            for col in col_labels:
                matrix.append(data.get(col, []))
            # Transpose: rows x cols
            if matrix:
                matrix_t = [[matrix[j][i] if i < len(matrix[j]) else 0
                             for j in range(len(matrix))]
                            for i in range(len(matrix[0]))]
                center = 0 if spec.chart_type == "heatmap_div" else None
                fig = heatmap(
                    matrix_t, row_labels, col_labels,
                    center=center,
                    figsize=spec.figsize or (6, 4),
                )

        elif spec.chart_type == "bubble_scatter":
            x = data.get(spec.x_column, [])
            y_vals = data.get(spec.y_columns[0] if spec.y_columns else "y", [])
            sizes = data.get("size", [1.0] * len(x)) if "size" in data else [10] * len(x)
            labels = data.get("label", []) if "label" in data else None
            if x and y_vals:
                fig = bubble_scatter(
                    x, y_vals, sizes, labels,
                    xlabel=spec.xlabel, ylabel=spec.ylabel,
                    figsize=spec.figsize,
                )

        elif spec.chart_type == "radar_polar":
            categories = data.get(spec.x_column, [])
            groups = {}
            for ycol in spec.y_columns:
                if ycol in data:
                    groups[ycol] = data[ycol]
            if categories and groups:
                fig = radar_chart(
                    categories, groups,
                    figsize=spec.figsize or (5, 5),
                    palette=get_palette(len(groups), spec.palette),
                )

        elif spec.chart_type == "gridspec":
            panel_specs = _build_panel_specs(spec, data)
            if panel_specs:
                fig = gridspec_figure(
                    panel_specs,
                    figsize=spec.figsize,
                    panel_labels=spec.panel_labels,
                )

        else:
            print(f"   ⚠️ 未知图表类型: {spec.chart_type}")
            return []

        if fig is None:
            print(f"   ⚠️ 无法生成图表 {spec.figure_id}")
            return []

        # Add title
        if spec.title:
            fig.suptitle(spec.title, fontsize=8, y=1.02)

        # Export
        base_path = os.path.join(output_dir, spec.figure_id)
        export_figure(fig, base_path, spec.formats)

        # Cleanup
        import matplotlib.pyplot as plt
        plt.close(fig)

    return [f"{base_path}.{fmt}" for fmt in spec.formats]


def _build_panel_specs(spec: FigureSpec, data: dict) -> list[dict]:
    """Build panel specifications for a GridSpec figure."""
    panels = []
    n_panels = spec.panel_layout[0] * spec.panel_layout[1] if spec.panel_layout else 4

    for i in range(n_panels):
        panel = {
            "type": spec.y_columns[i] if i < len(spec.y_columns) else "bar",
            "data": {"categories": data.get(spec.x_column, []),
                     "groups": {f"Panel {i+1}": data.get(f"panel_{i}", [])}},
            "title": spec.panel_labels[i] if i < len(spec.panel_labels) else "",
        }
        panels.append(panel)
    return panels


# ── Figure Checklist Generator ───────────────────────────────────────────────

def generate_figure_checklist(specs: list[FigureSpec], output_dir: str) -> str:
    """Generate 图表清单.md inventory of all figures."""
    md = f"""# 图表清单

> 生成时间：{_now()}
> 图表总数：{len(specs)}

## 图表索引

| 编号 | 类型 | 标题 | 数据来源 | 格式 |
|------|------|------|---------|------|
"""
    for s in specs:
        chart_name = CHART_TYPES.get(s.chart_type, {}).get("name", s.chart_type)
        formats_str = ", ".join(s.formats)
        md += f"| {s.figure_id} | {chart_name} | {s.title or '—'} | {s.data_source or '—'} | {formats_str} |\n"

    md += "\n## 设计自查\n\n"
    md += "- [ ] 每张图表不看正文能独立看懂吗？（caption 写全了吗？）\n"
    md += "- [ ] 是否有冗余面板？（两张图回答了同一个科学问题？）\n"
    md += "- [ ] 颜色是否有明确含义？（非 colour-blind 情况下区分度够吗？）\n"
    md += "- [ ] 字体在最终尺寸下可读吗？（≥6pt）\n"
    md += "- [ ] 坐标轴标签有单位吗？\n"
    md += "- [ ] 直标是否优于图例？（能用 direct label 不用 legend）\n"
    md += "- [ ] SVG 导出时文字是否保持可编辑？（svg.fonttype='none'）\n"

    return md


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate reviewable publication figures",
    )
    parser.add_argument(
        "manuscript", nargs="?",
        help="Path to manuscript .md file (extracts figure placeholders)",
    )
    parser.add_argument(
        "--data", "-d",
        help="Directory with CSV/TSV data files",
    )
    parser.add_argument(
        "--spec", "-s",
        help="Path to figure specification JSON file",
    )
    parser.add_argument(
        "--output", "-o", default="figures/",
        help="Output directory (default: figures/)",
    )
    parser.add_argument(
        "--format", "-f", default="svg",
        help="Export format: svg, pdf, tiff, png (default: svg)",
    )
    parser.add_argument(
        "--list-types", action="store_true",
        help="List available chart types and exit",
    )
    parser.add_argument(
        "--preview-colors",
        help="Preview a color scheme and exit (pastel, sequential, diverging)",
    )
    parser.add_argument(
        "--test",
        help="Generate a test figure of given type and exit",
    )
    parser.add_argument(
        "--backend", choices=["auto", "quick", "reproduction", "diagram"], default="auto",
        help="Figure backend. Auto recognizes native paper-diagram specs, VisualSpec, and ordinary charts.",
    )
    parser.add_argument(
        "--source",
        help="Reference image for reproduction visual QA; auto-selects the reproduction backend.",
    )
    parser.add_argument(
        "--require-strict", action="store_true",
        help="Require strict reproduction closure (requires --source).",
    )
    parser.add_argument(
        "--qa-profile", choices=["semantic", "visual", "trace"], default="semantic",
        help="QA profile used by the reproduction backend.",
    )
    parser.add_argument(
        "--custom-renderer",
        help="Custom renderer accepting --spec/--out-dir/--script for complex figures.",
    )
    parser.add_argument(
        "--transform-authorization",
        choices=["explicit_user_request"],
        help="Required for reproduction; records that the user explicitly requested redraw or digitization.",
    )
    parser.add_argument(
        "--inspect", action="store_true",
        help="For diagram backend, also emit a review overlay with node bounds and stable IDs.",
    )

    args = parser.parse_args()

    # --list-types
    if args.list_types:
        print("── 可用图表类型 ──")
        for key, info in CHART_TYPES.items():
            print(f"  {key:20s} {info['name']:10s} {info['description']}")
        print("\n── 原生论文流程图类型 ──")
        for key in sorted(DIAGRAM_TYPES):
            print(f"  {key}")
        print("\n── 原生流程图风格 ──")
        print("  " + ", ".join(sorted(STYLE_IDS)))
        return 0

    # --preview-colors
    if args.preview_colors:
        import matplotlib.pyplot as plt
        colors = get_palette(8, args.preview_colors)
        fig, ax = plt.subplots(figsize=(6, 1.5))
        for i, c in enumerate(colors):
            ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=c))
            ax.text(i + 0.5, 1.05, c, ha="center", fontsize=5)
        ax.set_xlim(0, len(colors))
        ax.set_ylim(0, 1.2)
        ax.axis("off")
        path = f"color_preview_{args.preview_colors}.svg"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"✅ 色彩预览已保存: {path}")
        return 0

    # --test
    if args.test:
        chart_type = args.test
        if chart_type not in CHART_TYPES:
            print(f"❌ 未知图表类型: {chart_type}")
            return 2
        import matplotlib.pyplot as plt
        with nature_style():
            if chart_type == "grouped_bar":
                fig = grouped_bar(
                    ["A", "B", "C", "D"],
                    {"Method 1": [3.2, 4.1, 2.8, 3.5],
                     "Method 2": [2.8, 3.5, 3.1, 2.9]},
                    ylabel="Value", xlabel="Category",
                )
            elif chart_type == "trend_line":
                fig = trend_line(
                    [1, 2, 3, 4, 5],
                    {"Series A": [1.0, 2.1, 3.0, 4.2, 5.1],
                     "Series B": [0.8, 1.9, 2.8, 3.9, 4.8]},
                    xlabel="X", ylabel="Y",
                )
            elif chart_type == "bubble_scatter":
                fig = bubble_scatter(
                    [1, 2, 3, 4, 5],
                    [2, 3, 4, 3, 5],
                    [10, 20, 30, 20, 40],
                    xlabel="X", ylabel="Y",
                )
            elif chart_type == "heatmap_seq":
                fig = heatmap(
                    [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                    ["Row1", "Row2", "Row3"],
                    ["Col1", "Col2", "Col3"],
                )
            else:
                fig = grouped_bar(
                    ["A", "B", "C"],
                    {"Test": [1, 2, 3]},
                    ylabel="Value",
                )
            path = f"test_{chart_type}.svg"
            export_figure(fig, path.replace('.svg', ''), ['svg'])
            plt.close(fig)
            print(f"✅ 测试图表已保存: {path}")
        return 0

    backend = select_figure_backend(
        args.backend,
        spec_path=args.spec,
        source_path=args.source,
    )
    if backend == "reproduction":
        return run_reproduction_backend(args)
    if backend == "diagram":
        if not args.spec:
            print("ERROR: diagram backend requires --spec with a native paper-diagram JSON file.", file=sys.stderr)
            return 2
        try:
            result = render_from_file(args.spec, args.output, inspect=args.inspect)
        except DiagramSpecError as exc:
            report = failure_report(args.spec, args.output, exc)
            status = "needs_author_check" if exc.needs_author_check else "fail"
            print(f"ERROR: diagram {status}: {exc} (report: {report})", file=sys.stderr)
            return 2
        except Exception as exc:
            error = DiagramSpecError("render_failed", str(exc))
            report = failure_report(args.spec, args.output, error)
            print(f"ERROR: diagram render failed: {exc} (report: {report})", file=sys.stderr)
            return 2
        print(f"✅ 原生论文流程图: {result['svg']} {result['png']}")
        print(f"✅ 布局检查: {result['check']}")
        print(f"✅ 图形证据: {result['evidence']}")
        return 0

    # Main flow
    specs = []

    if args.spec:
        specs = load_spec_json(args.spec)
        print(f"📋 从 spec 文件加载 {len(specs)} 个图表规格")
    elif args.manuscript:
        print(f"📄 从稿件提取图表占位符: {args.manuscript}")
        with open(args.manuscript, 'r', encoding='utf-8') as f:
            md_text = f.read()
        placeholders = extract_figure_placeholders(md_text)
        print(f"   找到 {len(placeholders)} 处图表引用")

        # Convert placeholders to specs
        for i, ph in enumerate(placeholders):
            chart_type = ph.get("chart_type", "grouped_bar")
            data_source = ph.get("data_source", "")
            # Resolve data path
            if args.data and data_source:
                data_source = os.path.join(args.data, os.path.basename(data_source))
            elif args.data and not data_source:
                data_source = os.path.join(args.data, f"fig_{i+1}.csv")

            specs.append(FigureSpec(
                figure_id=f"fig_{i+1}",
                chart_type=chart_type,
                data_source=data_source,
                title=ph.get("title", ""),
                formats=[args.format],
            ))
    else:
        parser.print_help()
        print("\n💡 提示：使用 --list-types 查看可用图表类型")
        return 0

    if not specs:
        print("⚠️ 未找到图表规格。请在稿件中添加 <!-- figure: chart_type, data=file.csv --> 注释，或使用 --spec 指定 JSON 规格文件。")
        return 2

    # Generate figures
    os.makedirs(args.output, exist_ok=True)
    print(f"\n🎨 生成 {len(specs)} 个图表 → {args.output}/")
    success = 0
    for spec in specs:
        print(f"   {spec.figure_id} ({CHART_TYPES.get(spec.chart_type, {}).get('name', spec.chart_type)}) ...", end=" ")
        paths = generate_figure(spec, args.output)
        if paths:
            print(f"✅ {' '.join(os.path.basename(p) for p in paths)}")
            success += 1
        else:
            print("❌ 跳过（数据不可用）")

    # Generate checklist
    checklist_md = generate_figure_checklist(specs, args.output)
    checklist_path = os.path.join(args.output, "图表清单.md")
    with open(checklist_path, 'w', encoding='utf-8') as f:
        f.write(checklist_md)
    print(f"\n✅ 图表清单: {checklist_path}")
    print(f"   成功: {success}/{len(specs)}")
    return 0 if success == len(specs) else 2


def _now():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


if __name__ == "__main__":
    raise SystemExit(main())
