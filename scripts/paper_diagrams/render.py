from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable

from .model import DiagramSpec, Edge, Node, TextRun


@dataclass(frozen=True)
class Theme:
    background: str
    surface: str
    surface_alt: str
    stroke: str
    text: str
    muted: str
    accent: str
    accent_alt: str
    grid: str
    radius: int


THEMES = {
    "clean": Theme("#ffffff", "#f8fafc", "#eef2ff", "#334155", "#0f172a", "#64748b", "#2563eb", "#7c3aed", "#e2e8f0", 18),
    "terminal": Theme("#0b1020", "#111827", "#172033", "#4ade80", "#dcfce7", "#86efac", "#22c55e", "#38bdf8", "#1f2937", 8),
    "blueprint": Theme("#082f49", "#0c4a6e", "#075985", "#bae6fd", "#f0f9ff", "#7dd3fc", "#38bdf8", "#fbbf24", "#0e7490", 4),
    "notebook": Theme("#fffdf5", "#ffffff", "#fef3c7", "#57534e", "#292524", "#78716c", "#d97706", "#2563eb", "#e7e5e4", 10),
    "glass": Theme("#e0f2fe", "#f8fafccc", "#ede9fecc", "#475569", "#0f172a", "#64748b", "#8b5cf6", "#06b6d4", "#cbd5e1", 24),
    "editorial": Theme("#faf7f2", "#ffffff", "#f5e8dc", "#3f3f46", "#18181b", "#71717a", "#b45309", "#9f1239", "#ded7ce", 2),
    "minimal": Theme("#ffffff", "#ffffff", "#ffffff", "#000000", "#000000", "#000000", "#000000", "#000000", "#000000", 0),
    "dark": Theme("#09090b", "#18181b", "#27272a", "#71717a", "#fafafa", "#a1a1aa", "#f59e0b", "#ec4899", "#27272a", 16),
    "review-canvas": Theme("#f8fafc", "#ffffff", "#f1f5f9", "#475569", "#0f172a", "#64748b", "#dc2626", "#2563eb", "#cbd5e1", 6),
    "cloud": Theme("#eff6ff", "#ffffff", "#dbeafe", "#1e40af", "#172554", "#64748b", "#0284c7", "#7c3aed", "#bfdbfe", 22),
    "event-stream": Theme("#fff7ed", "#ffffff", "#ffedd5", "#9a3412", "#431407", "#78716c", "#ea580c", "#0d9488", "#fed7aa", 12),
    "operations": Theme("#f0fdf4", "#ffffff", "#dcfce7", "#166534", "#052e16", "#4b5563", "#16a34a", "#2563eb", "#bbf7d0", 10),
}


@dataclass(frozen=True)
class Typography:
    title: int
    node: int
    secondary: int
    group: int


def typography_for(spec: DiagramSpec) -> Typography:
    """Return stable screen typography or width-normalized print typography."""
    scale = max(1.0, spec.width / 1200.0) if spec.style == "minimal" else 1.0
    return Typography(
        title=round(30 * scale),
        node=round(18 * scale),
        secondary=round(14 * scale),
        group=round(15 * scale),
    )


def publication_profile(spec: DiagramSpec) -> dict[str, object]:
    typography = typography_for(spec)
    if spec.style != "minimal":
        return {
            "mode": "screen_or_review",
            "black_white_only": False,
            "no_tinted_background": False,
        }
    points_at_180_mm = typography.node / spec.width * 180.0 / 25.4 * 72.0
    minimum_width_mm = 7.0 * 25.4 / 72.0 * spec.width / typography.node
    return {
        "mode": "black_white_full_width",
        "black_white_only": True,
        "no_tinted_background": True,
        "recommended_width_mm": [170, 180],
        "minimum_width_mm_for_7pt": round(minimum_width_mm, 1),
        "node_font_px": typography.node,
        "title_font_px": typography.title,
        "node_font_pt_at_180mm": round(points_at_180_mm, 1),
        "single_column_requires_simplified_spec": True,
    }


@dataclass
class Box:
    node: Node
    x: float
    y: float
    width: float
    height: float

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2


