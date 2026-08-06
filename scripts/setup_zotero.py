#!/usr/bin/env python3
# Copyright (c) 2026 Dr. Jiang Bingyun
# Licensed under CC BY-NC-SA 4.0 — Attribution-NonCommercial-ShareAlike 4.0 International
# https://creativecommons.org/licenses/by-nc-sa/4.0/
#
"""
Zotero MCP 配置工具 — 包含安装、配置、检测三合一。

功能：
  默认模式：检测 Zotero MCP 状态并显示报告
  --install: 一键安装+配置 Zotero MCP
  --check  : JSON 格式输出检测结果（供脚本调用）
  --export : 输出环境变量配置命令
  --target : 指定目标 Agent 环境（hermes / claude-code / claude-desktop / cursor / auto）
  --non-interactive: 非交互模式（配合 --install，通过环境变量传入参数）
  --smoke-test: 安装后自动执行功能验证

Usage:
  python3 scripts/setup_zotero.py                              检测状态
  python3 scripts/setup_zotero.py --install                    安装+配置（交互式）
  python3 scripts/setup_zotero.py --install --target claude-code  安装到 Claude Code
  python3 scripts/setup_zotero.py --install --target auto         自动检测环境
  python3 scripts/setup_zotero.py --check                      JSON 输出
  python3 scripts/setup_zotero.py --export                     输出 export 命令
  python3 scripts/setup_zotero.py --smoke-test                 功能验证
"""
try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import sys, os, json, subprocess, shutil, configparser, platform, ntpath, re

PACKAGE_NAME = "zotero-mcp-server"
RECOMMENDED_VERSION = "0.5.0"
PACKAGE_REQUIREMENT = f"{PACKAGE_NAME}>={RECOMMENDED_VERSION}"
HERMES_HOME = os.path.expanduser("~/.hermes")
HERMES_CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")

# Claude Code MCP 配置路径
CLAUDE_CODE_MCP_PATH = os.path.expanduser("~/.claude/mcp.json")

# Claude Desktop 配置路径（macOS）
if platform.system() == "Darwin":
    CLAUDE_DESKTOP_CONFIG = os.path.expanduser(
        "~/Library/Application Support/Claude/claude_desktop_config.json"
    )
elif platform.system() == "Windows":
    CLAUDE_DESKTOP_CONFIG = os.path.expanduser(
        "~/AppData/Roaming/Claude/claude_desktop_config.json"
    )
else:
    CLAUDE_DESKTOP_CONFIG = os.path.expanduser(
        "~/.config/Claude/claude_desktop_config.json"
    )

# Cursor MCP 配置路径
CURSOR_MCP_PATH = os.path.expanduser("~/.cursor/mcp.json")


# ── 检测函数 ──────────────────────────────────────────────

def check_installed():
    """检测 zotero-mcp-server pip 包是否已安装"""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "show", PACKAGE_NAME],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if line.startswith("Version:"):
                    return True, line.split(":", 1)[1].strip()
        return False, None
    except Exception:
        return False, None


def version_at_least(value, minimum=RECOMMENDED_VERSION):
    """Compare stable numeric release versions without requiring packaging."""
    current_match = re.match(r"^(\d+(?:\.\d+)*)", value or "")
    required_match = re.match(r"^(\d+(?:\.\d+)*)", minimum or "")
    if not current_match or not required_match:
        return False
    current = tuple(int(part) for part in current_match.group(1).split("."))
    required = tuple(int(part) for part in required_match.group(1).split("."))
    width = max(len(current), len(required))
    return current + (0,) * (width - len(current)) >= required + (0,) * (width - len(required))


def check_env():
    """检测环境变量"""
    api_key = os.environ.get("ZOTERO_API_KEY", "")
    user_id = os.environ.get("ZOTERO_USER_ID", "")
    local = os.environ.get("ZOTERO_LOCAL", "").lower() in ["true", "yes", "1"]
    return api_key, user_id, local


def detect_mode(config_path=None):
    """检测配置文件中 Zotero MCP 的运行模式。

    支持 Hermes YAML 格式和 Claude Code / Cursor JSON 格式。
    """
    if config_path is None:
        config_path = _find_existing_config()
    if not config_path or not os.path.exists(config_path):
        return None
    try:
        env = _get_zotero_env_from_config(config_path)
        if not env:
            return None
        if env.get("ZOTERO_LOCAL", "").lower() in ["true", "yes", "1"]:
            return "local"
        if env.get("ZOTERO_API_KEY"):
            return "web"
        return None
    except Exception:
        return None


