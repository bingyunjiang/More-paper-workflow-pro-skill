from __future__ import annotations

import argparse
import json
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any


FORBIDDEN_TERMS = [
    "".join(map(chr, [79, 80, 74, 85])),
    "".join(map(chr, [111, 112, 106, 117])),
    "".join(map(chr, [111, 114, 105, 103, 105, 110, 112, 114, 111])),
    "".join(map(chr, [79, 114, 105, 103, 105, 110, 76, 97, 98])),
    "".join(map(chr, [71, 114, 97, 112, 104, 32, 71, 97, 108, 108, 101, 114, 121])),
    "".join(map(chr, [67, 79, 77, 32, 97, 117, 116, 111, 109, 97, 116, 105, 111, 110])),
]

IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".claude", ".codex"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".r", ".toml", ".txt"}
SECURITY_IGNORED_PREFIXES = (
    "tests/tmp-pdf-drill/",
)
FORBIDDEN_PACKAGE_ENTRIES = {
    ".codex/config.toml",
}
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>ZOTERO_API_KEY|ZOTERO_LIBRARY_ID|ZOTERO_USER_ID)\s*=\s*['\"](?P<value>[^'\"]+)['\"]"
)
AUTHOR_LOCAL_PATH_RE = re.compile(
    r"(?:"
    + re.escape("/" + "Users" + "/" + "Bing" + "/")
    + r"|"
    + re.escape("C:" + "\\" + "Users" + "\\" + "Bing" + "\\")
    + r")",
    re.IGNORECASE,
)
PROJECT_NAME = "more-paper-workflow"
LEGACY_NAME = "more-paper-workflow" + "-pro-skill"
PUBLIC_STEP7_MODES = {
    "full-document",
    "chapter-only",
    "continue-existing",
    "abstract-only",
    "review-only",
    "revision-only",
}
STEP7_OPERATIONS = {"write", "citation-audit", "figure", "pre-review"}
STEP7_TARGET_GENRES = {"thesis", "journal", "review", "report", "proposal", "conference", "course-paper"}
STEP7_FIGURE_MODES = {"auto_insert", "post_write", "skip"}
STEP8_OUTPUT_MODES = {"quick-polish", "audited-polish"}
STEP8_REWRITE_SCOPES = {"in-place", "bounded", "structural"}
STEP8_REWRITE_LEVELS = {"minimal", "standard", "aggressive"}
STEP_RUNTIME_PATHS = (
    "agents/step_1_entry.md",
    "agents/step_1_topic.md",
    "agents/step_2_outline.md",
    "agents/step_3_entry.md",
    "agents/step_3_search_plan.md",
    "agents/step_4_search_score.md",
    "agents/step_5_download.md",
    "agents/step_6_entry.md",
    "agents/step_6_zotero.md",
    "agents/step_7_entry.md",
    "agents/step_7_writing.md",
    "agents/step_8_entry.md",
    "agents/step_8_polishing.md",
)
REQUIRED_RUNTIME_PATHS = {
    *STEP_RUNTIME_PATHS,
    "agents/openai.yaml",
    "references/entry-guide.md",
    "references/reference-index.md",
    "references/entry-routing-index.md",
    "references/trigger-catalog.md",
    "references/scientific-figure-reproduction.md",
    "references/paper-diagram-contract.md",
    "references/step7-evidence-intake.md",
    "references/step7-drafting-contract.md",
    "references/step7-citation-audit.md",
    "references/step7-figure-workflow.md",
    "references/step7-pre-review.md",
    "references/step7-completion-validation.md",
    "references/completion-gates.md",
    "references/equation-writing-contract.md",
    "references/failure-triage.md",
    "references/agent-execution-discipline.md",
    "references/step-handoff-contract.md",
    "references/update-reminder-protocol.md",
    "scripts/build_figure_asset_check.py",
    "scripts/paper_diagrams/__init__.py",
    "scripts/paper_diagrams/model.py",
    "scripts/paper_diagrams/render.py",
    "scripts/paper_diagrams/engine.py",
    "schemas/paper-diagram-v1.schema.json",
    "scripts/equation_guard.py",
}
LEGACY_NAME_ALLOWLIST = {
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "docs/rename-migration-v1.0.22.md",
    "references/trigger-catalog.md",
    "skills/more-paper-workflow/SKILL.md",
}
REQUIRED_ROOT_PATHS = {
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    "skills/more-paper-workflow/SKILL.md",
    "SKILL.md",
    "manifest.yaml",
    "manifest.step3.yaml",
    "manifest.step7.yaml",
    "manifest.step8.yaml",
    "schemas/workflow-contract-registry.json",
    "schemas/workflow-run-envelope.schema.json",
    "static/core/workflow-run-envelope.md",
} | REQUIRED_RUNTIME_PATHS