@dataclass
class RoutedEdge:
    edge: Edge
    points: list[tuple[float, float]]


@dataclass
class Scene:
    spec: DiagramSpec
    theme: Theme
    boxes: dict[str, Box]
    edges: list[RoutedEdge]
    findings: list[dict[str, str]]
    score: float


def _label_lines(runs: list[TextRun], limit: int = 24) -> list[list[TextRun]]:
    lines: list[list[TextRun]] = [[]]
    current = 0
    for run in runs:
        parts = run.value.split("\n") if run.kind == "text" else [run.value]
        for part_index, part in enumerate(parts):
            if part_index:
                lines.append([])
                current = 0
            if not part:
                continue
            units = max(1, len(part))
            if current and current + units > limit:
                lines.append([])
                current = 0
            lines[-1].append(TextRun(run.kind, part))
            current += units
    return lines or [[TextRun("text", "")]]


def _node_size(node: Node, font_size: int = 18) -> tuple[float, float]:
    lines = _label_lines(node.runs)
    longest = max(sum(len(run.value) for run in line) for line in lines)
    scale = font_size / 18.0
    width = node.width or min(360 * scale, max(150 * scale, (72 + longest * 10) * scale))
    height = node.height or max(76 * scale, (42 + len(lines) * 24) * scale)
    return width, height


def _topological_layers(spec: DiagramSpec) -> list[list[Node]]:
    incoming = {node.id: 0 for node in spec.nodes}
    outgoing: dict[str, list[str]] = {node.id: [] for node in spec.nodes}
    for edge in spec.edges:
        incoming[edge.target] += 1
        outgoing[edge.source].append(edge.target)
    by_id = {node.id: node for node in spec.nodes}
    ready = sorted((node for node in spec.nodes if incoming[node.id] == 0), key=lambda n: (n.order, n.id))
    layers: list[list[Node]] = []
    visited: set[str] = set()
    while ready:
        layer = ready
        layers.append(layer)
        next_ready: list[Node] = []
        for node in layer:
            visited.add(node.id)
            for target in outgoing[node.id]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    next_ready.append(by_id[target])
        ready = sorted(next_ready, key=lambda n: (n.order, n.id))
    remaining = sorted((node for node in spec.nodes if node.id not in visited), key=lambda n: (n.order, n.id))
    if remaining:
        layers.append(remaining)
    return layers


def _auto_layout(spec: DiagramSpec) -> dict[str, Box]:
    margin_x, margin_top, margin_bottom = 90.0, 130.0 if spec.title else 80.0, 90.0
    node_font_size = typography_for(spec).node
    boxes: dict[str, Box] = {}
    if spec.layout_locked:
        for node in spec.nodes:
            width, height = _node_size(node, node_font_size)
            boxes[node.id] = Box(node, float(node.x or 0), float(node.y or 0), width, height)
        return boxes

    if spec.diagram_type == "sequence":
        gap = (spec.width - 2 * margin_x) / max(1, len(spec.nodes))
        for index, node in enumerate(sorted(spec.nodes, key=lambda n: (n.order, n.id))):
            width, height = _node_size(node, node_font_size)
            width = min(width, gap * 0.75)
            boxes[node.id] = Box(node, margin_x + index * gap + (gap - width) / 2, margin_top, width, height)
        return boxes

    if spec.diagram_type == "timeline":
        ordered = sorted(spec.nodes, key=lambda n: (n.order, n.id))
        gap = (spec.width - 2 * margin_x) / max(1, len(ordered))
        mid = spec.height * 0.50
        for index, node in enumerate(ordered):
            width, height = _node_size(node, node_font_size)
            width = min(width, gap * 0.8)
            y = mid - height - 55 if index % 2 == 0 else mid + 55
            boxes[node.id] = Box(node, margin_x + index * gap + (gap - width) / 2, y, width, height)
        return boxes

    if spec.diagram_type == "comparison_matrix":
        columns = max(2, math.ceil(math.sqrt(len(spec.nodes))))
        rows = math.ceil(len(spec.nodes) / columns)
        cell_w = (spec.width - 2 * margin_x) / columns
        cell_h = (spec.height - margin_top - margin_bottom) / rows
        for index, node in enumerate(sorted(spec.nodes, key=lambda n: (n.order, n.id))):
            width, height = _node_size(node, node_font_size)
            width, height = min(width, cell_w - 30), min(height, cell_h - 30)
            row, column = divmod(index, columns)
            boxes[node.id] = Box(node, margin_x + column * cell_w + (cell_w - width) / 2,
                                 margin_top + row * cell_h + (cell_h - height) / 2, width, height)
        return boxes

    layers = _topological_layers(spec)
    available_h = spec.height - margin_top - margin_bottom
    layer_gap = available_h / max(1, len(layers))
    for layer_index, layer in enumerate(layers):
        cell_w = (spec.width - 2 * margin_x) / max(1, len(layer))
        for column, node in enumerate(layer):
            width, height = _node_size(node, node_font_size)
            width = min(width, cell_w - 28)
            x = margin_x + column * cell_w + (cell_w - width) / 2
            y = margin_top + layer_index * layer_gap + (layer_gap - height) / 2
            boxes[node.id] = Box(node, x, y, width, height)
    return boxes


