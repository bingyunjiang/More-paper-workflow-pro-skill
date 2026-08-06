#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
"""
Best-effort update reminder for more-paper-workflow.

The script never mutates the worktree. It compares local metadata with the
SKILL.md version on the current branch's upstream, then prints a short reminder.
"""
from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_INTERVAL_HOURS = 24
REMOTE_TIMEOUT_SECONDS = 5
DEFAULT_SUPPRESS_HOURS = 24


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_skill_version(root: Path) -> str | None:
    return parse_skill_version_text(read_text(root / "SKILL.md"))


def parse_skill_version_text(text: str) -> str | None:
    match = re.search(r"^version:\s*([^\s(]+)", text, re.M)
    if match:
        return match.group(1)
    match = re.search(r"^version:\s*([^\s(]+)", text.split("## Skill metadata", 1)[-1], re.M)
    return match.group(1) if match else None


def version_key(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)(?:-(\d{8}))?", value)
    if not match:
        return None
    major, minor, patch, date = match.groups()
    return int(major), int(minor), int(patch), int(date or 0)


def remote_version_is_newer(local_version: str | None, remote_version: str | None) -> bool:
    local_key = version_key(local_version)
    remote_key = version_key(remote_version)
    return bool(local_key and remote_key and remote_key > local_key)


def parse_readme_version(root: Path) -> str | None:
    match = re.search(r"more-paper-workflow\s+`([^`]+)`", read_text(root / "README.md"), re.I)
    return match.group(1) if match else None


def parse_changelog_version(root: Path) -> str | None:
    match = re.search(r"^##\s+(v[0-9][^\s]+)", read_text(root / "CHANGELOG.md"), re.M)
    return match.group(1) if match else None


def run_git(root: Path, args: list[str], timeout: int = REMOTE_TIMEOUT_SECONDS) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def run_git_status(root: Path, args: list[str], timeout: int = REMOTE_TIMEOUT_SECONDS) -> int | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode


def remote_has_update(root: Path, local_head: str | None, remote_head: str | None) -> bool:
    if not local_head or not remote_head or local_head == remote_head:
        return False

    remote_known = run_git_status(root, ["cat-file", "-e", f"{remote_head}^{{commit}}"], timeout=2)
    if remote_known == 0:
        remote_is_ancestor = run_git_status(
            root,
            ["merge-base", "--is-ancestor", remote_head, local_head],
            timeout=2,
        )
        if remote_is_ancestor == 0:
            return False
        local_is_ancestor = run_git_status(
            root,
            ["merge-base", "--is-ancestor", local_head, remote_head],
            timeout=2,
        )
        if local_is_ancestor == 0:
            return True

    return True


def upstream_parts(root: Path) -> tuple[str | None, str | None, str | None]:
    upstream = run_git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], timeout=2)
    if not upstream or "/" not in upstream:
        return upstream, None, None
    remote, branch = upstream.split("/", 1)
    return upstream, remote, branch


def read_remote_version(
    root: Path,
    remote: str,
    branch: str,
) -> tuple[str | None, str | None, str]:
    remote_raw = run_git(root, ["ls-remote", remote, f"refs/heads/{branch}"], timeout=REMOTE_TIMEOUT_SECONDS)
    if not remote_raw:
        return None, None, "remote_unreachable"
    remote_head = remote_raw.split()[0]
    fetched = run_git(
        root,
        ["fetch", "--quiet", "--no-tags", "--no-write-fetch-head", remote, f"refs/heads/{branch}"],
        timeout=REMOTE_TIMEOUT_SECONDS,
    )
    if fetched is None:
        return remote_head, None, "fetch_failed"
    remote_skill = run_git(root, ["show", f"{remote_head}:SKILL.md"], timeout=2)
    if remote_skill is None:
        return remote_head, None, "remote_skill_missing"
    remote_version = parse_skill_version_text(remote_skill)
    if not remote_version:
        return remote_head, None, "remote_version_missing"
    return remote_head, remote_version, "checked"


def state_path() -> Path:
    cache_root = os.environ.get("XDG_CACHE_HOME")
    if cache_root:
        base = Path(cache_root)
    else:
        base = Path.home() / ".cache"
    return base / "more-paper-workflow" / "update-check.json"


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def current_time() -> float:
    return time.time()


