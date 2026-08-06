#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
"""
Attempt a non-destructive git-based skill upgrade and report whether the host
can continue with the current local version.
"""
from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import json
import subprocess
import sys
from pathlib import Path


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def run_git(root: Path, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def trim(text: str, limit: int = 600) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def failed_result(root: Path, reason: str, message: str, before_head: str | None, details: str = "") -> dict:
    return {
        "ok": False,
        "upgraded": False,
        "continue_with_current_version": True,
        "reason": reason,
        "message": message,
        "details": trim(details),
        "command": f"cd {root} && git pull --ff-only",
        "local_head_before": before_head,
        "local_head_after": before_head,
    }


def build_result(root: Path) -> dict:
    local_before = run_git(root, ["rev-parse", "HEAD"], timeout=5)
    before_head = local_before.stdout.strip() if local_before.returncode == 0 else None
    if not before_head:
        return failed_result(
            root,
            "not_git_repository",
            "升级未执行：当前 skill 不是可更新的 Git 工作区。将继续使用当前本地版本。",
            None,
            local_before.stderr,
        )

    branch = run_git(root, ["symbolic-ref", "--quiet", "--short", "HEAD"], timeout=5)
    if branch.returncode != 0 or not branch.stdout.strip():
        return failed_result(
            root,
            "detached_head",
            "升级未执行：当前 Git 工作区处于 detached HEAD。将继续使用当前本地版本。",
            before_head,
            branch.stderr,
        )

    upstream = run_git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], timeout=5)
    if upstream.returncode != 0 or not upstream.stdout.strip():
        return failed_result(
            root,
            "missing_upstream",
            "升级未执行：当前分支没有 upstream。将继续使用当前本地版本。",
            before_head,
            upstream.stderr,
        )

    dirty = run_git(root, ["status", "--porcelain", "--untracked-files=normal"], timeout=5)
    if dirty.returncode != 0 or dirty.stdout.strip():
        return failed_result(
            root,
            "dirty_worktree",
            "升级未执行：当前工作区有未提交修改，请先提交或妥善保存。将继续使用当前本地版本。",
            before_head,
            dirty.stdout or dirty.stderr,
        )

    try:
        fetch = run_git(root, ["fetch", "--quiet"], timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return failed_result(
            root,
            "upgrade_command_failed",
            "升级失败：当前网络或 git 环境不可用。将继续使用当前本地版本。",
            before_head,
            str(exc),
        )

    if fetch.returncode != 0:
        return failed_result(
            root,
            "git_fetch_failed",
            "升级失败：无法读取远程更新。将继续使用当前本地版本。",
            before_head,
            fetch.stderr or fetch.stdout,
        )

    upstream_ref = upstream.stdout.strip()
    ancestry = run_git(root, ["merge-base", "--is-ancestor", "HEAD", upstream_ref], timeout=5)
    if ancestry.returncode != 0:
        return failed_result(
            root,
            "non_fast_forward",
            "升级未执行：本地分支与远程历史不能安全快进。将继续使用当前本地版本。",
            before_head,
            ancestry.stderr,
        )

    pull = run_git(root, ["merge", "--ff-only", upstream_ref], timeout=30)

    local_after = run_git(root, ["rev-parse", "HEAD"], timeout=5)
    after_head = local_after.stdout.strip() if local_after.returncode == 0 else before_head
    upgraded = bool(before_head and after_head and before_head != after_head)

    if pull.returncode == 0:
        message = "升级成功：已更新到最新可见版本。" if upgraded else "已是最新版本，无需升级。"
        return {
            "ok": True,
            "upgraded": upgraded,
            "continue_with_current_version": True,
            "reason": "success",
            "message": message,
            "details": trim((pull.stdout or "") + ("\n" + pull.stderr if pull.stderr else "")),
            "command": f"cd {root} && git pull --ff-only",
            "local_head_before": before_head,
            "local_head_after": after_head,
        }

    result = failed_result(
        root,
        "git_merge_failed",
        "升级失败：无法安全应用远程更新。将继续使用当前本地版本。",
        before_head,
        pull.stderr or pull.stdout,
    )
    result["local_head_after"] = after_head
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Perform a non-destructive skill upgrade attempt.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload instead of plain text.")
    args = parser.parse_args(argv)

    payload = build_result(skill_dir())

    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(payload["message"] + "\n")
        if payload.get("details"):
            sys.stdout.write(payload["details"] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