def _route_edge(edge: Edge, source: Box, target: Box, sequence_index: int = 0) -> RoutedEdge:
    if abs(source.cx - target.cx) < 12:
        return RoutedEdge(edge, [(source.cx, source.y + source.height), (target.cx, target.y)])
    if source.cy < target.cy:
        start = (source.cx, source.y + source.height)
        end = (target.cx, target.y)
        middle = (start[1] + end[1]) / 2
        return RoutedEdge(edge, [start, (start[0], middle), (end[0], middle), end])
    if source.cy > target.cy:
        start = (source.cx, source.y)
        end = (target.cx, target.y + target.height)
        middle = min(start[1], end[1]) - 30 - sequence_index * 8
        return RoutedEdge(edge, [start, (start[0], middle), (end[0], middle), end])
    direction = 1 if target.cx > source.cx else -1
    start = (source.x + source.width if direction > 0 else source.x, source.cy)
    end = (target.x if direction > 0 else target.x + target.width, target.cy)
    return RoutedEdge(edge, [start, end])


def _intersects(a: Box, b: Box, padding: float = 8) -> bool:
    return not (
        a.x + a.width + padding <= b.x or b.x + b.width + padding <= a.x
        or a.y + a.height + padding <= b.y or b.y + b.height + padding <= a.y
    )


def build_scene(spec: DiagramSpec) -> Scene:
    theme = THEMES[spec.style]
    typography = typography_for(spec)
    boxes = _auto_layout(spec)
    routed = [_route_edge(edge, boxes[edge.source], boxes[edge.target], index)
              for index, edge in enumerate(sorted(spec.edges, key=lambda e: (e.order, e.id)))]
    findings: list[dict[str, str]] = []
    values = list(boxes.values())
    for index, box in enumerate(values):
        if box.x < 24 or box.y < 24 or box.x + box.width > spec.width - 24 or box.y + box.height > spec.height - 24:
            findings.append({"severity": "fail", "code": "node_out_of_bounds", "message": box.node.id})
        for other in values[index + 1:]:
            if _intersects(box, other):
                findings.append({"severity": "fail", "code": "node_overlap", "message": f"{box.node.id},{other.node.id}"})
        longest = max((sum(len(run.value) for run in line) for line in _label_lines(box.node.runs)), default=0)
        if longest * typography.node * 0.53 > box.width - 24:
            findings.append({"severity": "fail", "code": "label_clipping", "message": box.node.id})
    for routed_edge in routed:
        excluded = {routed_edge.edge.source, routed_edge.edge.target}
        for box in values:
            if box.node.id in excluded:
                continue
            for start, end in zip(routed_edge.points, routed_edge.points[1:]):
                if _segment_crosses_box(start, end, box):
                    findings.append({"severity": "fail", "code": "edge_node_intrusion", "message": f"{routed_edge.edge.id},{box.node.id}"})
                    break
    used_area = sum(box.width * box.height for box in values)
    density = used_area / max(1, spec.width * spec.height)
    if density < 0.015:
        findings.append({"severity": "warn", "code": "sparse_composition", "message": f"density={density:.4f}"})
    if density > 0.55:
        findings.append({"severity": "fail", "code": "crowded_composition", "message": f"density={density:.4f}"})
    score = max(0.0, 100.0 - 25 * sum(f["severity"] == "fail" for f in findings) - 5 * sum(f["severity"] == "warn" for f in findings))
    return Scene(spec, theme, boxes, routed, findings, score)