def should_check(path: Path, interval_hours: float, force: bool) -> bool:
    if force:
        return True
    state = load_state(path)
    last_checked = float(state.get("last_checked", 0) or 0)
    return (current_time() - last_checked) >= interval_hours * 3600


def is_suppressed(state: dict, remote_head: str | None, now_ts: float) -> tuple[bool, str | None]:
    suppressed_remote = state.get("suppressed_remote_head")
    suppress_until = float(state.get("suppress_until", 0) or 0)
    if remote_head and suppressed_remote == remote_head and now_ts < suppress_until:
        return True, "snoozed_for_today"
    return False, None


def print_reminder(lines: list[str]) -> None:
    print("🔔 more-paper-workflow 更新提醒")
    for line in lines:
        print(line)


def emit_json(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def base_payload(
    root: Path,
    state_file: Path,
    state: dict,
    *,
    enabled: bool = True,
    skipped: bool = False,
    reason: str | None = None,
) -> dict:
    skill_version = parse_skill_version(root)
    readme_version = parse_readme_version(root)
    changelog_version = parse_changelog_version(root)
    return {
        "enabled": enabled,
        "skipped": skipped,
        "reason": reason,
        "skill_version": skill_version,
        "readme_version": readme_version,
        "changelog_version": changelog_version,
        "expected_version": skill_version or changelog_version or readme_version,
        "metadata_mismatch": False,
        "local_head": None,
        "remote_head": state.get("remote_head"),
        "remote_version": state.get("remote_version"),
        "remote_url": None,
        "upstream_ref": None,
        "remote_check_status": reason or "not_started",
        "remote_update_available": False,
        "update_available": False,
        "should_prompt": False,
        "suggested_action": "continue",
        "update_command": None,
        "prompt_mode": "none",
        "prompt_options": [],
        "suppressed": False,
        "suppress_reason": None,
        "suppress_until": state.get("suppress_until"),
        "last_user_choice": state.get("last_user_choice"),
        "choice_recorded": None,
        "state_file": str(state_file),
        "messages": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether this skill may need an update.")
    parser.add_argument("--force", action="store_true", help="Ignore daily throttling and check now.")
    parser.add_argument("--no-network", action="store_true", help="Only compare local metadata; skip git remote check.")
    parser.add_argument("--quiet", action="store_true", help="Only print when an update or metadata mismatch is found.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable status for runtime gating.")
    parser.add_argument(
        "--record-choice",
        choices=["upgrade", "skip_once", "snooze_today"],
        help="Persist the user's choice after a prompt so the next startup can decide whether to remind again.",
    )
    parser.add_argument(
        "--suppress-hours",
        type=float,
        default=float(os.environ.get("MORE_PAPER_SKILL_UPDATE_SUPPRESS_HOURS", DEFAULT_SUPPRESS_HOURS)),
        help="Hours to suppress the same remote update after choosing snooze_today. Default: 24.",
    )
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=float(os.environ.get("MORE_PAPER_SKILL_UPDATE_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS)),
        help="Minimum hours between automatic checks. Default: 24.",
    )
    args = parser.parse_args(argv)

    root = skill_dir()
    state_file = state_path()
    state = load_state(state_file)
    payload = base_payload(root, state_file, state)

    if os.environ.get("MORE_PAPER_SKILL_UPDATE_CHECK", "").lower() in {"0", "false", "no", "off"}:
        if args.json:
            payload.update(enabled=False, skipped=True, reason="disabled_by_env", remote_check_status="disabled_by_env")
            emit_json(payload)
        return 0

    if not args.record_choice and not should_check(state_file, args.interval_hours, args.force):
        if args.json:
            payload.update(skipped=True, reason="throttled", remote_check_status="throttled")
            emit_json(payload)
        return 0

    skill_version = payload["skill_version"]
    readme_version = payload["readme_version"]
    changelog_version = payload["changelog_version"]

    lines: list[str] = []
    metadata_mismatch = False
    if skill_version and readme_version and skill_version != readme_version:
        metadata_mismatch = True
        lines.append(f"- 本地 SKILL.md 版本为 {skill_version}，但 README 版本为 {readme_version}。")
    if skill_version and changelog_version and skill_version != changelog_version:
        metadata_mismatch = True
        lines.append(f"- 本地 SKILL.md 版本为 {skill_version}，但 CHANGELOG 最新为 {changelog_version}。")
    expected_version = payload["expected_version"]
    if metadata_mismatch:
        lines.append("- 建议先同步 skill 元数据，避免 Agent 读取到旧版本号。")

    local_head = run_git(root, ["rev-parse", "HEAD"], timeout=2)
    remote_head = None
    remote_version = None
    upstream_ref, upstream_remote, upstream_branch = upstream_parts(root)
    remote_url = (
        run_git(root, ["config", "--get", f"remote.{upstream_remote}.url"], timeout=2)
        if upstream_remote else None
    )
    remote_update_available = False
    remote_check_status = "no_network" if args.no_network else "no_upstream"
    if not args.no_network and upstream_remote and upstream_branch and local_head:
        remote_head, remote_version, remote_check_status = read_remote_version(root, upstream_remote, upstream_branch)
        remote_update_available = remote_version_is_newer(skill_version, remote_version)
        if remote_update_available:
            lines.append(f"- 远程版本 {remote_version} 高于本地版本 {skill_version}。")
            if remote_head:
                lines.append(f"- 远程提交：{remote_head[:7]}；跟踪分支：{upstream_ref}。")

    upgrade_script = shlex.quote(str(root / "scripts" / "perform_skill_upgrade.py"))
    update_command = f"python3 {upgrade_script} --json" if remote_update_available else None

    now_ts = current_time()
    suppressed, suppress_reason = is_suppressed(state, remote_head, now_ts)
    should_prompt = remote_update_available and not suppressed

    choice_recorded = None
    if args.record_choice:
        choice_remote_head = remote_head or state.get("last_prompted_remote_head") or state.get("remote_head")
        choice_recorded = args.record_choice
        state["last_user_choice"] = args.record_choice
        state["last_choice_at"] = now_ts
        state["last_prompted_remote_head"] = choice_remote_head
        if args.record_choice == "snooze_today" and choice_remote_head:
            state["suppressed_remote_head"] = choice_remote_head
            state["suppress_until"] = now_ts + args.suppress_hours * 3600
        elif args.record_choice == "upgrade":
            state.pop("suppressed_remote_head", None)
            state.pop("suppress_until", None)
        elif args.record_choice == "skip_once":
            # skip_once only affects the current host session; leave no long-lived suppression marker.
            state.pop("suppressed_remote_head", None)
            state.pop("suppress_until", None)
    elif should_prompt:
        state["last_prompted_remote_head"] = remote_head

    payload.update({
        "metadata_mismatch": metadata_mismatch,
        "local_head": local_head,
        "remote_head": remote_head,
        "remote_version": remote_version,
        "remote_url": remote_url,
        "upstream_ref": upstream_ref,
        "remote_check_status": remote_check_status,
        "remote_update_available": remote_update_available,
        "update_available": remote_update_available,
        "should_prompt": should_prompt,
        "suggested_action": "soft_prompt_upgrade_skip_snooze" if should_prompt else "continue",
        "update_command": update_command,
        "prompt_mode": "soft" if should_prompt else "none",
        "prompt_options": ["upgrade", "skip_once", "snooze_today"] if should_prompt else [],
        "suppressed": suppressed,
        "suppress_reason": suppress_reason,
        "suppress_until": state.get("suppress_until"),
        "last_user_choice": state.get("last_user_choice"),
        "choice_recorded": choice_recorded,
        "state_file": str(state_file),
        "messages": lines,
    })

    state.update(
        {
            "last_checked": now_ts,
            "skill_version": skill_version,
            "readme_version": readme_version,
            "changelog_version": changelog_version,
            "local_head": local_head,
            "remote_head": remote_head or state.get("remote_head"),
            "remote_version": remote_version or state.get("remote_version"),
            "upstream_ref": upstream_ref,
        }
    )
    save_state(state_file, state)

    if args.json:
        emit_json(payload)
    elif lines:
        print_reminder(lines)
    elif not args.quiet:
        print(f"✅ more-paper-workflow 已是当前可见版本：{skill_version or 'unknown'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
