#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Markdown → DOCX 转换器（pandoc 包装器）。

将论文初稿/润色稿等 Markdown 文件转换为格式规范的 .docx 文件。
底层调用 pandoc，支持自定义参考文档样式。

依赖：
  - pandoc: brew install pandoc  (macOS) / apt install pandoc (Linux)

Usage:
  python3 scripts/md_to_docx.py 论文初稿.md                        # → 论文初稿.docx
  python3 scripts/md_to_docx.py 论文初稿.md -o output.docx         # 指定输出路径
  python3 scripts/md_to_docx.py 论文初稿.md --reference ref.docx   # 使用参考样式文档
  python3 scripts/md_to_docx.py 论文润色稿.md -o 论文润色稿.docx
"""

try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import sys
import os
import argparse
import subprocess
import shutil
import time
from pathlib import Path

from equation_guard import audit_paths as audit_equations


# ── 依赖检查 ──────────────────────────────────────────────────

def check_pandoc() -> str:
    """查找 pandoc 可执行文件路径，未安装则报错退出。"""
    path = shutil.which("pandoc")
    if not path:
        print("❌ 未找到 pandoc，请执行: brew install pandoc", flush=True)
        sys.exit(1)
    return path


# ── 默认参考文档 ──────────────────────────────────────────────

def get_default_reference() -> str:
    """返回默认参考文档路径（如果存在）。

    查找顺序：
      1. references/academic-reference.docx (项目内学术论文模板)
      2. 不存在则返回 None（使用 pandoc 内置默认样式）
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_ref = os.path.join(
        os.path.dirname(script_dir),
        "references",
        "academic-reference.docx",
    )
    if os.path.exists(project_ref):
        return project_ref
    return None


# ── 转换核心 ──────────────────────────────────────────────────

def md_to_docx(input_path: str, output_path: str,
               reference_docx: str = None,
               extra_args: list = None) -> str:
    """调用 pandoc 将 Markdown 转换为 DOCX。

    Args:
        input_path: 输入 Markdown 文件路径
        output_path: 输出 .docx 路径
        reference_docx: 参考样式 .docx（None 则自动查找）
        extra_args: 传递给 pandoc 的额外参数列表

    Returns:
        生成的 .docx 文件绝对路径
    """
    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}", flush=True)
        sys.exit(1)

    input_path = str(Path(input_path).expanduser().resolve())
    output_path = str(Path(output_path).expanduser().resolve())

    source_audit, _ = audit_equations([Path(input_path)], "markdown")
    source_summary = source_audit["summary"]
    if source_summary["status"] == "fail":
        print("❌ DOCX 导出已阻断：Markdown 公式预检失败。", flush=True)
        for finding in source_audit["findings"][:10]:
            print(
                f"   {finding['code']} line {finding['line']}: {finding['message']}",
                flush=True,
            )
        print("   请先运行 scripts/equation_guard.py 并修复报告中的错误。", flush=True)
        sys.exit(1)

    pandoc = check_pandoc()

    cmd = [
        pandoc,
        input_path,
        "-f", "markdown",
        "-t", "docx",
        "-o", output_path,
        "--resource-path", str(Path(input_path).parent),
    ]

    # 参考文档
    ref = reference_docx or get_default_reference()
    if ref:
        if os.path.exists(ref):
            cmd.extend(["--reference-doc", ref])
        else:
            print(f"⚠️ 参考文档不存在，使用 pandoc 默认样式: {ref}", flush=True)

    # 额外参数
    if extra_args:
        cmd.extend(extra_args)

    # ── 执行转换 ──
    print(f"🔄 正在转换: {os.path.basename(input_path)} → {os.path.basename(output_path)}",
          flush=True)

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)

    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"❌ pandoc 转换失败 (exit code {result.returncode}):",
              flush=True)
        if result.stderr:
            print(f"   {result.stderr.strip()}", flush=True)
        sys.exit(1)

    # 警告（非致命）
    if result.stderr:
        for line in result.stderr.strip().split('\n'):
            if line.strip():
                print(f"   ⚠️ {line.strip()}", flush=True)

    docx_audit, _ = audit_equations([Path(output_path)], "docx")
    docx_summary = docx_audit["summary"]
    expected_equations = int(source_summary["equation_count"])
    native_equations = int(docx_summary["native_math_count"])
    transfer_failed = expected_equations > native_equations
    if docx_summary["status"] == "fail" or transfer_failed:
        print("❌ DOCX 已生成，但公式回读未通过；该文件不能作为正式交付。", flush=True)
        if transfer_failed:
            print(
                f"   源稿公式数 {expected_equations}，DOCX 原生公式对象数 {native_equations}。",
                flush=True,
            )
        for finding in docx_audit["findings"][:10]:
            print(
                f"   {finding['code']} paragraph {finding['line']}: {finding['message']}",
                flush=True,
            )
        sys.exit(1)

    size_kb = os.path.getsize(output_path) // 1024
    print(f"✅ DOCX 已生成: {output_path} ({size_kb} KB, {elapsed:.1f}s)",
          flush=True)
    return os.path.abspath(output_path)


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Markdown → DOCX 转换器（pandoc 包装器）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 论文初稿.md                      → 论文初稿.docx
  %(prog)s 论文润色稿.md -o 润色稿.docx     → 指定输出路径
  %(prog)s input.md --reference ref.docx    → 使用自定义参考样式

参考文档生成:
  pandoc -o reference.docx --print-default-data-file reference.docx
  # 编辑 reference.docx 的样式（字体/字号/边距），保存后作为 --reference 参数使用
        """,
    )
    parser.add_argument(
        "input", help="Markdown 文件路径",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="输出 .docx 路径（默认: 与输入文件同名 .docx）",
    )
    parser.add_argument(
        "--reference", "-r", dest="reference_docx", default=None,
        help="参考样式 .docx 文件路径（默认: 自动查找 references/academic-reference.docx）",
    )
    args = parser.parse_args()

    # ── 确定输出路径 ──
    output_path = args.output
    if not output_path:
        base = os.path.splitext(os.path.basename(args.input))[0]
        output_path = os.path.join(
            os.path.dirname(args.input) or ".",
            f"{base}.docx",
        )

    # ── 执行转换 ──
    md_to_docx(
        input_path=args.input,
        output_path=output_path,
        reference_docx=args.reference_docx,
    )


if __name__ == "__main__":
    main()