def _svg_path(points: Iterable[tuple[float, float]]) -> str:
    values = list(points)
    return "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in values)


def _segment_crosses_box(start: tuple[float, float], end: tuple[float, float], box: Box, padding: float = 5) -> bool:
    x1, y1 = start
    x2, y2 = end
    left, right = box.x - padding, box.x + box.width + padding
    top, bottom = box.y - padding, box.y + box.height + padding
    if abs(y1 - y2) < 0.01:
        return top <= y1 <= bottom and max(min(x1, x2), left) < min(max(x1, x2), right)
    if abs(x1 - x2) < 0.01:
        return left <= x1 <= right and max(min(y1, y2), top) < min(max(y1, y2), bottom)
    return False


def _crossings_for(routed: RoutedEdge, all_edges: list[RoutedEdge]) -> dict[int, list[float]]:
    crossings: dict[int, list[float]] = {}
    for segment_index, (start, end) in enumerate(zip(routed.points, routed.points[1:])):
        if abs(start[1] - end[1]) > 0.01:
            continue
        low_x, high_x = sorted((start[0], end[0]))
        for other in all_edges:
            if other.edge.id == routed.edge.id:
                continue
            for other_start, other_end in zip(other.points, other.points[1:]):
                if abs(other_start[0] - other_end[0]) > 0.01:
                    continue
                low_y, high_y = sorted((other_start[1], other_end[1]))
                x, y = other_start[0], start[1]
                if low_x + 10 < x < high_x - 10 and low_y + 10 < y < high_y - 10:
                    crossings.setdefault(segment_index, []).append(x)
    return crossings


def _svg_path_with_bridges(routed: RoutedEdge, all_edges: list[RoutedEdge]) -> str:
    crossings = _crossings_for(routed, all_edges)
    commands = [f"M {routed.points[0][0]:.2f} {routed.points[0][1]:.2f}"]
    for index, (start, end) in enumerate(zip(routed.points, routed.points[1:])):
        bridge_x = sorted(crossings.get(index, []), reverse=end[0] < start[0])
        direction = 1 if end[0] >= start[0] else -1
        for x in bridge_x:
            commands.append(f"L {x - 8 * direction:.2f} {start[1]:.2f}")
            commands.append(f"Q {x:.2f} {start[1] - 10:.2f} {x + 8 * direction:.2f} {start[1]:.2f}")
        commands.append(f"L {end[0]:.2f} {end[1]:.2f}")
    return " ".join(commands)


def _math_path(expression: str, x: float, baseline: float, size: float, fill: str) -> tuple[str, float]:
    try:
        cache = Path(tempfile.gettempdir()) / "morepaper-matplotlib-cache"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(cache))
        from matplotlib.textpath import TextPath
        from matplotlib.path import Path as MplPath
        path = TextPath((0, 0), f"${expression}$", size=size, usetex=False)
        codes = path.codes
        vertices = path.vertices
        chunks: list[str] = []
        for (vx, vy), code in zip(vertices, codes):
            px, py = x + float(vx), baseline - float(vy)
            if code == MplPath.MOVETO:
                chunks.append(f"M{px:.2f},{py:.2f}")
            elif code == MplPath.LINETO:
                chunks.append(f"L{px:.2f},{py:.2f}")
            elif code == MplPath.CURVE3:
                chunks.append(f"Q{px:.2f},{py:.2f}")
            elif code == MplPath.CURVE4:
                chunks.append(f"C{px:.2f},{py:.2f}")
            elif code == MplPath.CLOSEPOLY:
                chunks.append("Z")
        width = max((float(v[0]) for v in vertices), default=len(expression) * size * 0.55)
        return f'<path class="math-run" data-math="{escape(expression)}" fill="{fill}" d="{" ".join(chunks)}"/>', width
    except Exception as exc:
        raise RuntimeError(f"math vectorization failed for {expression!r}: {exc}") from exc