def add_failure(failures: list[dict[str, str]], code: str, path: str, **details: str) -> None:
    failures.append({"code": code, "path": path, **details})


def _is_placeholder_secret(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized.isdigit()
        or normalized.startswith("${")
        or "your" in normalized
        or "example" in normalized
        or "placeholder" in normalized
        or "你的" in value
    )


def scan_text_security(text: str, relative: str, failures: list[dict[str, str]]) -> None:
    normalized_relative = relative.replace("\\", "/")
    if any(normalized_relative.startswith(prefix) for prefix in SECURITY_IGNORED_PREFIXES):
        return
    if normalized_relative in FORBIDDEN_PACKAGE_ENTRIES:
        add_failure(failures, "local_codex_config_present", normalized_relative)
    for match in SECRET_ASSIGNMENT_RE.finditer(text):
        if not _is_placeholder_secret(match.group("value")):
            add_failure(
                failures,
                "committed_secret_value",
                normalized_relative,
                key=match.group("key"),
            )
    if AUTHOR_LOCAL_PATH_RE.search(text):
        add_failure(failures, "author_local_path", normalized_relative)


def read_json(path: Path, failures: list[dict[str, str]]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_failure(failures, "invalid_json", str(path), message=str(exc))
        return {}
    if not isinstance(payload, dict):
        add_failure(failures, "invalid_json_root", str(path))
        return {}
    return payload


def yaml_axis_allowed(text: str, axis: str) -> list[str]:
    lines = text.splitlines()
    in_axis = False
    in_allowed = False
    values: list[str] = []
    for line in lines:
        if re.fullmatch(rf"  {re.escape(axis)}:\s*", line):
            in_axis = True
            in_allowed = False
            continue
        if in_axis and re.match(r"  \S", line):
            break
        if in_axis and re.fullmatch(r"    allowed:\s*", line):
            in_allowed = True
            continue
        if in_allowed:
            match = re.fullmatch(r"      -\s+(.+?)\s*", line)
            if match:
                values.append(match.group(1).strip("'\""))
                continue
            if line.strip() and len(line) - len(line.lstrip()) <= 4:
                break
    return values


def yaml_top_level_sequence(text: str, section: str) -> list[str]:
    lines = text.splitlines()
    in_section = False
    values: list[str] = []
    for line in lines:
        if re.fullmatch(rf"{re.escape(section)}:\s*", line):
            in_section = True
            continue
        if in_section and line and not line.startswith((" ", "\t")):
            break
        if in_section:
            match = re.fullmatch(r"  -\s+(.+?)\s*", line)
            if match:
                values.append(match.group(1).strip("'\""))
    return values


def yaml_mapping(text: str, section: str) -> dict[str, str]:
    lines = text.splitlines()
    in_section = False
    result: dict[str, str] = {}
    for line in lines:
        if re.fullmatch(rf"{re.escape(section)}:\s*", line):
            in_section = True
            continue
        if in_section and line and not line.startswith((" ", "\t")):
            break
        if in_section:
            match = re.fullmatch(r"  ([^:#]+):\s*(\S.*?)\s*", line)
            if match:
                result[match.group(1).strip()] = match.group(2).strip("'\"")
    return result


def validate_route_targets(
    root: Path,
    mapping: dict[str, str],
    failures: list[dict[str, str]],
    manifest_path: Path,
) -> None:
    resolved_root = root.resolve()
    for route, target in mapping.items():
        candidate = (root / target).resolve()
        if not candidate.is_relative_to(resolved_root):
            add_failure(
                failures,
                "route_target_outside_root",
                str(manifest_path),
                route=route,
                target=target,
            )
        elif not candidate.is_file():
            add_failure(
                failures,
                "missing_route_target",
                str(manifest_path),
                route=route,
                target=target,
            )


def manifest_markdown_targets(text: str) -> set[str]:
    return set(
        re.findall(
            r"(?<![A-Za-z0-9_.-])((?:agents|references|commands|static)/[A-Za-z0-9_./-]+\.md)",
            text,
        )
    )


def validate_manifest_markdown_targets(
    root: Path,
    text: str,
    failures: list[dict[str, str]],
    manifest_path: Path,
) -> None:
    resolved_root = root.resolve()
    for target in sorted(manifest_markdown_targets(text)):
        candidate = (root / target).resolve()
        if not candidate.is_relative_to(resolved_root):
            add_failure(failures, "route_target_outside_root", str(manifest_path), target=target)
        elif not candidate.is_file():
            add_failure(failures, "missing_route_target", str(manifest_path), target=target)


def validate_repository_structure(root: Path, failures: list[dict[str, str]]) -> None:
    if not (root / "SKILL.md").is_file() or not (root / "manifest.yaml").is_file():
        return

    missing_required_paths = []
    for relative in sorted(REQUIRED_ROOT_PATHS):
        if not (root / relative).is_file():
            add_failure(failures, "missing_required_path", relative)
            missing_required_paths.append(relative)
    if missing_required_paths:
        return

    main_manifest_path = root / "manifest.yaml"
    main_text = main_manifest_path.read_text(encoding="utf-8")
    allowed_steps = set(yaml_axis_allowed(main_text, "step"))
    step_routes = yaml_mapping(main_text, "step_routes")
    if allowed_steps != set(step_routes):
        add_failure(
            failures,
            "manifest_route_mismatch",
            "manifest.yaml",
            allowed=",".join(sorted(allowed_steps)),
            routes=",".join(sorted(step_routes)),
        )
    validate_route_targets(root, step_routes, failures, main_manifest_path)

    registry_path = root / "schemas" / "workflow-contract-registry.json"
    registry = read_json(registry_path, failures) if registry_path.is_file() else {}
    if registry.get("schema_version") != "morepaper.workflow-contracts.v1":
        add_failure(
            failures,
            "workflow_registry_schema_mismatch",
            "schemas/workflow-contract-registry.json",
        )
    global_contract = registry.get("global") if isinstance(registry.get("global"), dict) else {}
    if set(yaml_axis_allowed(main_text, "entry_mode")) != set(global_contract.get("entry_modes", [])):
        add_failure(
            failures,
            "manifest_entry_mode_registry_mismatch",
            "manifest.yaml",
        )
    envelope_schema_path = root / "schemas" / "workflow-run-envelope.schema.json"
    envelope_schema = read_json(envelope_schema_path, failures) if envelope_schema_path.is_file() else {}
    envelope_properties = envelope_schema.get("properties") if isinstance(envelope_schema.get("properties"), dict) else {}
    schema_version_property = envelope_properties.get("schema_version") if isinstance(envelope_properties.get("schema_version"), dict) else {}
    if schema_version_property.get("const") != "morepaper.workflow-run.v1":
        add_failure(
            failures,
            "workflow_envelope_schema_mismatch",
            "schemas/workflow-run-envelope.schema.json",
        )
    for property_name, registry_name in (
        ("entry_mode", "entry_modes"),
        ("route_mode", "route_modes"),
        ("readiness", "readiness"),
    ):
        property_contract = envelope_properties.get(property_name) if isinstance(envelope_properties.get(property_name), dict) else {}
        if set(property_contract.get("enum", [])) != set(global_contract.get(registry_name, [])):
            add_failure(
                failures,
                "workflow_envelope_registry_mismatch",
                "schemas/workflow-run-envelope.schema.json",
                field=property_name,
            )

    step3_path = root / "manifest.step3.yaml"
    step3_text = step3_path.read_text(encoding="utf-8")
    step3_contract = registry.get("step3") if isinstance(registry.get("step3"), dict) else {}
    base_workflows = set(yaml_axis_allowed(step3_text, "base_workflow"))
    addons = set(yaml_axis_allowed(step3_text, "addons"))
    base_routes = yaml_mapping(step3_text, "base_workflow_routes")
    addon_routes = yaml_mapping(step3_text, "addon_routes")
    if base_workflows != set(step3_contract.get("base_workflow", [])) or base_workflows != set(base_routes):
        add_failure(failures, "step3_base_workflow_mismatch", "manifest.step3.yaml")
    if addons != set(step3_contract.get("addons", [])) or addons != set(addon_routes):
        add_failure(failures, "step3_addon_mismatch", "manifest.step3.yaml")
    validate_route_targets(root, base_routes, failures, step3_path)
    validate_route_targets(root, addon_routes, failures, step3_path)
    step3_docs = (
        (root / "agents" / "step_3_entry.md").read_text(encoding="utf-8")
        + (root / "agents" / "step_3_search_plan.md").read_text(encoding="utf-8")
    )
    for value in sorted(base_workflows | addons):
        if value not in step3_docs:
            add_failure(failures, "step3_axis_undocumented", "agents/step_3_entry.md", value=value)

    step7_path = root / "manifest.step7.yaml"
    step7_text = step7_path.read_text(encoding="utf-8")
    validate_manifest_markdown_targets(root, step7_text, failures, step7_path)
    modes = set(yaml_axis_allowed(step7_text, "mode"))
    operations = set(yaml_axis_allowed(step7_text, "operation"))
    target_genres = set(yaml_axis_allowed(step7_text, "target_genre"))
    figure_modes = set(yaml_axis_allowed(step7_text, "figure_mode"))
    figure_backends = set(yaml_axis_allowed(step7_text, "figure_backend"))
    figure_asset_actions = set(yaml_axis_allowed(step7_text, "figure_asset_action"))
    mode_routes = yaml_mapping(step7_text, "mode_routes")
    operation_routes = yaml_mapping(step7_text, "operation_routes")
    if modes != PUBLIC_STEP7_MODES or modes != set(mode_routes):
        add_failure(
            failures,
            "step7_mode_mismatch",
            "manifest.step7.yaml",
            allowed=",".join(sorted(modes)),
            routes=",".join(sorted(mode_routes)),
        )
    if operations != STEP7_OPERATIONS or operations != set(operation_routes):
        add_failure(
            failures,
            "step7_operation_mismatch",
            "manifest.step7.yaml",
            allowed=",".join(sorted(operations)),
            routes=",".join(sorted(operation_routes)),
        )
    step7_contract = registry.get("step7") if isinstance(registry.get("step7"), dict) else {}
    for axis, values in {
        "mode": modes,
        "operation": operations,
        "target_genre": target_genres,
        "figure_mode": figure_modes,
        "figure_backend": figure_backends,
        "figure_asset_action": figure_asset_actions,
    }.items():
        if values != set(step7_contract.get(axis, [])):
            add_failure(
                failures,
                "step7_registry_axis_mismatch",
                "manifest.step7.yaml",
                axis=axis,
            )
    if target_genres != STEP7_TARGET_GENRES:
        add_failure(failures, "step7_target_genre_mismatch", "manifest.step7.yaml")
    if figure_modes != STEP7_FIGURE_MODES:
        add_failure(failures, "step7_figure_mode_mismatch", "manifest.step7.yaml")
    validate_route_targets(root, mode_routes, failures, step7_path)
    validate_route_targets(root, operation_routes, failures, step7_path)
    step7_docs = (
        (root / "agents" / "step_7_entry.md").read_text(encoding="utf-8")
        + (root / "agents" / "step_7_writing.md").read_text(encoding="utf-8")
        + (root / "references" / "writing-modes.md").read_text(encoding="utf-8")
        + (root / "references" / "genre-style-axis.md").read_text(encoding="utf-8")
    )
    for value in sorted(modes | operations | target_genres | figure_modes | figure_backends | figure_asset_actions):
        if value not in step7_docs:
            add_failure(failures, "step7_axis_undocumented", "agents/step_7_entry.md", value=value)

    step8_path = root / "manifest.step8.yaml"
    step8_text = step8_path.read_text(encoding="utf-8")
    step8_contract = registry.get("step8") if isinstance(registry.get("step8"), dict) else {}
    for axis in ("revision_scope", "language", "target_genre", "output_mode", "rewrite_scope", "rewrite_level"):
        values = set(yaml_axis_allowed(step8_text, axis))
        if values != set(step8_contract.get(axis, [])):
            add_failure(
                failures,
                "step8_registry_axis_mismatch",
                "manifest.step8.yaml",
                axis=axis,
            )
    if set(yaml_axis_allowed(step8_text, "output_mode")) != STEP8_OUTPUT_MODES:
        add_failure(failures, "step8_output_mode_mismatch", "manifest.step8.yaml")
    if set(yaml_axis_allowed(step8_text, "rewrite_scope")) != STEP8_REWRITE_SCOPES:
        add_failure(failures, "step8_rewrite_scope_mismatch", "manifest.step8.yaml")
    if set(yaml_axis_allowed(step8_text, "rewrite_level")) != STEP8_REWRITE_LEVELS:
        add_failure(failures, "step8_rewrite_level_mismatch", "manifest.step8.yaml")
    for required_reference in (
        "references/step8-rewrite-scope.md",
        "references/protected-spans.md",
        "references/equation-writing-contract.md",
        "references/academic-ai-trace-index.md",
        "static/core/workflow-run-envelope.md",
    ):
        if f"- {required_reference}" not in step8_text:
            add_failure(
                failures,
                "step8_required_reference_missing",
                "manifest.step8.yaml",
                target=required_reference,
            )
    step8_docs = (
        (root / "agents" / "step_8_entry.md").read_text(encoding="utf-8")
        + (root / "agents" / "step_8_polishing.md").read_text(encoding="utf-8")
        + (root / "references" / "polish-modes.md").read_text(encoding="utf-8")
        + (root / "references" / "step8-rewrite-scope.md").read_text(encoding="utf-8")
    )
    step8_values: set[str] = set()
    for axis in ("revision_scope", "language", "target_genre", "output_mode", "rewrite_scope", "rewrite_level"):
        step8_values.update(yaml_axis_allowed(step8_text, axis))
    for value in sorted(step8_values):
        if value not in step8_docs:
            add_failure(failures, "step8_axis_undocumented", "agents/step_8_entry.md", value=value)

    step4_text = (root / "agents" / "step_4_search_score.md").read_text(encoding="utf-8")
    step4_contract = registry.get("step4") if isinstance(registry.get("step4"), dict) else {}
    for profile in step4_contract.get("execution_profiles", []):
        if f"`{profile}`" not in step4_text:
            add_failure(failures, "step4_profile_undocumented", "agents/step_4_search_score.md", profile=profile)

    step6_text = (root / "agents" / "step_6_zotero.md").read_text(encoding="utf-8")
    step6_contract = registry.get("step6") if isinstance(registry.get("step6"), dict) else {}
    for profile in step6_contract.get("execution_profiles", []):
        if f"`{profile}`" not in step6_text:
            add_failure(failures, "step6_profile_undocumented", "agents/step_6_zotero.md", profile=profile)

    step1_handoff = (root / "references" / "step1-handoff-schema.md").read_text(encoding="utf-8")
    for path in (registry.get("step1", {}).get("canonical_handoff", {}) if isinstance(registry.get("step1"), dict) else {}).values():
        if f"`{path}`" not in step1_handoff:
            add_failure(
                failures,
                "step1_handoff_registry_mismatch",
                "references/step1-handoff-schema.md",
                field=str(path),
            )

    step5_text = (root / "agents" / "step_5_download.md").read_text(encoding="utf-8")
    step5_contract = registry.get("step5") if isinstance(registry.get("step5"), dict) else {}
    for artifact in step5_contract.get("stable_artifacts", []):
        if f"`{artifact}`" not in step5_text:
            add_failure(failures, "step5_stable_artifact_missing", "agents/step_5_download.md", artifact=artifact)
    execution_policy = step5_contract.get("execution_policy", {})
    if (
        not isinstance(execution_policy, dict)
        or execution_policy.get("concurrency") != "serial"
        or execution_policy.get("parallel_downloads_allowed") is not False
        or "不得同时运行多个下载队列" not in step5_text
    ):
        add_failure(failures, "step5_serial_policy_mismatch", "agents/step_5_download.md")

    generator_text = (root / "scripts" / "generate_section_blueprints.py").read_text(encoding="utf-8")
    if "writing_blueprints.json" not in generator_text or "source_lineage" not in generator_text:
        add_failure(failures, "step2_step7_blueprint_lineage_missing", "scripts/generate_section_blueprints.py")

    step8_runner = (root / "scripts" / "run_step8_ai_trace.py").read_text(encoding="utf-8")
    if "--strict" not in step8_runner or "_atomic_write_text" not in step8_runner:
        add_failure(failures, "step8_strict_atomic_contract_missing", "scripts/run_step8_ai_trace.py")

    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    skill_name_match = re.search(r"^name:\s*(\S+)", skill_text, re.MULTILINE)
    skill_version_match = re.search(r"^version:\s*v?(\d+\.\d+\.\d+)", skill_text, re.MULTILINE)
    skill_name = skill_name_match.group(1) if skill_name_match else ""
    skill_version = skill_version_match.group(1) if skill_version_match else ""
    if "agents/step_*.md" in skill_text:
        add_failure(failures, "ambiguous_step_agent_wildcard", "SKILL.md")
    for runtime_path in STEP_RUNTIME_PATHS:
        if runtime_path not in skill_text:
            add_failure(
                failures,
                "runtime_path_undocumented",
                "SKILL.md",
                target=runtime_path,
            )

    plugin_path = root / ".codex-plugin" / "plugin.json"
    plugin = read_json(plugin_path, failures) if plugin_path.is_file() else {}
    if plugin.get("name") != skill_name or skill_name != PROJECT_NAME:
        add_failure(
            failures,
            "metadata_name_mismatch",
            ".codex-plugin/plugin.json",
            skill_name=skill_name,
            plugin_name=str(plugin.get("name", "")),
        )
    if plugin.get("version") != skill_version:
        add_failure(
            failures,
            "metadata_version_mismatch",
            ".codex-plugin/plugin.json",
            skill_version=skill_version,
            plugin_version=str(plugin.get("version", "")),
        )
    if plugin.get("skills") != "./skills/":
        add_failure(failures, "invalid_skills_root", ".codex-plugin/plugin.json")

    claude_plugin_path = root / ".claude-plugin" / "plugin.json"
    claude_plugin = read_json(claude_plugin_path, failures) if claude_plugin_path.is_file() else {}
    if claude_plugin.get("name") != PROJECT_NAME:
        add_failure(
            failures,
            "claude_plugin_name_mismatch",
            ".claude-plugin/plugin.json",
            plugin_name=str(claude_plugin.get("name", "")),
        )
    if claude_plugin.get("version") != skill_version:
        add_failure(
            failures,
            "claude_plugin_version_mismatch",
            ".claude-plugin/plugin.json",
            skill_version=skill_version,
            plugin_version=str(claude_plugin.get("version", "")),
        )

    claude_marketplace_path = root / ".claude-plugin" / "marketplace.json"
    claude_marketplace = (
        read_json(claude_marketplace_path, failures)
        if claude_marketplace_path.is_file()
        else {}
    )
    claude_plugins = (
        claude_marketplace.get("plugins")
        if isinstance(claude_marketplace.get("plugins"), list)
        else []
    )
    claude_entry = claude_plugins[0] if claude_plugins and isinstance(claude_plugins[0], dict) else {}
    if (
        claude_marketplace.get("name") != PROJECT_NAME
        or claude_entry.get("name") != PROJECT_NAME
    ):
        add_failure(
            failures,
            "claude_marketplace_name_mismatch",
            ".claude-plugin/marketplace.json",
        )
    if claude_entry.get("version") != skill_version:
        add_failure(
            failures,
            "claude_marketplace_version_mismatch",
            ".claude-plugin/marketplace.json",
            skill_version=skill_version,
            marketplace_version=str(claude_entry.get("version", "")),
        )

    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    marketplace = read_json(marketplace_path, failures) if marketplace_path.is_file() else {}
    plugins = marketplace.get("plugins") if isinstance(marketplace.get("plugins"), list) else []
    source_path = ""
    if plugins and isinstance(plugins[0], dict):
        if plugins[0].get("name") != PROJECT_NAME:
            add_failure(
                failures,
                "agents_marketplace_name_mismatch",
                ".agents/plugins/marketplace.json",
                plugin_name=str(plugins[0].get("name", "")),
            )
        source = plugins[0].get("source")
        if isinstance(source, dict):
            source_path = str(source.get("path", ""))
    if source_path != "./":
        add_failure(
            failures,
            "plugin_source_not_root",
            ".agents/plugins/marketplace.json",
            source_path=source_path,
        )

    entry_path = root / "skills" / PROJECT_NAME / "SKILL.md"
    if entry_path.is_file():
        entry_text = entry_path.read_text(encoding="utf-8")
        entry_name_match = re.search(r"^name:\s*(\S+)", entry_text, re.MULTILINE)
        entry_name = entry_name_match.group(1) if entry_name_match else ""
        if entry_name != PROJECT_NAME:
            add_failure(
                failures,
                "codex_skill_name_mismatch",
                str(entry_path.relative_to(root)),
                skill_name=entry_name,
            )
        targets = re.findall(r"\]\(([^)]+SKILL\.md)\)", entry_text)
        if not targets:
            add_failure(failures, "missing_canonical_skill_reference", str(entry_path.relative_to(root)))
        for target in targets:
            resolved = (entry_path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()):
                add_failure(
                    failures,
                    "reference_outside_plugin",
                    str(entry_path.relative_to(root)),
                    target=target,
                )
            elif resolved != (root / "SKILL.md").resolve():
                add_failure(
                    failures,
                    "invalid_canonical_skill_reference",
                    str(entry_path.relative_to(root)),
                    target=target,
                )
        if "agents/step_*.md" in entry_text:
            add_failure(
                failures,
                "ambiguous_step_agent_wildcard",
                str(entry_path.relative_to(root)),
            )
        for runtime_path in STEP_RUNTIME_PATHS:
            if runtime_path not in entry_text:
                add_failure(
                    failures,
                    "runtime_path_undocumented",
                    str(entry_path.relative_to(root)),
                    target=runtime_path,
                )

    nested_plugin = root / "plugins" / PROJECT_NAME / ".codex-plugin" / "plugin.json"
    if nested_plugin.exists():
        add_failure(
            failures,
            "legacy_plugin_layout_present",
            str(nested_plugin.relative_to(root)),
        )

    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_DIRS | {".git", ".codegraph"} for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES | {".html", ".svg"}:
            continue
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        if LEGACY_NAME in text and relative not in LEGACY_NAME_ALLOWLIST:
            add_failure(failures, "legacy_name_outside_allowlist", relative)
        if f"github.com/bingyunjiang/{LEGACY_NAME}" in text:
            add_failure(failures, "legacy_repository_url", relative)


def scan_skill(root: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in {".pyc", ".pyo"}:
            failures.append({"code": "bytecode_present", "path": str(path)})
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            relative = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            scan_text_security(text, relative, failures)
            for term in FORBIDDEN_TERMS:
                if term in text:
                    failures.append({"code": "forbidden_term", "term": term, "path": str(path)})
    validate_repository_structure(root, failures)
    return {
        "schema": "morepaper.package_validation.v1",
        "root": str(root),
        "status": "ok" if not failures else "failed",
        "failures": failures,
    }


def scan_zip(path: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        marker = ".codex-plugin/plugin.json"
        plugin_entries = [name for name in names if name == marker or name.endswith(f"/{marker}")]
        if len(plugin_entries) != 1:
            add_failure(
                failures,
                "invalid_plugin_root_count",
                str(path),
                count=str(len(plugin_entries)),
            )
            package_root = ""
        else:
            package_root = plugin_entries[0][: -len(marker)].rstrip("/")

        def packaged_path(relative: str) -> str:
            return f"{package_root}/{relative}" if package_root else relative

        for relative in sorted(REQUIRED_ROOT_PATHS):
            if packaged_path(relative) not in names:
                add_failure(
                    failures,
                    "missing_required_zip_entry",
                    str(path),
                    target=f"/{relative}",
                )
        if packaged_path(f"plugins/{PROJECT_NAME}/.codex-plugin/plugin.json") in names:
            add_failure(failures, "legacy_plugin_layout_in_zip", str(path))

        root_skill_name = packaged_path("SKILL.md")
        if root_skill_name in names:
            try:
                root_skill_text = archive.read(root_skill_name).decode("utf-8")
            except (KeyError, UnicodeDecodeError) as exc:
                add_failure(
                    failures,
                    "invalid_root_skill_entry",
                    root_skill_name,
                    message=str(exc),
                )
            else:
                if "agents/step_*.md" in root_skill_text:
                    add_failure(failures, "ambiguous_step_agent_wildcard", root_skill_name)
                for runtime_path in STEP_RUNTIME_PATHS:
                    if runtime_path not in root_skill_text:
                        add_failure(
                            failures,
                            "runtime_path_undocumented",
                            root_skill_name,
                            target=runtime_path,
                        )

        entry_name = packaged_path(f"skills/{PROJECT_NAME}/SKILL.md")
        if entry_name in names:
            try:
                entry_text = archive.read(entry_name).decode("utf-8")
            except (KeyError, UnicodeDecodeError) as exc:
                add_failure(
                    failures,
                    "invalid_codex_skill_entry",
                    entry_name,
                    message=str(exc),
                )
            else:
                targets = re.findall(r"\]\(([^)]+SKILL\.md)\)", entry_text)
                for target in targets:
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(entry_name), target))
                    if resolved != root_skill_name:
                        add_failure(
                            failures,
                            "invalid_zip_canonical_skill_reference",
                            entry_name,
                            target=target,
                        )
                if not targets:
                    add_failure(failures, "missing_canonical_skill_reference", entry_name)
                if "agents/step_*.md" in entry_text:
                    add_failure(failures, "ambiguous_step_agent_wildcard", entry_name)
                for runtime_path in STEP_RUNTIME_PATHS:
                    if runtime_path not in entry_text:
                        add_failure(
                            failures,
                            "runtime_path_undocumented",
                            entry_name,
                            target=runtime_path,
                        )
        for name in names:
            if "\\" in name:
                failures.append({"code": "windows_separator_in_zip", "path": name})
            if "__pycache__" in name or name.endswith((".pyc", ".pyo")):
                failures.append({"code": "cache_in_zip", "path": name})
            relative_name = name[len(package_root) + 1 :] if package_root and name.startswith(f"{package_root}/") else name
            if relative_name in FORBIDDEN_PACKAGE_ENTRIES or relative_name.startswith(".codex/"):
                add_failure(failures, "local_codex_config_in_zip", name)
            suffix = Path(relative_name).suffix.lower()
            try:
                with archive.open(name) as handle:
                    while handle.read(1024 * 64):
                        pass
            except Exception as exc:
                failures.append({"code": "zip_entry_unreadable", "path": name, "message": str(exc)})
                continue
            if suffix in TEXT_SUFFIXES | {".html", ".svg"}:
                try:
                    text = archive.read(name).decode("utf-8")
                except UnicodeDecodeError:
                    continue
                scan_text_security(text, relative_name, failures)
    return {
        "schema": "morepaper.zip_package_validation.v1",
        "zip": str(path),
        "status": "ok" if not failures else "failed",
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a more-paper-workflow package.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = scan_skill(args.root)
    if args.zip:
        result["zip_validation"] = scan_zip(args.zip)
        if result["zip_validation"]["status"] != "ok":
            result["status"] = "failed"
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
