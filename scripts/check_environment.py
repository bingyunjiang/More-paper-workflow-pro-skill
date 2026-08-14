from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

from font_discovery import CJK_FONT_FAMILY_CANDIDATES, LATIN_FALLBACK_FAMILIES


CAPABILITY_PROFILES = {
    "core": {"modules": (), "font": "none", "tools": ()},
    "quick_figure": {"modules": ("matplotlib", "numpy", "PIL"), "font": "any", "tools": ()},
    "chinese_diagram": {"modules": ("matplotlib", "numpy", "PIL"), "font": "cjk", "tools": ()},
    "strict_reproduction": {
        "modules": ("matplotlib", "numpy", "PIL", "skimage", "pypdf", "jsonschema"),
        "font": "any",
        "tools": (),
    },
    "docx_export": {"modules": (), "font": "none", "tools": ("pandoc",)},
    "publisher_download": {"modules": ("websocket",), "font": "none", "tools": ()},
}

MODULE_DISTRIBUTIONS = {
    "PIL": "Pillow",
    "skimage": "scikit-image",
    "websocket": "websocket-client",
}


def module_version(name: str) -> str | None:
    try:
        module = importlib.import_module(name)
    except Exception:
        return None
    distribution = MODULE_DISTRIBUTIONS.get(name, name)
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return str(getattr(module, "__version__", "installed"))


def font_available(name: str) -> bool:
    try:
        from matplotlib import font_manager

        resolved = font_manager.findfont(name, fallback_to_default=False)
    except Exception:
        return False
    return Path(resolved).exists()


def check_environment(capability: str = "strict_reproduction") -> dict[str, object]:
    if capability not in CAPABILITY_PROFILES:
        raise ValueError(f"unknown capability: {capability}")
    profile = CAPABILITY_PROFILES[capability]
    cjk_fonts = {name: font_available(name) for name in CJK_FONT_FAMILY_CANDIDATES}
    latin_fonts = {name: font_available(name) for name in LATIN_FALLBACK_FAMILIES}
    available_modules = {
        "matplotlib": module_version("matplotlib"),
        "numpy": module_version("numpy"),
        "PIL": module_version("PIL"),
        "skimage": module_version("skimage"),
        "pypdf": module_version("pypdf"),
        "jsonschema": module_version("jsonschema"),
        "websocket": module_version("websocket"),
        "pandas": module_version("pandas"),
        "openpyxl": module_version("openpyxl"),
        "pydantic": module_version("pydantic"),
    }
    required = {name: available_modules[name] for name in profile["modules"]}
    optional = {name: version for name, version in available_modules.items() if name not in required}
    missing_required = [name for name, version in required.items() if version is None]
    required_tools = {name: shutil.which(name) for name in profile["tools"]}
    missing_tools = [name for name, path in required_tools.items() if path is None]
    cjk_ready = bool(any(cjk_fonts.values()))
    any_font_ready = bool(any({**cjk_fonts, **latin_fonts}.values()))
    font_requirement = str(profile["font"])
    font_ready = cjk_ready if font_requirement == "cjk" else any_font_ready if font_requirement == "any" else True
    blocking_reasons = [f"missing_module:{name}" for name in missing_required]
    blocking_reasons.extend(f"missing_tool:{name}" for name in missing_tools)
    if not font_ready:
        blocking_reasons.append("missing_cjk_font" if font_requirement == "cjk" else "missing_usable_font")
    return {
        "schema": "scientificfigure.environment.v1",
        "capability": capability,
        "python": sys.version.split()[0],
        "executable_role": "python",
        "required_modules": required,
        "optional_modules": optional,
        "available_modules": available_modules,
        "required_tools": required_tools,
        "fonts_available": {**cjk_fonts, **latin_fonts},
        "cjk_fonts_available": cjk_fonts,
        "latin_fallbacks_available": latin_fonts,
        "r_available": shutil.which("Rscript") is not None,
        "status": "pass" if not blocking_reasons else "failed",
        "cjk_ready": cjk_ready,
        "cjk_status": "pass" if cjk_ready else "failed",
        "font_requirement": font_requirement,
        "font_ready": font_ready,
        "missing_required": missing_required,
        "missing_tools": missing_tools,
        "blocking_reasons": blocking_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check scientific figure reproduction runtime dependencies and fonts.")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--capability",
        choices=tuple(CAPABILITY_PROFILES),
        default="core",
        help="Check only the runtime needed by the requested capability (default: core).",
    )
    args = parser.parse_args()
    result = check_environment(args.capability)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
