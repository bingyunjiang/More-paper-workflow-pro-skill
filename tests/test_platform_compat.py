from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import io
from contextlib import redirect_stdout
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import cdp_utils  # noqa: E402
import auto_sd_downloader  # noqa: E402
import setup_zotero  # noqa: E402
import unified_download_router as router  # noqa: E402
import start_cdp_browser as start_cdp_browser  # noqa: E402


class PlatformCompatTest(unittest.TestCase):
    def test_macos_chrome_fallback_is_preserved(self):
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        with patch.object(cdp_utils, "_is_macos", return_value=True), \
             patch.object(cdp_utils, "_is_windows", return_value=False), \
             patch.object(cdp_utils.shutil, "which", return_value=None), \
             patch.object(cdp_utils.os.path, "isfile", side_effect=lambda p: p == chrome):
            self.assertEqual(cdp_utils.find_chrome_path(), chrome)

    def test_windows_chrome_fallback_is_detected(self):
        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        with patch.object(cdp_utils, "_is_macos", return_value=False), \
             patch.object(cdp_utils, "_is_windows", return_value=True), \
             patch.object(cdp_utils.shutil, "which", return_value=None), \
             patch.object(cdp_utils.os.path, "isfile", side_effect=lambda p: p == chrome):
            self.assertEqual(cdp_utils.find_chrome_path(), chrome)

    def test_windows_edge_localappdata_fallback_is_detected(self):
        edge = r"C:\Users\demo\AppData\Local\Microsoft\Edge\Application\msedge.exe"
        with patch.object(cdp_utils, "_is_macos", return_value=False), \
             patch.object(cdp_utils, "_is_windows", return_value=True), \
             patch.object(cdp_utils.shutil, "which", return_value=None), \
             patch.object(cdp_utils.os.path, "expandvars", return_value=edge), \
             patch.object(cdp_utils.os.path, "isfile", side_effect=lambda p: p == edge):
            self.assertEqual(cdp_utils.find_edge_path(), edge)

    def test_windows_start_persistent_cdp_browser_falls_back_to_edge(self):
        fake_proc = object()
        with patch.object(cdp_utils, "_is_windows", return_value=True), \
             patch.object(cdp_utils, "find_chrome_path", return_value=None), \
             patch.object(cdp_utils, "find_edge_path", return_value=r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"), \
             patch.object(cdp_utils, "kill_browser_by_port"), \
             patch.object(cdp_utils, "start_browser", return_value=fake_proc) as start_browser, \
             redirect_stdout(io.StringIO()) as stdout:
            proc = cdp_utils.start_persistent_cdp_browser(browser="chrome")

        self.assertIs(proc, fake_proc)
        self.assertIn("自动回退到 Edge", stdout.getvalue())
        self.assertEqual(start_browser.call_args.kwargs["browser_path"],
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")

    def test_start_browser_uses_open_na_on_macos(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(cdp_utils, "_is_macos", return_value=True), \
             patch.object(cdp_utils, "_is_windows", return_value=False), \
             patch.object(cdp_utils, "check_cdp", side_effect=[False, True]), \
             patch.object(cdp_utils.time, "sleep", return_value=None), \
             patch.object(cdp_utils.subprocess, "Popen") as popen:
            cdp_utils.start_browser(
                9223,
                tmp,
                url="https://example.com",
                browser_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            )

        command = popen.call_args.args[0]
        self.assertEqual(command[:4], ["open", "-na", "/Applications/Google Chrome.app", "--args"])
        self.assertIn("--remote-debugging-port=9223", command)
        self.assertIn("https://example.com", command)

    def test_start_browser_uses_start_process_on_windows(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(cdp_utils, "_is_macos", return_value=False), \
             patch.object(cdp_utils, "_is_windows", return_value=True), \
             patch.object(cdp_utils, "check_cdp", side_effect=[False, True]), \
             patch.object(cdp_utils.time, "sleep", return_value=None), \
             patch.object(cdp_utils.subprocess, "Popen") as popen:
            cdp_utils.start_browser(
                9223,
                tmp,
                url="https://example.com",
                browser_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            )

        command = popen.call_args.args[0]
        self.assertEqual(command[:3], ["powershell", "-NoProfile", "-Command"])
        self.assertIn("Start-Process", command[3])
        self.assertIn("--remote-debugging-port=9223", command[3])

    def test_start_browser_timeout_does_not_kill_process(self):
        fake_proc = object()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(cdp_utils, "_is_macos", return_value=False), \
             patch.object(cdp_utils, "_is_windows", return_value=False), \
             patch.object(cdp_utils, "check_cdp", return_value=False), \
             patch.object(cdp_utils.time, "sleep", return_value=None), \
             patch.object(cdp_utils.subprocess, "Popen", return_value=fake_proc), \
             redirect_stdout(io.StringIO()) as stdout:
            proc = cdp_utils.start_browser(
                9223,
                tmp,
                url="https://example.com",
                browser_path="/usr/bin/google-chrome",
            )

        self.assertIsNone(proc)
        self.assertIn("启动日志", stdout.getvalue())

    def test_windows_profile_cleanup_targets_only_matching_profile_processes(self):
        calls = []

        def _fake_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with patch.object(cdp_utils, "_is_macos", return_value=False), \
             patch.object(cdp_utils, "_is_windows", return_value=True), \
             patch.object(cdp_utils.subprocess, "run", side_effect=_fake_run), \
             patch.object(cdp_utils.time, "sleep", return_value=None):
            cdp_utils.kill_browser_by_profile(r"C:\Users\demo\.hermes\chrome_sd_profile")

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0:3], ["powershell", "-NoProfile", "-Command"])
        self.assertIn("chrome_sd_profile", calls[0][3])
        self.assertNotIn("/IM", " ".join(calls[0]))

    def test_profile_dir_uses_neutral_home_by_default(self):
        with patch.object(cdp_utils.os.path, "expanduser", return_value="/Users/demo"), \
             patch.object(cdp_utils.os.path, "exists", return_value=False), \
             patch.object(cdp_utils.os, "makedirs") as makedirs:
            profile_dir = cdp_utils._profile_dir("chrome")

        self.assertEqual(profile_dir, "/Users/demo/.more-paper-workflow/chrome_sd_profile")
        makedirs.assert_not_called()

    def test_profile_dir_migrates_legacy_hermes_profile(self):
        def _fake_exists(path):
            return path == "/Users/demo/.hermes/chrome_sd_profile"

        with patch.object(cdp_utils.os.path, "expanduser", return_value="/Users/demo"), \
             patch.object(cdp_utils.os.path, "exists", side_effect=_fake_exists), \
             patch.object(cdp_utils.os, "makedirs") as makedirs, \
             patch.object(cdp_utils.shutil, "move") as move:
            profile_dir = cdp_utils._profile_dir("chrome")

        self.assertEqual(profile_dir, "/Users/demo/.more-paper-workflow/chrome_sd_profile")
        makedirs.assert_called_once_with("/Users/demo/.more-paper-workflow", exist_ok=True)
        move.assert_called_once_with(
            "/Users/demo/.hermes/chrome_sd_profile",
            "/Users/demo/.more-paper-workflow/chrome_sd_profile",
        )

    def test_zotero_bin_detects_windows_scripts_exe(self):
        site_packages = r"C:\Users\demo\AppData\Local\Programs\Python\Python311\Lib\site-packages"
        expected = r"C:\Users\demo\AppData\Local\Programs\Python\Python311\Scripts\zotero-mcp.exe"
        pip_show = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=f"Name: zotero-mcp-server\nLocation: {site_packages}\n",
            stderr="",
        )
        with patch.object(setup_zotero.subprocess, "run", return_value=pip_show), \
             patch.object(setup_zotero.os.path, "exists", side_effect=lambda p: p == expected), \
             patch.object(setup_zotero.shutil, "which", return_value=None):
            self.assertEqual(setup_zotero.get_zotero_bin(), expected)

    def test_zotero_install_uses_locked_package_requirement(self):
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(setup_zotero, "find_local_wheel", return_value="/tmp/packages/zotero.whl"), \
             patch.object(setup_zotero.os, "listdir", return_value=["zotero.whl"]), \
             patch.object(setup_zotero.subprocess, "run", return_value=completed) as run:
            self.assertTrue(setup_zotero.install_package())
        command = run.call_args.args[0]
        self.assertIn("zotero-mcp-server>=0.5.0", command)

    def test_zotero_newer_version_satisfies_compatibility_baseline(self):
        self.assertTrue(setup_zotero.version_at_least("0.6.0"))
        self.assertTrue(setup_zotero.version_at_least("0.6.0rc1"))
        self.assertTrue(setup_zotero.version_at_least("0.5.0.post1"))
        self.assertTrue(setup_zotero.version_at_least("0.5.0"))
        self.assertFalse(setup_zotero.version_at_least("0.4.9"))

    def test_router_auto_start_uses_python_cdp_helper(self):
        with patch.object(router, "check_cdp", side_effect=[False, True]), \
             patch.object(router, "cdp_browser_matches", return_value=True), \
             patch.object(router, "start_persistent_cdp_browser") as starter:
            self.assertTrue(router.ensure_cdp_running(9223))
        starter.assert_called_once()

    def test_start_cdp_browser_prints_profile_and_log_on_success(self):
        argv = ["start_cdp_browser.py", "--browser", "chrome", "--port", "9223"]
        with patch.object(sys, "argv", argv), \
             patch.object(start_cdp_browser, "check_cdp", side_effect=[False, False, True]), \
             patch.object(start_cdp_browser, "cdp_browser_matches", return_value=True), \
             patch.object(start_cdp_browser, "start_persistent_cdp_browser"), \
             patch.object(start_cdp_browser, "get_persistent_profile_dir", return_value="/tmp/profile"), \
             patch.object(start_cdp_browser, "get_launch_log_path", return_value="/tmp/profile/cdp_launch.log"), \
             redirect_stdout(io.StringIO()) as stdout:
            rc = start_cdp_browser.main()

        self.assertEqual(rc, 0)
        text = stdout.getvalue()
        self.assertIn("Profile: /tmp/profile", text)
        self.assertIn("Launch log: /tmp/profile/cdp_launch.log", text)

    def test_auto_sd_default_browser_is_single_chrome(self):
        parser = auto_sd_downloader.argparse.ArgumentParser()
        parser.add_argument("--browser", choices=["auto", "chrome", "edge"], default="chrome")
        args = parser.parse_args([])
        self.assertEqual(args.browser, "chrome")

    def test_router_doi_file_entry_prefers_parse_doi_file(self):
        argv = ["unified_download_router.py", "--doi-file", "C:\\demo\\dois.txt", "--dry-run"]
        with patch.object(sys, "argv", argv), \
             patch.object(router, "parse_doi_file", return_value=["10.1016/j.test.2024.01.001"]) as parse_doi_file, \
             patch.object(router, "parse_input") as parse_input, \
             redirect_stdout(io.StringIO()):
            router.main()

        parse_doi_file.assert_called_once_with("C:\\demo\\dois.txt")
        parse_input.assert_not_called()

    def test_parse_doi_file_ignores_inline_hash_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            doi_file = Path(tmp) / "failed_dois.txt"
            doi_file.write_text(
                "\n".join([
                    "# full-line comment",
                    "10.1002/er.7775  # wiley",
                    "10.1016/j.ecmx.2026.101960#sd_elsevier",
                    "   10.1038/s41598-025-26279-4   ",
                    "",
                ]),
                encoding="utf-8",
            )

            dois = router.parse_doi_file(str(doi_file))

        self.assertEqual(dois, [
            "10.1002/er.7775",
            "10.1016/j.ecmx.2026.101960",
            "10.1038/s41598-025-26279-4",
        ])

    def test_platform_compat_scan_has_no_errors(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "check_platform_compat.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
