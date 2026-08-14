#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 - Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Unified PDF download router - single entry point for all publishers.

Routes each DOI to the optimal download strategy using the publisher
routing matrix, then orchestrates download rounds:

  1. Sci-Hub CDP    -> pre-2021 papers (free, ~6s/paper)
  2. OA Fast        -> public OA PDF verification (resolver + whitelist hints)
  3. IEEE CDP       -> dedicated IEEE route via download_via_ieee.py
  4. Generic CDP    -> Elsevier/ScienceDirect and other publishers
                     (Wiley, ACS, RSC, Nature, Springer, etc.)

Usage:
  python3 scripts/unified_download_router.py 检索文献表.md --output paper-temp/
  python3 scripts/unified_download_router.py dois.txt --port 9223
  python3 scripts/unified_download_router.py --papers DOI1,DOI2 --port 9223
  python3 scripts/unified_download_router.py --test 10.1021/acsnano.4c00001 --port 9223
  python3 scripts/unified_download_router.py --check-session --port 9223
"""

from __future__ import annotations

import sys, os, time, re, json, argparse, subprocess, hashlib, atexit
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

# Ensure scripts/ is on path
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from cdp_utils import (
    cdp_browser_matches,
    check_cdp,
    check_required_deps,
    create_tab,
    get_cdp_browser_product,
    get_tab_ws_url,
    start_persistent_cdp_browser,
)
from console_compat import (
    ARROW,
    DONE,
    FAIL,
    OK,
    SKIP,
    WARN,
    configure_child_python_utf8_env,
    configure_console_output,
)
from generic_publisher_downloader import (
    resolve_publisher, download_one as generic_download_one,
    check_publisher_session, describe_publisher_session, _PUBLISHER_CONFIGS,
    _find_reusable_cnki_tab, extract_dois,
)
from sd_download import diagnose_sd_pii
from workflow_contracts import (
    PdfPoolIndex,
    PdfPoolItem,
    Step5DownloadItem,
    Step5DownloadManifest,
    append_jsonl_durable,
    atomic_write_json,
    atomic_write_text,
    as_chinese_papers,
    dois_from_download_items,
    download_items_from_search_records,
    load_download_manifest,
    load_search_records,
    step5_attempt,
    write_pdf_pool_index,
    write_step5_download_manifest,
)

# ── Constants ───────────────────────────────────────────────────────────────

CDP_PORT = 9223
DEFAULT_OUTPUT = os.path.join(os.getcwd(), "paper-temp")
SCI_HUB_CUTOFF_YEAR = 2021  # Sci-Hub has very few papers after 2020
OA_FAST_MIN_BYTES = 5000
OA_FAST_TIMEOUT = 15
DOWNLOAD_LOCK_MESSAGE = "上一进程下载中，请等一等，下载完再运行中文下载。"
OA_HINT_OPEN_STATUSES = {"oa", "open", "open_access", "green", "gold", "hybrid", "bronze"}
OA_WHITELIST_JOURNAL_KEYWORDS = (
    "rsc advances",
    "scientific reports",
    "ieee access",
)
ENGLISH_CDP_PUBLISHER_PRIORITY = {
    "sd_elsevier": 0,
    "springer": 1,
    "wiley": 2,
    "acs": 3,
    "rsc": 4,
    "nature": 5,
}

# Strategy routing table (for display and decisions)
STRATEGY_ORDER = ["scihub", "ieee_cdp", "generic", "chinese_cdp", "direct_http", "skip"]

# Chinese CDP publishers (identified by strategy, not DOI prefix)
CHINESE_PUBLISHERS = {"cnki", "wanfang"}

# Chinese paper entry schema (from literature table or JSON)
# Each entry: {"title": str, "source": "cnki"|"wanfang", "article_url": str, "doi": str}
CHINESE_PAPER_FIELDS = frozenset({"title", "source", "article_url"})
CHINESE_SOURCE_PRIORITY = {"cnki": 0, "wanfang": 1}
CNKI_CAPTCHA_MONITOR_TIMEOUT = 600
CNKI_CAPTCHA_MONITOR_INTERVAL = 2
CNKI_AUTO_RECOVERY_ATTEMPTS = 3
CNKI_AUTO_RECOVERY_DELAY = 2


def step5_download_lock_path() -> Path:
    """Return the cross-process lock file used by real Step 5 downloads."""
    override = os.environ.get("MORE_PAPER_STEP5_LOCK_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "more-paper-workflow" / "step5_download.lock"


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            return True
        return str(pid) in (proc.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _read_download_lock(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def acquire_step5_download_lock(mode: str, port: int) -> tuple[bool, Path, dict]:
    """Atomically acquire the Step 5 real-download lock.

    Returns (acquired, lock_path, blocker_payload). If acquired is False, the
    lock belongs to a still-running process.
    """
    path = step5_download_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "port": port,
        "command": " ".join(sys.argv),
    }
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            blocker = _read_download_lock(path)
            blocker_pid = int(blocker.get("pid") or 0)
            if _pid_is_running(blocker_pid):
                return False, path, blocker
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True, path, {}


def release_step5_download_lock(path: Path | str) -> None:
    path = Path(path)
    payload = _read_download_lock(path)
    if int(payload.get("pid") or 0) != os.getpid():
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _print_download_lock_blocker(lock_path: Path, blocker: dict) -> None:
    print(f"\n{WARN} {DOWNLOAD_LOCK_MESSAGE}")
    pid = blocker.get("pid") or "unknown"
    mode = blocker.get("mode") or "unknown"
    started = blocker.get("started_at") or "unknown"
    print(f"  Lock: {lock_path}")
    print(f"  Running process: pid={pid}, mode={mode}, started_at={started}")
    print("  Recovery: 如确认没有 Step 5 下载进程仍在运行，可手动删除该 lock 后重试；真实下载进行中不要删除。")


def acquire_or_exit_step5_download_lock(mode: str, port: int) -> Path:
    acquired, lock_path, blocker = acquire_step5_download_lock(mode, port)
    if not acquired:
        _print_download_lock_blocker(lock_path, blocker)
        sys.exit(2)
    atexit.register(release_step5_download_lock, lock_path)
    return lock_path


def sort_chinese_papers_for_download(papers: list[dict]) -> list[dict]:
    """Stable Step 5 Chinese download order: CNKI, then Wanfang, then unknown."""
    return sorted(
        papers,
        key=lambda paper: CHINESE_SOURCE_PRIORITY.get(
            str(paper.get("source", "")).strip().lower(),
            len(CHINESE_SOURCE_PRIORITY),
        ),
    )


def ensure_cdp_running(port: int, browser: str = "chrome") -> bool:
    """Reuse an existing CDP browser only when it matches the requested browser."""
    browser = (browser or "chrome").lower()
    if check_cdp(port):
        if cdp_browser_matches(port, browser):
            return True
        product = get_cdp_browser_product(port) or "unknown browser"
        print(f"\nCDP port :{port} is {product}, but {browser.title()} was requested. Restarting {browser.title()}...")
    else:
        print(f"\nCDP {browser.title()} not detected on :{port}. Starting browser automatically...")
    start_persistent_cdp_browser(
        port=port,
        browser=browser,
        urls=["https://www.sciencedirect.com/"],
    )
    ok = check_cdp(port) and cdp_browser_matches(port, browser)
    if not ok:
        print(f"  {FAIL} CDP browser failed to start.")
        print("     Windows: set CHROME_PATH or EDGE_PATH if browser auto-detection fails.")
    return ok


# ── Year Estimation ─────────────────────────────────────────────────────────

def estimate_year(doi: str) -> Optional[int]:
    """Estimate publication year from DOI patterns. Returns int or None.

    DOIs often embed the year, e.g.:
      - 10.1016/j.jpowsour.2019.01.052 -> 2019
      - 10.1109/tvt.2022.3183866 -> 2022
      - 10.1002/ente.202301205 -> 2023 (year embedded in larger number)
      - 10.1038/s41467-2024-45578 -> 2024

    We scan the part AFTER the first '/' for 4-digit numbers in the
    publication-year range (1990–2026), skipping the DOI prefix.
    """
    # Split: "10.1016/j.jpowsour.2019.01.052" -> prefix="10.1016", rest="j.jpowsour.2019.01.052"
    parts = doi.split("/", 1)
    search_region = parts[1] if len(parts) > 1 else doi

    # Find all 4-digit numbers in the search region, return the first valid year
    for m in re.finditer(r'\d{4}', search_region):
        year = int(m.group(0))
        if 1990 <= year <= 2026:
            return year
    return None


def _scihub_eligible_dois(dois: list[str]) -> list[str]:
    return [
        doi for doi in dois
        if (estimate_year(doi) is not None and estimate_year(doi) <= SCI_HUB_CUTOFF_YEAR)
    ]


# ── DOI Classification ──────────────────────────────────────────────────────

def classify_doi(doi: str) -> dict:
    """Classify a DOI into a download strategy category.
    Returns dict with: doi, strategy, publisher_name, year, reason"""
    publisher = resolve_publisher(doi)
    pub_name = publisher.get("_key", "unknown") if publisher else "unknown"
    strategy = publisher.get("strategy", "generic") if publisher else "generic"
    year = estimate_year(doi)

    return {
        "doi": doi,
        "strategy": strategy,
        "publisher": pub_name,
        "year": year,
        "publisher_config": publisher or {},
    }


# ── Input Parsing ───────────────────────────────────────────────────────────

def parse_input(input_path: str) -> list[str]:
    """Extract DOIs from a file. Supports:
    - Plain text (one DOI per line or inline)
    - Markdown literature tables (检索文献表.md)
    - BibTeX (.bib files)
    """
    path = Path(input_path)
    if not path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    dois = extract_dois(input_path)
    if not dois:
        print(f"ERROR: No DOIs found in {input_path}")
        sys.exit(1)
    return dois


def _parse_bibtex_fields(entry: str) -> dict[str, str]:
    """Extract simple BibTeX key/value fields used for routing decisions."""
    fields: dict[str, str] = {}
    for match in re.finditer(r'(?m)^\s*([A-Za-z_][\w-]*)\s*=\s*([{\"])(.*?)[}\"],?\s*$', entry):
        fields[match.group(1).lower()] = match.group(3).strip()
    return fields


def _split_bibtex_entries(text: str) -> list[str]:
    """Split BibTeX text into top-level entries without a full parser."""
    entries: list[str] = []
    start: Optional[int] = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == "@" and depth == 0:
            start = i
        if start is None:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                entries.append(text[start:i + 1])
                start = None
    return entries


def _is_chinese_bibtex_entry(fields: dict[str, str]) -> bool:
    doi = fields.get("doi", "").lower()
    haystack = " ".join(fields.get(k, "") for k in ("title", "journal", "school", "langid")).lower()
    if fields.get("langid", "").lower() in ("chinese", "zh", "zh-cn"):
        return True
    if doi.startswith(("10.16638/j.cnki", "10.14044/j.1674-1757")):
        return True
    return bool(re.search(r"[\u4e00-\u9fff]", haystack))


def parse_bibtex_chinese_papers(input_path: str) -> list[dict]:
    """Extract Chinese BibTeX entries so they do not fall through to Generic CDP."""
    path = Path(input_path)
    if path.suffix.lower() != ".bib" or not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    papers: list[dict] = []
    for entry in _split_bibtex_entries(text):
        fields = _parse_bibtex_fields(entry)
        doi = fields.get("doi", "").strip()
        if not doi or not _is_chinese_bibtex_entry(fields):
            continue
        url = fields.get("article_url") or fields.get("url", "")
        if not url and doi:
            url = f"https://doi.org/{doi}"
        source = "cnki" if "cnki" in doi.lower() or "cnki" in url.lower() else "cnki"
        papers.append({
            "title": fields.get("title", ""),
            "source": source,
            "article_url": url if url.startswith("http") else "",
            "doi": doi,
        })
    return papers


def parse_doi_file(input_path: str) -> list[str]:
    """Read one DOI per line from a plain text file."""
    path = Path(input_path)
    if not path.exists():
        print(f"ERROR: DOI file not found: {input_path}")
        sys.exit(1)
    dois = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            dois.append(line)
    if not dois:
        print(f"ERROR: No DOIs found in DOI file: {input_path}")
        sys.exit(1)
    return dois


# ── Chinese Paper Parsing ────────────────────────────────────────────────────

def parse_chinese_papers(input_path: str) -> list[dict]:
    """Extract Chinese papers (CNKI/Wanfang) from literature table or JSON.

    For Markdown literature tables, reads rows where the source column
    is 'cnki' or 'wanfang'. Extracts title, DOI/synthetic-ID, and
    any article URL present.

    For JSON files, expects:
      [{"title": "...", "source": "cnki"|"wanfang",
        "article_url": "https://...", "doi": "10.xxxx/..."}, ...]

    Returns list of {title, source, article_url, doi} dicts.
    """
    path = Path(input_path)
    if not path.exists():
        print(f"ERROR: Chinese input file not found: {input_path}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8", errors="replace")

    # Try JSON first
    stripped = text.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict) and "papers" in data:
                data = data["papers"]
            if not isinstance(data, list):
                print("ERROR: Chinese JSON must be a list of paper objects.")
                sys.exit(1)
            papers = []
            for item in data:
                if isinstance(item, dict) and item.get("source", "").lower() in ("cnki", "wanfang"):
                    papers.append({
                        "title": item.get("title", ""),
                        "source": item["source"].lower(),
                        "article_url": item.get("article_url", item.get("url", "")),
                        "doi": item.get("doi") or item.get("source_id", ""),
                    })
            return papers
        except json.JSONDecodeError:
            pass  # Not JSON, fall through to Markdown parsing

    # Markdown table parsing
    papers = []
    in_table = False
    headers: list[str] = []
    source_col = -1
    title_col = -1
    doi_col = -1
    url_col = -1

    for line in text.split("\n"):
        # Detect table header row
        if "|" in line and not in_table:
            parts = [p.strip() for p in line.split("|")]
            # Skip separator lines (|---|---|)
            if all(re.match(r'^[-:]+$', p) for p in parts if p):
                continue
            headers = parts
            # Find column indices (case-insensitive)
            for i, h in enumerate(headers):
                hl = h.lower()
                if hl in ("来源", "source"):
                    source_col = i
                elif hl in ("标题", "title", "论文标题"):
                    title_col = i
                elif hl in ("doi", "doi/url", "doi/source_id", "source_id"):
                    doi_col = i
                elif hl in ("文章链接", "url", "article_url", "详情链接"):
                    url_col = i
            if source_col >= 0:
                in_table = True
            continue

        if not in_table:
            continue

        # End of table: blank line or new heading
        if not line.strip() or line.startswith("##"):
            in_table = False
            continue

        # Skip separator lines inside table
        parts = [p.strip() for p in line.split("|")]
        if all(re.match(r'^[-:]+$', p) for p in parts if p):
            continue

        if source_col >= len(parts):
            continue

        source_val = parts[source_col].strip().lower()
        if source_val not in ("cnki", "wanfang"):
            continue

        title = parts[title_col].strip() if 0 <= title_col < len(parts) else ""
        # Clean markdown link formatting from title
        title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)

        doi = parts[doi_col].strip() if 0 <= doi_col < len(parts) else ""
        # Extract DOI from markdown link if present
        doi_m = re.search(r'(10\.\d{4,}/[^\s<")]+|cnki\.\w+|wanfang\.\w+)', doi)
        doi = doi_m.group(1) if doi_m else doi

        article_url = parts[url_col].strip() if 0 <= url_col < len(parts) else ""
        # Extract URL from markdown link
        url_m = re.search(r'\]\(([^)]+)\)', article_url) or re.search(r'(https?://[^\s)]+)', article_url)
        if url_m and not article_url.startswith("http"):
            article_url = url_m.group(1)

        if title:
            papers.append({
                "title": title,
                "source": source_val,
                "article_url": article_url,
                "doi": doi,
            })

    return papers


def resolve_output_dir(args: argparse.Namespace) -> str:
    """Resolve output directory with a file-local default.

    When --output is omitted and the entrypoint includes a real input file,
    default to a sibling paper-temp/ beside that file. This avoids sending
    download artifacts into the skill repo or an unrelated cwd.
    """
    if args.output:
        return args.output

    for raw_path in (
        args.input,
        args.doi_file,
        args.chinese_input,
        args.workflow_results,
        args.download_manifest,
    ):
        if not raw_path:
            continue
        candidate = Path(raw_path).expanduser()
        if candidate.exists():
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            return str(candidate.parent / "paper-temp")
    return DEFAULT_OUTPUT


# ── Round Executors ─────────────────────────────────────────────────────────

def run_scihub_round(dois: list[str], output_dir: str, port: int) -> tuple[list[str], list[str]]:
    """Round 1: Try Sci-Hub for papers with estimated year <= 2021.
    Returns (downloaded_dois, remaining_dois)."""
    old_dois = []
    new_dois = []
    for d in dois:
        year = estimate_year(d)
        if year and year <= SCI_HUB_CUTOFF_YEAR:
            old_dois.append(d)
        else:
            new_dois.append(d)

    if not old_dois:
        print(f"\n{SKIP} Round 1 (Sci-Hub): No <= {SCI_HUB_CUTOFF_YEAR} papers to try ({len(new_dois)} papers are > {SCI_HUB_CUTOFF_YEAR} or year unknown).")
        return [], dois

    print(f"\n{'='*60}")
    print(f"Round 1: Sci-Hub CDP ({len(old_dois)} papers with year <= {SCI_HUB_CUTOFF_YEAR})")
    print(f"{'='*60}")

    # Write temp DOI list for scihub script
    scihub_input = os.path.join(output_dir, ".scihub_input.txt")
    os.makedirs(output_dir, exist_ok=True)
    with open(scihub_input, "w", encoding="utf-8") as f:
        for d in old_dois:
            f.write(d + "\n")

    scihub_script = SCRIPTS_DIR / "download_via_scihub.py"
    if not scihub_script.exists():
        print(f"  WARNING: {scihub_script} not found - skipping Sci-Hub round.")
        return [], dois

    try:
        subprocess.run(
            [sys.executable, str(scihub_script), scihub_input,
             "--output", output_dir, "--port", str(port),
             "--retry-mirrors", "1"],
            check=False, timeout=600, env=configure_child_python_utf8_env()
        )
    except subprocess.TimeoutExpired:
        print(f"  {WARN} Sci-Hub round timed out after 10 minutes.")

    # Check which papers now exist on disk
    downloaded = []
    remaining = list(new_dois)  # post-2021 papers always go to next round
    for d in old_dois:
        basename = d.replace("/", "_").replace(":", "_")
        fpath = os.path.join(output_dir, f"{basename}.pdf")
        if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
            downloaded.append(d)
        else:
            remaining.append(d)

    print(f"  Sci-Hub result: {OK} {len(downloaded)} downloaded, {ARROW} {len(old_dois) - len(downloaded)} remaining for next round")

    # Cleanup
    try:
        os.remove(scihub_input)
    except Exception:
        pass

    return downloaded, remaining


def _normalise_oa_hints(oa_hints: Optional[dict[str, dict]]) -> dict[str, dict]:
    if not oa_hints:
        return {}
    return {k.strip().lower(): v for k, v in oa_hints.items() if k and isinstance(v, dict)}


def build_oa_hints_from_items(items: list) -> dict[str, dict]:
    """Collect Step 4 OA hints keyed by normalized DOI."""
    hints: dict[str, dict] = {}
    for item in items:
        doi = getattr(item, "doi", "") or ""
        if not doi:
            continue
        hint = {
            "oa_status": getattr(item, "oa_status", ""),
            "oa_source": getattr(item, "oa_source", ""),
            "oa_pdf_url": getattr(item, "oa_pdf_url", ""),
            "oa_landing_url": getattr(item, "oa_landing_url", ""),
            "oa_license": getattr(item, "oa_license", ""),
            "oa_checked_at": getattr(item, "oa_checked_at", ""),
            "journal": getattr(item, "journal", ""),
            "title": getattr(item, "title", ""),
        }
        raw = getattr(item, "raw", {}) or {}
        for key in list(hint):
            if not hint[key]:
                hint[key] = raw.get(key, "")
        if any(hint.values()):
            hints[doi.strip().lower()] = hint
    return hints


def classify_oa_hint(hint: Optional[dict]) -> str:
    """Classify list-time OA metadata. This is not PDF verification."""
    if not hint or not any(str(v).strip() for v in hint.values()):
        return "no_oa_hint"
    pdf_url = str(hint.get("oa_pdf_url") or "").strip()
    if pdf_url:
        return "oa_candidate" if _looks_like_pdf_url(pdf_url) else "unknown"
    status = str(hint.get("oa_status") or "").strip().lower()
    source = str(hint.get("oa_source") or "").strip().lower()
    if status in OA_HINT_OPEN_STATUSES:
        return "oa_candidate"
    if source in {"unpaywall", "openalex", "semantic_scholar", "pmc", "pubmed"} and status:
        return "oa_candidate"
    return "unknown"


def classify_english_oa_hints(dois: list[str], oa_hints: Optional[dict[str, dict]]) -> dict[str, str]:
    hints = _normalise_oa_hints(oa_hints)
    return {
        doi: classify_oa_hint(hints.get(doi.strip().lower()))
        for doi in dois
    }


def print_english_oa_hint_summary(dois: list[str], oa_hints: Optional[dict[str, dict]]) -> None:
    if not dois:
        return
    classifications = classify_english_oa_hints(dois, oa_hints)
    counts = {"oa_candidate": 0, "no_oa_hint": 0, "unknown": 0}
    for status in classifications.values():
        counts[status] = counts.get(status, 0) + 1
    print("English OA hints:")
    print(f"  oa_candidate: {counts.get('oa_candidate', 0):3d}")
    print(f"  no_oa_hint:   {counts.get('no_oa_hint', 0):3d}")
    print(f"  unknown:      {counts.get('unknown', 0):3d}")


def group_english_cdp_dois(dois: list[str]) -> list[tuple[str, str, list[str]]]:
    """Group English CDP DOI list by publisher while preserving in-group order."""
    grouped: dict[str, dict] = {}
    first_seen: dict[str, int] = {}
    for idx, doi in enumerate(dois):
        pub = resolve_publisher(doi)
        pub_name = pub.get("_key", "unknown") if pub else "unknown"
        publisher_domain = pub.get("publisher_domain", "?") if pub else "?"
        if pub_name not in grouped:
            grouped[pub_name] = {"domain": publisher_domain, "dois": []}
            first_seen[pub_name] = idx
        grouped[pub_name]["dois"].append(doi)

    def sort_key(item: tuple[str, dict]) -> tuple[int, int]:
        name, _payload = item
        if name == "unknown":
            return (10_000, first_seen[name])
        return (ENGLISH_CDP_PUBLISHER_PRIORITY.get(name, 1_000), first_seen[name])

    return [
        (name, payload["domain"], payload["dois"])
        for name, payload in sorted(grouped.items(), key=sort_key)
    ]


def _looks_like_pdf_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    haystack = f"{parsed.path}?{parsed.query}".lower()
    return ".pdf" in haystack or "/pdf" in haystack or "download" in haystack


def _fetch_url_bytes(url: str, timeout: int = OA_FAST_TIMEOUT) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 more-paper-workflow/Step5 OA verifier",
            "Accept": "application/pdf,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read(50 * 1024 * 1024 + 1)
    return data, content_type


def verify_public_pdf_bytes(data: bytes, content_type: str = "",
                            min_bytes: int = OA_FAST_MIN_BYTES) -> tuple[bool, str]:
    """Validate that an OA candidate is a real PDF, not a landing/placeholder page."""
    head = data[:2048].lstrip().lower()
    if "html" in content_type.lower() or head.startswith((b"<!doctype html", b"<html")):
        return False, "html_response"
    if len(data) < min_bytes:
        return False, "too_small"
    if not data.lstrip().startswith(b"%PDF"):
        return False, "missing_pdf_header"
    if not re.search(rb"/Type\s*/Page\b", data):
        return False, "no_readable_pages"
    return True, "public_pdf_verified"


def _save_oa_pdf(output_dir: str, doi: str, data: bytes) -> str:
    os.makedirs(output_dir, exist_ok=True)
    basename = doi.replace("/", "_").replace(":", "_")
    path = os.path.join(output_dir, f"{basename}.pdf")
    with open(path, "wb") as f:
        f.write(data)
    return path


def _resolve_oa_pdf_url_lightweight(doi: str) -> Optional[str]:
    """Best-effort OA resolver. Network failures never block the main flow."""
    quoted = urllib.parse.quote(doi, safe="")
    url = f"https://api.unpaywall.org/v2/{quoted}?email=more-paper-workflow@example.invalid"
    try:
        data, content_type = _fetch_url_bytes(url, timeout=4)
        if "json" not in content_type.lower():
            return None
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return None
    best = payload.get("best_oa_location") or {}
    candidate = best.get("url_for_pdf") or ""
    return candidate if _looks_like_pdf_url(candidate) else None


def _resolve_oa_pdf_url_openalex(doi: str) -> Optional[str]:
    quoted = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
    url = f"https://api.openalex.org/works/{quoted}"
    try:
        data, content_type = _fetch_url_bytes(url, timeout=4)
        if "json" not in content_type.lower():
            return None
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return None
    open_access = payload.get("open_access") or {}
    locations = payload.get("locations") or []
    candidates = [
        open_access.get("oa_url", ""),
        open_access.get("any_repository_has_fulltext") and open_access.get("oa_url", ""),
    ]
    for location in locations:
        if not isinstance(location, dict):
            continue
        candidates.extend([
            location.get("pdf_url", ""),
            location.get("landing_page_url", ""),
        ])
    for candidate in candidates:
        if isinstance(candidate, str) and _looks_like_pdf_url(candidate.strip()):
            return candidate.strip()
    return None


def _resolve_oa_pdf_url_semantic_scholar(doi: str) -> Optional[str]:
    quoted = urllib.parse.quote(doi, safe="")
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/"
        f"DOI:{quoted}?fields=isOpenAccess,openAccessPdf"
    )
    try:
        data, content_type = _fetch_url_bytes(url, timeout=4)
        if "json" not in content_type.lower():
            return None
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return None
    open_access_pdf = payload.get("openAccessPdf") or {}
    candidate = open_access_pdf.get("url") or ""
    return candidate.strip() if _looks_like_pdf_url(candidate.strip()) else None


def _resolve_oa_pdf_url_multi_source(doi: str) -> tuple[str, str]:
    resolvers = (
        ("unpaywall", _resolve_oa_pdf_url_lightweight),
        ("openalex", _resolve_oa_pdf_url_openalex),
        ("semantic_scholar", _resolve_oa_pdf_url_semantic_scholar),
    )
    for source, resolver in resolvers:
        try:
            candidate = resolver(doi) or ""
        except Exception:
            candidate = ""
        if candidate:
            return candidate, source
    return "", ""


def _is_known_oa_whitelist(doi: str, hint: Optional[dict]) -> bool:
    info = classify_doi(doi)
    pub_key = info.get("publisher", "")
    hint = hint or {}
    status = str(hint.get("oa_status") or "").strip().lower()
    journal_haystack = " ".join(
        str(hint.get(field) or "").strip().lower()
        for field in ("journal", "title", "oa_source")
    )
    if pub_key == "mdpi":
        return True
    if pub_key == "wiley" and status in OA_HINT_OPEN_STATUSES:
        return True
    if pub_key in {"rsc", "nature", "ieee"} and status in OA_HINT_OPEN_STATUSES:
        return True
    return any(keyword in journal_haystack for keyword in OA_WHITELIST_JOURNAL_KEYWORDS)


def _is_oa_confirmed_or_whitelisted(doi: str, oa_hints: Optional[dict[str, dict]]) -> bool:
    hint = _normalise_oa_hints(oa_hints).get(doi.strip().lower(), {})
    status = str(hint.get("oa_status") or "").strip().lower()
    if status == "public_pdf_verified":
        return True
    return _is_known_oa_whitelist(doi, hint)


def run_oa_fast_round(dois: list[str], output_dir: str,
                      oa_hints: Optional[dict[str, dict]] = None,
                      use_resolver: bool = True
                      ) -> tuple[list[str], list[str], dict[str, str]]:
    """Try public OA PDF URLs before institution CDP."""
    hints = _normalise_oa_hints(oa_hints)
    downloaded: list[str] = []
    remaining: list[str] = []
    failure_reasons: dict[str, str] = {}

    if not dois:
        return downloaded, remaining, failure_reasons

    print(f"\n{'='*60}")
    print(f"Round 2: OA Fast public PDF ({len(dois)} papers)")
    print(f"{'='*60}")

    for doi in dois:
        hint = hints.get(doi.strip().lower(), {})
        is_whitelist = _is_known_oa_whitelist(doi, hint)
        url = (hint.get("oa_pdf_url") or "").strip()
        resolver_source = ""
        if not url and use_resolver:
            url, resolver_source = _resolve_oa_pdf_url_multi_source(doi)

        if not url:
            remaining.append(doi)
            if is_whitelist:
                failure_reasons[doi] = "oa_whitelist_but_verification_failed"
            continue
        if not _looks_like_pdf_url(url):
            remaining.append(doi)
            failure_reasons[doi] = "oa_whitelist_but_verification_failed" if is_whitelist else "invalid_oa_candidate"
            print(f"  {FAIL} {doi[:50]} OA candidate is not a PDF URL")
            continue

        try:
            data, content_type = _fetch_url_bytes(url)
            ok, reason = verify_public_pdf_bytes(data, content_type)
        except Exception as exc:
            ok, reason = False, f"oa_fetch_failed:{type(exc).__name__}"
            data = b""

        if ok:
            path = _save_oa_pdf(output_dir, doi, data)
            size_kb = os.path.getsize(path) // 1024
            if resolver_source:
                print(f"  {OK} {doi[:50]} public_pdf_verified via {resolver_source} ({size_kb}KB)")
            else:
                print(f"  {OK} {doi[:50]} public_pdf_verified ({size_kb}KB)")
            downloaded.append(doi)
        else:
            print(f"  {FAIL} {doi[:50]} invalid OA PDF candidate ({reason})")
            remaining.append(doi)
            failure_reasons[doi] = "oa_whitelist_but_verification_failed" if is_whitelist else "invalid_oa_candidate"

    print(f"  OA fast result: {OK} {len(downloaded)} downloaded, {ARROW} {len(remaining)} remaining for CDP")
    return downloaded, remaining, failure_reasons


def run_sd_round(dois: list[str], output_dir: str, port: int,
                 sd_browser: str = "chrome") -> tuple[list[str], list[str], dict[str, str]]:
    """Legacy standalone ScienceDirect CDP round.

    Main routing now sends 10.1016/ papers through Generic CDP, which calls
    the ScienceDirect adapter internally.

    Returns (downloaded_dois, remaining_dois)."""
    sd_dois = []
    other_dois = []
    for d in dois:
        pub = resolve_publisher(d)
        strategy = pub.get("strategy", "generic") if pub else "generic"
        # Check if it's an SD DOI (with PII resolvable) or if publisher says sd_cdp
        if strategy == "sd_cdp":
            sd_dois.append(d)
        else:
            other_dois.append(d)

    if not sd_dois:
        print(f"\n{SKIP} Round 2 (SD CDP): No Elsevier papers remaining.")
        return [], dois, {}

    print(f"\n{'='*60}")
    print(f"Round 2: ScienceDirect CDP ({len(sd_dois)} Elsevier papers)")
    print(f"{'='*60}")

    # First resolve PII via batch_resolve_pii.py
    sd_input = os.path.join(output_dir, ".sd_input.txt")
    pii_map_path = os.path.join(output_dir, "sd_pii_map.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(sd_input, "w", encoding="utf-8") as f:
        for d in sd_dois:
            f.write(d + "\n")

    batch_pii_script = SCRIPTS_DIR / "batch_resolve_pii.py"
    if batch_pii_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(batch_pii_script), sd_input,
                 "--output", pii_map_path],
                check=False, timeout=300, env=configure_child_python_utf8_env()
            )
        except subprocess.TimeoutExpired:
            print(f"  {WARN} PII resolution timed out.")
    else:
        print(f"  WARNING: {batch_pii_script} not found - cannot resolve PII for SD.")

    # Download via auto_sd_downloader
    auto_sd_script = SCRIPTS_DIR / "auto_sd_downloader.py"
    if auto_sd_script.exists() and os.path.exists(pii_map_path):
        auto_sd_cmd = [
            sys.executable, str(auto_sd_script),
            "--output-dir", output_dir,
            "--pii-map", pii_map_path,
            "--browser", sd_browser,
        ]
        if sd_browser == "edge":
            auto_sd_cmd.extend(["--port-edge", str(port)])
        else:
            auto_sd_cmd.extend(["--port-chrome", str(port)])
        try:
            subprocess.run(
                auto_sd_cmd,
                check=False, timeout=1800, env=configure_child_python_utf8_env()
            )
        except subprocess.TimeoutExpired:
            print(f"  {WARN} SD download timed out after 30 minutes.")
    elif not os.path.exists(pii_map_path):
        print(f"  {WARN} PII map not found - skipping SD download.")

    # Check results
    downloaded = []
    remaining = list(other_dois)
    failure_reasons: dict[str, str] = {}
    pii_map: dict[str, dict] = {}
    if os.path.exists(pii_map_path):
        try:
            pii_map = json.loads(Path(pii_map_path).read_text(encoding="utf-8")).get("resolved", {})
        except Exception:
            pii_map = {}
    for d in sd_dois:
        basename = d.replace("/", "_").replace(":", "_")
        fpath = os.path.join(output_dir, f"{basename}.pdf")
        if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
            downloaded.append(d)
        else:
            remaining.append(d)
            pii = pii_map.get(basename, {}).get("pii")
            if pii:
                diag = diagnose_sd_pii(port, pii)
                if diag["kind"] == "manual_verification_required":
                    failure_reasons[d] = "manual_verification_required"
                elif diag["kind"] == "referencework_abs":
                    failure_reasons[d] = "not_subscribed_or_referencework"
                elif diag["kind"] == "article_page_only":
                    failure_reasons[d] = "article_page_no_pdf_route"
                else:
                    failure_reasons[d] = "sd_failed_unknown"
            else:
                failure_reasons[d] = "pii_resolution_failed"

    print(f"  SD result: {OK} {len(downloaded)} downloaded, {ARROW} {len(sd_dois) - len(downloaded)} remaining for next round")

    try:
        os.remove(sd_input)
    except Exception:
        pass

    return downloaded, remaining, failure_reasons


def run_ieee_round(dois: list[str], output_dir: str, port: int) -> tuple[list[str], list[str]]:
    """Round 3: IEEE CDP for 10.1109/ papers via the dedicated IEEE downloader."""
    ieee_dois = []
    other_dois = []
    for d in dois:
        pub = resolve_publisher(d)
        strategy = pub.get("strategy", "generic") if pub else "generic"
        if strategy == "ieee_cdp":
            ieee_dois.append(d)
        else:
            other_dois.append(d)

    if not ieee_dois:
        print(f"\n{SKIP} Round 3 (IEEE CDP): No IEEE papers remaining.")
        return [], dois

    print(f"\n{'='*60}")
    print(f"Round 3: IEEE CDP ({len(ieee_dois)} IEEE papers)")
    print(f"{'='*60}")

    ieee_script = SCRIPTS_DIR / "download_via_ieee.py"
    if not ieee_script.exists():
        print(f"  WARNING: {ieee_script} not found - skipping IEEE round.")
        return [], dois

    # Write temp input
    ieee_input = os.path.join(output_dir, ".ieee_input.txt")
    os.makedirs(output_dir, exist_ok=True)
    with open(ieee_input, "w", encoding="utf-8") as f:
        for d in ieee_dois:
            f.write(d + "\n")

    try:
        subprocess.run(
            [sys.executable, str(ieee_script), ieee_input,
             "--output", output_dir, "--port", str(port),
             "--skip-session-check"],
            check=False, timeout=900, env=configure_child_python_utf8_env()
        )
    except subprocess.TimeoutExpired:
        print(f"  {WARN} IEEE round timed out after 15 minutes.")

    # Check results - IEEE uses arnumber_DOI.pdf naming
    downloaded = []
    remaining = list(other_dois)
    for d in ieee_dois:
        basename = d.replace("/", "_").replace(":", "_").replace("/", "_")
        # Look for any file containing the DOI basename
        found = False
        for f in os.listdir(output_dir) if os.path.exists(output_dir) else []:
            if basename in f and f.endswith(".pdf"):
                fpath = os.path.join(output_dir, f)
                if os.path.getsize(fpath) > 5000:
                    downloaded.append(d)
                    found = True
                    break
        if not found:
            remaining.append(d)

    print(f"  IEEE result: {OK} {len(downloaded)} downloaded, {ARROW} {len(ieee_dois) - len(downloaded)} remaining for next round")

    try:
        os.remove(ieee_input)
    except Exception:
        pass

    return downloaded, remaining


def run_generic_round(dois: list[str], output_dir: str, port: int,
                      include_si: bool = False) -> tuple[list[str], list[str], dict[str, str]]:
    """Round 2: Generic CDP for all remaining publishers.
    Returns (downloaded_dois, remaining_dois)."""
    # Filter: generic + direct_http publishers only
    generic_dois = []
    skip_dois = []
    for d in dois:
        pub = resolve_publisher(d)
        strategy = pub.get("strategy", "generic") if pub else "generic"
        if strategy in ("generic", "direct_http"):
            generic_dois.append(d)
        elif strategy == "skip":
            skip_dois.append(d)
        else:
            # SD or IEEE that weren't caught earlier - still try generic
            generic_dois.append(d)

    if not generic_dois:
        if skip_dois:
            print(f"\n{SKIP} Round 2 (Generic CDP): {len(skip_dois)} unavailable papers skipped, 0 eligible.")
        else:
            print(f"\n{SKIP} Round 2 (Generic CDP): No remaining papers.")
        return [], dois, {}

    print(f"\n{'='*60}")
    print(f"Round 2: Generic Publisher CDP ({len(generic_dois)} papers)")
    print(f"{'='*60}")

    ok, fail = 0, 0
    downloaded = []
    remaining = []
    failure_reasons: dict[str, str] = {}

    global_i = 0
    for pub_name, publisher_domain, group_dois in group_english_cdp_dois(generic_dois):
        print(f"\n  English CDP group: {pub_name} ({publisher_domain}), {len(group_dois)} papers")
        for doi in group_dois:
            global_i += 1
            print(f"  [{global_i}/{len(generic_dois)}] {doi[:50]} {ARROW} {pub_name} ({publisher_domain})", end=" ", flush=True)

            t0 = time.time()
            try:
                result_path, status, _ = generic_download_one(
                    port, doi, output_dir, include_si=include_si
                )
            except Exception as e:
                if ensure_cdp_running(port):
                    try:
                        result_path, status, _ = generic_download_one(
                            port, doi, output_dir, include_si=include_si
                        )
                    except Exception:
                        result_path, status = None, "failed"
                else:
                    result_path, status = None, "failed"
                print(f"\n  {WARN} Retry after error: {type(e).__name__}")
            elapsed = time.time() - t0

            if result_path and status == "ok":
                size_kb = os.path.getsize(result_path) // 1024
                print(f"{OK} ({size_kb}KB, {elapsed:.1f}s)")
                downloaded.append(doi)
                ok += 1
            elif status in (
                "manual_required",
                "captcha_required",
                "institution_login_required",
                "pdf_probe_unknown",
                "access_denied",
                "login_required",
            ):
                print(f"{WARN} manual confirmation needed ({elapsed:.1f}s)")
                if pub_name == "mdpi":
                    print(f"  {ARROW} MDPI 已打开详情页；请在可见 Chrome 点击 Download PDF，完成后可继续重跑剩余列表。")
                else:
                    print(f"  {ARROW} {pub_name} 需要你现在去可见 Chrome 完成机构登录/验证；完成后可继续重跑剩余列表。")
                remaining.append(doi)
                fail += 1
                failure_reasons[doi] = status
            elif status == "si_only":
                print(f"{WARN} SI only ({elapsed:.1f}s)")
                remaining.append(doi)
                fail += 1
                failure_reasons[doi] = "supplementary_only"
            elif status in ("pii_resolution_failed", "not_subscribed_or_referencework", "article_page_no_pdf_route"):
                print(f"{FAIL} ({status}, {elapsed:.1f}s)")
                remaining.append(doi)
                fail += 1
                failure_reasons[doi] = status
            else:
                print(f"{FAIL} ({elapsed:.1f}s)")
                remaining.append(doi)
                fail += 1
                failure_reasons[doi] = "generic_failed"

    # Remaining = failures + skips
    remaining = remaining + skip_dois
    print(f"  Generic result: {OK} {ok} downloaded, {FAIL} {fail} failed, {SKIP} {len(skip_dois)} skipped")

    return downloaded, remaining, failure_reasons


# ── Chinese Round ────────────────────────────────────────────────────────────

CHINESE_MANUAL_RETRY_STATUSES = {
    "manual_confirmation_required",
    "manual_required",
    "institution_login_required",
    "pdf_probe_unknown",
    "access_denied",
    "login_required",
    "chapter_download_mode",
}


def _confirm_cnki_captcha_resolution(title: str, confirmed_login: bool = False) -> str:
    """Ask the outer agent/user to confirm CNKI captcha completion."""
    print()
    print(f"  {WARN} CNKI 当前篇触发图形验证。")
    print("  请在已打开的 CDP 浏览器里完成图形验证，并停留在该论文详情页。")
    print("  完成后回到对话/终端输入完整短语。")
    print("Choose one option by typing the full phrase:")
    print("  已验证继续")
    print("  稍后重试")
    if confirmed_login:
        print(f"  {OK} --confirmed supplied: treating current CNKI captcha as verified and retrying.\n")
        print(f"  {ARROW} Retrying current paper after captcha verification: {title[:45]}")
        return "retry"
    resp = _safe_gate_input("输入完整短语: ")
    if resp is None:
        return "checkpoint"
    resp = resp.strip()
    if resp == "已验证继续":
        print(f"  {ARROW} Retrying current paper after captcha verification: {title[:45]}")
        return "retry"
    if resp == "稍后重试":
        return "checkpoint"
    print(f"  {WARN} 未识别输入，保留中文 checkpoint，稍后从 checkpoint 恢复。")
    return "checkpoint"


def _confirm_chinese_manual_retry(title: str, source: str, status: str) -> bool:
    """Pause on CNKI/Wanfang manual states so the current paper can be retried."""
    print()
    print(f"  {WARN} {source.upper()} 需要人工处理当前篇：{status}")
    print(f"  {ARROW} 请在已打开的 CDP 浏览器里完成图形验证/机构验证，或手动点击当前篇下载。")
    print("Choose one option:")
    print("  1) 已处理，重试当前篇")
    print("  2) 跳过当前篇，继续下一篇")
    print("  3) 稍后重试（保留为失败项）")
    resp = _safe_gate_input("Enter 1/2/3: ")
    if resp is None:
        return False
    resp = resp.strip()
    if resp == "1":
        print(f"  {ARROW} Retrying current paper: {title[:45]}")
        return True
    return False


def _wait_for_cnki_captcha_resolution(
    paper: dict,
    port: int,
    timeout_seconds: int = CNKI_CAPTCHA_MONITOR_TIMEOUT,
    poll_interval: int = CNKI_CAPTCHA_MONITOR_INTERVAL,
) -> str:
    """Wait for the current CNKI captcha page to return to the target detail tab."""
    article_url = paper.get("article_url", "")
    title = paper.get("title", "")
    print(f"  {ARROW} 已开始监控当前篇 CNKI 验证页；请在已打开的浏览器里完成图形验证，完成后会自动继续。")
    deadline = time.time() + timeout_seconds
    last_progress_log = time.time()
    watched_tab_id, watched_status = _find_reusable_cnki_tab(port, article_url, title=title)
    lost_since: float | None = None
    while time.time() < deadline:
        if watched_tab_id:
            tab_id, status = _find_reusable_cnki_tab(port, article_url, title=title)
            if tab_id != watched_tab_id:
                if get_tab_ws_url(port, watched_tab_id):
                    tab_id, status = watched_tab_id, "captcha_required"
                else:
                    watched_tab_id = None
                    watched_status = None
        else:
            tab_id, status = _find_reusable_cnki_tab(port, article_url, title=title)
            if tab_id:
                watched_tab_id, watched_status = tab_id, status
        if tab_id and status != "captcha_required":
            print(f"  {ARROW} 已检测到验证完成，正在自动重试当前篇。")
            return "ready"
        if not tab_id and status != "captcha_required":
            now = time.time()
            if lost_since is None:
                lost_since = now
            elif now - lost_since >= max(8, poll_interval * 4):
                print(f"  {WARN} 当前篇 CNKI 验证页已丢失或跳转到无关页面。")
                return "page_lost"
        else:
            lost_since = None
        now = time.time()
        if now - last_progress_log >= 10:
            print(f"  {ARROW} 仍在等待当前篇 CNKI 验证完成...")
            last_progress_log = now
        time.sleep(poll_interval)
    print(f"  {WARN} 当前篇 CNKI 验证等待超时。")
    return "timeout"


def _checkpoint_pending_chinese_papers(
    pending_papers: list[dict], output_dir: str
) -> tuple[str, list[str], dict[str, str]]:
    """Persist a resumable Chinese checkpoint for the remaining papers."""
    failure_reasons = {
        (paper.get("doi") or paper.get("title", "")): paper.get("failure_reason") or "pending_user_login"
        for paper in pending_papers
    }
    checkpoint_path = write_chinese_login_checkpoint(output_dir, pending_papers, failure_reasons)
    remaining = list(failure_reasons)
    print(f"  {ARROW} 当前篇等待未完成，已写 checkpoint：{checkpoint_path}")
    return checkpoint_path, remaining, failure_reasons


def _auto_retry_cnki_current_paper(
    paper: dict,
    output_dir: str,
    port: int,
    reason: str,
    *,
    max_attempts: int = CNKI_AUTO_RECOVERY_ATTEMPTS,
) -> tuple[Optional[str], str, float]:
    """Try to recover the current CNKI paper without asking the outer host again."""
    title = paper.get("title", "")
    print(
        f"  {ARROW} 当前篇触发 {reason}，先自动恢复并重试 "
        f"({max_attempts} 次以内)，尽量不再要求人工确认。"
    )
    last_status = reason
    last_elapsed = 0.0
    for attempt in range(1, max_attempts + 1):
        if attempt > 1 and CNKI_AUTO_RECOVERY_DELAY > 0:
            time.sleep(CNKI_AUTO_RECOVERY_DELAY)
        print(f"  {ARROW} 自动重试当前篇 ({attempt}/{max_attempts})：{title[:45]}")
        t0 = time.time()
        result_path, status, _ = _download_chinese_paper_once(paper, output_dir, port)
        last_elapsed = time.time() - t0
        last_status = status or reason
        if result_path and status == "ok":
            return result_path, status, last_elapsed
        if last_status == "captcha_required":
            captcha_wait_status = _wait_for_cnki_captcha_resolution(paper, port)
            if captcha_wait_status == "ready":
                continue
            if captcha_wait_status == "timeout":
                return None, "captcha_required", last_elapsed
            last_status = "captcha_required"
            continue
        if last_status in CHINESE_MANUAL_RETRY_STATUSES:
            continue
        return result_path, last_status, last_elapsed
    return None, last_status, last_elapsed


def _download_chinese_paper_once(paper: dict, output_dir: str, port: int) -> tuple[Optional[str], str, str]:
    title = paper.get("title", "")
    source = paper.get("source", "").lower()
    article_url = paper.get("article_url", "")
    doi = paper.get("doi", "")
    source_to_pub = {"cnki": "cnki", "wanfang": "wanfang"}

    pub_key = source_to_pub.get(source, source)
    publisher = resolve_publisher(doi) if doi else None
    if publisher is None or publisher.get("strategy") != "chinese_cdp":
        # Force publisher to Chinese config
        from generic_publisher_downloader import _PUBLISHER_CONFIGS
        publisher = _PUBLISHER_CONFIGS.get(pub_key, {"strategy": "chinese_cdp", "_key": pub_key})

    return generic_download_one(
        port, doi or f"{source}.{hashlib.md5(title.encode()).hexdigest()[:12]}",
        output_dir, article_url=article_url, title=title
    )


def run_chinese_round_with_reasons(
    papers: list[dict], output_dir: str, port: int,
    confirmed_login: bool = False
) -> tuple[list[str], list[str], dict[str, str]]:
    """Chinese CDP download round for CNKI and Wanfang papers.

    Each paper dict must have: title, source (cnki|wanfang), article_url.
    Uses the generic_publisher_downloader engine with publisher override
    set to the matching Chinese publisher config.

    Args:
        papers: List of {title, source, article_url, doi} dicts.
        output_dir: Directory to save downloaded PDFs.
        port: CDP Chrome debug port.

    Returns: (downloaded_dois, remaining_dois, failure_reasons).
    """
    if not papers:
        print(f"\n{SKIP} Chinese Round: No Chinese papers to download.")
        return [], [], {}

    print(f"\n{'='*60}")
    print(f"Chinese Round: CNKI / Wanfang CDP ({len(papers)} papers)")
    print(f"{'='*60}")

    ok, fail, skipped = 0, 0, 0
    downloaded = []
    remaining = []
    failure_reasons: dict[str, str] = {}

    for i, paper in enumerate(papers):
        title = paper.get("title", f"paper_{i+1}")
        source = paper.get("source", "").lower()
        article_url = paper.get("article_url", "")
        doi = paper.get("doi", "")
        paper_id = doi or title

        # Shorten title for display
        display_title = title[:45] + ("..." if len(title) > 45 else "")

        print(f"  [{i+1}/{len(papers)}] [{source.upper():6s}] {display_title}", end=" ", flush=True)

        if not article_url:
            print(f"{FAIL} (no article URL - cannot download)")
            remaining.append(paper_id)
            failure_reasons[paper_id] = "no_url"
            skipped += 1
            continue

        t0 = time.time()
        manual_prompt_used = False

        result_path, status, _ = _download_chinese_paper_once(paper, output_dir, port)
        elapsed = time.time() - t0

        if not result_path and status == "captcha_required" and source == "cnki":
            print(f"{WARN} ({status}, {elapsed:.1f}s)")
            captcha_wait_status = _wait_for_cnki_captcha_resolution(paper, port)
            if captcha_wait_status == "ready":
                t0 = time.time()
                result_path, status, _ = _download_chinese_paper_once(paper, output_dir, port)
                elapsed = time.time() - t0
            else:
                if captcha_wait_status == "page_lost":
                    print(f"  {WARN} 当前篇已离开目标详情页，先尝试自动恢复。")
                    result_path, status, elapsed = _auto_retry_cnki_current_paper(
                        paper,
                        output_dir,
                        port,
                        "page_lost",
                    )
                if (
                    captcha_wait_status != "timeout"
                    and not result_path
                    and status == "captcha_required"
                ):
                    captcha_action = _confirm_cnki_captcha_resolution(
                        title,
                        confirmed_login=confirmed_login,
                    )
                    if captcha_action == "retry":
                        t0 = time.time()
                        result_path, status, _ = _download_chinese_paper_once(paper, output_dir, port)
                        elapsed = time.time() - t0
                if not result_path and status == "captcha_required":
                    pending_papers = []
                    for pending_paper in papers[i:]:
                        pending_copy = dict(pending_paper)
                        pending_copy["failure_reason"] = "captcha_required"
                        pending_papers.append(pending_copy)
                    _checkpoint_path, checkpoint_remaining, checkpoint_reasons = _checkpoint_pending_chinese_papers(
                        pending_papers, output_dir
                    )
                    remaining.extend(checkpoint_remaining)
                    failure_reasons.update(checkpoint_reasons)
                    fail += len(checkpoint_remaining)
                    break

        while not result_path and status in CHINESE_MANUAL_RETRY_STATUSES:
            print(f"{WARN} ({status}, {elapsed:.1f}s)")
            if source == "cnki":
                result_path, status, elapsed = _auto_retry_cnki_current_paper(
                    paper,
                    output_dir,
                    port,
                    status,
                )
                if result_path or status not in CHINESE_MANUAL_RETRY_STATUSES:
                    continue
            if manual_prompt_used or not _confirm_chinese_manual_retry(title, source, status):
                break
            manual_prompt_used = True
            t0 = time.time()
            result_path, status, _ = _download_chinese_paper_once(paper, output_dir, port)
            elapsed = time.time() - t0

        if not result_path and status == "captcha_required" and source == "cnki":
            pending_papers = []
            for pending_paper in papers[i:]:
                pending_copy = dict(pending_paper)
                pending_copy["failure_reason"] = "captcha_required"
                pending_papers.append(pending_copy)
            _checkpoint_path, checkpoint_remaining, checkpoint_reasons = _checkpoint_pending_chinese_papers(
                pending_papers, output_dir
            )
            remaining.extend(checkpoint_remaining)
            failure_reasons.update(checkpoint_reasons)
            fail += len(checkpoint_remaining)
            break

        if result_path and status == "ok":
            size_kb = os.path.getsize(result_path) // 1024
            print(f"{OK} ({size_kb}KB, {elapsed:.1f}s)")
            downloaded.append(paper_id)
            ok += 1
        elif status == "no_url":
            print(f"{FAIL} (no article URL)")
            remaining.append(paper_id)
            failure_reasons[paper_id] = status
            skipped += 1
        else:
            print(f"{FAIL} ({elapsed:.1f}s)")
            remaining.append(paper_id)
            failure_reasons[paper_id] = status or "chinese_cdp_failed"
            fail += 1

    print(f"  Chinese result: {OK} {ok} downloaded, {FAIL} {fail} failed, {SKIP} {skipped} skipped (no URL)")

    return downloaded, remaining, failure_reasons


def run_chinese_round(papers: list[dict], output_dir: str, port: int,
                      confirmed_login: bool = False) -> tuple[list[str], list[str]]:
    """Backward-compatible wrapper for callers that do not need failure reasons."""
    downloaded, remaining, _failure_reasons = run_chinese_round_with_reasons(
        papers,
        output_dir,
        port,
        confirmed_login=confirmed_login,
    )
    return downloaded, remaining


# ── English Pipeline (R1->R2->R3 sequential) ────────────────────────────────

def run_english_pipeline(dois: list[str], output_dir: str, port: int,
                         skip_scihub: bool = False, skip_sd: bool = False,
                         include_si: bool = False,
                         sd_browser: str = "chrome",
                         skip_oa_fast: bool = False,
                         oa_hints: Optional[dict[str, dict]] = None,
                         ) -> tuple[list[str], list[str], list[dict], dict[str, str]]:
    """Run English download pipeline: Sci-Hub (<=2021) -> OA fast -> IEEE -> Generic CDP.

    English paths must finish before CNKI/Wanfang CDP starts. This helper is
    retained for direct callers; main() now serializes English before Chinese.

    Args:
        dois: List of DOIs to download.
        output_dir: Directory to save PDFs.
        port: CDP Chrome debug port.
        skip_scihub: Skip Sci-Hub round.
        skip_sd: Backward-compatible no-op; ScienceDirect now flows through Generic CDP.
        include_si: Download supplementary info where available.
        skip_oa_fast: Skip public OA PDF candidates.
        oa_hints: Step 4 OA candidate metadata keyed by DOI.

    Returns:
        (downloaded, remaining, round_results) tuple.
    """
    all_downloaded: list[str] = []
    round_results: list[dict] = []
    remaining = list(dois)
    failure_reasons: dict[str, str] = {}

    # Round 1: Sci-Hub
    if not skip_scihub and _scihub_eligible_dois(remaining):
        downloaded, remaining = run_scihub_round(remaining, output_dir, port)
        all_downloaded.extend(downloaded)
        round_results.append({"round": "Sci-Hub", "downloaded": downloaded})
    elif skip_scihub:
        print(f"\n{SKIP} Round 1 (Sci-Hub): Skipped (--skip-scihub)")
    else:
        print(f"\n{SKIP} Round 1 (Sci-Hub): No <= {SCI_HUB_CUTOFF_YEAR} papers to try.")

    if not remaining:
        print(f"\n{DONE} English pipeline complete - all {len(all_downloaded)}/{len(dois)} downloaded!")
        return all_downloaded, remaining, round_results, failure_reasons

    if skip_sd:
        print(f"\n{SKIP} --skip-sd ignored: ScienceDirect is handled inside Generic CDP.")

    # Round 2: OA fast (public PDF only)
    if not skip_oa_fast:
        downloaded, remaining, oa_failures = run_oa_fast_round(
            remaining, output_dir, oa_hints=oa_hints
        )
        all_downloaded.extend(downloaded)
        round_results.append({"round": "OA fast (public_pdf_verified)", "downloaded": downloaded})
        failure_reasons.update(oa_failures)
    else:
        print(f"\n{SKIP} Round 2 (OA fast): Skipped (--skip-oa-fast)")

    if not remaining:
        print(f"\n{DONE} English pipeline complete - all {len(all_downloaded)}/{len(dois)} downloaded!")
        return all_downloaded, remaining, round_results, failure_reasons

    if not remaining:
        print(f"\n{DONE} English pipeline complete - all {len(all_downloaded)}/{len(dois)} downloaded!")
        return all_downloaded, remaining, round_results, failure_reasons

    # Round 3: IEEE CDP (dedicated path)
    downloaded, remaining = run_ieee_round(remaining, output_dir, port)
    all_downloaded.extend(downloaded)
    round_results.append({"round": "IEEE CDP", "downloaded": downloaded})

    if not remaining:
        print(f"\n{DONE} English pipeline complete - all {len(all_downloaded)}/{len(dois)} downloaded!")
        return all_downloaded, remaining, round_results, failure_reasons

    # Round 4: Generic CDP (ScienceDirect and other English publishers)
    downloaded, remaining, generic_failures = run_generic_round(
        remaining, output_dir, port, include_si=include_si
    )
    all_downloaded.extend(downloaded)
    round_results.append({"round": "Generic CDP", "downloaded": downloaded})
    failure_reasons.update(generic_failures)

    print(f"\n{DONE} English pipeline complete - {OK} {len(all_downloaded)}/{len(dois)}, {FAIL} {len(remaining)} remaining")
    return all_downloaded, remaining, round_results, failure_reasons


def run_english_cdp(dois: list[str], output_dir: str, port: int,
                    skip_sd: bool = False, include_si: bool = False,
                    sd_browser: str = "chrome"
                    ) -> tuple[list[str], list[str], list[dict], dict[str, str]]:
    """Run English CDP-only pipeline through Generic CDP. No Sci-Hub.

    Designed to run AFTER English login gate in Phase 2.
    """
    all_downloaded: list[str] = []
    round_results: list[dict] = []
    remaining = list(dois)
    failure_reasons: dict[str, str] = {}

    if skip_sd:
        print(f"\n{SKIP} --skip-sd ignored: ScienceDirect is handled inside Generic CDP.")

    # R2: Generic CDP
    downloaded, remaining, generic_failures = run_generic_round(
        remaining, output_dir, port, include_si=include_si
    )
    all_downloaded.extend(downloaded)
    round_results.append({"round": "Generic CDP", "downloaded": downloaded})
    failure_reasons.update(generic_failures)

    login_retry_dois = _filter_login_required_dois(remaining, generic_failures)
    if login_retry_dois:
        print(f"\n{WARN} First grouped English CDP pass completed; institutional login/manual confirmation required for {len(login_retry_dois)} item(s).")
        print("  Only those login-required item(s) will be retried once after confirmation.")
        gate_result = show_english_login_gate(
            login_retry_dois,
            skip_sd=skip_sd,
            port=port,
            interactive=sys.stdin.isatty(),
        )
        if gate_result is None:
            failure_reasons.update({
                doi: "pending_user_login"
                for doi in login_retry_dois
            })
            checkpoint_path = write_login_checkpoint(
                output_dir,
                stage="english_cdp_retry",
                dois=login_retry_dois,
                failure_reasons=failure_reasons,
            )
            print(f"  {ARROW} Login checkpoint written; resume after manual login: {checkpoint_path}")
        elif gate_result:
            retry_downloaded, retry_remaining, retry_failures = run_generic_round(
                login_retry_dois, output_dir, port, include_si=include_si
            )
            all_downloaded.extend(retry_downloaded)
            round_results.append({"round": "Generic CDP (after login)", "downloaded": retry_downloaded})
            remaining = [doi for doi in remaining if doi not in login_retry_dois]
            remaining.extend(retry_remaining)
            for doi in retry_downloaded:
                failure_reasons.pop(doi, None)
            failure_reasons.update(retry_failures)
        else:
            print("English CDP login retry skipped by user.")

    print(f"\n{DONE} English CDP complete - {OK} {len(all_downloaded)}/{len(dois)}, {FAIL} {len(remaining)} remaining")
    return all_downloaded, remaining, round_results, failure_reasons


# ── Download Log ────────────────────────────────────────────────────────────

def generate_download_log(output_dir: str, all_dois: list[str],
                          round_results: list[dict],
                          failure_reasons: Optional[dict[str, str]] = None) -> str:
    """Generate a Markdown download tracking log."""
    log_path = os.path.join(output_dir, "download_log.md")

    failure_reasons = failure_reasons or {}
    # Build status map
    status_map: dict[str, dict] = {}
    for d in all_dois:
        status_map[d] = {"status": "pending", "source": "", "path": "", "size_kb": 0, "reason": failure_reasons.get(d, "")}

    for result in round_results:
        for d in result.get("downloaded", []):
            basename = d.replace("/", "_").replace(":", "_")
            fpath = os.path.join(output_dir, f"{basename}.pdf")
            size_kb = os.path.getsize(fpath) // 1024 if os.path.exists(fpath) else 0
            status_map[d] = {
                "status": "[OK]",
                "source": result.get("round", "unknown"),
                "path": fpath,
                "size_kb": size_kb,
                "reason": "",
            }

    # Generate Markdown
    lines = [
        f"# Download Log",
        f"",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Output dir: {output_dir}",
        f"Total DOIs: {len(all_dois)}",
        f"",
        f"| # | DOI | Status | Source | Reason | Size | Path |",
        f"|---|-----|--------|--------|--------|------|------|",
    ]

    for i, doi in enumerate(all_dois, 1):
        info = status_map.get(doi, {})
        status = info.get("status", "[PENDING]")
        source = info.get("source", "")
        reason = info.get("reason", "") or "-"
        size = f"{info.get('size_kb', 0)}KB" if info.get("size_kb") else "-"
        path = os.path.basename(info.get("path", "")) if info.get("path") else "-"
        lines.append(f"| {i} | `{doi[:45]}` | {status} | {source} | {reason} | {size} | {path} |")

    # Summary
    ok_count = sum(1 for v in status_map.values() if v["status"] == "[OK]")
    fail_count = sum(1 for v in status_map.values() if v["status"] == "pending")
    lines.extend([
        f"",
        f"## Summary",
        f"",
        f"- [OK] Downloaded: {ok_count}/{len(all_dois)}",
        f"- [FAIL] Failed/Pending: {fail_count}/{len(all_dois)}",
    ])

    content = "\n".join(lines)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(content)

    return log_path


STEP5_RETRYABLE_REASONS = {
    "generic_failed",
    "sd_failed_unknown",
    "oa_fetch_failed",
    "detail_click_no_effect",
}
STEP5_LOGIN_REASONS = {"pending_user_login", "institution_login_required", "login_required"}
STEP5_USER_ACTION_REASONS = {"captcha_required", "manual_required", "manual_verification_required"}
STEP5_NOT_AVAILABLE_REASONS = {"access_denied", "no_url", "fulltext_delivery_mode", "not_subscribed_or_referencework"}
STEP5_METADATA_REASONS = {"pii_resolution_failed", "invalid_oa_candidate", "oa_whitelist_but_verification_failed"}


def _safe_pdf_quality(path: str | Path) -> str:
    diagnostics = diagnose_pdf_file(path)
    return "pdf_verified" if diagnostics.get("verification_status") == "verified" else "pdf_unverified"


def diagnose_pdf_file(path: str | Path) -> dict[str, Any]:
    """Return lightweight PDF diagnostics without parsing full content."""
    pdf_path = Path(path)
    diagnostics: dict[str, Any] = {
        "exists": pdf_path.exists(),
        "size_bytes": 0,
        "magic": "",
        "page_count_probe": 0,
        "looks_like_html": False,
        "verification_status": "invalid",
        "sha256": "",
        "issue": "missing",
    }
    if not pdf_path.exists():
        return diagnostics
    try:
        digest = hashlib.sha256()
        data = b""
        page_count_probe = 0
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                if not data:
                    data = chunk
                digest.update(chunk)
                page_count_probe += max(chunk.count(b"/Type /Page"), chunk.count(b"/Type/Page"))
        size = pdf_path.stat().st_size
    except OSError as exc:
        diagnostics["issue"] = f"read_error:{type(exc).__name__}"
        return diagnostics

    header = data[:16].lstrip()
    lower_head = data[:512].lower()
    looks_like_html = b"<html" in lower_head or b"<!doctype html" in lower_head
    is_pdf = header.startswith(b"%PDF")
    diagnostics.update({
        "size_bytes": size,
        "magic": "%PDF" if is_pdf else header[:8].decode("latin-1", errors="ignore"),
        "page_count_probe": page_count_probe,
        "looks_like_html": looks_like_html,
        "sha256": digest.hexdigest(),
    })
    if looks_like_html:
        diagnostics["issue"] = "html_saved_as_pdf"
    elif not is_pdf:
        diagnostics["issue"] = "not_pdf_magic"
    elif size < OA_FAST_MIN_BYTES:
        diagnostics["issue"] = "too_small"
    elif diagnostics["page_count_probe"] <= 0:
        diagnostics["issue"] = "no_readable_pages"
    else:
        diagnostics["issue"] = "ok"
        diagnostics["verification_status"] = "verified"
    return diagnostics


def _doi_pdf_basename(identifier: str) -> str:
    return identifier.replace("/", "_").replace(":", "_")


def _pdf_candidates_for_identifier(output_dir: str | Path, identifier: str) -> list[Path]:
    if not identifier:
        return []
    output = Path(output_dir)
    candidates = [output / f"{_doi_pdf_basename(identifier)}.pdf"]
    lowered = identifier.lower().replace("https://doi.org/", "").replace("doi:", "")
    safe_fragment = _doi_pdf_basename(lowered).lower()
    if output.exists():
        candidates.extend(
            p for p in output.glob("*.pdf")
            if safe_fragment and safe_fragment in p.name.lower()
        )
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _find_pdf_candidate_for_identifier(output_dir: str | Path, identifier: str) -> str:
    for path in _pdf_candidates_for_identifier(output_dir, identifier):
        try:
            if path.exists():
                return str(path)
        except OSError:
            continue
    return ""


def _find_pdf_for_identifier(output_dir: str | Path, identifier: str) -> str:
    for path in _pdf_candidates_for_identifier(output_dir, identifier):
        try:
            if path.exists() and diagnose_pdf_file(path).get("verification_status") == "verified":
                return str(path)
        except OSError:
            continue
    return ""


def build_pdf_pool_index(output_dir: str, items: list[dict] | None = None) -> PdfPoolIndex:
    output = Path(output_dir)
    known: dict[str, dict] = {}
    for item in items or []:
        key = (item.get("doi") or item.get("id") or item.get("title") or "").strip()
        if key:
            known[key.lower()] = item

    pool_items: list[PdfPoolItem] = []
    if output.exists():
        for idx, path in enumerate(sorted(output.glob("*.pdf")), 1):
            stat = path.stat()
            diagnostics = diagnose_pdf_file(path)
            matched = {}
            name_key = path.stem.lower()
            for key, item in known.items():
                if key and _doi_pdf_basename(key).lower() in name_key:
                    matched = item
                    break
            pool_items.append(PdfPoolItem(
                id=matched.get("id") or matched.get("source_id") or f"pdf-{idx:04d}",
                doi=matched.get("doi", ""),
                title=matched.get("title", ""),
                source=matched.get("source", ""),
                source_id=matched.get("source_id", ""),
                pdf_path=str(path),
                quality="pdf_verified" if diagnostics.get("verification_status") == "verified" else "pdf_unverified",
                size_bytes=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                pdf_diagnostics=diagnostics,
                verification_status=diagnostics.get("verification_status", "invalid"),
                verification_reason=diagnostics.get("issue", ""),
                sha256=diagnostics.get("sha256", ""),
            ))
    return PdfPoolIndex(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        output_dir=str(output),
        items=pool_items,
    )


def _recovery_buckets(failure_reasons: dict[str, str]) -> dict[str, list[str]]:
    buckets = {
        "retryable": [],
        "needs_login": [],
        "needs_user_action": [],
        "not_available": [],
        "needs_metadata_fix": [],
    }
    for identifier, reason in failure_reasons.items():
        if reason in STEP5_LOGIN_REASONS:
            buckets["needs_login"].append(identifier)
        elif reason in STEP5_USER_ACTION_REASONS:
            buckets["needs_user_action"].append(identifier)
        elif reason in STEP5_NOT_AVAILABLE_REASONS:
            buckets["not_available"].append(identifier)
        elif reason in STEP5_METADATA_REASONS:
            buckets["needs_metadata_fix"].append(identifier)
        elif reason in STEP5_RETRYABLE_REASONS or reason.startswith("oa_fetch_failed"):
            buckets["retryable"].append(identifier)
        else:
            buckets["retryable"].append(identifier)
    return buckets


def _recommended_next_step(readiness: str, buckets: dict[str, list[str]]) -> str:
    if buckets.get("needs_login"):
        return "resume_after_login"
    if buckets.get("needs_user_action"):
        if any(True for _ in buckets["needs_user_action"]):
            return "solve_captcha_or_manual_download_then_resume"
    if buckets.get("needs_metadata_fix"):
        return "fix_metadata_then_rerun"
    if buckets.get("retryable"):
        return "rerun_failed_items"
    if readiness == "partial":
        return "proceed_to_step6_with_partial_pool"
    return "proceed_to_step6"


def _publisher_for_identifier(identifier: str) -> str:
    try:
        pub = resolve_publisher(identifier)
        return pub.get("_key", "unknown") if pub else "unknown"
    except Exception:
        return "unknown"


def _status_for_reason(reason: str) -> str:
    if reason in STEP5_LOGIN_REASONS:
        return "pending_user_login"
    if reason in STEP5_USER_ACTION_REASONS:
        return "manual_required"
    if reason in STEP5_NOT_AVAILABLE_REASONS:
        return "access_denied"
    if reason in {"invalid_pdf", "html_saved_as_pdf", "not_pdf_magic", "too_small", "no_readable_pages"}:
        return "invalid_pdf"
    if reason in {"login_skipped_by_user"}:
        return "skipped"
    return "unresolved"


def _pending_checkpoint_reasons(output_dir: str | Path, identifiers: set[str]) -> dict[str, str]:
    pending: dict[str, str] = {}
    for name in ("login_checkpoint.json", "chinese_login_checkpoint.json"):
        path = Path(output_dir) / name
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "pending_user_login":
            continue
        for item in payload.get("items", []):
            identifier = item.get("doi") or item.get("source_id") or item.get("id") or item.get("title", "")
            if identifier in identifiers:
                pending[identifier] = item.get("failure_reason") or "pending_user_login"
    return pending


def _domain_for_item(identifier: str, item: dict[str, Any]) -> str:
    article_url = item.get("article_url", "")
    if article_url:
        parsed = urllib.parse.urlparse(article_url)
        if parsed.netloc:
            return parsed.netloc.lower()
    try:
        pub = resolve_publisher(identifier)
        return pub.get("publisher_domain", "") if pub else ""
    except Exception:
        return ""


def build_publisher_summary(items: list[Step5DownloadItem]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item.publisher or item.source or "unknown"
        bucket = summary.setdefault(key, {"total": 0, "downloaded": 0, "failed_or_pending": 0, "failure_reasons": {}})
        bucket["total"] += 1
        if item.status == "downloaded":
            bucket["downloaded"] += 1
        else:
            bucket["failed_or_pending"] += 1
            reason = item.failure_reason or "unknown"
            bucket["failure_reasons"][reason] = bucket["failure_reasons"].get(reason, 0) + 1
    return summary


def build_domain_summary(items: list[Step5DownloadItem], item_domains: dict[str, str]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for item in items:
        identifier = item.doi or item.source_id or item.id or item.title
        key = item_domains.get(identifier) or "unknown"
        bucket = summary.setdefault(key, {"total": 0, "downloaded": 0, "failed_or_pending": 0, "failure_reasons": {}})
        bucket["total"] += 1
        if item.status == "downloaded":
            bucket["downloaded"] += 1
        else:
            bucket["failed_or_pending"] += 1
            reason = item.failure_reason or "unknown"
            bucket["failure_reasons"][reason] = bucket["failure_reasons"].get(reason, 0) + 1
    return summary


def build_step5_preflight_summary(
    items: list[dict[str, Any]],
    output_dir: str,
    port: int,
    browser: str,
    local_hits: list[str] | None = None,
    probe_cdp: bool = True,
) -> dict[str, Any]:
    local_hits = local_hits or []
    cdp_ok = check_cdp(port) if probe_cdp else False
    browser_match = False
    browser_product = ""
    if cdp_ok:
        try:
            browser_product = get_cdp_browser_product(port)
            browser_match = cdp_browser_matches(port, browser)
        except Exception:
            browser_match = False
    return {
        "total_items": len(items),
        "local_pdf_hits": len(local_hits),
        "output_dir": str(output_dir),
        "cdp": {
            "checked": probe_cdp,
            "ok": cdp_ok,
            "port": port,
            "browser": browser,
            "matches_requested_browser": browser_match,
            "product": browser_product,
        },
    }


def print_step5_preflight_summary(summary: dict[str, Any]) -> None:
    cdp = summary.get("cdp", {})
    status = OK if cdp.get("ok") else WARN
    print("Step 5 preflight summary:")
    print(f"  items:          {summary.get('total_items', 0)}")
    print(f"  local PDF hits: {summary.get('local_pdf_hits', 0)}")
    print(f"  output_dir:     {summary.get('output_dir', '')}")
    if cdp.get("checked", True):
        print(f"  {status} CDP:        {cdp.get('ok')} ({cdp.get('product') or 'not running'})")
    else:
        print(f"  {status} CDP:        not checked (dry-run has no browser dependency)")


def _dry_run_route(item: dict[str, Any]) -> tuple[str, str]:
    source = str(item.get("source") or "").strip().lower()
    article_url = str(item.get("article_url") or "").strip().lower()
    if source in {"cnki", "wanfang"} or "cnki.net" in article_url or "wanfangdata.com.cn" in article_url:
        return "chinese_cdp", source or ("cnki" if "cnki.net" in article_url else "wanfang")
    doi = str(item.get("doi") or "").strip()
    if doi:
        classified = classify_doi(doi)
        return str(classified.get("strategy") or "generic"), str(classified.get("publisher") or "unknown")
    return "unresolved", str(item.get("publisher") or source or "unknown")


def write_step5_dry_run_outputs(
    output_dir: str,
    all_items: list[dict[str, Any]],
    preflight_summary: dict[str, Any],
) -> dict[str, str]:
    """Write plan artifacts without browser, login, lock, or download side effects."""
    os.makedirs(output_dir, exist_ok=True)
    run_id = f"step5-dryrun-{datetime.now():%Y%m%d-%H%M%S-%f}"
    manifest_items: list[Step5DownloadItem] = []
    item_domains: dict[str, str] = {}
    route_plan: list[dict[str, str]] = []
    unresolved_rows: list[dict[str, str]] = []

    for index, item in enumerate(all_items, 1):
        identifier = str(
            item.get("doi") or item.get("source_id") or item.get("id") or item.get("title") or f"item-{index:04d}"
        )
        strategy, publisher = _dry_run_route(item)
        missing_chinese_url = strategy == "chinese_cdp" and not item.get("article_url")
        unavailable = strategy in {"skip", "unresolved"} or missing_chinese_url
        status = "skipped" if strategy == "skip" else "unresolved"
        reason = "missing_article_url" if missing_chinese_url else "route_unavailable" if unavailable else ""
        next_action = "fix_metadata_then_rerun" if reason == "missing_article_url" else "manual_route_review" if unavailable else f"execute_route:{strategy}"
        route_plan.append({
            "id": identifier,
            "strategy": strategy,
            "publisher": publisher,
        })
        if unavailable:
            unresolved_rows.append({"id": identifier, "reason": reason or "route_unavailable"})
        item_domains[identifier] = _domain_for_item(identifier, item)
        manifest_items.append(Step5DownloadItem(
            id=str(item.get("id") or item.get("source_id") or f"step5-{index:04d}"),
            doi=str(item.get("doi") or ""),
            title=str(item.get("title") or ""),
            source=str(item.get("source") or ""),
            source_id=str(item.get("source_id") or ""),
            article_url=str(item.get("article_url") or ""),
            publisher=publisher,
            status=status,
            quality="metadata_only" if item.get("title") else "none",
            failure_reason=reason,
            next_action=next_action,
            attempts=[],
            verification_status="not_checked",
            verification_reason="dry_run_only",
        ))

    total = len(manifest_items)
    status_counts = {
        status: sum(1 for item in manifest_items if item.status == status)
        for status in sorted({item.status for item in manifest_items})
    }
    manifest = Step5DownloadManifest(
        run_id=run_id,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        readiness="blocked",
        recommended_next_step="review_dry_run_then_execute_step5",
        summary={
            "execution_mode": "dry_run",
            "total": total,
            "downloaded": 0,
            "remaining": total,
            "failed_or_pending": total,
            "status_counts": status_counts,
            "route_plan": route_plan,
            "publisher_summary": build_publisher_summary(manifest_items),
            "domain_summary": build_domain_summary(manifest_items, item_domains),
            "preflight": preflight_summary,
        },
        recovery_buckets={
            "retryable": [],
            "needs_login": [],
            "needs_user_action": [row["id"] for row in unresolved_rows],
            "not_available": [],
            "needs_metadata_fix": [row["id"] for row in unresolved_rows if row["reason"] == "missing_article_url"],
        },
        items=manifest_items,
    )

    manifest_path = Path(output_dir) / "download_manifest.json"
    preflight_path = Path(output_dir) / "preflight_summary.json"
    write_step5_download_manifest(manifest_path, manifest)
    atomic_write_json(preflight_path, preflight_summary)
    paths = {"manifest": str(manifest_path), "preflight": str(preflight_path)}
    if unresolved_rows:
        unresolved_path = Path(output_dir) / "unresolved_download_items.md"
        lines = [
            "# Unresolved download items",
            "",
            "> Generated by Step 5 dry-run; no download was attempted.",
            "",
            "| Identifier | Reason |",
            "|---|---|",
        ]
        lines.extend(f"| {row['id']} | {row['reason']} |" for row in unresolved_rows)
        atomic_write_text(unresolved_path, "\n".join(lines) + "\n")
        paths["unresolved"] = str(unresolved_path)
    return paths


def write_failure_snapshots(output_dir: str, items: list[Step5DownloadItem]) -> str:
    snapshot_reasons = {"captcha_required", "manual_required", "pdf_probe_unknown"}
    debug_dir = Path(output_dir) / "step5-debug"
    written = 0
    for item in items:
        if item.failure_reason not in snapshot_reasons:
            continue
        identifier = item.doi or item.source_id or item.id or item.title
        if not identifier:
            continue
        digest = hashlib.md5(identifier.encode("utf-8")).hexdigest()[:12]
        item_dir = debug_dir / digest
        item_dir.mkdir(parents=True, exist_ok=True)
        (item_dir / "reason.json").write_text(json.dumps({
            "id": item.id,
            "doi": item.doi,
            "title": item.title,
            "source": item.source,
            "publisher": item.publisher,
            "failure_reason": item.failure_reason,
            "next_action": item.next_action,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        (item_dir / "final_url.txt").write_text(item.article_url or "", encoding="utf-8")
        (item_dir / "page_title.txt").write_text(item.title or "", encoding="utf-8")
        written += 1
    return str(debug_dir) if written else ""


def write_step5_outputs(
    output_dir: str,
    all_items: list[dict],
    downloaded: list[str],
    remaining: list[str],
    round_results: list[dict],
    failure_reasons: dict[str, str],
    preflight_summary: dict[str, Any] | None = None,
) -> dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    run_id = f"step5-{datetime.now():%Y%m%d-%H%M%S-%f}"
    downloaded_set = set(downloaded)
    remaining_set = set(remaining)
    item_map: dict[str, dict] = {}
    for idx, item in enumerate(all_items, 1):
        key = item.get("doi") or item.get("id") or item.get("title") or f"item-{idx:04d}"
        item_map[key] = item
    checkpoint_reasons = _pending_checkpoint_reasons(output_dir, set(item_map))

    manifest_items: list[Step5DownloadItem] = []
    attempts_rows: list[dict] = []
    item_domains: dict[str, str] = {}
    effective_failure_reasons: dict[str, str] = {}
    for idx, (identifier, item) in enumerate(item_map.items(), 1):
        reason = failure_reasons.get(identifier, "") or checkpoint_reasons.get(identifier, "")
        pdf_path = _find_pdf_candidate_for_identifier(output_dir, identifier)
        diagnostics = diagnose_pdf_file(pdf_path) if pdf_path else {}
        verified = diagnostics.get("verification_status") == "verified"
        if verified:
            status = "downloaded"
            reason = ""
        else:
            if pdf_path:
                reason = diagnostics.get("issue") or "invalid_pdf"
            elif identifier in downloaded_set:
                reason = reason or "download_reported_but_pdf_missing"
            status = _status_for_reason(reason)
        quality = "pdf_verified" if verified else ("pdf_unverified" if pdf_path else ("metadata_only" if item.get("title") else "none"))
        if reason:
            effective_failure_reasons[identifier] = reason
        attempts: list[dict] = []
        if pdf_path:
            attempts.append(step5_attempt(
                "local_index",
                "verified" if verified else "invalid",
                reason=diagnostics.get("issue", ""),
                pdf_path=pdf_path,
                run_id=run_id,
                item_id=identifier,
                route="local_index",
                verification_status=diagnostics.get("verification_status", "invalid"),
            ))
        for result in round_results:
            round_name = result.get("round", "")
            if identifier in result.get("downloaded", []):
                attempts.append(step5_attempt(
                    round_name,
                    "downloaded" if verified else "download_reported_unverified",
                    source=round_name,
                    pdf_path=pdf_path,
                    reason="" if verified else reason,
                    run_id=run_id,
                    item_id=identifier,
                    route=round_name,
                    verification_status="verified" if verified else "invalid",
                ))
        if status != "downloaded" or identifier in remaining_set:
            attempts.append(step5_attempt(
                "final",
                status,
                reason=reason,
                run_id=run_id,
                item_id=identifier,
                verification_status="verified" if verified else "invalid" if pdf_path else "not_checked",
            ))
        attempts_rows.extend({"id": identifier, **attempt} for attempt in attempts)
        item_domains[identifier] = _domain_for_item(identifier, item)
        manifest_items.append(Step5DownloadItem(
            id=item.get("id") or item.get("source_id") or f"step5-{idx:04d}",
            doi=item.get("doi", identifier if identifier.startswith("10.") else ""),
            title=item.get("title", ""),
            source=item.get("source", ""),
            source_id=item.get("source_id", ""),
            article_url=item.get("article_url", ""),
            publisher=item.get("publisher") or _publisher_for_identifier(identifier),
            status=status,
            quality=quality,
            pdf_path=pdf_path,
            failure_reason=reason,
            next_action=_recommended_next_step("partial", _recovery_buckets({identifier: reason})) if reason else "",
            attempts=attempts,
            verification_status="verified" if verified else "invalid" if pdf_path else "not_checked",
            verification_reason=diagnostics.get("issue", reason),
            verified_at=datetime.now().isoformat(timespec="seconds") if verified else "",
            sha256=diagnostics.get("sha256", ""),
        ))

    total = len(manifest_items)
    downloaded_count = sum(1 for item in manifest_items if item.status == "downloaded")
    unresolved_count = total - downloaded_count
    readiness = "complete" if total and unresolved_count == 0 else "partial" if downloaded_count else "blocked"
    buckets = _recovery_buckets(effective_failure_reasons)
    publisher_summary = build_publisher_summary(manifest_items)
    domain_summary = build_domain_summary(manifest_items, item_domains)
    manifest = Step5DownloadManifest(
        run_id=run_id,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        readiness=readiness,
        recommended_next_step=_recommended_next_step(readiness, buckets),
        summary={
            "total": total,
            "downloaded": downloaded_count,
            "remaining": unresolved_count,
            "failed_or_pending": unresolved_count,
            "status_counts": {
                status: sum(1 for item in manifest_items if item.status == status)
                for status in sorted({item.status for item in manifest_items})
            },
            "publisher_summary": publisher_summary,
            "domain_summary": domain_summary,
            "preflight": preflight_summary or {},
        },
        recovery_buckets=buckets,
        items=manifest_items,
    )
    manifest_path = os.path.join(output_dir, "download_manifest.json")
    attempts_path = os.path.join(output_dir, "download_attempts.jsonl")
    pool_path = os.path.join(output_dir, "pdf-附件池索引.json")
    write_step5_download_manifest(manifest_path, manifest)
    append_jsonl_durable(attempts_path, attempts_rows)
    write_pdf_pool_index(pool_path, build_pdf_pool_index(output_dir, [item.__dict__ for item in manifest_items]))
    debug_path = write_failure_snapshots(output_dir, manifest_items)
    paths = {"manifest": manifest_path, "attempts": attempts_path, "pdf_pool": pool_path}
    if debug_path:
        paths["debug_snapshots"] = debug_path
    return paths


def _input_items_for_step5_manifest(dois: list[str], chinese_papers: list[dict]) -> list[dict]:
    items = []
    for doi in dois:
        items.append({"id": doi, "doi": doi, "publisher": _publisher_for_identifier(doi)})
    for paper in chinese_papers:
        identifier = paper.get("doi") or paper.get("source_id") or paper.get("title", "")
        items.append({
            "id": identifier,
            "doi": paper.get("doi", ""),
            "title": paper.get("title", ""),
            "source": paper.get("source", ""),
            "source_id": paper.get("source_id", ""),
            "article_url": paper.get("article_url", ""),
            "publisher": paper.get("source", ""),
        })
    return items


def filter_local_pdf_hits(dois: list[str], chinese_papers: list[dict], output_dir: str) -> tuple[list[str], list[dict], list[str]]:
    downloaded: list[str] = []
    remaining_dois: list[str] = []
    for doi in dois:
        if _find_pdf_for_identifier(output_dir, doi):
            downloaded.append(doi)
        else:
            remaining_dois.append(doi)
    remaining_chinese: list[dict] = []
    for paper in chinese_papers:
        identifier = paper.get("doi") or paper.get("source_id") or paper.get("title", "")
        if identifier and _find_pdf_for_identifier(output_dir, identifier):
            downloaded.append(identifier)
        else:
            remaining_chinese.append(paper)
    if downloaded:
        print(f"  {OK} Local PDF index: {len(downloaded)} existing PDF(s) will be skipped")
    return remaining_dois, remaining_chinese, downloaded


def write_failed_doi_sidecar(output_dir: str, remaining: list[str],
                             failure_reasons: dict[str, str]) -> str:
    """Write structured failed DOI metadata for later replay and triage."""
    sidecar_path = os.path.join(output_dir, "failed_dois.json")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    for doi in remaining:
        pub = resolve_publisher(doi)
        payload["items"].append({
            "doi": doi,
            "publisher": pub.get("_key", "unknown") if pub else "unknown",
            "domain": pub.get("publisher_domain", "") if pub else "",
            "strategy": pub.get("strategy", "") if pub else "",
            "failure_reason": failure_reasons.get(doi, ""),
            "retry_hint": f"python3 scripts/unified_download_router.py --papers \"{doi}\" --output {output_dir}",
        })
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return sidecar_path


# ── Login Gates ──────────────────────────────────────────────────────────────

# Publishers that typically require institutional login for CDP download.
# OA publishers (direct_http strategy) are excluded.
# Sci-Hub and Chinese publishers are handled separately.
ENGLISH_LOGIN_STRATEGIES = {"generic", "ieee_cdp"}
ENGLISH_LOGIN_REQUIRED_REASONS = {
    "manual_confirmation_required",
    "manual_required",
    "captcha_required",
    "institution_login_required",
    "login_required",
    "login_wall",
    "access_denied",
    "pdf_probe_blocked",
    "pdf_probe_unknown",
}


def _safe_gate_input(prompt: str) -> Optional[str]:
    """Read gate input without collapsing host IO failures into explicit skip."""
    try:
        return input(prompt)
    except EOFError:
        print(f"\n{WARN} Interactive input unavailable in current host.")
        return None
    except KeyboardInterrupt:
        print(f"\n{WARN} Login confirmation interrupted.")
        return None


def _filter_login_required_dois(dois: list[str], failure_reasons: dict[str, str]) -> list[str]:
    """Return failed DOIs that should prompt an institutional-login retry."""
    return [
        doi for doi in dois
        if failure_reasons.get(doi) in ENGLISH_LOGIN_REQUIRED_REASONS
    ]


def _english_login_candidate_dois(dois: list[str],
                                  oa_hints: Optional[dict[str, dict]] = None) -> list[str]:
    """Return remaining English DOI(s) whose route may require institution login."""
    candidates: list[str] = []
    for doi in dois:
        c = classify_doi(doi)
        if c["strategy"] not in ENGLISH_LOGIN_STRATEGIES:
            continue
        if _is_oa_confirmed_or_whitelisted(doi, oa_hints):
            continue
        pub_cfg = c.get("publisher_config", {}) or {}
        if pub_cfg.get("requires_auth", "institution") == "none":
            continue
        candidates.append(doi)
    return candidates


def _english_login_dois_without_trusted_session(dois: list[str], port: int,
                                                oa_hints: Optional[dict[str, dict]] = None) -> list[str]:
    """Return login candidates lacking a trusted PDF/article probe signal.

    Cookie presence is intentionally treated as weak. A publisher is trusted
    only when its current access probe reports ``ok``.
    """
    pending: list[str] = []
    session_cache: dict[str, bool] = {}
    for doi in _english_login_candidate_dois(dois, oa_hints=oa_hints):
        c = classify_doi(doi)
        pub_cfg = c.get("publisher_config", {}) or {}
        pub_key = c.get("publisher", "unknown")
        if pub_key not in session_cache:
            try:
                signal = describe_publisher_session(port, pub_cfg)
                session_cache[pub_key] = signal.get("probe_status") == "ok"
            except Exception:
                session_cache[pub_key] = False
        if not session_cache[pub_key]:
            pending.append(doi)
    return pending


def _publisher_login_url(pub_cfg: dict) -> str:
    """Return the configured login URL, falling back to the publisher domain."""
    login_url = str(pub_cfg.get("login_url", "")).strip()
    if login_url:
        return login_url
    domain = str(pub_cfg.get("publisher_domain", "")).strip()
    if not domain:
        return ""
    if domain.startswith(("http://", "https://")):
        return domain
    return f"https://{domain}/"


def _english_login_publishers(dois: list[str]) -> dict[str, dict]:
    """Return unique English-login publishers that need user login tabs."""
    publishers: dict[str, dict] = {}
    for doi in _english_login_candidate_dois(dois):
        info = classify_doi(doi)
        pub_key = info.get("publisher", "unknown")
        pub_cfg = info.get("publisher_config", {}) or {}
        if pub_key not in publishers:
            publishers[pub_key] = pub_cfg
    return publishers


def open_english_login_tabs(port: int, dois: list[str]) -> dict[str, list[str]]:
    """Open one login tab per publisher needed by the given English DOI list."""
    opened: list[str] = []
    failed: list[str] = []
    publishers = _english_login_publishers(dois)

    for pub_key, pub_cfg in sorted(publishers.items()):
        url = _publisher_login_url(pub_cfg)
        domain = pub_cfg.get("publisher_domain", "?")
        if not url:
            failed.append(f"{pub_key} ({domain}) - missing login_url/publisher_domain")
            continue
        try:
            _, tab_id = create_tab(port, url)
        except Exception as exc:
            failed.append(f"{pub_key} ({url}) - {exc}")
            continue
        if not tab_id:
            failed.append(f"{pub_key} ({url}) - CDP did not return a tab id")
            continue
        opened.append(f"{pub_key} ({url})")

    return {"opened": opened, "failed": failed}


def _chinese_login_publishers(chinese_papers: list[dict]) -> dict[str, dict]:
    """Return unique CNKI/Wanfang publishers needed by the Chinese paper list."""
    publishers: dict[str, dict] = {}
    for paper in chinese_papers:
        source = str(paper.get("source", "")).strip().lower()
        if source not in CHINESE_PUBLISHERS or source in publishers:
            continue
        publishers[source] = _PUBLISHER_CONFIGS.get(source, {})
    return publishers


def open_chinese_login_tabs(port: int, chinese_papers: list[dict]) -> dict[str, list[str]]:
    """Open one login tab per Chinese literature source needed by this batch."""
    opened: list[str] = []
    failed: list[str] = []
    publishers = _chinese_login_publishers(chinese_papers)

    for source, pub_cfg in sorted(publishers.items(), key=lambda item: CHINESE_SOURCE_PRIORITY.get(item[0], 99)):
        url = _publisher_login_url(pub_cfg)
        domain = pub_cfg.get("publisher_domain", "?")
        if not url:
            failed.append(f"{source} ({domain}) - missing login_url/publisher_domain")
            continue
        try:
            _, tab_id = create_tab(port, url)
        except Exception as exc:
            failed.append(f"{source} ({url}) - {exc}")
            continue
        if not tab_id:
            failed.append(f"{source} ({url}) - CDP did not return a tab id")
            continue
        opened.append(f"{source} ({url})")

    return {"opened": opened, "failed": failed}


def _print_opened_login_tabs(tab_result: dict[str, list[str]]) -> None:
    if not (tab_result.get("opened") or tab_result.get("failed")):
        return
    print("CDP Chrome opened the login tabs needed for this batch:")
    for item in tab_result.get("opened", []):
        print(f"  {OK} {item}")
    for item in tab_result.get("failed", []):
        print(f"  {WARN} {item}")


def _print_login_choice_prompt() -> None:
    print("已打开本轮需要登录的网站。")
    print("只有部分权限也选 1；无权限论文会在下载结果中单独记录。")
    print("Choose one option:")
    print("  1) 已登录，继续")
    print("  2) 跳过登录")
    print("  3) 稍后重试")


def _print_chinese_login_choice_prompt() -> None:
    print("已打开本轮需要登录的网站。")
    print("只有部分权限也输入完整确认短语；无权限论文会在下载结果中单独记录。")
    print("为避免宿主或 agent 误触发，中文 CNKI/万方门控不接受数字 1/2/3。")
    print("Choose one option by typing the full phrase:")
    print("  已登录继续")
    print("  跳过登录")
    print("  稍后重试")


def write_login_checkpoint(output_dir: str, stage: str, dois: list[str],
                           failure_reasons: dict[str, str]) -> str:
    """Write a re-runnable login checkpoint for remaining English CDP items."""
    path = os.path.join(output_dir, "login_checkpoint.json")
    items = []
    for doi in dois:
        info = classify_doi(doi)
        pub_cfg = info.get("publisher_config", {}) or {}
        items.append({
            "doi": doi,
            "publisher": info.get("publisher", "unknown"),
            "strategy": info.get("strategy", "unknown"),
            "domain": pub_cfg.get("publisher_domain", ""),
            "failure_reason": failure_reasons.get(doi, ""),
        })
    payload = {
        "checkpoint_type": "publisher_login",
        "status": "pending_user_login",
        "stage": stage,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "items": items,
        "rerun_hint": "python3 scripts/unified_download_router.py --resume-login-checkpoint paper-temp/login_checkpoint.json --output paper-temp/ --confirmed",
    }
    atomic_write_json(path, payload)
    return path


def write_chinese_login_checkpoint(
    output_dir: str,
    papers: list[dict],
    failure_reasons: Optional[dict[str, str]] = None,
) -> str:
    """Write a re-runnable checkpoint for pending CNKI/Wanfang papers."""
    path = os.path.join(output_dir, "chinese_login_checkpoint.json")
    os.makedirs(output_dir, exist_ok=True)
    failure_reasons = failure_reasons or {}
    items = []
    for idx, paper in enumerate(papers, start=1):
        paper_id = paper.get("doi") or paper.get("source_id") or paper.get("title", f"paper_{idx}")
        items.append({
            "source": paper.get("source", ""),
            "title": paper.get("title", f"paper_{idx}"),
            "doi": paper.get("doi", paper.get("source_id", "")),
            "source_id": paper.get("source_id", ""),
            "article_url": paper.get("article_url", ""),
            "failure_reason": paper.get("failure_reason") or failure_reasons.get(paper_id) or "pending_user_login",
        })
    status = "pending_user_login"
    item_reasons = {item.get("failure_reason", "") for item in items}
    if item_reasons and item_reasons == {"captcha_required"}:
        status = "pending_captcha_verification"
    payload = {
        "checkpoint_type": "chinese_publisher_login",
        "status": status,
        "stage": "chinese_cdp_login",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "items": items,
        "rerun_hint": "python3 scripts/unified_download_router.py --resume-chinese-login-checkpoint paper-temp/chinese_login_checkpoint.json --output paper-temp/ --require-login-confirm",
    }
    atomic_write_json(path, payload)
    return path


def resolve_login_checkpoint(checkpoint_path: str | Path, *, downloaded: list[str], remaining: list[str]) -> None:
    """Close a checkpoint without deleting its recovery audit trail."""
    path = Path(checkpoint_path)
    if not path.exists() or remaining:
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    payload["status"] = "resolved"
    payload["resolved_at"] = datetime.now().isoformat(timespec="seconds")
    payload["resolved_items"] = list(dict.fromkeys(downloaded))
    atomic_write_json(path, payload)


def resume_from_chinese_login_checkpoint(checkpoint_path: str, output_dir: str,
                                         port: int,
                                         confirmed_login: bool = False) -> tuple[list[str], list[str]]:
    """Backward-compatible checkpoint resume without failure-reason sidecar."""
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    papers = [
        item for item in payload.get("items", [])
        if item.get("source") in {"cnki", "wanfang"} and item.get("article_url")
    ]
    papers = sort_chinese_papers_for_download(papers)
    if not papers:
        return [], []

    gate = show_chinese_login_gate(papers, port=port, confirmed_login=confirmed_login)
    if gate is True:
        downloaded, remaining = run_chinese_round(papers, output_dir, port, confirmed_login=confirmed_login)
        resolve_login_checkpoint(checkpoint_path, downloaded=downloaded, remaining=remaining)
        return downloaded, remaining
    if gate is False:
        print("Chinese download skipped by user.")
        return [], [paper.get("doi") or paper.get("title", "") for paper in papers]

    refreshed = write_chinese_login_checkpoint(output_dir, papers)
    print(f"{WARN} Chinese login still pending; checkpoint refreshed: {refreshed}")
    return [], [paper.get("doi") or paper.get("title", "") for paper in papers]


def resume_from_chinese_login_checkpoint_with_reasons(
    checkpoint_path: str, output_dir: str, port: int,
    confirmed_login: bool = False
) -> tuple[list[str], list[str], dict[str, str]]:
    """Resume only the CNKI/Wanfang papers stored in a Chinese login checkpoint."""
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    papers = [
        item for item in payload.get("items", [])
        if item.get("source") in {"cnki", "wanfang"} and item.get("article_url")
    ]
    papers = sort_chinese_papers_for_download(papers)
    if not papers:
        return [], [], {}

    gate = show_chinese_login_gate(papers, port=port, confirmed_login=confirmed_login)
    if gate is True:
        downloaded, remaining, reasons = run_chinese_round_with_reasons(
            papers,
            output_dir,
            port,
            confirmed_login=confirmed_login,
        )
        resolve_login_checkpoint(checkpoint_path, downloaded=downloaded, remaining=remaining)
        return downloaded, remaining, reasons
    if gate is False:
        print("Chinese download skipped by user.")
        remaining = [paper.get("doi") or paper.get("title", "") for paper in papers]
        return [], remaining, {paper_id: "login_skipped_by_user" for paper_id in remaining}

    refreshed = write_chinese_login_checkpoint(output_dir, papers)
    print(f"{WARN} Chinese login still pending; checkpoint refreshed: {refreshed}")
    remaining = [paper.get("doi") or paper.get("title", "") for paper in papers]
    return [], remaining, {paper_id: "pending_user_login" for paper_id in remaining}


def prepare_chinese_round_with_login_gate(papers: list[dict], output_dir: str,
                                          port: int = CDP_PORT,
                                          confirmed_login: bool = False) -> bool:
    """Return True only when Chinese login was explicitly confirmed."""
    gate = show_chinese_login_gate(papers, port=port, confirmed_login=confirmed_login)
    if gate is True:
        return True
    if gate is False:
        print("Chinese download skipped by user.")
        return False

    checkpoint = write_chinese_login_checkpoint(output_dir, papers)
    print(f"{WARN} Chinese login pending; checkpoint written: {checkpoint}")
    return False


def _post_confirmed_login_failure_reason(reason: str) -> str:
    """Collapse login-gate reasons after the user already confirmed login."""
    if reason in {
        "manual_confirmation_required",
        "manual_required",
        "login_required",
        "login_wall",
        "pdf_probe_blocked",
        "pdf_probe_unknown",
    }:
        return "generic_failed"
    return reason


def resume_from_login_checkpoint(checkpoint_path: str, output_dir: str, port: int,
                                 include_si: bool = False,
                                 confirmed_login: bool = False
                                 ) -> tuple[list[str], list[str], list[dict], dict[str, str]]:
    """Resume only the English DOI subset stored in a login checkpoint."""
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    dois = [
        item.get("doi", "").strip()
        for item in payload.get("items", [])
        if item.get("doi", "").strip()
    ]
    if not dois:
        return [], [], [], {}

    _print_opened_login_tabs(open_english_login_tabs(port, dois))
    downloaded, remaining, failure_reasons = run_generic_round(
        dois, output_dir, port, include_si=include_si
    )
    round_results = [{"round": "Generic CDP (resume login checkpoint)", "downloaded": downloaded}]

    if confirmed_login:
        failure_reasons = {
            doi: _post_confirmed_login_failure_reason(reason)
            for doi, reason in failure_reasons.items()
        }
        resolve_login_checkpoint(checkpoint_path, downloaded=downloaded, remaining=remaining)
        return downloaded, remaining, round_results, failure_reasons

    login_retry_dois = _filter_login_required_dois(remaining, failure_reasons)
    if login_retry_dois:
        failure_reasons.update({
            doi: "pending_user_login"
            for doi in login_retry_dois
        })
        refreshed = write_login_checkpoint(
            output_dir,
            stage="english_cdp_retry_resume",
            dois=login_retry_dois,
            failure_reasons=failure_reasons,
        )
        print(f"{WARN} Some resumed DOI(s) still require login; checkpoint refreshed: {refreshed}")

    resolve_login_checkpoint(checkpoint_path, downloaded=downloaded, remaining=remaining)
    return downloaded, remaining, round_results, failure_reasons


def show_chinese_login_gate(chinese_papers: list[dict],
                            port: int = CDP_PORT,
                            confirmed_login: bool = False) -> Optional[bool]:
    """Display Chinese login gate.

    Returns:
      True  -> user explicitly confirmed login
      False -> user explicitly skipped
      None  -> host cannot read input or user deferred
    """
    if not chinese_papers:
        return True
    from generic_publisher_downloader import _PUBLISHER_CONFIGS

    pubs: list[str] = []
    for paper in chinese_papers:
        source = paper.get("source", "").lower()
        if source in ("cnki", "wanfang"):
            cfg = _PUBLISHER_CONFIGS.get(source, {})
            domain = cfg.get("publisher_domain", "?")
            pubs.append(f"  - {source} ({domain})")
    if not pubs:
        return True
    tab_result = open_chinese_login_tabs(port, chinese_papers)

    print(f"\n{'='*60}")
    print("Chinese Login Gate - CNKI / Wanfang")
    print(f"{'='*60}")
    print()
    print("Please verify CNKI/Wanfang login in the CDP browser.")
    print()
    for p in sorted(set(pubs)):
        print(p)
    print()
    _print_opened_login_tabs(tab_result)
    print()
    _print_chinese_login_choice_prompt()
    print()
    if confirmed_login:
        print(f"{OK} --confirmed supplied: skipping Chinese login prompt and starting CNKI/Wanfang CDP.\n")
        return True
    raw_resp = _safe_gate_input("输入完整短语: ")
    if raw_resp is None:
        print("\nChinese login requires checkpoint/resume rather than treating this as skip.")
        return None
    resp = raw_resp.strip().lower()
    if resp in ("已登录继续", "登录完成继续", "continue"):
        print(f"{OK} Chinese login confirmed - starting CNKI/Wanfang CDP.\n")
        return True
    if resp in ("跳过登录", "skip"):
        print(f"{SKIP} Chinese login skipped - continuing with other download paths.\n")
        return False
    if resp in ("稍后重试", "写checkpoint", "checkpoint"):
        print("Chinese login deferred - checkpoint required before rerun.\n")
        return None
    print(f"{WARN} Unrecognized response - checkpoint required before rerun.\n")
    return None


def show_english_login_gate(dois: list[str], skip_sd: bool = False,
                            port: int = CDP_PORT,
                            interactive: bool = True) -> Optional[bool]:
    """Display English publisher login gate for remaining CDP papers.

    Only triggers for English routes that need institutional login.
    Sci-Hub, OA/direct HTTP, and Chinese are excluded (handled separately).
    Returns:
      True  -> user explicitly confirmed login
      False -> user explicitly skipped or deferred
      None  -> host cannot continue interactive input
    """
    # Classify remaining DOIs to find CDP-dependent publishers
    login_publishers: dict[str, set[str]] = {}  # strategy -> set of publisher keys
    seen = set()

    for doi in dois:
        c = classify_doi(doi)
        strategy = c["strategy"]
        if strategy not in ENGLISH_LOGIN_STRATEGIES:
            continue
        pub_key = c["publisher"]
        pub_config = c.get("publisher_config", {})
        domain = pub_config.get("publisher_domain", "?") if pub_config else "?"
        if pub_key not in seen:
            seen.add(pub_key)
            login_publishers.setdefault(strategy, set()).add(f"{pub_key} ({domain})")

    if not login_publishers:
        print(f"\n{OK} No English publishers requiring institutional login.")
        return True

    tab_result = open_english_login_tabs(port, dois)

    print(f"\n{'='*60}")
    print("English Login Gate - Institutional Access Required")
    print(f"{'='*60}")
    print()
    print("The following publishers require institutional login before download:")
    print()
    for strategy, pubs in sorted(login_publishers.items()):
        label = {
            "generic": "Generic CDP",
            "ieee_cdp": "IEEE CDP",
        }.get(strategy, strategy)
        print(f"  [{label}]")
        for p in sorted(pubs):
            print(f"    - {p}")
        print()
    _print_opened_login_tabs(tab_result)
    print()
    print("  1. Use the opened tabs in the CDP Chrome window")
    print("  2. Complete institutional SSO login for each opened publisher")
    print("  3. Verify the login persists (check for 'Access provided by...' badges)")
    print()
    _print_login_choice_prompt()
    print()
    print(f"{'='*60}")
    if not interactive:
        print(f"{WARN} Non-interactive mode: login checkpoint required before rerun.\n")
        return None
    raw_resp = _safe_gate_input("\nEnter 1/2/3: ")
    if raw_resp is None:
        print("\nEnglish login requires checkpoint/resume rather than treating this as skip.")
        return None
    resp = raw_resp.strip().lower()
    if resp in ("1", "已登录", "y", "yes", "done", "logged in", "继续", "go"):
        print(f"{OK} Login confirmed - proceeding with English CDP.\n")
        return True
    elif resp in ("2", "q", "quit", "exit", "n", "no", "skip", "无账号", "没有账号"):
        print(f"{SKIP} English institutional login skipped - continuing without login-only publishers.")
        return False
    elif resp in ("3", "later", "retry", "稍后", "重试", "稍后重试"):
        print("English login deferred - checkpoint required before rerun.\n")
        return None
    else:
        print(f"{WARN} Unrecognized response - checkpoint required before rerun.\n")
        return None


# ── Session Check ───────────────────────────────────────────────────────────

def check_all_sessions(port: int):
    """Print session status for all known publishers."""
    def _readiness_label(signal: dict) -> str:
        if signal.get("probe_status") == "ok":
            return "可直接尝试下载"
        if signal.get("probe_status") == "blocked":
            return "需要先人工登录/验证"
        return "信号不足，需实际下载验证"

    print("=== Publisher Session Check ===")
    print(f"{'Publisher':20s} {'Domain':35s} {'结论':16s} {'Signal':16s} {'Probe'}")
    print("-" * 128)

    for key, cfg in _PUBLISHER_CONFIGS.items():
        signal = describe_publisher_session(port, cfg)
        icon = OK if signal["has_session"] else FAIL
        probe = f"{signal['probe_status']}: {signal['probe_reason']}"
        signal_label = f"{signal['signal_strength']} ({signal['cookie_count']})"
        readiness = _readiness_label(signal)
        print(f"  {icon} {key:18s} | {signal['domain']:35s} | {readiness:16s} | {signal_label:16s} | {probe}")

    # Also check generic CDP browser availability
    if check_cdp(port):
        print(f"\n  {OK} CDP Chrome running on port {port}")
    else:
        print(f"\n  {FAIL} CDP Chrome NOT running on port {port}")
    print("  Note: cookie count is a weak signal; only PDF/article probe can confirm access.")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    configure_console_output()

    parser = argparse.ArgumentParser(
        description="Unified PDF download router - auto-routes DOI to optimal strategy."
    )
    parser.add_argument("input", nargs="?", help="Input file: DOI list, Markdown literature table, or BibTeX")
    parser.add_argument("--papers", help="Comma-separated list of DOIs (inline)")
    parser.add_argument("--doi-file", help="Plain text file with one DOI per line")
    parser.add_argument("--port", type=int, default=CDP_PORT, help=f"CDP Chrome debug port (default: {CDP_PORT})")
    parser.add_argument("--browser", choices=("chrome", "edge"),
                        default=os.environ.get("CDP_BROWSER", "chrome"),
                        help="CDP browser for single-browser rounds (default: chrome; use edge to reuse Edge login)")
    parser.add_argument("--sd-browser", choices=("chrome", "edge", "auto"),
                        help=argparse.SUPPRESS)
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: input file sibling paper-temp/, or current working directory paper-temp/)",
    )
    parser.add_argument("--test", help="Test a single DOI (show routing decision + download)")
    parser.add_argument("--check-session", action="store_true", help="Check publisher sessions and exit")
    parser.add_argument("--skip-scihub", action="store_true", help="Skip Sci-Hub round (post-2021 papers)")
    parser.add_argument("--skip-oa-fast", action="store_true", help="Skip public OA fast round and go directly to CDP")
    parser.add_argument("--skip-sd", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--skip-ieee", action="store_true", help="Skip IEEE round")
    parser.add_argument("--include-si", action="store_true", help="Download supplementary info where available")
    parser.add_argument("--dry-run", action="store_true", help="Show routing decisions without downloading")
    parser.add_argument("--require-login-confirm", action="store_true",
                        help="Pause before CDP rounds to prompt user to complete institutional login")
    parser.add_argument("--chinese-input", help="Chinese papers input: JSON file or Markdown literature table")
    parser.add_argument("--workflow-results", help="Step 4 workflow search results JSON (workflow-contracts.v1)")
    parser.add_argument("--download-manifest", help="Direct download manifest JSON (workflow-contracts.v1)")
    parser.add_argument("--skip-chinese", action="store_true", help="Skip Chinese CDP round")
    parser.add_argument("--parallel-phase1", action="store_true",
                        help="Opt in to running Sci-Hub and Chinese CDP concurrently. Default is serial for CDP reliability.")
    parser.add_argument("--test-cnki", help="Test single CNKI paper download (provide article URL)")
    parser.add_argument("--test-wanfang", help="Test single Wanfang paper download (provide article URL)")
    parser.add_argument("--resume-login-checkpoint", nargs="?", const="AUTO",
                        help="Resume English DOI download from login_checkpoint.json (default: <output>/login_checkpoint.json)")
    parser.add_argument("--confirmed", "--assume-login-confirmed", "--confirmed-login",
                        dest="confirmed_login", action="store_true",
                        help="Skip script-side English login prompts because the outer host/user already confirmed login; also applies to --resume-login-checkpoint")
    parser.add_argument("--resume-chinese-login-checkpoint", nargs="?", const="AUTO",
                        help="Resume CNKI/Wanfang download from chinese_login_checkpoint.json (default: <output>/chinese_login_checkpoint.json)")

    args = parser.parse_args()
    sd_browser = args.sd_browser or args.browser
    args.output = resolve_output_dir(args)

    # --check-session
    if args.check_session:
        check_all_sessions(args.port)
        return

    if args.resume_login_checkpoint:
        checkpoint_path = args.resume_login_checkpoint
        if checkpoint_path == "AUTO":
            checkpoint_path = os.path.join(args.output, "login_checkpoint.json")
        if not os.path.exists(checkpoint_path):
            print(f"ERROR: login checkpoint not found: {checkpoint_path}")
            sys.exit(1)
        lock_path = acquire_or_exit_step5_download_lock("resume_english_login_checkpoint", args.port)
        if not ensure_cdp_running(args.port, browser=args.browser):
            print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
            sys.exit(1)
        if not check_required_deps():
            sys.exit(1)

        try:
            downloaded, remaining, round_results, failure_reasons = resume_from_login_checkpoint(
                checkpoint_path,
                args.output,
                args.port,
                include_si=args.include_si,
                confirmed_login=args.confirmed_login,
            )
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            all_dois = [
                item.get("doi", "").strip()
                for item in payload.get("items", [])
                if item.get("doi", "").strip()
            ]
            generate_download_log(args.output, all_dois, round_results, failure_reasons)
            write_step5_outputs(
                args.output,
                _input_items_for_step5_manifest(all_dois, []),
                downloaded,
                remaining,
                round_results,
                failure_reasons,
            )
            if remaining:
                failed_path = os.path.join(args.output, "failed_dois.txt")
                with open(failed_path, "w", encoding="utf-8") as f:
                    for doi in remaining:
                        pub = resolve_publisher(doi)
                        pub_name = pub.get("_key", "unknown") if pub else "unknown"
                        reason = failure_reasons.get(doi, "")
                        suffix = f" | {reason}" if reason else ""
                        f.write(f"{doi}  # {pub_name}{suffix}\n")
                write_failed_doi_sidecar(args.output, remaining, failure_reasons)
            print(f"\n{DONE} Resume complete - {OK} {len(downloaded)}/{len(all_dois)}, {FAIL} {len(remaining)} remaining")
        finally:
            release_step5_download_lock(lock_path)
        return

    if args.resume_chinese_login_checkpoint:
        checkpoint_path = args.resume_chinese_login_checkpoint
        if checkpoint_path == "AUTO":
            checkpoint_path = os.path.join(args.output, "chinese_login_checkpoint.json")
        if not os.path.exists(checkpoint_path):
            print(f"ERROR: Chinese login checkpoint not found: {checkpoint_path}")
            sys.exit(1)
        lock_path = acquire_or_exit_step5_download_lock("resume_chinese_login_checkpoint", args.port)
        if not ensure_cdp_running(args.port, browser=args.browser):
            print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
            sys.exit(1)
        if not check_required_deps():
            sys.exit(1)

        try:
            downloaded, remaining, failure_reasons = resume_from_chinese_login_checkpoint_with_reasons(
                checkpoint_path,
                args.output,
                args.port,
                confirmed_login=args.confirmed_login,
            )
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            all_items = [
                item.get("doi") or item.get("title", "")
                for item in payload.get("items", [])
                if item.get("doi") or item.get("title")
            ]
            generate_download_log(
                args.output,
                all_items,
                [{"round": "Chinese CDP (resume login checkpoint)", "downloaded": downloaded}],
                failure_reasons,
            )
            write_step5_outputs(
                args.output,
                _input_items_for_step5_manifest([], payload.get("items", [])),
                downloaded,
                remaining,
                [{"round": "Chinese CDP (resume login checkpoint)", "downloaded": downloaded}],
                failure_reasons,
            )
            print(f"\n{DONE} Chinese resume complete - {OK} {len(downloaded)}/{len(all_items)}, {FAIL} {len(remaining)} remaining")
        finally:
            release_step5_download_lock(lock_path)
        return

    # --test
    if args.test:
        doi = args.test.strip()
        info = classify_doi(doi)
        print("=== DOI Router - Test Mode ===")
        print(f"DOI:       {doi}")
        print(f"Publisher: {info['publisher']}")
        print(f"Strategy:  {info['strategy']}")
        print(f"Est. year: {info['year'] or 'unknown'}")

        domain = info['publisher_config'].get('publisher_domain', 'N/A')
        notes = info['publisher_config'].get('notes', '')
        known = info['publisher_config'].get('known_issues', '')
        print(f"Domain:    {domain}")
        if notes:
            print(f"Notes:     {notes}")
        if known:
            print(f"Issues:    {known}")

        if info['strategy'] == "skip":
            print(f"\n{SKIP} SKIPPED - automation not possible for this publisher")
            return

        if info['strategy'] == "ieee_cdp":
            print(f"\n{ARROW} Delegated to {info['strategy']} script (use dedicated downloader).")
            return

        if args.dry_run:
            print(f"\n[DRY RUN] Would use {info['strategy']} strategy.")
            return

        # Actual download attempt
        lock_path = acquire_or_exit_step5_download_lock("test_doi", args.port)
        if not ensure_cdp_running(args.port, browser=args.browser):
            print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
            sys.exit(1)

        try:
            print(f"\nDownloading via {info['strategy']} strategy...")
            result_path, status, pub = generic_download_one(
                args.port, doi, args.output, include_si=args.include_si
            )
            if result_path and status == "ok":
                size_kb = os.path.getsize(result_path) // 1024
                print(f"{OK} Downloaded: {result_path} ({size_kb} KB)")
            elif status == "si_only":
                print(f"{WARN} SI downloaded only (no PDF)")
            else:
                print(f"{FAIL} Failed: status={status}")
        finally:
            release_step5_download_lock(lock_path)
        return

    # --test-cnki (single CNKI paper via article URL)
    if args.test_cnki:
        article_url = args.test_cnki.strip()
        if not article_url.startswith("http"):
            print(f"ERROR: --test-cnki requires a full article URL (https://...)")
            sys.exit(1)
        lock_path = acquire_or_exit_step5_download_lock("test_cnki", args.port)
        print("=== Chinese Download - Test Mode (CNKI) ===")
        print(f"URL: {article_url}")
        if not ensure_cdp_running(args.port, browser=args.browser):
            print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
            sys.exit(1)
        try:
            print(f"\nDownloading via CNKI CDP...")
            result_path, status, pub = generic_download_one(
                args.port, f"cnki.test.{hashlib.md5(article_url.encode()).hexdigest()[:8]}",
                args.output, article_url=article_url
            )
            if result_path and status == "ok":
                size_kb = os.path.getsize(result_path) // 1024
                print(f"{OK} Downloaded: {result_path} ({size_kb} KB)")
            else:
                print(f"{FAIL} Failed: status={status}")
        finally:
            release_step5_download_lock(lock_path)
        return

    # --test-wanfang (single Wanfang paper via article URL)
    if args.test_wanfang:
        article_url = args.test_wanfang.strip()
        if not article_url.startswith("http"):
            print(f"ERROR: --test-wanfang requires a full article URL (https://...)")
            sys.exit(1)
        lock_path = acquire_or_exit_step5_download_lock("test_wanfang", args.port)
        print("=== Chinese Download - Test Mode (Wanfang) ===")
        print(f"URL: {article_url}")
        if not ensure_cdp_running(args.port, browser=args.browser):
            print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
            sys.exit(1)
        try:
            print(f"\nDownloading via Wanfang CDP...")
            result_path, status, pub = generic_download_one(
                args.port, f"wanfang.test.{hashlib.md5(article_url.encode()).hexdigest()[:8]}",
                args.output, article_url=article_url
            )
            if result_path and status == "ok":
                size_kb = os.path.getsize(result_path) // 1024
                print(f"{OK} Downloaded: {result_path} ({size_kb} KB)")
            else:
                print(f"{FAIL} Failed: status={status}")
        finally:
            release_step5_download_lock(lock_path)
        return

    workflow_items = []
    if args.workflow_results:
        workflow_items.extend(download_items_from_search_records(load_search_records(args.workflow_results)))
    if args.download_manifest:
        workflow_items.extend(load_download_manifest(args.download_manifest))

    workflow_dois = dois_from_download_items(workflow_items)
    workflow_chinese_papers = as_chinese_papers(workflow_items)
    oa_hints = build_oa_hints_from_items(workflow_items)

    # Batch mode
    bibtex_chinese_papers: list[dict] = []
    if args.doi_file:
        dois = parse_doi_file(args.doi_file)
    elif args.input:
        dois = parse_input(args.input)
        bibtex_chinese_papers = parse_bibtex_chinese_papers(args.input)
        if bibtex_chinese_papers:
            chinese_dois = {
                p.get("doi", "").strip().lower()
                for p in bibtex_chinese_papers
                if p.get("doi")
            }
            dois = [d for d in dois if d.strip().lower() not in chinese_dois]
    elif args.papers:
        dois = [d.strip() for d in args.papers.split(",") if d.strip()]
    elif workflow_items:
        dois = workflow_dois
    elif args.chinese_input:
        dois = []  # Chinese-only mode, no English DOIs to parse
    else:
        parser.print_help()
        sys.exit(1)

    if not dois and not args.chinese_input and not workflow_chinese_papers:
        print("No DOIs or Chinese papers found.")
        sys.exit(1)

    # ── Parse Chinese papers ───────────────────────────────────────────
    chinese_papers: list[dict] = list(workflow_chinese_papers) + bibtex_chinese_papers
    if args.chinese_input:
        chinese_papers.extend(parse_chinese_papers(args.chinese_input))
    if chinese_papers:
        seen_chinese: dict[tuple[str, str], int] = {}
        deduped_chinese: list[dict] = []
        for paper in chinese_papers:
            key = (paper.get("source", ""), paper.get("doi", "") or paper.get("title", ""))
            if key in seen_chinese:
                existing = deduped_chinese[seen_chinese[key]]
                if not existing.get("article_url") or "doi.org/" in existing.get("article_url", ""):
                    if paper.get("article_url"):
                        existing.update(paper)
                continue
            seen_chinese[key] = len(deduped_chinese)
            deduped_chinese.append(paper)
        chinese_papers = deduped_chinese
        chinese_papers = sort_chinese_papers_for_download(chinese_papers)
        cnki_count = sum(1 for p in chinese_papers if p["source"] == "cnki")
        wf_count = sum(1 for p in chinese_papers if p["source"] == "wanfang")
        print(f"Chinese papers: {len(chinese_papers)} total ({cnki_count} CNKI + {wf_count} Wanfang)")
    elif args.chinese_input or args.workflow_results or args.download_manifest:
        print("No Chinese papers found in input.")

    # Deduplicate
    seen = set()
    unique_dois = []
    for d in dois:
        d_clean = d.strip().lower()
        if d_clean not in seen:
            seen.add(d_clean)
            unique_dois.append(d.strip())
    dois = unique_dois

    os.makedirs(args.output, exist_ok=True)

    # Print classification summary
    print(f"=== Unified Download Router ===")
    print(f"Total unique DOIs: {len(dois)}")
    print(f"Output directory:  {args.output}/")
    print(f"CDP port:          {args.port}")
    if chinese_papers:
        print(f"Chinese papers:    {len(chinese_papers)} "
              f"({sum(1 for p in chinese_papers if p['source']=='cnki')} CNKI + "
              f"{sum(1 for p in chinese_papers if p['source']=='wanfang')} Wanfang)")
    print()

    # Initialize classified list (may be empty for Chinese-only mode)
    classified = [classify_doi(d) for d in dois]

    # Build classified entries for Chinese papers (for routing display + login gate)
    if chinese_papers:
        for p in chinese_papers:
            if p.get("article_url"):
                c = classify_doi(p.get("doi", ""))
                c["strategy"] = "chinese_cdp"
                c["publisher"] = p["source"]
                classified.append(c)

    # Group classified entries by strategy for display
    by_strategy: dict[str, list] = {}
    for c in classified:
        s = c["strategy"]
        by_strategy.setdefault(s, []).append(c)

    print("Routing summary:")
    strategy_labels = {
        "scihub_only": "Sci-Hub (<=2021)",
        "ieee_cdp": "IEEE CDP",
        "generic": "Generic CDP",
        "chinese_cdp": "Chinese CDP (CNKI/Wanfang)",
        "direct_http": "Direct HTTP",
        "skip": "SKIP (unavailable)",
    }
    for s in STRATEGY_ORDER:
        items = by_strategy.get(s, [])
        if items:
            label = strategy_labels.get(s, s)
            print(f"  {label:25s}: {len(items):3d} papers")
    print_english_oa_hint_summary(dois, oa_hints)

    manifest_input_items = _input_items_for_step5_manifest(dois, chinese_papers)
    if args.dry_run:
        total = sum(1 for c in classified if c["strategy"] != "skip")
        print(f"\n[DRY RUN] Would download {total} papers "
              f"({sum(1 for c in classified if c['strategy']=='chinese_cdp')} Chinese)")
        preflight_summary = build_step5_preflight_summary(
            manifest_input_items,
            args.output,
            args.port,
            args.browser,
            probe_cdp=False,
        )
        print_step5_preflight_summary(preflight_summary)
        dry_run_paths = write_step5_dry_run_outputs(
            args.output,
            manifest_input_items,
            preflight_summary,
        )
        print(f"  Manifest:        {dry_run_paths['manifest']}")
        print(f"  Preflight:       {dry_run_paths['preflight']}")
        if dry_run_paths.get("unresolved"):
            print(f"  Unresolved:      {dry_run_paths['unresolved']}")
        return

    lock_path = acquire_or_exit_step5_download_lock("batch_download", args.port)
    if args.parallel_phase1:
        print(f"\n{WARN} --parallel-phase1 is deprecated and ignored: English and Chinese downloads are serialized to protect the CDP browser.")

    all_log_ids = [item.get("doi") or item.get("id") or item.get("title", "") for item in manifest_input_items]
    all_log_ids = [item for item in all_log_ids if item]
    dois, chinese_papers, local_dl = filter_local_pdf_hits(dois, chinese_papers, args.output)
    preflight_summary = build_step5_preflight_summary(
        manifest_input_items,
        args.output,
        args.port,
        args.browser,
        local_hits=local_dl,
    )
    print_step5_preflight_summary(preflight_summary)

    # Check CDP only for early CDP work. English Generic CDP is checked after
    # OA fast so public PDFs do not get blocked by institutional browser setup.
    has_scihub_round = bool(dois) and not args.skip_scihub and bool(_scihub_eligible_dois(dois))
    if has_scihub_round and not ensure_cdp_running(args.port, browser=args.browser):
        print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
        print(f"Start {args.browser.title()} with:")
        print(f"  {sys.executable} scripts/start_cdp_browser.py --browser {args.browser} --port {args.port}")
        print("  macOS/Linux wrapper also supported: bash scripts/start_cdp_chrome.sh")
        sys.exit(1)

    if not check_required_deps():
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════════
    # Phase 1: Sci-Hub
    # Chinese CDP is intentionally delayed until all English DOI paths finish.
    # ═══════════════════════════════════════════════════════════════════

    scihub_dl: list[str] = []
    scihub_rem = list(dois)
    ch_dl: list[str] = []
    ch_rem: list[str] = []
    ch_failure_reasons: dict[str, str] = {}

    if has_scihub_round:
        scihub_dl, scihub_rem = run_scihub_round(list(dois), args.output, args.port)
    elif dois and args.skip_scihub:
        print(f"\n{SKIP} Round 1 (Sci-Hub): Skipped (--skip-scihub)")
    elif dois:
        print(f"\n{SKIP} Round 1 (Sci-Hub): No <= {SCI_HUB_CUTOFF_YEAR} papers to try.")

    # ═══════════════════════════════════════════════════════════════════
    # Phase 2: English login gate (after Sci-Hub) + English CDP
    # Only fires if papers remain after Sci-Hub and need CDP access.
    # ═══════════════════════════════════════════════════════════════════

    en_dl: list[str] = []
    en_rem = list(scihub_rem)
    en_results: list[dict] = []
    en_failure_reasons: dict[str, str] = {}
    oa_dl: list[str] = []
    oa_results: list[dict] = []
    oa_failure_reasons: dict[str, str] = {}
    ieee_dl: list[str] = []
    ieee_results: list[dict] = []

    if en_rem:
        if args.skip_oa_fast:
            print(f"\n{SKIP} Round 2 (OA fast): Skipped (--skip-oa-fast)")
        else:
            oa_dl, en_rem, oa_failure_reasons = run_oa_fast_round(
                en_rem,
                args.output,
                oa_hints=oa_hints,
            )
            oa_results.append({"round": "OA fast (public_pdf_verified)", "downloaded": oa_dl})

    if en_rem:
        # Check if remaining papers actually need CDP
        has_cdp = any(
            classify_doi(d)["strategy"] in ENGLISH_LOGIN_STRATEGIES
            for d in en_rem
        )
        if has_cdp and not ensure_cdp_running(args.port, browser=args.browser):
            print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
            print(f"Start {args.browser.title()} with:")
            print(f"  {sys.executable} scripts/start_cdp_browser.py --browser {args.browser} --port {args.port}")
            print("  macOS/Linux wrapper also supported: bash scripts/start_cdp_chrome.sh")
            sys.exit(1)
        preflight_login_dois: list[str] = []
        if has_cdp:
            if args.require_login_confirm:
                preflight_login_dois = _english_login_candidate_dois(en_rem, oa_hints=oa_hints)
            else:
                preflight_login_dois = _english_login_dois_without_trusted_session(
                    en_rem, args.port, oa_hints=oa_hints
                )
        if preflight_login_dois:
            print(f"\n{WARN} English CDP includes {len(preflight_login_dois)} login-sensitive item(s) without confirmed access.")
            print("  Login is checked before the grouped download loop to avoid per-paper login-wall failures.")
            if args.confirmed_login:
                print(f"{OK} --confirmed supplied: skipping preflight login prompt and attempting English CDP directly.")
                gate_result = True
            else:
                gate_result = show_english_login_gate(
                    preflight_login_dois,
                    skip_sd=args.skip_sd,
                    port=args.port,
                )
            non_login_dois = [doi for doi in en_rem if doi not in set(preflight_login_dois)]
            if gate_result is None:
                en_failure_reasons.update({doi: "pending_user_login" for doi in preflight_login_dois})
                checkpoint_path = write_login_checkpoint(
                    args.output,
                    stage="english_preflight_login",
                    dois=preflight_login_dois,
                    failure_reasons=en_failure_reasons,
                )
                print(f"English CDP login checkpoint written: {checkpoint_path}")
                en_rem = non_login_dois
            elif gate_result:
                # Login confirmed: keep IEEE + Generic items for their normal
                # execution order below (IEEE first, then Generic CDP).
                pass
            else:
                print("English CDP login-sensitive items skipped by user - OA/direct/skipped paths are preserved.")
                en_failure_reasons.update({doi: "login_skipped_by_user" for doi in preflight_login_dois})
                en_rem = non_login_dois

    if en_rem and not args.skip_ieee:
        has_ieee = any(classify_doi(d)["strategy"] == "ieee_cdp" for d in en_rem)
        if has_ieee:
            if not ensure_cdp_running(args.port, browser=args.browser):
                print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
                print(f"Start {args.browser.title()} with:")
                print(f"  {sys.executable} scripts/start_cdp_browser.py --browser {args.browser} --port {args.port}")
                print("  macOS/Linux wrapper also supported: bash scripts/start_cdp_chrome.sh")
                sys.exit(1)
            ieee_dl, en_rem = run_ieee_round(en_rem, args.output, args.port)
            ieee_results.append({"round": "IEEE CDP", "downloaded": ieee_dl})
    elif en_rem and args.skip_ieee:
        print(f"\n{SKIP} Round 3 (IEEE CDP): Skipped (--skip-ieee)")
    elif not scihub_rem:
        print(f"\n{DONE} Sci-Hub downloaded all papers! ({len(scihub_dl)}/{len(dois)})")

    if en_rem:
        generic_dl, en_rem, generic_results, generic_failure_reasons = run_english_cdp(
            en_rem, args.output, args.port,
            skip_sd=args.skip_sd, include_si=args.include_si,
            sd_browser=sd_browser
        )
        en_dl.extend(generic_dl)
        en_results.extend(generic_results)
        en_failure_reasons.update(generic_failure_reasons)

    en_dl = oa_dl + ieee_dl + en_dl
    en_results = oa_results + ieee_results + en_results
    en_failure_reasons = {**oa_failure_reasons, **en_failure_reasons}

    # ═══════════════════════════════════════════════════════════════════
    # Phase 3: Chinese login gate + Chinese CDP
    # Runs only after English DOI paths have finished or were explicitly skipped.
    # ═══════════════════════════════════════════════════════════════════

    english_login_pending = any(reason == "pending_user_login" for reason in en_failure_reasons.values())
    if chinese_papers and not args.skip_chinese and english_login_pending:
        print(f"\n{WARN} English login is still pending; Chinese CDP will wait until the English checkpoint is resumed.")
        print(f"  {ARROW} Resume English first: python3 scripts/unified_download_router.py --resume-login-checkpoint {os.path.join(args.output, 'login_checkpoint.json')} --output {args.output}/")
    else:
        if chinese_papers and not args.skip_chinese:
            if not ensure_cdp_running(args.port, browser=args.browser):
                print(f"\nERROR: CDP {args.browser.title()} not running on port {args.port}.")
                print(f"Start {args.browser.title()} with:")
                print(f"  {sys.executable} scripts/start_cdp_browser.py --browser {args.browser} --port {args.port}")
                print("  macOS/Linux wrapper also supported: bash scripts/start_cdp_chrome.sh")
                sys.exit(1)
            if args.require_login_confirm:
                if prepare_chinese_round_with_login_gate(
                    chinese_papers,
                    args.output,
                    port=args.port,
                    confirmed_login=args.confirmed_login,
                ):
                    if args.confirmed_login:
                        ch_dl, ch_rem, ch_failure_reasons = run_chinese_round_with_reasons(
                            chinese_papers,
                            args.output,
                            args.port,
                            confirmed_login=True,
                        )
                    else:
                        ch_dl, ch_rem, ch_failure_reasons = run_chinese_round_with_reasons(
                            chinese_papers,
                            args.output,
                            args.port,
                        )
            else:
                if args.confirmed_login:
                    ch_dl, ch_rem, ch_failure_reasons = run_chinese_round_with_reasons(
                        chinese_papers,
                        args.output,
                        args.port,
                        confirmed_login=True,
                    )
                else:
                    ch_dl, ch_rem, ch_failure_reasons = run_chinese_round_with_reasons(
                        chinese_papers,
                        args.output,
                        args.port,
                    )

    # ═══════════════════════════════════════════════════════════════════
    # Phase 4: Merge results from all phases
    # ═══════════════════════════════════════════════════════════════════

    all_downloaded = local_dl + scihub_dl + ch_dl + en_dl
    round_results = (
        ([{"round": "Local PDF index", "downloaded": local_dl}] if local_dl else []) +
        [{"round": "Sci-Hub", "downloaded": scihub_dl}] * (1 if scihub_dl else 0) +
        en_results +
        ([{"round": "Chinese CDP", "downloaded": ch_dl}] if ch_dl or (chinese_papers and not args.skip_chinese) else [])
    )
    remaining = en_rem + ch_rem

    # Extend doi list with Chinese paper identifiers for download log
    ch_dois = [p.get("doi") or p.get("title", "") for p in chinese_papers] if chinese_papers else []
    if ch_dois:
        dois = dois + ch_dois
    log_ids = all_log_ids or dois

    # ── Final summary ─────────────────────────────────────────────────
    failure_reasons = {**en_failure_reasons, **ch_failure_reasons}
    log_path = generate_download_log(args.output, log_ids, round_results, failure_reasons)
    step5_paths = write_step5_outputs(
        args.output,
        manifest_input_items,
        all_downloaded,
        remaining,
        round_results,
        failure_reasons,
        preflight_summary=preflight_summary,
    )

    final_manifest = json.loads(Path(step5_paths["manifest"]).read_text(encoding="utf-8"))
    final_summary = final_manifest.get("summary", {})
    total_all = final_summary.get("total", len(log_ids))
    verified_downloaded = final_summary.get("downloaded", 0)
    failed_or_pending = final_summary.get("failed_or_pending", total_all - verified_downloaded)
    print(f"\n{'='*60}")
    print(f"Final Summary")
    print(f"{'='*60}")
    print(f"  Total papers:     {total_all}")
    print(f"  {OK} Downloaded:    {verified_downloaded}")
    print(f"  {FAIL} Failed/Pending: {failed_or_pending}")

    if remaining:
        failed_path = os.path.join(args.output, "failed_dois.txt")
        with open(failed_path, "w", encoding="utf-8") as f:
            for d in remaining:
                pub = resolve_publisher(d)
                pub_name = pub.get("_key", "unknown") if pub else "unknown"
                reason = failure_reasons.get(d, "")
                suffix = f" | {reason}" if reason else ""
                f.write(f"{d}  # {pub_name}{suffix}\n")
        sidecar_path = write_failed_doi_sidecar(args.output, remaining, failure_reasons)
        print(f"  Failed list:     {failed_path}")
        print(f"  Failed sidecar:  {sidecar_path}")

    print(f"  Download log:    {log_path}")
    print(f"  Manifest:        {step5_paths['manifest']}")
    print(f"  PDF pool index:  {step5_paths['pdf_pool']}")
    next_action = final_manifest.get("recommended_next_step", "")
    if final_manifest.get("readiness") == "complete":
        print(f"\n  Next step {ARROW} Step 6: Zotero library management")
    else:
        print(f"\n  Next action {ARROW} {next_action or 'review unresolved Step 5 items'}")
    release_step5_download_lock(lock_path)


if __name__ == "__main__":
    main()
