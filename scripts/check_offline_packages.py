#!/usr/bin/env python3
"""Validate the offline dependency bundle manifest."""
from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "scripts" / "packages"
MANIFEST_PATH = PACKAGE_DIR / "manifest.lock.json"
PACKAGE_EXTENSIONS = (".whl", ".tar.gz", ".zip")


@dataclass(frozen=True)
class PackageFile:
    filename: str
    name: str
    version: str
    size_bytes: int
    sha256: str
    platform_tag: str


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def parse_name_version(filename: str) -> tuple[str, str]:
    base = filename
    if base.endswith(".tar.gz"):
        base = base[:-7]
    else:
        base = Path(base).stem
    parts = base.split("-")
    if len(parts) < 2:
        return normalize_name(base), ""
    return normalize_name(parts[0]), parts[1]


def platform_tag(filename: str) -> str:
    if filename.endswith(".tar.gz"):
        return "sdist"
    stem = Path(filename).stem
    parts = stem.split("-")
    if len(parts) >= 5:
        return parts[-1]
    return "py-any"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_package_paths() -> list[Path]:
    return sorted(
        path for path in PACKAGE_DIR.iterdir()
        if path.is_file() and path.name.endswith(PACKAGE_EXTENSIONS)
    )


def package_record(path: Path) -> PackageFile:
    name, version = parse_name_version(path.name)
    return PackageFile(
        filename=path.name,
        name=name,
        version=version,
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
        platform_tag=platform_tag(path.name),
    )


def build_manifest() -> dict:
    packages = [package_record(path) for path in iter_package_paths()]
    duplicate_names = sorted(
        name for name, versions in _versions_by_name(packages).items()
        if len(versions) > 1
    )
    return {
        "schema_version": "offline-package-manifest.v1",
        "bundle": {
            "id": "zotero-mcp-server-offline-cache",
            "package_dir": "scripts/packages",
            "primary_package": "zotero-mcp-server",
            "primary_version": "0.5.0",
            "target_platform": "macos-arm64",
            "target_python": "cp314",
            "package_count": len(packages),
            "total_size_bytes": sum(package.size_bytes for package in packages),
            "duplicate_package_names": duplicate_names,
            "notes": [
                "Current cache includes platform-specific wheels and is not a universal bundle.",
                "Generate separate bundles per platform before slimming or redistributing.",
            ],
        },
        "packages": [package.__dict__ for package in packages],
    }


def _versions_by_name(packages: list[PackageFile]) -> dict[str, set[str]]:
    versions: dict[str, set[str]] = defaultdict(set)
    for package in packages:
        versions[package.name].add(package.version)
    return versions


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def check_manifest(strict: bool = False) -> list[str]:
    findings: list[str] = []
    if not MANIFEST_PATH.exists():
        return [f"missing manifest: {MANIFEST_PATH.relative_to(ROOT)}"]

    manifest = load_manifest()
    actual = {package.filename: package for package in (package_record(path) for path in iter_package_paths())}
    expected = {package["filename"]: package for package in manifest.get("packages", [])}

    for filename in sorted(set(expected) - set(actual)):
        findings.append(f"manifest lists missing package: {filename}")
    for filename in sorted(set(actual) - set(expected)):
        findings.append(f"package not listed in manifest: {filename}")

    for filename in sorted(set(actual) & set(expected)):
        expected_package = expected[filename]
        actual_package = actual[filename]
        if expected_package.get("sha256") != actual_package.sha256:
            findings.append(f"sha256 mismatch: {filename}")
        if expected_package.get("size_bytes") != actual_package.size_bytes:
            findings.append(f"size mismatch: {filename}")

    expected_count = manifest.get("bundle", {}).get("package_count")
    if expected_count != len(actual):
        findings.append(f"package_count mismatch: manifest={expected_count} actual={len(actual)}")

    duplicates = {
        name: sorted(versions)
        for name, versions in _versions_by_name(list(actual.values())).items()
        if len(versions) > 1
    }
    if duplicates:
        message = "duplicate package versions: " + ", ".join(
            f"{name}={versions}" for name, versions in sorted(duplicates.items())
        )
        if strict:
            findings.append(message)
        else:
            print(f"WARN: {message}")

    source_distributions = sorted(
        filename for filename in actual if filename.endswith((".tar.gz", ".zip"))
    )
    if strict and source_distributions:
        findings.append(
            "source distributions are not allowed in strict offline bundles: "
            + ", ".join(source_distributions)
        )

    return findings


def check_resolution(timeout: int = 120) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--ignore-installed",
        "--no-index",
        "--only-binary=:all:",
        "--find-links",
        str(PACKAGE_DIR),
        "zotero-mcp-server==0.5.0",
    ]
    env = dict(os.environ)
    env.update({"PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1"})
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"offline dependency resolution could not run: {exc}"]
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "unknown pip failure").strip()
        return [f"offline dependency resolution failed: {details[-1200:]}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate scripts/packages against manifest.lock.json.")
    parser.add_argument("--write-manifest", action="store_true", help="Rewrite scripts/packages/manifest.lock.json.")
    parser.add_argument("--strict", action="store_true", help="Fail on duplicate package versions.")
    parser.add_argument("--resolve", action="store_true", help="Run a fully offline pip dependency dry-run.")
    args = parser.parse_args()

    if args.write_manifest:
        manifest = build_manifest()
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote: {MANIFEST_PATH.relative_to(ROOT)}")

    findings = check_manifest(strict=args.strict)
    if args.resolve and not findings:
        findings.extend(check_resolution())
    for finding in findings:
        print(f"ERROR: {finding}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
