#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
"""
Render a host-agnostic update reminder prompt from check_skill_update.py JSON.
"""
from __future__ import annotations

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import json
import sys
from pathlib import Path


def short_sha(value: str | None) -> str:
    if not value:
        return "unknown"
    return value[:7]


def load_payload(args: argparse.Namespace) -> dict:
    if args.input:
        return json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)
    raise SystemExit("render_update_prompt.py requires --input <json-file> or JSON on stdin")


def build_prompt(payload: dict) -> str:
    if not payload.get("should_prompt"):
        return ""

    skill_version = payload.get("skill_version") or "unknown"
    remote_version = payload.get("remote_version") or "unknown"
    remote_head = short_sha(payload.get("remote_head"))
    update_command = payload.get("update_command") or "git pull --ff-only"
    lines = [
        "检测到 more-paper-workflow 有新版本可用。",
        "",
        f"- 当前版本：{skill_version}",
        f"- 远程版本：{remote_version}",
        f"- 远程提交：{remote_head}",
        f"- 建议更新命令：{update_command}",
    ]
    extra = payload.get("messages") or []
    if extra:
        lines.append("")
        lines.append("补充说明：")
        lines.extend(extra[:2])
    lines.extend(
        [
            "",
            "请选择其一：",
            "1. 升级",
            "2. 本次跳过",
            "3. 今日不再提醒",
            "",
            "请直接回复：升级 / 本次跳过 / 今日不再提醒",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render update reminder prompt text from JSON status.")
    parser.add_argument("--input", help="Path to the JSON output produced by check_skill_update.py --json")
    parser.add_argument("--json", action="store_true", help="Return the rendered prompt as JSON {prompt: ...}")
    args = parser.parse_args(argv)

    payload = load_payload(args)
    prompt = build_prompt(payload)

    if args.json:
        json.dump({"prompt": prompt}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif prompt:
        sys.stdout.write(prompt + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