def _runs_svg(runs: list[TextRun], box: Box, color: str, font_size: int = 18) -> str:
    lines = _label_lines(runs)
    line_height = font_size * 1.45
    baseline = box.cy - (len(lines) - 1) * line_height / 2 + font_size * 0.35
    output: list[str] = []
    for line_index, line in enumerate(lines):
        widths = [len(run.value) * font_size * (0.58 if run.kind == "text" else 0.62) for run in line]
        cursor = box.cx - sum(widths) / 2
        y = baseline + line_index * line_height
        for run, estimated in zip(line, widths):
            if run.kind == "text":
                output.append(
                    f'<text class="label-run" x="{cursor:.2f}" y="{y:.2f}" fill="{color}" '
                    f'font-size="{font_size}" font-family="Arial, Noto Sans CJK SC, sans-serif">{escape(run.value)}</text>'
                )
                cursor += estimated
            else:
                path, actual = _math_path(run.value, cursor, y, font_size, color)
                output.append(path)
                cursor += max(actual, estimated)
    return "\n".join(output)


def render_svg(scene: Scene, *, inspect: bool = False) -> str:
    spec, theme = scene.spec, scene.theme
    typography = typography_for(spec)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" height="{spec.height}" viewBox="0 0 {spec.width} {spec.height}" role="img" aria-labelledby="diagram-title diagram-desc">',
        f'<title id="diagram-title">{escape(spec.title or spec.figure_id)}</title>',
        f'<desc id="diagram-desc">{escape(spec.caption or spec.diagram_type)}</desc>',
        '<metadata>more-paper-workflow Step 7 native diagram</metadata>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z"/></marker></defs>',
        f'<rect width="100%" height="100%" fill="{theme.background}"/>',
    ]
    if spec.style in {"blueprint", "notebook", "review-canvas"}:
        for x in range(40, spec.width, 40):
            parts.append(f'<line class="grid" x1="{x}" y1="0" x2="{x}" y2="{spec.height}" stroke="{theme.grid}" stroke-width="1" opacity="0.35"/>')
        for y in range(40, spec.height, 40):
            parts.append(f'<line class="grid" x1="0" y1="{y}" x2="{spec.width}" y2="{y}" stroke="{theme.grid}" stroke-width="1" opacity="0.35"/>')
    if spec.title:
        parts.append(f'<text x="{spec.width / 2:.1f}" y="62" text-anchor="middle" fill="{theme.text}" font-size="{typography.title}" font-weight="700" font-family="Arial, Noto Sans CJK SC, sans-serif">{escape(spec.title)}</text>')

    for group in spec.groups:
        members = [scene.boxes[node_id] for node_id in group.node_ids]
        if not members:
            continue
        x = min(box.x for box in members) - 26
        y = min(box.y for box in members) - 44
        x2 = max(box.x + box.width for box in members) + 26
        y2 = max(box.y + box.height for box in members) + 26
        group_fill = "none" if spec.style == "minimal" else theme.surface_alt
        parts.append(f'<g class="group" data-group-id="{escape(group.id)}"><rect x="{x:.2f}" y="{y:.2f}" width="{x2-x:.2f}" height="{y2-y:.2f}" rx="16" fill="{group_fill}" stroke="{theme.grid}" stroke-dasharray="8 6"/><text x="{x+14:.2f}" y="{y+25:.2f}" fill="{theme.muted}" font-size="{typography.group}">{escape(group.label)}</text></g>')

    if spec.diagram_type == "sequence":
        for box in scene.boxes.values():
            parts.append(f'<line class="lifeline" x1="{box.cx:.2f}" y1="{box.y+box.height:.2f}" x2="{box.cx:.2f}" y2="{spec.height-70}" stroke="{theme.muted}" stroke-dasharray="7 7"/>')
    if spec.diagram_type == "timeline":
        y = spec.height * 0.5
        parts.append(f'<line class="timeline-axis" x1="70" y1="{y}" x2="{spec.width-70}" y2="{y}" stroke="{theme.stroke}" stroke-width="4"/>')

    for routed in scene.edges:
        d = _svg_path_with_bridges(routed, scene.edges)
        parts.append(f'<g class="edge" data-edge-id="{escape(routed.edge.id)}" data-kind="{escape(routed.edge.kind)}"><path d="{d}" fill="none" stroke="{theme.accent}" stroke-width="3" stroke-linejoin="round" marker-end="url(#arrow)"/>')
        if routed.edge.label:
            middle = routed.points[len(routed.points) // 2]
            label_box = Box(Node(routed.edge.id, routed.edge.runs), middle[0] - 80, middle[1] - 36, 160, 28)
            parts.append(_runs_svg(routed.edge.runs, label_box, theme.muted, typography.secondary))
        parts.append('</g>')

    for box in scene.boxes.values():
        fill = theme.surface_alt if box.node.role in {"decision", "store", "external"} else theme.surface
        if box.node.shape == "diamond":
            points = f"{box.cx:.2f},{box.y:.2f} {box.x+box.width:.2f},{box.cy:.2f} {box.cx:.2f},{box.y+box.height:.2f} {box.x:.2f},{box.cy:.2f}"
            shape = f'<polygon points="{points}" fill="{fill}" stroke="{theme.stroke}" stroke-width="2"/>'
        elif box.node.shape == "ellipse" or spec.diagram_type == "use_case":
            shape = f'<ellipse cx="{box.cx:.2f}" cy="{box.cy:.2f}" rx="{box.width/2:.2f}" ry="{box.height/2:.2f}" fill="{fill}" stroke="{theme.stroke}" stroke-width="2"/>'
        else:
            shape = f'<rect x="{box.x:.2f}" y="{box.y:.2f}" width="{box.width:.2f}" height="{box.height:.2f}" rx="{theme.radius}" fill="{fill}" stroke="{theme.stroke}" stroke-width="2"/>'
        parts.append(f'<g class="node" data-node-id="{escape(box.node.id)}" data-role="{escape(box.node.role)}">{shape}{_runs_svg(box.node.runs, box, theme.text, typography.node)}</g>')
        if inspect:
            parts.append(f'<rect class="inspect-box" x="{box.x:.2f}" y="{box.y:.2f}" width="{box.width:.2f}" height="{box.height:.2f}" fill="none" stroke="#dc2626" stroke-width="1" stroke-dasharray="5 4"/><text x="{box.x+4:.2f}" y="{box.y-5:.2f}" fill="#dc2626" font-size="12">{escape(box.node.id)}</text>')

    for index, annotation in enumerate(spec.annotations):
        annotation_box = Box(Node(annotation.id, annotation.runs), 42, spec.height - 70 - index * 28, spec.width - 84, 24)
        parts.append(f'<g class="annotation" data-annotation-id="{escape(annotation.id)}">{_runs_svg(annotation.runs, annotation_box, theme.muted, typography.secondary)}</g>')
    parts.append('</svg>')
    return "\n".join(parts)


def _hex(color: str) -> str:
    return color[:7] if re.fullmatch(r"#[0-9a-fA-F]{8}", color) else color


def _font(size: int):
    from PIL import ImageFont
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _math_png(expression: str, size: int, color: str):
    from PIL import Image
    cache = Path(tempfile.gettempdir()) / "morepaper-matplotlib-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image
    buffer = BytesIO()
    math_to_image(f"${expression}$", buffer, prop=FontProperties(size=size), dpi=72, format="png", color=color)
    buffer.seek(0)
    return Image.open(buffer).convert("RGBA")


def _draw_runs_png(image, draw, runs: list[TextRun], box: Box, color: str, font_size: int = 18) -> None:
    font = _font(font_size)
    lines = _label_lines(runs)
    line_height = font_size * 1.55
    top = box.cy - len(lines) * line_height / 2
    for line_index, line in enumerate(lines):
        fragments = []
        total_width = 0.0
        for run in line:
            if run.kind == "math":
                fragment = _math_png(run.value, font_size, color)
                width = fragment.width
            else:
                fragment = run.value
                bounds = draw.textbbox((0, 0), fragment, font=font)
                width = bounds[2] - bounds[0]
            fragments.append((run.kind, fragment, width))
            total_width += width
        cursor = box.cx - total_width / 2
        y = top + line_index * line_height
        for kind, fragment, width in fragments:
            if kind == "math":
                image.paste(fragment, (int(cursor), int(y + (line_height - fragment.height) / 2)), fragment)
            else:
                draw.text((cursor, y + line_height / 2), fragment, font=font, fill=color, anchor="lm")
            cursor += width


def render_png(scene: Scene, path: Path) -> None:
    from PIL import Image, ImageDraw
    spec, theme = scene.spec, scene.theme
    typography = typography_for(spec)
    image = Image.new("RGB", (spec.width, spec.height), _hex(theme.background))
    draw = ImageDraw.Draw(image)
    title_font, small_font = _font(typography.title), _font(typography.group)
    if spec.title:
        draw.text((spec.width / 2, 38), spec.title, font=title_font, fill=_hex(theme.text), anchor="ma")
    for group in spec.groups:
        members = [scene.boxes[node_id] for node_id in group.node_ids]
        if not members:
            continue
        x = min(box.x for box in members) - 26
        y = min(box.y for box in members) - 44
        x2 = max(box.x + box.width for box in members) + 26
        y2 = max(box.y + box.height for box in members) + 26
        group_fill = None if spec.style == "minimal" else _hex(theme.surface_alt)
        draw.rounded_rectangle((x, y, x2, y2), radius=16, fill=group_fill, outline=_hex(theme.grid), width=2)
        draw.text((x + 14, y + 10), group.label, font=small_font, fill=_hex(theme.muted))
    if spec.diagram_type == "sequence":
        for box in scene.boxes.values():
            draw.line((box.cx, box.y + box.height, box.cx, spec.height - 70), fill=_hex(theme.muted), width=2)
    if spec.diagram_type == "timeline":
        y = spec.height * 0.5
        draw.line((70, y, spec.width - 70, y), fill=_hex(theme.stroke), width=4)
    for routed in scene.edges:
        draw.line(routed.points, fill=_hex(theme.accent), width=3, joint="curve")
        if len(routed.points) >= 2:
            (x1, y1), (x2, y2) = routed.points[-2:]
            angle = math.atan2(y2 - y1, x2 - x1)
            arrow = [(x2, y2), (x2 - 14 * math.cos(angle - 0.45), y2 - 14 * math.sin(angle - 0.45)),
                     (x2 - 14 * math.cos(angle + 0.45), y2 - 14 * math.sin(angle + 0.45))]
            draw.polygon(arrow, fill=_hex(theme.accent))
        if routed.edge.label:
            middle = routed.points[len(routed.points) // 2]
            label_box = Box(Node(routed.edge.id, routed.edge.runs), middle[0] - 80, middle[1] - 34, 160, 24)
            _draw_runs_png(image, draw, routed.edge.runs, label_box, _hex(theme.muted), typography.secondary)
    for box in scene.boxes.values():
        fill = _hex(theme.surface_alt if box.node.role in {"decision", "store", "external"} else theme.surface)
        bounds = (box.x, box.y, box.x + box.width, box.y + box.height)
        if box.node.shape == "ellipse" or spec.diagram_type == "use_case":
            draw.ellipse(bounds, fill=fill, outline=_hex(theme.stroke), width=2)
        elif box.node.shape == "diamond":
            draw.polygon([(box.cx, box.y), (box.x + box.width, box.cy), (box.cx, box.y + box.height), (box.x, box.cy)], fill=fill, outline=_hex(theme.stroke))
        else:
            draw.rounded_rectangle(bounds, radius=theme.radius, fill=fill, outline=_hex(theme.stroke), width=2)
        _draw_runs_png(image, draw, box.node.runs, box, _hex(theme.text), typography.node)
    for index, annotation in enumerate(spec.annotations):
        annotation_box = Box(Node(annotation.id, annotation.runs), 42, spec.height - 70 - index * 28, spec.width - 84, 24)
        _draw_runs_png(image, draw, annotation.runs, annotation_box, _hex(theme.muted), typography.secondary)
    image.save(path, format="PNG", optimize=True)