def check_mcp_registered():
    """检测是否有任何配置文件中注册了 zotero MCP"""
    for cfg_path in _all_config_paths():
        if os.path.exists(cfg_path):
            try:
                env = _get_zotero_env_from_config(cfg_path)
                if env:
                    return True
            except Exception:
                pass

    # 也检查 zotero-mcp 自身的 setup 状态
    try:
        r = subprocess.run(
            [sys.executable, "-m", "zotero_mcp_server.setup_info"],
            capture_output=True, text=True, timeout=10
        )
        if "Claude integration: enabled" in r.stdout:
            return True
    except Exception:
        pass
    return False


def _all_config_paths():
    """返回所有可能的 MCP 配置路径"""
    paths = [HERMES_CONFIG_PATH, CLAUDE_CODE_MCP_PATH, CURSOR_MCP_PATH]
    if CLAUDE_DESKTOP_CONFIG:
        paths.append(CLAUDE_DESKTOP_CONFIG)
    return paths


def _find_existing_config():
    """查找第一个存在且有 Zotero 配置的配置文件"""
    for cfg_path in _all_config_paths():
        if os.path.exists(cfg_path):
            try:
                env = _get_zotero_env_from_config(cfg_path)
                if env:
                    return cfg_path
            except Exception:
                pass
    return None


def _get_zotero_env_from_config(config_path):
    """从配置文件（YAML 或 JSON）中提取 Zotero MCP 的环境变量"""
    ext = os.path.splitext(config_path)[1].lower()

    if ext in [".yaml", ".yml"]:
        import yaml
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        zot = cfg.get("mcp_servers", {}).get("zotero", {})
        return zot.get("env", {})
    elif ext == ".json":
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f) or {}
        zot = cfg.get("mcpServers", {}).get("zotero", {})
        return zot.get("env", {})
    return None


def detect_target():
    """自动检测当前 Agent 环境

    Returns: 'hermes' | 'claude-code' | 'claude-desktop' | 'cursor' | None
    """
    # 检测 Claude Code
    if os.path.exists(CLAUDE_CODE_MCP_PATH):
        return "claude-code"
    # 检测 Cursor
    if os.path.exists(CURSOR_MCP_PATH):
        return "cursor"
    # 检测 Hermes
    if os.path.exists(HERMES_CONFIG_PATH):
        return "hermes"
    # 检测 Claude Desktop
    if os.path.exists(CLAUDE_DESKTOP_CONFIG):
        return "claude-desktop"
    # 通过环境变量检测
    if os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_CODE"):
        return "claude-code"
    if os.environ.get("HERMES_HOME"):
        return "hermes"
    return None


def check_zotero_local():
    """检测 Zotero 桌面端是否运行（本地 API 端口）"""
    try:
        import urllib.request
        r = urllib.request.urlopen(
            "http://127.0.0.1:23119/api/users/1/items?limit=1", timeout=3
        )
        return True
    except Exception:
        return False


def check_mcp_process():
    """通过 Hermes CLI 检测 MCP 是否存活"""
    for cmd in ["hermes", "openclaw"]:
        if shutil.which(cmd):
            try:
                r = subprocess.run(
                    [cmd, "mcp", "list"], capture_output=True, text=True, timeout=5
                )
                if "zotero" in r.stdout.lower():
                    return True
            except Exception:
                pass
    return False


# ── 安装与配置 ─────────────────────────────────────────────

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES_DIR = os.path.join(SKILL_DIR, "scripts", "packages")


def find_local_wheel():
    """在 skill 的 packages/ 目录查找本地 wheel 文件"""
    if not os.path.isdir(PACKAGES_DIR):
        return None
    for f in os.listdir(PACKAGES_DIR):
        if f.startswith("zotero_mcp_server") and f.endswith(".whl"):
            return os.path.join(PACKAGES_DIR, f)
    return None


def install_package():
    """安装 zotero-mcp-server — 优先本地 wheel，跨平台编译包自动从 PyPI 补全"""
    local_wheel = find_local_wheel()

    if local_wheel:
        pkgs_dir = os.path.dirname(local_wheel)
        print(f"  发现本地包目录: {pkgs_dir} ({len(os.listdir(pkgs_dir))} 个 wheel)")
        print(f"  使用 --find-links 本地优先策略...")
        # --find-links: pip优先用本地wheel，缺的平台二进制自动降级到PyPI
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             PACKAGE_REQUIREMENT,
             "--find-links", pkgs_dir,
             "-q"],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            print(f"  ✅ zotero-mcp-server 安装成功")
            return True
        else:
            err = r.stderr.strip()
            if "find-links" in err.lower():
                print(f"  ⚠ --find-links 失败，尝试直接安装本地 wheel...")
                r2 = subprocess.run(
                    [sys.executable, "-m", "pip", "install",
                     local_wheel,
                     "--find-links", pkgs_dir,
                     "-q"],
                    capture_output=True, text=True, timeout=120
                )
                if r2.returncode == 0:
                    print(f"  ✅ zotero-mcp-server 安装成功")
                    return True
            print(f"  ❌ 安装失败，尝试从 PyPI 下载...")

    print(f"  从 PyPI 安装 {PACKAGE_REQUIREMENT}（需联网）...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", PACKAGE_REQUIREMENT, "-q"],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode == 0:
        print(f"  ✅ {PACKAGE_NAME} 安装成功（PyPI）")
        return True
    else:
        print(f"  ❌ 安装失败: {r.stderr.strip()}")
        return False


def get_zotero_bin():
    """获取 zotero-mcp 可执行文件路径"""
    # 优先用 pip show 定位
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "show", PACKAGE_NAME],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.splitlines():
            if line.startswith("Location:"):
                site_pkgs = line.split(":", 1)[1].strip()
                pathmod = ntpath if "\\" in site_pkgs else os.path
                site_parent = pathmod.dirname(site_pkgs)
                py_root = pathmod.dirname(site_parent)
                # zotero-mcp 可执行文件通常在 bin/ 目录（同级或上一级）
                for candidate in [
                    pathmod.join(py_root, "Scripts", "zotero-mcp.exe"),
                    pathmod.join(py_root, "Scripts", "zotero-mcp"),
                    pathmod.join(site_parent, "Scripts", "zotero-mcp.exe"),
                    pathmod.join(site_parent, "Scripts", "zotero-mcp"),
                    pathmod.join(site_parent, "bin", "zotero-mcp"),
                    pathmod.join(site_pkgs, "Scripts", "zotero-mcp.exe"),
                    pathmod.join(site_pkgs, "Scripts", "zotero-mcp"),
                    pathmod.join(site_pkgs, "bin", "zotero-mcp"),
                ]:
                    if os.path.exists(candidate):
                        return candidate
    except Exception:
        pass
    # fallback: which
    return shutil.which("zotero-mcp.exe") or shutil.which("zotero-mcp") or "zotero-mcp"


def configure_mcp(api_key="", user_id="", local_mode=False, target="hermes"):
    """写入/更新 MCP 配置

    Args:
        api_key: Web API 模式时需要的 Zotero API Key
        user_id: Web API 模式时需要的 Zotero 用户数字 ID
        local_mode: True=本地模式（桌面端直连），False=Web API 模式
        target: 目标环境 — 'hermes' | 'claude-code' | 'claude-desktop' | 'cursor' | 'auto'
    """
    if target == "auto":
        target = detect_target() or "claude-code"

    if target == "claude-desktop":
        return _configure_via_zotero_mcp_setup(api_key, user_id, local_mode)
    elif target == "claude-code":
        # Claude Code 优先使用 claude mcp add（官方 CLI 方式），
        # 失败时回退到直接写 mcp.json
        if _try_claude_mcp_add(api_key, user_id, local_mode):
            return True
        print("  ⚠ claude mcp add 失败，回退到直接写 mcp.json...")
        return _configure_json_mcp(api_key, user_id, local_mode, "claude-code")
    elif target == "cursor":
        return _configure_json_mcp(api_key, user_id, local_mode, "cursor")
    else:
        return _configure_hermes_mcp(api_key, user_id, local_mode)


def _try_claude_mcp_add(api_key, user_id, local_mode):
    """尝试通过 claude mcp add 命令注册 Zotero MCP（Claude Code 官方方式）

    这是 VS Code 扩展版 Claude Code 推荐的方式，优于直接写 mcp.json。
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return False

    zotero_bin = get_zotero_bin()
    cmd = [claude_bin, "mcp", "add"]

    if local_mode:
        cmd.extend(["-e", "ZOTERO_LOCAL=true"])
    else:
        if api_key:
            cmd.extend(["-e", f"ZOTERO_API_KEY={api_key}"])
        if user_id:
            cmd.extend(["-e", f"ZOTERO_LIBRARY_ID={user_id}"])

    cmd.extend([
        "-e", "no_proxy=localhost,127.0.0.1,::1",
        "-e", "NO_PROXY=localhost,127.0.0.1,::1",
        "--", "zotero", zotero_bin, "serve",
    ])

    print(f"  执行: claude mcp add zotero ...")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print(f"  ✅ 通过 claude mcp add 注册成功")
            _print_config_result(target="claude-code",
                                 config_path="claude mcp (CLI 管理)",
                                 zotero_bin=zotero_bin, local_mode=local_mode,
                                 user_id=user_id, api_key=api_key)
            return True
        else:
            print(f"  ⚠ claude mcp add 返回非零: {r.stderr.strip()}")
            return False
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"  ⚠ claude mcp add 异常: {e}")
        return False


def _configure_hermes_mcp(api_key="", user_id="", local_mode=False):
    """写入 ~/.hermes/config.yaml 的 mcp_servers.zotero 节"""
    import yaml

    os.makedirs(HERMES_HOME, exist_ok=True)

    if os.path.exists(HERMES_CONFIG_PATH):
        with open(HERMES_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    if "mcp_servers" not in cfg:
        cfg["mcp_servers"] = {}

    zotero_bin = get_zotero_bin()

    if local_mode:
        env = {
            "ZOTERO_LOCAL": "true",
            "no_proxy": "localhost,127.0.0.1,::1",
            "NO_PROXY": "localhost,127.0.0.1,::1",
        }
    else:
        env = {
            "ZOTERO_API_KEY": api_key,
            "ZOTERO_LIBRARY_ID": user_id,
            "no_proxy": "localhost,127.0.0.1,::1",
            "NO_PROXY": "localhost,127.0.0.1,::1",
        }

    cfg["mcp_servers"]["zotero"] = {
        "command": zotero_bin,
        "env": env,
        "enabled": True,
    }

    with open(HERMES_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

    _print_config_result(target="hermes", config_path=HERMES_CONFIG_PATH,
                         zotero_bin=zotero_bin, local_mode=local_mode,
                         user_id=user_id, api_key=api_key)
    return True


def _configure_json_mcp(api_key="", user_id="", local_mode=False, target="claude-code"):
    """写入 Claude Code / Cursor 的 JSON 格式 MCP 配置

    Claude Code: ~/.claude/mcp.json
    Cursor:      ~/.cursor/mcp.json
    """
    if target == "cursor":
        config_path = CURSOR_MCP_PATH
    else:
        config_path = CLAUDE_CODE_MCP_PATH

    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)

    # 读取已有配置，保留其他 MCP 服务器
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError:
                cfg = {}
    else:
        cfg = {}

    if "mcpServers" not in cfg:
        cfg["mcpServers"] = {}

    zotero_bin = get_zotero_bin()

    if local_mode:
        env = {
            "ZOTERO_LOCAL": "true",
            "no_proxy": "localhost,127.0.0.1,::1",
            "NO_PROXY": "localhost,127.0.0.1,::1",
        }
    else:
        env = {
            "ZOTERO_API_KEY": api_key,
            "ZOTERO_LIBRARY_ID": user_id,
            "no_proxy": "localhost,127.0.0.1,::1",
            "NO_PROXY": "localhost,127.0.0.1,::1",
        }

    cfg["mcpServers"]["zotero"] = {
        "command": zotero_bin,
        "env": env,
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")

    _print_config_result(target=target, config_path=config_path,
                         zotero_bin=zotero_bin, local_mode=local_mode,
                         user_id=user_id, api_key=api_key)
    return True


def _configure_via_zotero_mcp_setup(api_key="", user_id="", local_mode=False):
    """通过 zotero-mcp setup 命令配置 Claude Desktop

    调用上游 zotero-mcp-server 自带 setup 命令。
    """
    zotero_bin = get_zotero_bin()
    cmd = [zotero_bin, "setup"]

    if local_mode:
        # 默认就是 local 模式
        pass
    else:
        cmd.extend(["--no-local", "--api-key", api_key, "--library-id", user_id])

    print(f"  执行: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(r.stdout)
        if r.returncode != 0:
            print(f"  ⚠ setup 输出: {r.stderr}")
        _print_config_result(target="claude-desktop",
                             config_path=CLAUDE_DESKTOP_CONFIG,
                             zotero_bin=zotero_bin, local_mode=local_mode,
                             user_id=user_id, api_key=api_key)
        return r.returncode == 0
    except Exception as e:
        print(f"  ❌ zotero-mcp setup 失败: {e}")
        print(f"  回退：直接写入 {CLAUDE_DESKTOP_CONFIG}")
        return _configure_json_mcp(api_key, user_id, local_mode, "claude-desktop")
        # Claude Desktop 和 Claude Code 共用同样的 JSON 结构，
        # 但必须写入 Claude Desktop 自己的配置路径。


def _print_config_result(target, config_path, zotero_bin, local_mode, user_id, api_key):
    """打印配置结果"""
    target_labels = {
        "hermes": "Hermes/OpenClaw",
        "claude-code": "Claude Code",
        "claude-desktop": "Claude Desktop",
        "cursor": "Cursor",
    }
    label = target_labels.get(target, target)

    mode_label = "本地 API（桌面端直连，仅读取）" if local_mode else "Web API（远程，支持读写）"

    print(f"  ✅ 目标环境: {label}")
    print(f"  ✅ MCP 配置已写入 {config_path}")
    print(f"  ✅ 模式: {mode_label}")
    print(f"     command: {zotero_bin}")
    if local_mode:
        print(f"     ZOTERO_LOCAL: true（本地模式）")
    else:
        print(f"     library_id: {user_id}")
        print(f"     api_key: {'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    # 给出下一步提示
    if target == "claude-code":
        print(f"\n  📌 下一步：重启 Claude Code 后 Zotero MCP 即生效。")
        print(f"     验证: 在 Claude Code 中检查是否出现 zotero_* 工具")
    elif target == "cursor":
        print(f"\n  📌 下一步：重启 Cursor 后 Zotero MCP 即生效。")
    elif target == "claude-desktop":
        print(f"\n  📌 下一步：完全退出并重启 Claude Desktop 应用。")
    elif target == "hermes":
        print(f"\n  📌 下一步：重启 Hermes 后 Zotero MCP 即生效。")
        print(f"     验证: hermes mcp list")


def prompt_and_install(target="hermes", non_interactive=False):
    """交互式（或非交互式）安装流程

    Args:
        target: 目标环境 — 'hermes' | 'claude-code' | 'claude-desktop' | 'cursor' | 'auto'
        non_interactive: True 时不等待用户输入，从环境变量获取参数
    """
    if target == "auto":
        target = detect_target() or "claude-code"

    target_labels = {
        "hermes": "Hermes/OpenClaw",
        "claude-code": "Claude Code",
        "claude-desktop": "Claude Desktop",
        "cursor": "Cursor",
    }
    target_label = target_labels.get(target, target)

    print("=" * 55)
    print(f"  Zotero MCP 一键安装与配置 → {target_label}")
    print("=" * 55)

    # 1. 安装包
    installed, ver = check_installed()
    if installed and version_at_least(ver):
        version_note = (
            " 当前版本高于离线验证基线，予以保留。"
            if ver != RECOMMENDED_VERSION else ""
        )
        print(f"\n✅ zotero-mcp-server (v{ver}) 已安装，跳过安装步骤。{version_note}")
    else:
        reason = f"当前版本 v{ver} 低于兼容基线" if installed else "尚未安装"
        print(f"\n⏳ {PACKAGE_NAME} {reason}，开始安装/升级...")
        if not install_package():
            print("\n❌ pip 安装失败。请手动执行:")
            print(f"   pip install \"{PACKAGE_REQUIREMENT}\"")
            return False

    # 2. 非交互模式：从环境变量获取参数
    if non_interactive:
        api_key = os.environ.get("ZOTERO_API_KEY", "")
        user_id = os.environ.get("ZOTERO_USER_ID", "")
        local_mode = os.environ.get("ZOTERO_LOCAL", "").lower() in ["true", "yes", "1"]

        if local_mode:
            print("\n📋 非交互模式: 本地 API")
            configure_mcp(local_mode=True, target=target)
        elif api_key and user_id:
            print("\n📋 非交互模式: Web API")
            configure_mcp(api_key=api_key, user_id=user_id, target=target)
        else:
            print("\n⚠ 非交互模式需要设置环境变量：")
            print("  方式 A (Web API): ZOTERO_API_KEY + ZOTERO_USER_ID")
            print("  方式 B (本地):     ZOTERO_LOCAL=true")
            return False

        _print_post_install_help(target)
        return True

    # 3. 交互模式：选择连接模式
    current_mode = detect_mode()
    if current_mode:
        mode_hint = "本地" if current_mode == "local" else "Web API"
        print(f"\n当前已配置模式: {mode_hint}")
        try:
            val = input("  是否切换模式？(y/n, 默认 n): ").strip().lower()
            if val == "y":
                current_mode = None  # 强制进入选择流程
        except (EOFError, KeyboardInterrupt):
            print("   [跳过]")
            return True

    if not current_mode:
        print("\n请选择 Zotero 连接模式：")
        print("  1) Web API（远程连接 zotero.org，支持读写操作）")
        print("     需要 API Key，不需要 Zotero 桌面端运行")
        print("  2) 本地 API（直连 Zotero 桌面端，无需 API Key）")
        print("     仅支持读取，需要 Zotero 桌面端保持运行")
        print()
        try:
            choice = input("  请输入 1 或 2（默认 1）: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""

        local_mode = (choice == "2")

        if local_mode:
            print("\n📋 本地模式配置")
            if not check_zotero_local():
                print("  ⚠ 未检测到 Zotero 桌面端运行。")
                print("    请先启动 Zotero 桌面端，然后重新运行本脚本。")
                print("    或继续配置，稍后启动 Zotero。")
            configure_mcp(local_mode=True, target=target)
        else:
            print("\n📋 Web API 模式配置")
            api_key, user_id, _ = check_env()
            if not api_key:
                print("\n请输入你的 Zotero API Key：")
                print("  （打开 https://www.zotero.org/settings/keys 创建）")
                try:
                    val = input("   ZOTERO_API_KEY: ").strip()
                    if val:
                        api_key = val
                except (EOFError, KeyboardInterrupt):
                    print("   [跳过输入]")

            if not user_id:
                print("\n请输入你的 Zotero 用户数字 ID：")
                print("  （打开 zotero.org/settings/keys，URL 中可找到数字 ID）")
                try:
                    val = input("   ZOTERO_USER_ID: ").strip()
                    if val:
                        user_id = val
                except (EOFError, KeyboardInterrupt):
                    print("   [跳过输入]")

            if api_key and user_id:
                configure_mcp(api_key=api_key, user_id=user_id, target=target)
            else:
                print("\n⚠  API Key 或 User ID 不完整，跳过配置写入。")
                _print_manual_config_help(target)
                return False
    else:
        print("  保持当前配置不变。")

    _print_post_install_help(target)
    return True


def _print_post_install_help(target):
    """打印安装后的下一步提示"""
    print("\n" + "=" * 55)
    print("  安装完成！")
    print("=" * 55)

    if target == "claude-code":
        print("  📌 重启 Claude Code 后 Zotero MCP 即生效。")
        print("     在对话中检查是否出现 zotero_* 系列工具。")
    elif target == "hermes":
        print("  📌 重启 Hermes 后生效。")
        print("  验证命令：")
        print("    hermes mcp list          # 查看 MCP 列表")
    elif target == "claude-desktop":
        print("  📌 完全退出并重启 Claude Desktop 应用。")
    elif target == "cursor":
        print("  📌 重启 Cursor 后生效。")

    print("  验证命令：")
    print("    python3 scripts/setup_zotero.py            # 检测状态")
    print("    python3 scripts/setup_zotero.py --check    # JSON 检测报告")
    print("=" * 55)


def _print_manual_config_help(target):
    """打印手动配置帮助"""
    if target == "claude-code":
        print(f"   可稍后手动编辑 {CLAUDE_CODE_MCP_PATH} 补全。")
        print(f"   格式参考: https://docs.anthropic.com/en/docs/claude-code/mcp")
    elif target == "claude-desktop":
        print(f"   可稍后手动编辑 {CLAUDE_DESKTOP_CONFIG} 补全。")
    elif target == "hermes":
        print(f"   可稍后手动编辑 {HERMES_CONFIG_PATH} 补全。")


# ── 状态报告 ──────────────────────────────────────────────

def print_status():
    """打印人类可读的状态报告（多目标检测）"""
    installed, ver = check_installed()
    api_key, user_id, local_env = check_env()
    mode = detect_mode()
    registered = check_mcp_registered()
    alive = check_mcp_process()
    local_ok = check_zotero_local()

    print("=" * 55)
    print("  Zotero MCP 环境检测")
    print("=" * 55)

    # 1. 包安装
    if installed:
        print(f"\n📦 zotero-mcp-server  v{ver}  ✅ 已安装")
    else:
        print("\n📦 zotero-mcp-server     ❌ 未安装")
        print("   执行 python3 scripts/setup_zotero.py --install 一键安装")

    # 2. 模式
    mode_text = {"web": "Web API（远程读写）", "local": "本地 API（桌面端只读）"}
    if registered and mode:
        print(f"🔌 连接模式:           {mode_text.get(mode, mode)}")
    else:
        print("🔌 连接模式:           未配置")

    # 3. 可执行文件
    zotero_bin = get_zotero_bin()
    if zotero_bin and os.path.exists(zotero_bin):
        print(f"🔧 可执行文件:         {zotero_bin}")
    else:
        print(f"🔧 可执行文件:         未找到")

    # 4. 各环境配置注册状态
    print("⚙️  配置注册状态:")
    _print_target_status("Hermes/OpenClaw", HERMES_CONFIG_PATH)
    _print_target_status("Claude Code", CLAUDE_CODE_MCP_PATH)
    _print_target_status("Cursor", CURSOR_MCP_PATH)
    if CLAUDE_DESKTOP_CONFIG:
        _print_target_status("Claude Desktop", CLAUDE_DESKTOP_CONFIG)

    # 5. 环境变量
    if mode == "web":
        print(f"🔑 ZOTERO_API_KEY:     {'✅ 已设置' if api_key else '❌ 未设置'}")
        print(f"👤 ZOTERO_LIBRARY_ID:  {'✅ 已设置 (' + user_id + ')' if user_id else '❌ 未设置'}")
    elif mode == "local":
        print("🔑 ZOTERO_LOCAL:       ✅ true（本地模式）")

    # 6. 进程存活
    if alive:
        print("🚀 MCP 进程:            ✅ 运行中")
    else:
        print("🚀 MCP 进程:            ⏸️  未启动（重启 Agent 后生效）")

    # 7. Zotero 桌面端
    if local_ok:
        print("💻 Zotero 桌面端:        ✅ 运行中")
    else:
        print("💻 Zotero 桌面端:        ⏹️  未检测到")

    # 8. 自动检测当前环境
    detected = detect_target()
    if detected:
        target_labels = {
            "hermes": "Hermes/OpenClaw",
            "claude-code": "Claude Code",
            "claude-desktop": "Claude Desktop",
            "cursor": "Cursor",
        }
        print(f"🎯 检测到当前环境:     {target_labels.get(detected, detected)}")

    # 总结
    print()
    if installed and registered and (mode == "local" or api_key):
        print("🎯 状态：就绪，Zotero MCP 可正常使用")
    elif installed and not registered:
        print("💡 提示：包已安装，执行 python3 scripts/setup_zotero.py --install 完成配置写入")
    else:
        print("💡 提示：执行 python3 scripts/setup_zotero.py --install 一键配置")

    if not os.path.exists(CLAUDE_CODE_MCP_PATH) and detected == "claude-code":
        print("💡 Claude Code 用户：执行 python3 scripts/setup_zotero.py --install --target claude-code")
    print()


def _print_target_status(label, config_path):
    """打印单个目标环境的配置状态"""
    if os.path.exists(config_path):
        try:
            env = _get_zotero_env_from_config(config_path)
            if env:
                print(f"   {label:20s} ✅ 已配置")
                return
        except Exception:
            pass
        print(f"   {label:20s} ⚠️  文件存在但未找到 Zotero 配置")
    else:
        print(f"   {label:20s} ❌ 未配置")


# ── 烟雾测试 ──────────────────────────────────────────────

def smoke_test():
    """安装后自动化功能验证"""
    print("=" * 55)
    print("  Zotero MCP 烟雾测试")
    print("=" * 55)

    results = []
    all_pass = True

    # 1. 包安装检查
    installed, ver = check_installed()
    status = "✅" if installed else "❌"
    if not installed:
        all_pass = False
    print(f"\n{status} 1. zotero-mcp-server 包安装")
    results.append({"test": "package_installed", "pass": installed, "version": ver})

    # 2. 可执行文件
    zotero_bin = get_zotero_bin()
    bin_exists = bool(zotero_bin and os.path.exists(zotero_bin))
    status = "✅" if bin_exists else "❌"
    if not bin_exists:
        all_pass = False
    print(f"{status} 2. zotero-mcp 可执行文件 ({zotero_bin})")
    results.append({"test": "binary_found", "pass": bin_exists, "path": zotero_bin})

    # 3. 可执行文件能否运行
    if bin_exists:
        try:
            r = subprocess.run([zotero_bin, "version"], capture_output=True, text=True, timeout=10)
            bin_runnable = r.returncode == 0
            status = "✅" if bin_runnable else "❌"
            if not bin_runnable:
                all_pass = False
            print(f"{status} 3. zotero-mcp 可运行 ({r.stdout.strip()})")
            results.append({"test": "binary_runnable", "pass": bin_runnable, "output": r.stdout.strip()})
        except Exception as e:
            print(f"❌ 3. zotero-mcp 运行失败: {e}")
            results.append({"test": "binary_runnable", "pass": False, "error": str(e)})
            all_pass = False
    else:
        print("⏭️  3. zotero-mcp 可运行 (跳过 — 未找到可执行文件)")
        results.append({"test": "binary_runnable", "pass": None, "error": "binary not found"})

    # 4. MCP 配置注册
    registered = check_mcp_registered()
    status = "✅" if registered else "⚠️"
    print(f"{status} 4. MCP 配置注册")
    results.append({"test": "mcp_registered", "pass": registered})

    # 5. 检测配置了哪些环境
    configs_found = []
    for label, path in [
        ("Hermes", HERMES_CONFIG_PATH),
        ("Claude Code", CLAUDE_CODE_MCP_PATH),
        ("Cursor", CURSOR_MCP_PATH),
    ]:
        if os.path.exists(path):
            try:
                env = _get_zotero_env_from_config(path)
                if env:
                    configs_found.append(label)
            except Exception:
                pass
    status = "✅" if configs_found else "⚠️"
    print(f"{status} 5. 已配置环境: {', '.join(configs_found) if configs_found else '无'}")
    results.append({"test": "configs_found", "pass": bool(configs_found), "environments": configs_found})

    # 6. 连接模式
    mode = detect_mode()
    mode_label = {"web": "Web API", "local": "Local API"}.get(mode or "", "未知")
    status = "✅" if mode else "⚠️"
    print(f"{status} 6. 连接模式: {mode_label}")
    results.append({"test": "mode_detected", "pass": bool(mode), "mode": mode})

    # 7. 环境变量
    api_key, user_id, local_env = check_env()
    if mode == "web":
        env_ok = bool(api_key and user_id)
    elif mode == "local":
        env_ok = local_env
    else:
        env_ok = False
    status = "✅" if env_ok else "⚠️"
    print(f"{status} 7. 环境变量/凭据设置")
    results.append({"test": "credentials_set", "pass": env_ok})

    # 8. Zotero 桌面端检测
    local_ok = check_zotero_local()
    if mode == "local":
        status = "✅" if local_ok else "⚠️"
        if not local_ok:
            print(f"{status} 8. Zotero 桌面端运行中 (本地模式需要)")
        else:
            print(f"{status} 8. Zotero 桌面端运行中")
    else:
        status = "✅" if local_ok else "ℹ️"
        print(f"{status} 8. Zotero 桌面端运行中 (Web API 模式不需要)")
    results.append({"test": "zotero_desktop_running", "pass": local_ok})

    # 总结
    print("\n" + "=" * 55)
    if all_pass:
        print("🎯 烟雾测试通过！Zotero MCP 配置正确。")
    else:
        print("⚠️  部分测试未通过，请根据上述提示修复。")
        print("   常见解决方案：")
        if not installed:
            print("   - 执行 python3 scripts/setup_zotero.py --install")
        if not registered:
            print("   - 执行 python3 scripts/setup_zotero.py --install --target claude-code")
        if not env_ok:
            print("   - Web API: 设置 ZOTERO_API_KEY 和 ZOTERO_USER_ID")
            print("   - Local API: 设置 ZOTERO_LOCAL=true 并启动 Zotero 桌面端")

    print("=" * 55)
    return all_pass


# ── 主入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    if "--install" in sys.argv:
        # 解析 --target
        target = "hermes"  # 默认
        for i, arg in enumerate(sys.argv):
            if arg == "--target" and i + 1 < len(sys.argv):
                target = sys.argv[i + 1]
            elif arg.startswith("--target="):
                target = arg.split("=", 1)[1]

        non_interactive = "--non-interactive" in sys.argv or "-y" in sys.argv
        prompt_and_install(target=target, non_interactive=non_interactive)

    elif "--check" in sys.argv:
        installed, ver = check_installed()
        api_key, user_id, local_env = check_env()
        mode = detect_mode()
        detected = detect_target()

        # 多目标配置状态
        configs = {}
        for label, path in [
            ("hermes", HERMES_CONFIG_PATH),
            ("claude_code", CLAUDE_CODE_MCP_PATH),
            ("cursor", CURSOR_MCP_PATH),
        ]:
            if os.path.exists(path):
                try:
                    env = _get_zotero_env_from_config(path)
                    configs[label] = {
                        "configured": bool(env),
                        "mode": "local" if (env or {}).get("ZOTERO_LOCAL", "").lower() in ["true", "yes", "1"] else "web" if env else None,
                    }
                except Exception:
                    configs[label] = {"configured": False, "mode": None}
            else:
                configs[label] = {"configured": False, "mode": None}

        result = {
            "installed": installed,
            "version": ver,
            "mode": mode,
            "api_key_set": bool(api_key),
            "user_id_set": bool(user_id),
            "local_mode": local_env,
            "mcp_registered": check_mcp_registered(),
            "mcp_alive": check_mcp_process(),
            "local_running": check_zotero_local(),
            "binary": get_zotero_bin(),
            "detected_environment": detected,
            "configs": configs,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif "--export" in sys.argv:
        print("# Zotero MCP 环境变量（二选一）")
        print("#")
        print("# 选项 A: Web API 模式（远程，支持读写）")
        print('export ZOTERO_API_KEY="你的_API_KEY"')
        print('export ZOTERO_USER_ID="你的_USER_ID"')
        print("#")
        print("# 选项 B: 本地模式（桌面端直连，仅读取）")
        print("# export ZOTERO_LOCAL=true")
        print("#")
        print("# Claude Code 用户安装:")
        print("#   python3 scripts/setup_zotero.py --install --target claude-code")
        print("# Hermes 用户安装:")
        print("#   python3 scripts/setup_zotero.py --install --target hermes")
        print("# 自动检测环境安装:")
        print("#   python3 scripts/setup_zotero.py --install --target auto")
        print("#")
        print("# 查看完整配置：python3 scripts/setup_zotero.py")

    elif "--smoke-test" in sys.argv:
        smoke_test()

    else:
        print_status()
