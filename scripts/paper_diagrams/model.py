from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "morepaper.paper-diagram.v1"
DIAGRAM_TYPES = {
    "architecture",
    "agent_architecture",
    "flowchart",
    "data_flow",
    "sequence",
    "state_machine",
    "timeline",
    "comparison_matrix",
    "er_diagram",
    "use_case",
}
STYLE_IDS = {
    "clean",
    "terminal",
    "blueprint",
    "notebook",
    "glass",
    "editorial",
    "minimal",
    "dark",
    "review-canvas",
    "cloud",
    "event-stream",
    "operations",
}

TOP_FIELDS = {
    "schema_version", "figure_id", "diagram_type", "style", "title", "caption",
    "canvas", "nodes", "edges", "groups", "annotations", "layout_locked",
}
NODE_FIELDS = {
    "id", "label", "label_runs", "role", "group", "order", "x", "y", "width",
    "height", "shape", "metadata",
}
EDGE_FIELDS = {"id", "source", "target", "label", "label_runs", "kind", "order", "metadata"}
GROUP_FIELDS = {"id", "label", "node_ids", "role"}
ANNOTATION_FIELDS = {"id", "label", "label_runs", "anchor", "role"}
RUN_FIELDS = {"kind", "value"}
SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
MATH_SPLIT = re.compile(r"(\$[^$]+\$)")
MATH_COMMAND = re.compile(r"\\([A-Za-z]+)")
SUPPORTED_MATH_COMMANDS = {
    "alpha", "beta", "gamma", "delta", "epsilon", "theta", "lambda", "mu", "nu",
    "pi", "rho", "sigma", "tau", "phi", "chi", "psi", "omega", "Delta", "Gamma",
    "Lambda", "Omega", "Phi", "Pi", "Psi", "Sigma", "Theta", "cdot", "times", "pm",
    "leq", "geq", "neq", "approx", "infty", "sum", "prod", "int", "partial", "sqrt",
    "frac", "mathrm", "mathbf", "mathit", "text", "left", "right", "log", "ln", "exp",
    "sin", "cos", "tan", "min", "max", "argmin", "argmax",
    "hat", "bar", "vec", "overline", "underline", "dot", "ddot",
}
UNSAFE_TEXT = re.compile(r"(?:<\s*script|javascript:|https?://|file://|data:text/html)", re.I)


class DiagramSpecError(ValueError):
    def __init__(self, code: str, message: str, *, needs_author_check: bool = False):
        super().__init__(message)
        self.code = code
        self.needs_author_check = needs_author_check


@dataclass(frozen=True)
class TextRun:
    kind: str
    value: str


@dataclass
class Node:
    id: str
    runs: list[TextRun]
    role: str = "process"
    group: str = ""
    order: int = 0
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    shape: str = "rounded"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return "".join(run.value for run in self.runs)


@dataclass
class Edge:
    id: str
    source: str
    target: str
    runs: list[TextRun]
    kind: str = "flow"
    order: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return "".join(run.value for run in self.runs)


@dataclass
class Group:
    id: str
    label: str
    node_ids: list[str]
    role: str = "section"


@dataclass
class Annotation:
    id: str
    runs: list[TextRun]
    anchor: str = ""
    role: str = "note"


