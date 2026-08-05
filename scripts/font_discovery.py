from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable


CJK_FONT_FAMILY_CANDIDATES = [
    "Microsoft YaHei",
    "微软雅黑",
    "SimSun",
    "宋体",
    "SimHei",
    "黑体",
    "Source Han Sans SC",
    "思源黑体",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "WenQuanYi Micro Hei",
    "PingFang SC",
    "STHeiti",
]

LATIN_FALLBACK_FAMILIES = [
    "Arial",
    "Liberation Sans",
    "DejaVu Sans",
    "Helvetica",
    "STIXGeneral",
]


def cjk_family_candidates(extra: Iterable[str] | None = None) -> list[str]:
    candidates: list[str] = []
    for value in list(extra or []) + CJK_FONT_FAMILY_CANDIDATES + LATIN_FALLBACK_FAMILIES:
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def available_matplotlib_families(candidates: Iterable[str] | None = None) -> list[str]:
    from matplotlib import font_manager

    available: list[str] = []
    for candidate in cjk_family_candidates(candidates):
        try:
            font_manager.findfont(candidate, fallback_to_default=False)
        except Exception:
            continue
        if candidate not in available:
            available.append(candidate)
    return available


def resolve_matplotlib_families(candidates: Iterable[str] | None = None) -> list[str]:
    return available_matplotlib_families(candidates) or ["DejaVu Sans"]


def pil_font_path_candidates() -> list[Path]:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    home = Path.home()
    platform_candidates: list[Path] = []
    if sys.platform.startswith("win"):
        platform_candidates.extend(
            [
                windir / "Fonts" / "msyh.ttc",
                windir / "Fonts" / "msyhbd.ttc",
                windir / "Fonts" / "simsun.ttc",
                windir / "Fonts" / "simhei.ttf",
            ]
        )
    elif sys.platform == "darwin":
        platform_candidates.extend(
            [
                Path("/System/Library/Fonts/PingFang.ttc"),
                Path("/System/Library/Fonts/STHeiti Light.ttc"),
                Path("/System/Library/Fonts/STHeiti Medium.ttc"),
                Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
                Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            ]
        )
    else:
        platform_candidates.extend(
            [
                Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
                Path("/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf"),
                Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
                Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
            ]
        )
    platform_candidates.extend(
        [
            home / ".local/share/fonts/NotoSansCJK-Regular.ttc",
            home / ".local/share/fonts/SourceHanSansSC-Regular.otf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in platform_candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique
