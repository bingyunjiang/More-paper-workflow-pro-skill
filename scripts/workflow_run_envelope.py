#!/usr/bin/env python3
"""Create and validate the shared Step 1-8 workflow run envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "schemas/workflow-contract-registry.json").read_text(encoding="utf-8"))
SCHEMA_VERSION = "morepaper.workflow-run.v1"
ENTRY_MODES = set(REGISTRY["global"]["entry_modes"])
ROUTE_MODES = set(REGISTRY["global"]["route_modes"])
READINESS = set(REGISTRY["global"]["readiness"])
REQUIRED_FIELDS = {
    "schema_version",
    "run_id",
    "step",
    "entry_mode",
    "route_mode",
    "execution_profile",
    "input_hashes",
    "outputs",
    "domain_state",
    "readiness",
    "can_continue",
    "blocking",
    "warnings",
    "checkpoint_state",
    "recommended_next_step",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def validate_envelope(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["envelope root must be an object"]
    errors = [f"missing required field: {field}" for field in sorted(REQUIRED_FIELDS - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    step = payload.get("step")
    if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step <= 8:
        errors.append("step must be an integer from 1 to 8")
    if payload.get("entry_mode") not in ENTRY_MODES:
        errors.append("entry_mode is invalid")
    if payload.get("route_mode") not in ROUTE_MODES:
        errors.append("route_mode is invalid")
    if payload.get("readiness") not in READINESS:
        errors.append("readiness is invalid")
    if not isinstance(payload.get("can_continue"), bool):
        errors.append("can_continue must be boolean")
    if payload.get("readiness") == "blocked" and payload.get("can_continue") is not False:
        errors.append("blocked readiness requires can_continue=false")
    if payload.get("readiness") == "complete" and payload.get("blocking"):
        errors.append("complete readiness cannot contain blocking items")
    for field in ("outputs", "blocking", "warnings"):
        value = payload.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"{field} must be a list of strings")
    hashes = payload.get("input_hashes")
    if not isinstance(hashes, dict):
        errors.append("input_hashes must be an object")
    else:
        for path, digest in hashes.items():
            if not isinstance(path, str) or not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"input_hashes entry is invalid: {path}")
    if not isinstance(payload.get("checkpoint_state"), dict):
        errors.append("checkpoint_state must be an object")
    for field in ("run_id", "execution_profile", "domain_state", "recommended_next_step"):
        if not isinstance(payload.get(field), str) or not payload.get(field):
            errors.append(f"{field} must be a non-empty string")
    return errors


def _resolve_paths(root: Path, paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in paths:
        candidate = Path(raw).expanduser()
        resolved.append(candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve())
    return resolved


def create_envelope(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    input_paths = _resolve_paths(root, args.input)
    missing_inputs = [str(path) for path in input_paths if not path.is_file()]
    if missing_inputs:
        raise SystemExit(f"input files do not exist: {', '.join(missing_inputs)}")
    output_paths = _resolve_paths(root, args.artifact)
    missing_outputs = [str(path) for path in output_paths if not path.exists()]
    if missing_outputs:
        raise SystemExit(f"declared output artifacts do not exist: {', '.join(missing_outputs)}")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id or f"step{args.step}-{uuid.uuid4().hex[:12]}",
        "step": args.step,
        "entry_mode": args.entry_mode,
        "route_mode": args.route_mode,
        "execution_profile": args.execution_profile,
        "input_hashes": {
            path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path): sha256_file(path)
            for path in input_paths
        },
        "outputs": [
            path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
            for path in output_paths
        ],
        "domain_state": args.domain_state,
        "readiness": args.readiness,
        "can_continue": args.can_continue,
        "blocking": args.blocking,
        "warnings": args.warning,
        "checkpoint_state": json.loads(args.checkpoint_state),
        "recommended_next_step": args.recommended_next_step,
    }
    errors = validate_envelope(payload)
    if errors:
        raise SystemExit("invalid workflow envelope: " + "; ".join(errors))
    output_path = _resolve_paths(root, [args.output])[0]
    atomic_write_text(output_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(output_path)
    return 0


def validate_file(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    errors = validate_envelope(payload)
    print(json.dumps({"status": "ok" if not errors else "failed", "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="Create an atomic workflow run envelope.")
    create.add_argument("--project-root", default=".")
    create.add_argument("--output", default="workflow_run.json")
    create.add_argument("--run-id")
    create.add_argument("--step", type=int, required=True)
    create.add_argument("--entry-mode", choices=sorted(ENTRY_MODES), required=True)
    create.add_argument("--route-mode", choices=sorted(ROUTE_MODES), required=True)
    create.add_argument("--execution-profile", required=True)
    create.add_argument("--input", action="append", default=[])
    create.add_argument("--artifact", action="append", default=[])
    create.add_argument("--domain-state", required=True)
    create.add_argument("--readiness", choices=sorted(READINESS), required=True)
    continuation = create.add_mutually_exclusive_group(required=True)
    continuation.add_argument("--can-continue", action="store_true", dest="can_continue")
    continuation.add_argument("--cannot-continue", action="store_false", dest="can_continue")
    create.add_argument("--blocking", action="append", default=[])
    create.add_argument("--warning", action="append", default=[])
    create.add_argument("--checkpoint-state", default="{}")
    create.add_argument("--recommended-next-step", required=True)
    create.set_defaults(func=create_envelope)

    validate = subparsers.add_parser("validate", help="Validate an existing envelope.")
    validate.add_argument("path")
    validate.set_defaults(func=validate_file)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