@dataclass
class DiagramSpec:
    figure_id: str
    diagram_type: str
    style: str
    title: str
    caption: str
    width: int
    height: int
    nodes: list[Node]
    edges: list[Edge]
    groups: list[Group]
    annotations: list[Annotation]
    layout_locked: bool
    source_path: Path
    source_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_unknown(payload: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise DiagramSpecError("unknown_field", f"{context} contains unknown fields: {', '.join(unknown)}")


def _safe_string(value: Any, context: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise DiagramSpecError("invalid_string", f"{context} must be a string")
    if not allow_empty and not value.strip():
        raise DiagramSpecError("empty_string", f"{context} must not be empty")
    if UNSAFE_TEXT.search(value):
        raise DiagramSpecError("unsafe_content", f"{context} contains an external or executable reference")
    return value


def _safe_id(value: Any, context: str) -> str:
    text = _safe_string(value, context, allow_empty=False)
    if not SAFE_ID.fullmatch(text):
        raise DiagramSpecError("invalid_id", f"{context} is not a stable identifier: {text!r}")
    return text


def _math_run(value: str, context: str) -> TextRun:
    expression = value[1:-1] if value.startswith("$") and value.endswith("$") else value
    if not expression.strip() or "$$" in value or "\\begin" in expression or "\\end" in expression:
        raise DiagramSpecError(
            "unsupported_math", f"{context} contains unsupported display or matrix math", needs_author_check=True
        )
    unsupported = sorted(set(MATH_COMMAND.findall(expression)) - SUPPORTED_MATH_COMMANDS)
    if unsupported:
        raise DiagramSpecError(
            "unsupported_math_command",
            f"{context} contains unsupported math commands: {', '.join(unsupported)}",
            needs_author_check=True,
        )
    if expression.count("{") != expression.count("}"):
        raise DiagramSpecError("unbalanced_math", f"{context} has unbalanced braces", needs_author_check=True)
    return TextRun("math", expression)


def parse_runs(payload: dict[str, Any], context: str) -> list[TextRun]:
    explicit = payload.get("label_runs")
    if explicit is not None:
        if not isinstance(explicit, list) or not explicit:
            raise DiagramSpecError("invalid_label_runs", f"{context}.label_runs must be a non-empty list")
        runs: list[TextRun] = []
        for index, item in enumerate(explicit):
            if not isinstance(item, dict):
                raise DiagramSpecError("invalid_label_run", f"{context}.label_runs[{index}] must be an object")
            _reject_unknown(item, RUN_FIELDS, f"{context}.label_runs[{index}]")
            kind = item.get("kind")
            value = _safe_string(item.get("value"), f"{context}.label_runs[{index}].value", allow_empty=False)
            if kind == "math":
                runs.append(_math_run(value, context))
            elif kind == "text":
                runs.append(TextRun("text", value))
            else:
                raise DiagramSpecError("invalid_run_kind", f"{context} run kind must be text or math")
        return runs

    label = _safe_string(payload.get("label", ""), f"{context}.label")
    if label.count("$") % 2:
        raise DiagramSpecError("unbalanced_inline_math", f"{context} has an unmatched $", needs_author_check=True)
    runs = []
    for part in MATH_SPLIT.split(label):
        if not part:
            continue
        runs.append(_math_run(part, context) if part.startswith("$") else TextRun("text", part))
    return runs or [TextRun("text", "")]


def _number(value: Any, context: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DiagramSpecError("invalid_number", f"{context} must be numeric")
    number = float(value)
    if not minimum <= number <= maximum:
        raise DiagramSpecError("number_out_of_range", f"{context} must be between {minimum} and {maximum}")
    return number


def is_diagram_spec(path: str | Path | None) -> bool:
    if not path:
        return False
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    return isinstance(payload, dict) and payload.get("schema_version") == SCHEMA_VERSION


def load_spec(path: str | Path) -> DiagramSpec:
    source = Path(path).expanduser().resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise DiagramSpecError("spec_unreadable", f"cannot read diagram spec: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DiagramSpecError("invalid_json", f"diagram spec is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DiagramSpecError("invalid_spec", "diagram spec must be a JSON object")
    _reject_unknown(payload, TOP_FIELDS, "diagram spec")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise DiagramSpecError("invalid_schema", f"schema_version must be {SCHEMA_VERSION}")

    figure_id = _safe_id(payload.get("figure_id"), "figure_id")
    diagram_type = _safe_string(payload.get("diagram_type"), "diagram_type", allow_empty=False)
    if diagram_type not in DIAGRAM_TYPES:
        raise DiagramSpecError("invalid_diagram_type", f"unsupported diagram_type: {diagram_type}")
    style = _safe_string(payload.get("style", "clean"), "style", allow_empty=False)
    if style not in STYLE_IDS:
        raise DiagramSpecError("invalid_style", f"unsupported style: {style}")
    title = _safe_string(payload.get("title", ""), "title")
    caption = _safe_string(payload.get("caption", ""), "caption")

    canvas = payload.get("canvas", {})
    if not isinstance(canvas, dict):
        raise DiagramSpecError("invalid_canvas", "canvas must be an object")
    _reject_unknown(canvas, {"width", "height"}, "canvas")
    width = int(_number(canvas.get("width", 1600), "canvas.width", 640, 5000))
    height = int(_number(canvas.get("height", 1000), "canvas.height", 480, 5000))
    layout_locked = payload.get("layout_locked", False)
    if not isinstance(layout_locked, bool):
        raise DiagramSpecError("invalid_layout_lock", "layout_locked must be boolean")

    raw_nodes = payload.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise DiagramSpecError("missing_nodes", "nodes must be a non-empty list")
    nodes: list[Node] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_nodes):
        context = f"nodes[{index}]"
        if not isinstance(item, dict):
            raise DiagramSpecError("invalid_node", f"{context} must be an object")
        _reject_unknown(item, NODE_FIELDS, context)
        node_id = _safe_id(item.get("id"), f"{context}.id")
        if node_id in seen:
            raise DiagramSpecError("duplicate_id", f"duplicate node id: {node_id}")
        seen.add(node_id)
        has_position = "x" in item or "y" in item
        if has_position and not layout_locked:
            raise DiagramSpecError("unreviewed_fixed_layout", f"{context} has coordinates but layout_locked is false")
        if has_position and not {"x", "y"}.issubset(item):
            raise DiagramSpecError("incomplete_position", f"{context} must provide both x and y")
        nodes.append(Node(
            id=node_id,
            runs=parse_runs(item, context),
            role=_safe_string(item.get("role", "process"), f"{context}.role", allow_empty=False),
            group=_safe_string(item.get("group", ""), f"{context}.group"),
            order=int(item.get("order", index)),
            x=_number(item["x"], f"{context}.x", 0, width) if "x" in item else None,
            y=_number(item["y"], f"{context}.y", 0, height) if "y" in item else None,
            width=_number(item["width"], f"{context}.width", 60, width) if "width" in item else None,
            height=_number(item["height"], f"{context}.height", 36, height) if "height" in item else None,
            shape=_safe_string(item.get("shape", "rounded"), f"{context}.shape", allow_empty=False),
            metadata=item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {},
        ))

    raw_edges = payload.get("edges", [])
    if not isinstance(raw_edges, list):
        raise DiagramSpecError("invalid_edges", "edges must be a list")
    edges: list[Edge] = []
    edge_ids: set[str] = set()
    for index, item in enumerate(raw_edges):
        context = f"edges[{index}]"
        if not isinstance(item, dict):
            raise DiagramSpecError("invalid_edge", f"{context} must be an object")
        _reject_unknown(item, EDGE_FIELDS, context)
        edge_id = _safe_id(item.get("id", f"edge-{index + 1}"), f"{context}.id")
        if edge_id in edge_ids or edge_id in seen:
            raise DiagramSpecError("duplicate_id", f"duplicate id: {edge_id}")
        edge_ids.add(edge_id)
        source_id = _safe_id(item.get("source"), f"{context}.source")
        target_id = _safe_id(item.get("target"), f"{context}.target")
        if source_id not in seen or target_id not in seen:
            raise DiagramSpecError("dangling_edge", f"{context} references a missing node")
        if source_id == target_id:
            raise DiagramSpecError("self_edge", f"{context} cannot connect a node to itself")
        edges.append(Edge(
            id=edge_id, source=source_id, target=target_id, runs=parse_runs(item, context),
            kind=_safe_string(item.get("kind", "flow"), f"{context}.kind", allow_empty=False),
            order=int(item.get("order", index)),
            metadata=item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {},
        ))

    raw_groups = payload.get("groups", [])
    if not isinstance(raw_groups, list):
        raise DiagramSpecError("invalid_groups", "groups must be a list")
    groups: list[Group] = []
    for index, item in enumerate(raw_groups):
        context = f"groups[{index}]"
        if not isinstance(item, dict):
            raise DiagramSpecError("invalid_group", f"{context} must be an object")
        _reject_unknown(item, GROUP_FIELDS, context)
        group_id = _safe_id(item.get("id"), f"{context}.id")
        node_ids = item.get("node_ids", [])
        if not isinstance(node_ids, list) or any(value not in seen for value in node_ids):
            raise DiagramSpecError("invalid_group_nodes", f"{context}.node_ids contains missing nodes")
        groups.append(Group(group_id, _safe_string(item.get("label", ""), f"{context}.label"), node_ids,
                            _safe_string(item.get("role", "section"), f"{context}.role", allow_empty=False)))

    raw_annotations = payload.get("annotations", [])
    if not isinstance(raw_annotations, list):
        raise DiagramSpecError("invalid_annotations", "annotations must be a list")
    annotations: list[Annotation] = []
    for index, item in enumerate(raw_annotations):
        context = f"annotations[{index}]"
        if not isinstance(item, dict):
            raise DiagramSpecError("invalid_annotation", f"{context} must be an object")
        _reject_unknown(item, ANNOTATION_FIELDS, context)
        annotations.append(Annotation(
            _safe_id(item.get("id", f"annotation-{index + 1}"), f"{context}.id"),
            parse_runs(item, context),
            _safe_string(item.get("anchor", ""), f"{context}.anchor"),
            _safe_string(item.get("role", "note"), f"{context}.role", allow_empty=False),
        ))

    return DiagramSpec(
        figure_id, diagram_type, style, title, caption, width, height, nodes, edges,
        groups, annotations, layout_locked, source, sha256_file(source)
    )
