from pathlib import Path
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import unified_download_router as router  # noqa: E402
import generic_publisher_downloader as gpd  # noqa: E402
import auto_sd_downloader as auto_sd  # noqa: E402
import parallel_sd_download as parallel_sd  # noqa: E402
import cdp_utils  # noqa: E402
import sd_download  # noqa: E402
import batch_resolve_pii  # noqa: E402
import console_compat  # noqa: E402
import download_via_scihub as scihub  # noqa: E402
import download_via_ieee as ieee  # noqa: E402
import step5_download_doctor as doctor  # noqa: E402
import step5_reconcile_pdf_pool as reconcile  # noqa: E402


class Step5DownloadTest(unittest.TestCase):
    def _valid_pdf_bytes(self):
        return b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n" + b"x" * 6000

    def _valid_scihub_pdf_bytes(self):
        return b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n" + b"x" * 25000

    class _FakeScihubWs:
        def __init__(self, events, bodies):
            self.events = list(events)
            self.bodies = list(bodies)
            self.sent = []

        def send(self, payload):
            self.sent.append(json.loads(payload))

        def settimeout(self, _timeout):
            pass

        def recv(self):
            if self.sent and self.sent[-1].get("method") == "Fetch.getResponseBody":
                if not self.bodies:
                    raise TimeoutError("no body")
                return json.dumps(self.bodies.pop(0))
            if self.sent and self.sent[-1].get("method") in {"Fetch.disable", "Fetch.enable"}:
                return json.dumps({"id": self.sent[-1].get("id"), "result": {}})
            if self.events:
                return json.dumps(self.events.pop(0))
            raise TimeoutError("no event")

        def close(self):
            pass

    def _run_scihub_fetch_with_events(self, events, bodies, ticks):
        fake_ws = self._FakeScihubWs(events, bodies)
        with patch.object(scihub, "check_cdp", return_value=True), \
             patch.object(scihub, "get_tab_ws_url", return_value="ws://tab"), \
             patch.object(scihub.websocket, "create_connection", return_value=fake_ws), \
             patch.object(scihub.time, "sleep", return_value=None), \
             patch.object(scihub.time, "time", side_effect=ticks):
            pdf, status = scihub._fetch_pdf_via_navigate(
                9223, "https://sci-hub.test/paper.pdf", pdf_tab="tab-1", timeout=3
            )
        return pdf, status, fake_ws

    def test_scihub_fetch_continues_after_html_then_captures_pdf(self):
        pdf_bytes = self._valid_scihub_pdf_bytes()
        events = [
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "html-1",
                    "request": {"url": "https://sci-hub.test/landing"},
                    "responseHeaders": [{"name": "content-type", "value": "text/html"}],
                },
            },
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "pdf-1",
                    "request": {"url": "https://sci-hub.test/files/paper.pdf"},
                    "responseHeaders": [{"name": "content-type", "value": "application/pdf"}],
                },
            },
        ]
        bodies = [{"result": {"body": pdf_bytes.decode("latin-1"), "base64Encoded": False}}]

        pdf, status, fake_ws = self._run_scihub_fetch_with_events(
            events, bodies, ticks=[0, 0.5, 1.0]
        )

        self.assertEqual(status, "ok_pdf_captured")
        self.assertEqual(pdf, pdf_bytes)
        continue_requests = [m for m in fake_ws.sent if m.get("method") == "Fetch.continueRequest"]
        self.assertEqual(len(continue_requests), 2)

    def test_scihub_fetch_only_html_returns_non_pdf_seen(self):
        events = [
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "html-1",
                    "request": {"url": "https://sci-hub.test/landing"},
                    "responseHeaders": [{"name": "content-type", "value": "text/html"}],
                },
            }
        ]

        pdf, status, fake_ws = self._run_scihub_fetch_with_events(
            events, [], ticks=[0, 0.5, 1.0, 2.0, 4.0]
        )

        self.assertIsNone(pdf)
        self.assertEqual(status, "non_pdf_response_seen")
        continue_requests = [m for m in fake_ws.sent if m.get("method") == "Fetch.continueRequest"]
        self.assertEqual(len(continue_requests), 1)

    def test_scihub_fetch_invalid_pdf_like_body_does_not_succeed(self):
        events = [
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "pdf-1",
                    "request": {"url": "https://sci-hub.test/files/paper.pdf"},
                    "responseHeaders": [{"name": "content-type", "value": "application/pdf"}],
                },
            }
        ]
        bodies = [{"result": {"body": "<html>not a pdf</html>", "base64Encoded": False}}]

        pdf, status, fake_ws = self._run_scihub_fetch_with_events(
            events, bodies, ticks=[0, 0.5, 1.0, 2.0, 4.0]
        )

        self.assertIsNone(pdf)
        self.assertEqual(status, "pdf_like_response_invalid_body")
        continue_requests = [m for m in fake_ws.sent if m.get("method") == "Fetch.continueRequest"]
        self.assertEqual(len(continue_requests), 1)

    def test_scihub_fetch_probes_unknown_binary_content_type(self):
        pdf_bytes = self._valid_scihub_pdf_bytes()
        events = [
            {
                "method": "Fetch.requestPaused",
                "params": {
                    "requestId": "bin-1",
                    "request": {"url": "https://sci-hub.test/download?id=123"},
                    "responseHeaders": [{"name": "content-type", "value": "application/octet-stream"}],
                },
            }
        ]
        bodies = [{"result": {"body": pdf_bytes.decode("latin-1"), "base64Encoded": False}}]

        pdf, status, fake_ws = self._run_scihub_fetch_with_events(
            events, bodies, ticks=[0, 0.5, 1.0]
        )

        self.assertEqual(status, "ok_pdf_captured")
        self.assertEqual(pdf, pdf_bytes)
        get_body_requests = [m for m in fake_ws.sent if m.get("method") == "Fetch.getResponseBody"]
        self.assertEqual(len(get_body_requests), 1)

    def test_auto_sd_loader_reads_pii_map_as_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            pii_map = Path(tmp) / "sd_pii_map.json"
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            pii_map.write_text(
                """{
                  "resolved": {
                    "paper_001": {"doi": "10.1016/j.demo.2026.01.001", "pii": "S0000000000000001"}
                  }
                }""",
                encoding="utf-8",
            )

            remaining, done = auto_sd._load_remaining_papers(str(pii_map), str(out_dir))

        self.assertEqual(done, 0)
        self.assertEqual(remaining, [("paper_001", "10.1016/j.demo.2026.01.001", "S0000000000000001")])

    def test_auto_sd_loader_recognizes_completed_key_named_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            pii_map = Path(tmp) / "sd_pii_map.json"
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            pii_map.write_text(
                """{
                  "resolved": {
                    "S8RREAFT": {"doi": "10.1016/j.ijheatmasstransfer.2021.121612", "pii": "S0017931021007158"},
                    "WI9CIV79": {"doi": "10.1016/j.ijheatmasstransfer.2025.127378", "pii": "S0017931025007173"}
                  }
                }""",
                encoding="utf-8",
            )
            (out_dir / "S8RREAFT.pdf").write_bytes(b"%PDF-1.4\n")

            remaining, done = auto_sd._load_remaining_papers(str(pii_map), str(out_dir))

        self.assertEqual(done, 1)
        self.assertEqual(remaining, [("WI9CIV79", "10.1016/j.ijheatmasstransfer.2025.127378", "S0017931025007173")])

    def test_batch_resolve_pii_preserves_balanced_parentheses_in_old_doi(self):
        self.assertEqual(
            batch_resolve_pii._clean_doi("https://doi.org/10.1016/S0378-7753(03)00012-3)"),
            "10.1016/S0378-7753(03)00012-3",
        )
        self.assertEqual(
            batch_resolve_pii._clean_doi("10.1016/S0378-7753(03)00012-3"),
            "10.1016/S0378-7753(03)00012-3",
        )

    def test_auto_sd_worker_passes_timeout_overrides_to_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            results = {}
            papers = [("paper_001", "10.1016/j.demo.2026.01.001", "S0000000000000001")]

            with patch.object(auto_sd, "download_sd_pii", return_value=b"%PDF" + b"x" * 25000) as mock_download:
                auto_sd._worker("Chrome", 9223, papers, str(out_dir), results, auto_sd.threading.Lock(), 11, 27)
                self.assertTrue((out_dir / "paper_001.pdf").exists())

        mock_download.assert_called_once_with(9223, "S0000000000000001", timeout_a=11, timeout_b=27)

    def test_auto_sd_resolve_browsers_edge_uses_edge_only(self):
        args = auto_sd.argparse.Namespace(
            browser="edge",
            browser_path=None,
            browser_path_edge=None,
            port_chrome=9223,
            port_edge=9223,
        )
        with patch.object(auto_sd, "find_chrome_path", return_value=r"C:\Chrome\chrome.exe") as find_chrome, \
             patch.object(auto_sd, "find_edge_path", return_value=r"C:\Edge\msedge.exe"):
            browsers = auto_sd._resolve_browsers(args)

        find_chrome.assert_not_called()
        self.assertEqual(browsers, [("Edge", r"C:\Edge\msedge.exe", 9223, auto_sd.DEFAULT_PROFILES["edge"])])

    def test_run_generic_round_routes_sciencedirect_through_generic_cdp(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "10.1016_j.demo_2026.01.001.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n" + b"x" * 6000)
            with patch.object(router, "generic_download_one", return_value=(str(pdf_path), "ok", "sd_elsevier")) as download:
                downloaded, remaining, reasons = router.run_generic_round(
                    ["10.1016/j.demo.2026.01.001"], tmp, 9223
                )

        self.assertEqual(downloaded, ["10.1016/j.demo.2026.01.001"])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        download.assert_called_once_with(9223, "10.1016/j.demo.2026.01.001", tmp, include_si=False)

    def test_english_pipeline_old_doi_scihub_success_skips_oa_and_cdp(self):
        with patch.object(router, "run_scihub_round", return_value=(["10.1016/j.demo.2020.01.001"], [])) as scihub, \
             patch.object(router, "run_oa_fast_round") as oa_fast, \
             patch.object(router, "run_generic_round") as generic:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                ["10.1016/j.demo.2020.01.001"], "paper-temp", 9223
            )

        self.assertEqual(downloaded, ["10.1016/j.demo.2020.01.001"])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        self.assertEqual(results, [{"round": "Sci-Hub", "downloaded": ["10.1016/j.demo.2020.01.001"]}])
        scihub.assert_called_once()
        oa_fast.assert_not_called()
        generic.assert_not_called()

    def test_english_pipeline_old_doi_scihub_failure_then_oa_success_skips_cdp(self):
        doi = "10.1016/j.demo.2020.01.001"
        with patch.object(router, "run_scihub_round", return_value=([], [doi])) as scihub, \
             patch.object(router, "run_oa_fast_round", return_value=([doi], [], {})) as oa_fast, \
             patch.object(router, "run_generic_round") as generic:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                [doi], "paper-temp", 9223
            )

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        self.assertEqual(results[-1]["round"], "OA fast (public_pdf_verified)")
        scihub.assert_called_once()
        oa_fast.assert_called_once()
        generic.assert_not_called()

    def test_english_pipeline_2024_doi_skips_scihub_and_starts_oa_fast(self):
        doi = "10.1016/j.demo.2024.01.001"
        with patch.object(router, "run_scihub_round") as scihub, \
             patch.object(router, "run_oa_fast_round", return_value=([doi], [], {})) as oa_fast, \
             patch.object(router, "run_generic_round") as generic:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                [doi], "paper-temp", 9223
            )

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        scihub.assert_not_called()
        oa_fast.assert_called_once()
        generic.assert_not_called()

    def test_english_pipeline_skip_scihub_sends_old_doi_to_oa_fast(self):
        doi = "10.1016/j.demo.2020.01.001"
        with patch.object(router, "run_scihub_round") as scihub, \
             patch.object(router, "run_oa_fast_round", return_value=([doi], [], {})) as oa_fast:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                [doi], "paper-temp", 9223, skip_scihub=True
            )

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        scihub.assert_not_called()
        oa_fast.assert_called_once()

    def test_english_pipeline_skip_oa_fast_goes_to_generic_cdp(self):
        doi = "10.1016/j.demo.2024.01.001"
        with patch.object(router, "run_scihub_round") as scihub, \
             patch.object(router, "run_oa_fast_round") as oa_fast, \
             patch.object(router, "run_ieee_round", return_value=([], [doi])) as ieee_round, \
             patch.object(router, "run_generic_round", return_value=([doi], [], {})) as generic:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                [doi], "paper-temp", 9223, skip_oa_fast=True
            )

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        scihub.assert_not_called()
        oa_fast.assert_not_called()
        ieee_round.assert_called_once()
        generic.assert_called_once()

    def test_english_pipeline_routes_ieee_through_dedicated_round(self):
        doi = "10.1109/demo.2024.123"
        with patch.object(router, "run_scihub_round") as scihub, \
             patch.object(router, "run_oa_fast_round", return_value=([], [doi], {})) as oa_fast, \
             patch.object(router, "run_ieee_round", return_value=([doi], [])) as ieee_round, \
             patch.object(router, "run_generic_round") as generic:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                [doi], "paper-temp", 9223
            )

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        scihub.assert_not_called()
        oa_fast.assert_called_once()
        ieee_round.assert_called_once_with([doi], "paper-temp", 9223)
        generic.assert_not_called()
        self.assertEqual(results[-1]["round"], "IEEE CDP")

    def test_classify_english_oa_hints_marks_candidate_no_hint_and_unknown(self):
        dois = ["10.1016/j.demo.1", "10.1007/demo", "10.1021/demo"]
        hints = {
            "10.1016/j.demo.1": {"oa_pdf_url": "https://example.org/paper.pdf"},
            "10.1021/demo": {"oa_landing_url": "https://example.org/article", "oa_status": "maybe"},
        }

        classified = router.classify_english_oa_hints(dois, hints)

        self.assertEqual(classified["10.1016/j.demo.1"], "oa_candidate")
        self.assertEqual(classified["10.1007/demo"], "no_oa_hint")
        self.assertEqual(classified["10.1021/demo"], "unknown")

    def test_classify_oa_hint_treats_non_pdf_url_as_unknown(self):
        self.assertEqual(
            router.classify_oa_hint({"oa_pdf_url": "https://example.org/article"}),
            "unknown",
        )
        self.assertEqual(
            router.classify_oa_hint({"oa_status": "gold", "oa_source": "unpaywall"}),
            "oa_candidate",
        )

    def test_oa_fast_invalid_html_candidate_continues_to_cdp(self):
        doi = "10.1016/j.demo.2024.01.001"
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(router, "_fetch_url_bytes", return_value=(b"<html>not a pdf</html>" + b"x" * 6000, "text/html")):
            downloaded, remaining, reasons = router.run_oa_fast_round(
                [doi],
                tmp,
                oa_hints={doi: {"oa_pdf_url": "https://example.org/demo.pdf"}},
                use_resolver=False,
            )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, [doi])
        self.assertEqual(reasons[doi], "invalid_oa_candidate")

    def test_oa_fast_uses_whitelist_reason_for_known_oa_failure(self):
        doi = "10.3390/demo"
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(router, "_fetch_url_bytes", return_value=(b"<html>not a pdf</html>" + b"x" * 6000, "text/html")), \
             patch.object(router, "resolve_publisher", return_value={"strategy": "generic", "_key": "mdpi", "requires_auth": "none"}):
            downloaded, remaining, reasons = router.run_oa_fast_round(
                [doi],
                tmp,
                oa_hints={doi: {"oa_pdf_url": "https://example.org/demo.pdf", "oa_status": "gold"}},
                use_resolver=False,
            )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, [doi])
        self.assertEqual(reasons[doi], "oa_whitelist_but_verification_failed")

    def test_oa_candidate_failed_verification_reaches_generic_cdp(self):
        doi = "10.1016/j.demo.2024.01.001"
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(router, "run_scihub_round") as scihub, \
             patch.object(router, "_fetch_url_bytes", return_value=(b"<html>not a pdf</html>" + b"x" * 6000, "text/html")), \
             patch.object(router, "run_ieee_round", return_value=([], [doi])) as ieee_round, \
             patch.object(router, "run_generic_round", return_value=([doi], [], {})) as generic:
            downloaded, remaining, results, reasons = router.run_english_pipeline(
                [doi],
                tmp,
                9223,
                oa_hints={doi: {"oa_pdf_url": "https://example.org/demo.pdf"}},
            )

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertIn({"round": "OA fast (public_pdf_verified)", "downloaded": []}, results)
        self.assertEqual(results[-1]["round"], "Generic CDP")
        scihub.assert_not_called()
        ieee_round.assert_called_once()
        generic.assert_called_once_with([doi], tmp, 9223, include_si=False)


    def test_oa_fast_valid_public_pdf_downloads_and_marks_verified(self):
        doi = "10.1016/j.demo.2024.01.001"
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(router, "_fetch_url_bytes", return_value=(self._valid_pdf_bytes(), "application/pdf")):
            downloaded, remaining, reasons = router.run_oa_fast_round(
                [doi],
                tmp,
                oa_hints={doi: {"oa_pdf_url": "https://example.org/demo.pdf"}},
                use_resolver=False,
            )
            pdf_path = Path(tmp) / "10.1016_j.demo.2024.01.001.pdf"

            self.assertTrue(pdf_path.exists())

        self.assertEqual(downloaded, [doi])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})

    def test_sd_download_strategy_b_uses_timeout_for_article_page_wait(self):
        with patch.object(sd_download, "_extract_pdfft_url", return_value="https://example.com/pdfft?md5=abc") as mock_extract, \
             patch.object(sd_download, "_navigate_and_capture", return_value=b"%PDFdemo") as mock_capture:
            pdf = sd_download._strategy_b(9223, "S0000000000000001", timeout=17)

        self.assertEqual(pdf, b"%PDFdemo")
        mock_extract.assert_called_once_with(9223, "S0000000000000001", render_timeout=17)
        mock_capture.assert_called_once_with(9223, "https://example.com/pdfft?md5=abc", redirect_timeout=17, capture_timeout=20)

    def test_parallel_sd_worker_passes_timeout_overrides_to_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            papers = [("paper_001", "10.1016/j.demo.2026.01.001", "S0000000000000001")]

            with patch.object(parallel_sd, "download_sd_pii", return_value=b"%PDF" + b"x" * 25000) as mock_download:
                parallel_sd.worker("Chrome", 9223, papers, str(out_dir), 9, 21)
                self.assertTrue((out_dir / "paper_001.pdf").exists())

        mock_download.assert_called_once_with(9223, "S0000000000000001", timeout_a=9, timeout_b=21)

    def test_sd_access_probe_uses_current_known_good_pii_sample(self):
        self.assertEqual(cdp_utils._SD_TEST_DOI, "10.1016/j.est.2024.113105")
        self.assertIn("S2352152X24026914", cdp_utils._SD_TEST_URL)
        self.assertTrue(cdp_utils._SD_TEST_URL.endswith("/pdfft"))

    def test_sd_access_probe_unknown_article_page_is_blocked(self):
        tabs = [{
            "id": "tab-1",
            "url": "https://www.sciencedirect.com/science/article/pii/S2352152X24026914",
            "title": "Article page - ScienceDirect",
        }]
        with patch.object(cdp_utils, "check_cdp", return_value=True), \
             patch.object(cdp_utils, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(cdp_utils.websocket, "create_connection") as create_connection, \
             patch.object(cdp_utils, "list_tabs", return_value=tabs), \
             patch.object(cdp_utils, "close_tab") as close_tab, \
             patch.object(cdp_utils.time, "sleep", return_value=None):
            ws = create_connection.return_value
            ws.recv.return_value = '{"result":{"targetId":"tab-1"}}'

            status, reason = cdp_utils.check_sd_access(9223)

        self.assertEqual(status, "blocked")
        self.assertIn("pdf probe unknown", reason)
        close_tab.assert_called_with(9223, "tab-1")

    def test_sd_access_probe_pdf_redirect_is_ok(self):
        tabs = [{
            "id": "tab-1",
            "url": "https://pdf.sciencedirectassets.com/demo/main.pdf",
            "title": "main.pdf",
        }]
        with patch.object(cdp_utils, "check_cdp", return_value=True), \
             patch.object(cdp_utils, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(cdp_utils.websocket, "create_connection") as create_connection, \
             patch.object(cdp_utils, "list_tabs", return_value=tabs), \
             patch.object(cdp_utils, "close_tab") as close_tab, \
             patch.object(cdp_utils.time, "sleep", return_value=None):
            ws = create_connection.return_value
            ws.recv.return_value = '{"result":{"targetId":"tab-1"}}'

            status, reason = cdp_utils.check_sd_access(9223)

        self.assertEqual((status, reason), ("ok", "pdf_probe_ok"))
        close_tab.assert_called_with(9223, "tab-1")

    def test_sd_download_diagnosis_detects_referencework_and_verification(self):
        tabs = [
            {"id": "ref", "url": "https://www.sciencedirect.com/science/chapter/referencework/abs/pii/B9780323960205000388", "title": "Book chapter - ScienceDirect"},
            {"id": "chk", "url": "https://www.sciencedirect.com/science/article/pii/S0000", "title": "请稍候…"},
        ]
        with patch.object(sd_download, "list_tabs", return_value=tabs):
            ref_state = sd_download._inspect_sd_tab_state(9223, "ref")
            chk_state = sd_download._inspect_sd_tab_state(9223, "chk")

        self.assertEqual(ref_state["kind"], "referencework_abs")
        self.assertEqual(chk_state["kind"], "manual_verification_required")

    def test_console_compat_translates_status_symbols_for_ascii_mode(self):
        with patch.dict("os.environ", {"MORE_PAPER_SYMBOLS": "ascii"}):
            self.assertEqual(console_compat.symbol("ok"), "[OK]")
            self.assertEqual(console_compat.replace_status_symbols("✅ → ❌"), "[OK] -> [FAIL]")

    def test_child_python_env_sets_utf8_backslashreplace(self):
        env = console_compat.configure_child_python_utf8_env({"EXISTING": "1"})

        self.assertEqual(env["EXISTING"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8:backslashreplace")

    def test_parse_chinese_papers_from_markdown_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chinese.md"
            path.write_text(
                "\n".join([
                    "| 来源 | 标题 | DOI | 文章链接 |",
                    "|---|---|---|---|",
                    "| cnki | 薄壁管弯曲回弹研究 | cnki.demo | https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test |",
                    "| wanfang | 无链接条目 | wanfang.demo |  |",
                ]),
                encoding="utf-8",
            )

            papers = router.parse_chinese_papers(str(path))

        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0]["source"], "cnki")
        self.assertTrue(papers[0]["article_url"].startswith("https://kns.cnki.net/"))
        self.assertEqual(papers[0]["doi"], "cnki.demo")
        self.assertEqual(papers[1]["source"], "wanfang")
        self.assertEqual(papers[1]["article_url"], "")

    def test_parse_chinese_papers_from_json_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chinese.json"
            path.write_text(
                """[
                  {"title": "万方论文", "source": "wanfang", "article_url": "https://www.wanfangdata.com.cn/details/detail.do?_type=perio&id=test", "source_id": "wanfang.test"}
                ]""",
                encoding="utf-8",
            )

            papers = router.parse_chinese_papers(str(path))

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["source"], "wanfang")
        self.assertIn("wanfangdata.com.cn", papers[0]["article_url"])
        self.assertEqual(papers[0]["doi"], "wanfang.test")

    def test_parse_doi_file_reads_one_doi_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dois.txt"
            path.write_text("\n".join([
                "# comment",
                "10.1016/j.test.2024.01.001",
                "",
                "10.1007/demo.2024.1",
            ]), encoding="utf-8")

            dois = router.parse_doi_file(str(path))

        self.assertEqual(dois, ["10.1016/j.test.2024.01.001", "10.1007/demo.2024.1"])

    def test_parse_bibtex_chinese_papers_extracts_cnki_doi_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.bib"
            path.write_text("""
@article{english,
  title = {Battery Thermal Management},
  doi = {10.1016/j.est.2025.117285},
  langid = {english}
}

@article{cnki,
  title = {电动汽车充电桩电源模块热仿真分析},
  doi = {10.16638/j.cnki.1671-7988.2022.011.001},
  langid = {chinese}
}
""", encoding="utf-8")

            papers = router.parse_bibtex_chinese_papers(str(path))

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["source"], "cnki")
        self.assertEqual(papers[0]["doi"], "10.16638/j.cnki.1671-7988.2022.011.001")

    def test_show_chinese_login_gate_accepts_confirmed_login(self):
        papers = [{
            "title": "CNKI demo",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
        }]

        with patch.object(router, "open_chinese_login_tabs", return_value={"opened": [], "failed": []}) as open_tabs, \
             patch("builtins.input", return_value="已登录继续"), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertTrue(router.show_chinese_login_gate(papers))
        open_tabs.assert_called_once_with(router.CDP_PORT, papers)
        text = stdout.getvalue()
        self.assertIn("不接受数字 1/2/3", text)
        self.assertIn("  已登录继续", text)
        self.assertIn("  跳过登录", text)
        self.assertIn("  稍后重试", text)
        self.assertNotIn("没有账号，跳过并继续", text)
        self.assertNotIn("稍后重试（写 checkpoint", text)

    def test_show_chinese_login_gate_skip_is_explicit_false(self):
        papers = [{
            "title": "CNKI demo",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
        }]
        with patch.object(router, "open_chinese_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", return_value="跳过登录"):
            self.assertFalse(router.show_chinese_login_gate(papers))

    def test_open_chinese_login_tabs_deduplicates_sources(self):
        papers = [
            {
                "title": "CNKI demo",
                "source": "cnki",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
            },
            {
                "title": "CNKI demo 2",
                "source": "cnki",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=test2",
            },
            {
                "title": "Wanfang demo",
                "source": "wanfang",
                "article_url": "https://d.wanfangdata.com.cn/periodical/demo",
            },
        ]
        with patch.object(router, "create_tab", return_value=(None, "tab-1")) as create_tab:
            result = router.open_chinese_login_tabs(9223, papers)

        self.assertEqual(result["failed"], [])
        self.assertEqual(result["opened"], [
            "cnki (https://kns.cnki.net/kns8s/)",
            "wanfang (https://www.wanfangdata.com.cn/)",
        ])
        opened_urls = [call.args[1] for call in create_tab.call_args_list]
        self.assertEqual(opened_urls, [
            "https://kns.cnki.net/kns8s/",
            "https://www.wanfangdata.com.cn/",
        ])

    def test_show_chinese_login_gate_defer_and_eof_return_none(self):
        papers = [{
            "title": "CNKI demo",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
        }]
        with patch.object(router, "open_chinese_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", return_value="稍后重试"):
            self.assertIsNone(router.show_chinese_login_gate(papers))
        with patch.object(router, "open_chinese_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(router.show_chinese_login_gate(papers))

    def test_show_chinese_login_gate_numeric_shortcuts_return_none(self):
        papers = [{
            "title": "CNKI demo",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
        }]
        for response in ("1", "2", "3"):
            with self.subTest(response=response), \
                 patch.object(router, "open_chinese_login_tabs", return_value={"opened": [], "failed": []}), \
                 patch("builtins.input", return_value=response):
                self.assertIsNone(router.show_chinese_login_gate(papers))

    def test_chinese_round_cnki_captcha_auto_retry_after_monitor_ready(self):
        paper = {
            "title": "CNKI demo",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
            "doi": "cnki.demo",
        }
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(
                 router,
                 "_download_chinese_paper_once",
                 side_effect=[
                     (None, "captcha_required", "cnki"),
                     (str(Path(tmp) / "cnki.demo.pdf"), "ok", "cnki"),
                 ],
             ) as download_once, \
             patch.object(router, "_wait_for_cnki_captcha_resolution", return_value="ready") as wait_captcha, \
             patch.object(router, "_confirm_cnki_captcha_resolution") as confirm_captcha, \
             patch.object(router.os.path, "getsize", return_value=6144):
            downloaded, remaining, reasons = router.run_chinese_round_with_reasons([paper], tmp, 9223)

        self.assertEqual(downloaded, ["cnki.demo"])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        self.assertEqual(download_once.call_count, 2)
        wait_captcha.assert_called_once_with(paper, 9223)
        confirm_captcha.assert_not_called()

    def test_chinese_round_cnki_captcha_page_lost_auto_recovers_before_prompt(self):
        paper = {
            "title": "CNKI demo",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
            "doi": "cnki.demo",
        }
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(
                 router,
                 "_download_chinese_paper_once",
                 return_value=(None, "captcha_required", "cnki"),
             ) as download_once, \
             patch.object(router, "_wait_for_cnki_captcha_resolution", return_value="page_lost") as wait_captcha, \
             patch.object(
                 router,
                 "_auto_retry_cnki_current_paper",
                 return_value=(str(Path(tmp) / "cnki.demo.pdf"), "ok", 0.3),
             ) as auto_retry, \
             patch.object(router, "_confirm_cnki_captcha_resolution") as confirm_captcha, \
             patch.object(router.os.path, "getsize", return_value=6144):
            downloaded, remaining, reasons = router.run_chinese_round_with_reasons([paper], tmp, 9223)

        self.assertEqual(downloaded, ["cnki.demo"])
        self.assertEqual(remaining, [])
        self.assertEqual(reasons, {})
        download_once.assert_called_once_with(paper, tmp, 9223)
        wait_captcha.assert_called_once_with(paper, 9223)
        auto_retry.assert_called_once_with(paper, tmp, 9223, "page_lost")
        confirm_captcha.assert_not_called()

    def test_chinese_round_cnki_captcha_timeout_writes_checkpoint_for_remaining(self):
        papers = [
            {
                "title": "CNKI demo 1",
                "source": "cnki",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test1",
                "doi": "cnki.demo1",
            },
            {
                "title": "CNKI demo 2",
                "source": "cnki",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test2",
                "doi": "cnki.demo2",
            },
        ]
        checkpoint_remaining = ["cnki.demo1", "cnki.demo2"]
        checkpoint_reasons = {
            "cnki.demo1": "captcha_required",
            "cnki.demo2": "captcha_required",
        }
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(
                 router,
                 "_download_chinese_paper_once",
                 return_value=(None, "captcha_required", "cnki"),
             ) as download_once, \
             patch.object(router, "_wait_for_cnki_captcha_resolution", return_value="timeout") as wait_captcha, \
             patch.object(router, "_confirm_cnki_captcha_resolution") as confirm_captcha, \
             patch.object(
                 router,
                 "_checkpoint_pending_chinese_papers",
                 return_value=("paper-temp/chinese_login_checkpoint.json", checkpoint_remaining, checkpoint_reasons),
             ) as checkpoint_pending:
            downloaded, remaining, reasons = router.run_chinese_round_with_reasons(papers, tmp, 9223)

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, checkpoint_remaining)
        self.assertEqual(reasons, checkpoint_reasons)
        download_once.assert_called_once_with(papers[0], tmp, 9223)
        wait_captcha.assert_called_once_with(papers[0], 9223)
        confirm_captcha.assert_not_called()
        checkpoint_pending.assert_called_once()
        pending_papers = checkpoint_pending.call_args.args[0]
        self.assertEqual([paper["doi"] for paper in pending_papers], checkpoint_remaining)
        self.assertTrue(all(paper["failure_reason"] == "captcha_required" for paper in pending_papers))

    def test_show_english_login_gate_lists_cdp_publishers(self):
        dois = [
            "10.1016/j.test.2024.01.001",
            "10.1109/test.2024.00001",
            "10.1038/s41467-2024-00001",
        ]

        with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}) as open_tabs, \
             patch("builtins.input", return_value="已登录"), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertTrue(router.show_english_login_gate(dois))
        open_tabs.assert_called_once_with(router.CDP_PORT, dois)
        text = stdout.getvalue()
        self.assertIn("[IEEE CDP]", text)
        self.assertIn("只有部分权限也选 1", text)
        self.assertIn("  2) 跳过登录", text)
        self.assertIn("  3) 稍后重试", text)
        self.assertNotIn("没有账号，跳过并继续", text)
        self.assertNotIn("稍后重试（写 checkpoint", text)

    def test_show_english_login_gate_noninteractive_returns_none(self):
        with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}) as open_tabs:
            self.assertIsNone(
                router.show_english_login_gate(
                    ["10.1016/j.test.2024.01.001"],
                    port=9444,
                    interactive=False,
                )
            )
        open_tabs.assert_called_once_with(9444, ["10.1016/j.test.2024.01.001"])

    def test_show_english_login_gate_eoferror_returns_none(self):
        with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(router.show_english_login_gate(["10.1016/j.test.2024.01.001"]))

    def test_open_english_login_tabs_deduplicates_publishers(self):
        dois = [
            "10.1016/j.demo.2026.01.001",
            "10.1016/j.demo.2026.01.002",
            "10.1109/demo.2026.001",
        ]
        with patch.object(router, "create_tab", return_value=(None, "tab-1")) as create_tab:
            result = router.open_english_login_tabs(9223, dois)

        self.assertEqual(result["failed"], [])
        self.assertEqual(len(result["opened"]), 2)
        opened_urls = [call.args[1] for call in create_tab.call_args_list]
        self.assertEqual(
            opened_urls,
            ["https://ieeexplore.ieee.org/", "https://www.sciencedirect.com/"],
        )

    def test_open_english_login_tabs_only_uses_login_candidate_dois(self):
        pub_map = {
            "10.1109/demo": {
                "strategy": "ieee_cdp",
                "_key": "ieee",
                "publisher_domain": "ieeexplore.ieee.org",
                "login_url": "https://ieeexplore.ieee.org/",
                "requires_auth": "sso",
            },
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "login_url": "https://wayf.springernature.com/?redirect_uri=https%3A%2F%2Flink.springer.com%2F",
                "requires_auth": "institution",
            },
            "10.3389/demo": {
                "strategy": "direct_http",
                "_key": "frontiers",
                "publisher_domain": "www.frontiersin.org",
                "requires_auth": "none",
            },
            "10.3390/demo": {
                "strategy": "generic",
                "_key": "mdpi",
                "publisher_domain": "www.mdpi.com",
                "requires_auth": "none",
            },
        }
        with patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]), \
             patch.object(router, "create_tab", return_value=(None, "tab-1")) as create_tab:
            result = router.open_english_login_tabs(9223, list(pub_map))

        self.assertEqual(result["failed"], [])
        self.assertEqual(result["opened"], [
            "ieee (https://ieeexplore.ieee.org/)",
            "springer (https://wayf.springernature.com/?redirect_uri=https%3A%2F%2Flink.springer.com%2F)",
        ])
        self.assertEqual(
            [call.args for call in create_tab.call_args_list],
            [
                (9223, "https://ieeexplore.ieee.org/"),
                (9223, "https://wayf.springernature.com/?redirect_uri=https%3A%2F%2Flink.springer.com%2F"),
            ],
        )

    def test_open_english_login_tabs_falls_back_to_publisher_domain(self):
        with patch.object(router, "resolve_publisher", return_value={
            "strategy": "generic",
            "_key": "custom",
            "publisher_domain": "example.org",
            "requires_auth": "institution",
        }), patch.object(router, "create_tab", return_value=(None, "tab-1")) as create_tab:
            result = router.open_english_login_tabs(9223, ["10.5555/demo"])

        self.assertEqual(result["opened"], ["custom (https://example.org/)"])
        create_tab.assert_called_once_with(9223, "https://example.org/")

    def test_open_english_login_tabs_records_create_tab_failures(self):
        with patch.object(router, "resolve_publisher", return_value={
            "strategy": "generic",
            "_key": "custom",
            "publisher_domain": "example.org",
            "requires_auth": "institution",
        }), patch.object(router, "create_tab", side_effect=RuntimeError("cdp down")):
            result = router.open_english_login_tabs(9223, ["10.5555/demo"])

        self.assertEqual(result["opened"], [])
        self.assertIn("custom (https://example.org/) - cdp down", result["failed"])

    def test_ensure_cdp_running_reuses_existing_browser(self):
        with patch.object(router, "check_cdp", return_value=True), \
             patch.object(router, "cdp_browser_matches", return_value=True):
            self.assertTrue(router.ensure_cdp_running(9223))

    def test_ensure_cdp_running_auto_starts_browser(self):
        with patch.object(router, "check_cdp", side_effect=[False, True]), \
             patch.object(router, "cdp_browser_matches", return_value=True), \
             patch.object(router, "start_persistent_cdp_browser") as starter:
            self.assertTrue(router.ensure_cdp_running(9223))
        starter.assert_called_once()

    def test_ensure_cdp_running_restarts_when_existing_browser_mismatches(self):
        with patch.object(router, "check_cdp", side_effect=[True, True]), \
             patch.object(router, "cdp_browser_matches", side_effect=[False, True]), \
             patch.object(router, "get_cdp_browser_product", return_value="Microsoft Edge/125.0"), \
             patch.object(router, "start_persistent_cdp_browser") as starter:
            self.assertTrue(router.ensure_cdp_running(9223, browser="chrome"))

        starter.assert_called_once_with(
            port=9223,
            browser="chrome",
            urls=["https://www.sciencedirect.com/"],
        )

    def test_cdp_browser_matches_distinguishes_chrome_from_edge(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def read(self):
                return self.payload.encode("utf-8")

        with patch.object(cdp_utils.urllib.request, "urlopen", return_value=FakeResponse('{"Browser":"Microsoft Edge/125.0"}')):
            self.assertTrue(cdp_utils.cdp_browser_matches(9223, "edge"))
            self.assertFalse(cdp_utils.cdp_browser_matches(9223, "chrome"))

        with patch.object(cdp_utils.urllib.request, "urlopen", return_value=FakeResponse('{"Browser":"Chrome/125.0"}')):
            self.assertTrue(cdp_utils.cdp_browser_matches(9223, "chrome"))
            self.assertFalse(cdp_utils.cdp_browser_matches(9223, "edge"))

    def test_dry_run_classification_includes_chinese_and_english_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            chinese_path = Path(tmp) / "chinese.json"
            chinese_path.write_text(
                """[
                  {"title": "中文论文", "source": "cnki", "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test", "doi": "cnki.test"}
                ]""",
                encoding="utf-8",
            )

            chinese_papers = router.parse_chinese_papers(str(chinese_path))
            classified = [router.classify_doi("10.1016/j.test.2024.01.001")]
            for paper in chinese_papers:
                c = router.classify_doi(paper.get("doi", ""))
                c["strategy"] = "chinese_cdp"
                c["publisher"] = paper["source"]
                classified.append(c)

        strategies = {item["strategy"] for item in classified}
        self.assertIn("generic", strategies)
        self.assertIn("chinese_cdp", strategies)

    def test_dry_run_writes_plan_artifacts_without_browser_lock_or_download_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = [
                "unified_download_router.py",
                "--papers",
                "10.1109/demo,10.1007/demo",
                "--output",
                tmp,
                "--dry-run",
            ]
            with patch.object(sys, "argv", argv), \
                 patch.object(router, "check_cdp") as check_cdp, \
                 patch.object(router, "acquire_or_exit_step5_download_lock") as acquire_lock, \
                 patch.object(router, "ensure_cdp_running") as ensure_cdp, \
                 patch.object(router, "run_scihub_round") as scihub, \
                 patch.object(router, "run_oa_fast_round") as oa_fast, \
                 patch.object(router, "run_english_cdp") as english_cdp, \
                 patch("sys.stdout", new_callable=io.StringIO):
                router.main()

            manifest_path = Path(tmp) / "download_manifest.json"
            preflight_path = Path(tmp) / "preflight_summary.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            preflight = json.loads(preflight_path.read_text(encoding="utf-8"))

        check_cdp.assert_not_called()
        acquire_lock.assert_not_called()
        ensure_cdp.assert_not_called()
        scihub.assert_not_called()
        oa_fast.assert_not_called()
        english_cdp.assert_not_called()
        self.assertEqual("dry_run", manifest["summary"]["execution_mode"])
        self.assertEqual(2, manifest["summary"]["total"])
        self.assertEqual(0, manifest["summary"]["downloaded"])
        self.assertEqual({"unresolved"}, {item["status"] for item in manifest["items"]})
        self.assertTrue(all(item["attempts"] == [] for item in manifest["items"]))
        self.assertFalse(preflight["cdp"]["checked"])
        self.assertFalse((Path(tmp) / "download_attempts.jsonl").exists())
        self.assertFalse((Path(tmp) / "login_checkpoint.json").exists())

    def test_dry_run_records_missing_chinese_url_as_unresolved_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = router.write_step5_dry_run_outputs(
                tmp,
                [{"id": "cnki.demo", "doi": "cnki.demo", "source": "cnki", "title": "中文论文"}],
                {"total_items": 1, "cdp": {"checked": False, "ok": False}},
            )
            manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
            unresolved = Path(paths["unresolved"]).read_text(encoding="utf-8")

        self.assertEqual("missing_article_url", manifest["items"][0]["failure_reason"])
        self.assertIn("cnki.demo", manifest["recovery_buckets"]["needs_metadata_fix"])
        self.assertIn("missing_article_url", unresolved)

    def test_main_defaults_output_to_input_sibling_paper_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "demo.bib"
            input_path.write_text(
                "@article{demo,\n"
                "  title = {Demo},\n"
                "  doi = {10.1007/demo}\n"
                "}\n",
                encoding="utf-8",
            )
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                str(input_path),
                "--dry-run",
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                router.main()

        self.assertIn(
            f"Output directory:  {Path(tmp) / 'paper-temp'}/",
            stdout.getvalue(),
        )

    def test_wanfang_article_url_parser_supports_detail_and_d_urls(self):
        cases = [
            (
                "https://d.wanfangdata.com.cn/periodical/demo123",
                ("periodical", "demo123", "https://d.wanfangdata.com.cn/periodical/demo123"),
            ),
            (
                "https://d.wanfangdata.com.cn/thesis/demo456",
                ("thesis", "demo456", "https://d.wanfangdata.com.cn/thesis/demo456"),
            ),
            (
                "https://www.wanfangdata.com.cn/details/detail.do?_type=perio&id=perio789",
                ("periodical", "perio789", "https://d.wanfangdata.com.cn/periodical/perio789"),
            ),
            (
                "https://www.wanfangdata.com.cn/details/detail.do?_type=thesis&id=thesis789",
                ("thesis", "thesis789", "https://d.wanfangdata.com.cn/thesis/thesis789"),
            ),
        ]

        for url, expected in cases:
            self.assertEqual(gpd._parse_wanfang_article_url(url), expected)

    def test_wanfang_periodical_expression_clicks_download_only(self):
        js = gpd._wanfang_detail_click_expression("periodical")

        self.assertIn("allowed = ['下载']", js)
        self.assertIn("在线阅读", js)
        self.assertIn("评审材料", js)
        self.assertNotIn("allowed = ['整篇下载', '下载']", js)
        self.assertNotIn("分章下载')", js)

    def test_wanfang_thesis_expression_clicks_whole_paper_only(self):
        js = gpd._wanfang_detail_click_expression("thesis")

        self.assertIn("allowed = ['整篇下载', '下载']", js)
        self.assertIn("在线阅读", js)
        self.assertIn("分章下载", js)

    def test_wanfang_download_info_page_clicks_do_download(self):
        class FakeWs:
            def __init__(self):
                self.sent = []

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def recv(self):
                return json.dumps({"result": {"result": {"value": "clicked_doDownload"}}})

            def close(self):
                pass

        fake_ws = FakeWs()
        with patch.object(gpd, "list_tabs", return_value=[
            {"id": "tab-1", "url": "https://d.wanfangdata.com.cn/thesis/D03731170"},
            {"id": "tab-2", "url": "https://f.wanfangdata.com.cn/download/pc/thesis/D03731170?transaction=x"},
        ]), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://tab-2"), \
             patch.object(gpd.websocket, "create_connection", return_value=fake_ws):
            result = gpd._wanfang_click_download_info_page(9223)

        self.assertEqual(result, "clicked_doDownload")
        expression = fake_ws.sent[0]["params"]["expression"]
        self.assertIn("#doDownload", expression)
        self.assertIn("点击此处", expression)

    def test_wanfang_download_info_page_prefers_new_tab(self):
        class FakeWs:
            def __init__(self, value):
                self.value = value

            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"result": {"value": self.value}}})

            def close(self):
                pass

        opened = []

        def fake_connection(ws_url, timeout=10):
            opened.append(ws_url)
            return FakeWs("clicked_doDownload")

        with patch.object(gpd, "list_tabs", return_value=[
            {"id": "old-tab", "url": "https://f.wanfangdata.com.cn/download/pc/thesis/old?transaction=x"},
            {"id": "new-tab", "url": "https://f.wanfangdata.com.cn/download/pc/thesis/D03731170?transaction=y"},
        ]), \
             patch.object(gpd, "get_tab_ws_url", side_effect=lambda _port, tab_id: f"ws://{tab_id}"), \
             patch.object(gpd.websocket, "create_connection", side_effect=fake_connection):
            result = gpd._wanfang_click_download_info_page(9223, known_tab_ids={"old-tab"})

        self.assertEqual(result, "clicked_doDownload")
        self.assertEqual(opened, ["ws://new-tab"])

    def test_wait_for_wanfang_download_info_click_retries_until_tab_appears(self):
        class FakeWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"result": {"value": "clicked_doDownload"}}})

            def close(self):
                pass

        tab_snapshots = [
            [{"id": "detail-tab", "url": "https://d.wanfangdata.com.cn/thesis/D03731170"}],
            [{"id": "download-tab", "url": "https://f.wanfangdata.com.cn/download/pc/thesis/D03731170?transaction=x"}],
        ]

        time_points = iter([100.0, 100.5, 101.5, 102.0])

        with patch.object(gpd, "list_tabs", side_effect=tab_snapshots), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://download-tab"), \
             patch.object(gpd.websocket, "create_connection", return_value=FakeWs()), \
             patch.object(gpd.time, "sleep", return_value=None), \
             patch.object(gpd.time, "time", side_effect=lambda: next(time_points)):
            result = gpd._wait_for_wanfang_download_info_click(9223, timeout=3)

        self.assertEqual(result, "clicked_doDownload")

    def test_wait_for_wanfang_interstitial_click_retries_until_link_appears(self):
        time_points = iter([100.0, 100.5, 101.5, 102.0])

        with patch.object(gpd, "_wanfang_click_download_interstitial", side_effect=["not_found", "clicked"]), \
             patch.object(gpd.time, "sleep", return_value=None), \
             patch.object(gpd.time, "time", side_effect=lambda: next(time_points)):
            result = gpd._wait_for_wanfang_interstitial_click(9223, "detail-tab", timeout=3)

        self.assertEqual(result, "clicked")

    def test_download_wanfang_starts_download_window_after_info_click(self):
        class FakeBrowserWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"targetId": "detail-tab"}})

            def close(self):
                pass

        class FakeTabWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"result": {"value": "clicked:下载"}}})

            def close(self):
                pass

        time_points = iter([100.0, 130.0])

        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(gpd, "_parse_wanfang_article_url", return_value=("thesis", "D03731170", "https://d.wanfangdata.com.cn/thesis/D03731170")), \
             patch.object(gpd, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(gpd.websocket, "create_connection", side_effect=[FakeBrowserWs(), FakeTabWs()]), \
             patch.object(gpd, "list_tabs", return_value=[]), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://detail-tab"), \
             patch.object(gpd, "_wanfang_real_click_target", return_value="clicked_real:下载"), \
             patch.object(gpd, "_wait_for_wanfang_interstitial_click", return_value="not_found"), \
             patch.object(gpd, "_wait_for_wanfang_download_info_click", return_value="clicked_doDownload"), \
             patch.object(gpd.time, "sleep", return_value=None), \
             patch.object(gpd.time, "time", side_effect=lambda: next(time_points)), \
             patch("glob.glob", side_effect=[
                 [],
                 [os.path.join(tmpdir, "paper.pdf")],
                 [],
             ]), \
             patch("os.path.getmtime", return_value=131.0), \
             patch("os.path.getsize", return_value=6001), \
             patch.object(gpd, "_archive_browser_download", return_value=os.path.join(tmpdir, "wanfang.pdf")) as archive, \
             patch.object(gpd, "close_tab"):
            path = gpd._download_wanfang(9223, "https://d.wanfangdata.com.cn/thesis/D03731170", {}, output_dir=tmpdir)

        self.assertTrue(str(path).endswith(".pdf"))
        archive.assert_called_once()

    def test_download_wanfang_prefers_primary_detail_download_before_fallback(self):
        class FakeBrowserWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"targetId": "detail-tab"}})

            def close(self):
                pass

        class FakeTabWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"result": {"value": "clicked:下载"}}})

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(gpd, "_parse_wanfang_article_url", return_value=("periodical", "wf-demo", "https://d.wanfangdata.com.cn/periodical/wf-demo")), \
             patch.object(gpd, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(gpd.websocket, "create_connection", side_effect=[FakeBrowserWs(), FakeTabWs()]), \
             patch.object(gpd, "list_tabs", return_value=[]), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://detail-tab"), \
             patch.object(gpd, "_wanfang_real_click_target", return_value="clicked_real:下载"), \
             patch.object(gpd, "_wait_for_downloaded_pdf", side_effect=[os.path.join(tmpdir, "paper.pdf")]) as wait_pdf, \
             patch.object(gpd, "_wait_for_wanfang_interstitial_click") as wait_interstitial, \
             patch.object(gpd, "_wait_for_wanfang_download_info_click") as wait_info, \
             patch.object(gpd, "_archive_browser_download", return_value=os.path.join(tmpdir, "wanfang.pdf")) as archive, \
             patch.object(gpd, "close_tab"):
            path = gpd._download_wanfang(
                9223,
                "https://d.wanfangdata.com.cn/periodical/wf-demo",
                {},
                output_dir=tmpdir,
            )

        self.assertTrue(str(path).endswith(".pdf"))
        self.assertEqual(wait_pdf.call_count, 1)
        wait_interstitial.assert_not_called()
        wait_info.assert_not_called()
        archive.assert_called_once()

    def test_download_wanfang_accepts_interstitial_click_without_info_page_click(self):
        class FakeBrowserWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"targetId": "detail-tab"}})

            def close(self):
                pass

        class FakeTabWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"result": {"value": "clicked:下载"}}})

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(gpd, "_parse_wanfang_article_url", return_value=("periodical", "wf-demo", "https://d.wanfangdata.com.cn/periodical/wf-demo")), \
             patch.object(gpd, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(gpd.websocket, "create_connection", side_effect=[FakeBrowserWs(), FakeTabWs()]), \
             patch.object(gpd, "list_tabs", return_value=[]), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://detail-tab"), \
             patch.object(gpd, "_wanfang_real_click_target", return_value="clicked_real:下载"), \
             patch.object(gpd, "_wait_for_downloaded_pdf", side_effect=[None, os.path.join(tmpdir, "paper.pdf")]), \
             patch.object(gpd, "_wait_for_wanfang_interstitial_click", return_value="clicked"), \
             patch.object(gpd, "_wait_for_wanfang_download_info_click", return_value="not_found"), \
             patch.object(gpd, "_archive_browser_download", return_value=os.path.join(tmpdir, "wanfang.pdf")) as archive, \
             patch.object(gpd, "close_tab"):
            path = gpd._download_wanfang(
                9223,
                "https://d.wanfangdata.com.cn/periodical/wf-demo",
                {},
                output_dir=tmpdir,
            )

        self.assertTrue(str(path).endswith(".pdf"))
        archive.assert_called_once()

    def test_archive_browser_download_moves_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "Downloads", "paper.pdf")
            dest = os.path.join(tmpdir, "paper-temp", "paper.pdf")
            os.makedirs(os.path.dirname(source), exist_ok=True)
            with open(source, "wb") as f:
                f.write(self._valid_pdf_bytes())

            result = gpd._archive_browser_download(source, dest)

            self.assertEqual(result, dest)
            self.assertTrue(os.path.exists(dest))
            self.assertFalse(os.path.exists(source))

    def test_archive_browser_download_overwrites_existing_dest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "Downloads", "paper.pdf")
            dest = os.path.join(tmpdir, "paper-temp", "paper.pdf")
            os.makedirs(os.path.dirname(source), exist_ok=True)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(source, "wb") as f:
                f.write(self._valid_pdf_bytes())
            with open(dest, "wb") as f:
                f.write(b"old")

            result = gpd._archive_browser_download(source, dest)

            self.assertEqual(result, dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), self._valid_pdf_bytes())
            self.assertFalse(os.path.exists(source))

    def test_archive_browser_download_falls_back_to_copy_then_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "Downloads", "paper.pdf")
            dest = os.path.join(tmpdir, "paper-temp", "paper.pdf")
            os.makedirs(os.path.dirname(source), exist_ok=True)
            with open(source, "wb") as f:
                f.write(self._valid_pdf_bytes())

            def fail_replace(_src, _dest):
                raise OSError("cross-device")

            with patch.object(gpd.os, "replace", side_effect=fail_replace), \
                 patch("shutil.move", side_effect=RuntimeError("move failed")), \
                 patch("shutil.copy2", wraps=__import__("shutil").copy2) as copy2, \
                 patch.object(gpd.os, "remove", wraps=gpd.os.remove) as remove:
                result = gpd._archive_browser_download(source, dest)

            self.assertEqual(result, dest)
            self.assertTrue(os.path.exists(dest))
            self.assertFalse(os.path.exists(source))
            copy2.assert_called_once_with(source, dest)
            remove.assert_called_once_with(source)

    def test_archive_browser_download_keeps_source_when_copy_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "Downloads", "paper.pdf")
            dest = os.path.join(tmpdir, "paper-temp", "paper.pdf")
            os.makedirs(os.path.dirname(source), exist_ok=True)
            with open(source, "wb") as f:
                f.write(self._valid_pdf_bytes())

            def fail_replace(_src, _dest):
                raise OSError("cross-device")

            with patch.object(gpd.os, "replace", side_effect=fail_replace), \
                 patch("shutil.move", side_effect=RuntimeError("move failed")), \
                 patch("shutil.copy2", side_effect=RuntimeError("copy failed")), \
                 patch.object(gpd.os, "remove", wraps=gpd.os.remove) as remove:
                with self.assertRaises(RuntimeError):
                    gpd._archive_browser_download(source, dest)

            self.assertTrue(os.path.exists(source))
            self.assertFalse(os.path.exists(dest))
            remove.assert_not_called()

    def test_download_wanfang_fetch_fallback_writes_pdf_when_download_page_has_no_actionable_control(self):
        class FakeBrowserWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"targetId": "detail-tab"}})

            def close(self):
                pass

        class FakeTabWs:
            def __init__(self):
                self.responses = [
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "click_target",
                        "text": "下载",
                        "x": 50,
                        "y": 60,
                        "visible": True,
                    })}}}),
                    json.dumps({"result": {}}),
                    json.dumps({"result": {}}),
                ]

            def send(self, _payload):
                pass

            def recv(self):
                return self.responses.pop(0)

            def close(self):
                pass

        pdf_bytes = self._valid_pdf_bytes()
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(gpd, "_parse_wanfang_article_url", return_value=("periodical", "wf-demo", "https://d.wanfangdata.com.cn/periodical/wf-demo")), \
             patch.object(gpd, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(gpd.websocket, "create_connection", side_effect=[FakeBrowserWs(), FakeTabWs()]), \
             patch.object(gpd, "list_tabs", return_value=[{"id": "download-tab", "url": "https://oss.wanfangdata.com.cn/Fulltext/Download?filename=demo.pdf"}]), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://detail-tab"), \
             patch.object(gpd, "_wanfang_real_click_target", return_value="clicked_real:下载"), \
             patch.object(gpd, "_wait_for_downloaded_pdf", side_effect=[None]), \
             patch.object(gpd, "_wait_for_wanfang_interstitial_click", return_value="not_found"), \
             patch.object(gpd, "_wait_for_wanfang_download_info_click", return_value="download_page_no_actionable_control"), \
             patch.object(gpd, "_navigate_and_capture_pdf", return_value=pdf_bytes) as capture, \
             patch.object(gpd.time, "sleep", return_value=None), \
             patch.object(gpd, "close_tab"):
            path = gpd._download_wanfang(
                9223,
                "https://d.wanfangdata.com.cn/periodical/wf-demo",
                {},
                output_dir=tmpdir,
            )

        self.assertTrue(str(path).endswith(".pdf"))
        self.assertTrue(str(path).startswith(tmpdir))
        capture.assert_called_once_with(
            9223,
            "https://oss.wanfangdata.com.cn/Fulltext/Download?filename=demo.pdf",
            timeout=25,
        )

    def test_download_wanfang_returns_download_page_no_actionable_control_when_fetch_fallback_fails(self):
        class FakeBrowserWs:
            def send(self, _payload):
                pass

            def recv(self):
                return json.dumps({"result": {"targetId": "detail-tab"}})

            def close(self):
                pass

        class FakeTabWs:
            def __init__(self):
                self.responses = [
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "click_target",
                        "text": "下载",
                        "x": 50,
                        "y": 60,
                        "visible": True,
                    })}}}),
                    json.dumps({"result": {}}),
                    json.dumps({"result": {}}),
                ]

            def send(self, _payload):
                pass

            def recv(self):
                return self.responses.pop(0)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(gpd, "_parse_wanfang_article_url", return_value=("periodical", "wf-demo", "https://d.wanfangdata.com.cn/periodical/wf-demo")), \
             patch.object(gpd, "get_cdp_ws_url", return_value="ws://browser"), \
             patch.object(gpd.websocket, "create_connection", side_effect=[FakeBrowserWs(), FakeTabWs()]), \
             patch.object(gpd, "list_tabs", return_value=[{"id": "download-tab", "url": "https://www.wanfangdata.com.cn/NewFulltext?download=1"}]), \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://detail-tab"), \
             patch.object(gpd, "_wanfang_real_click_target", return_value="clicked_real:下载"), \
             patch.object(gpd, "_wait_for_downloaded_pdf", side_effect=[None]), \
             patch.object(gpd, "_wait_for_wanfang_interstitial_click", return_value="not_found"), \
             patch.object(gpd, "_wait_for_wanfang_download_info_click", return_value="download_page_no_actionable_control"), \
             patch.object(gpd, "_navigate_and_capture_pdf", return_value=None), \
             patch.object(gpd.time, "sleep", return_value=None), \
             patch.object(gpd, "close_tab"):
            result = gpd._download_wanfang(
                9223,
                "https://d.wanfangdata.com.cn/periodical/wf-demo",
                {},
                output_dir=tmpdir,
            )

        self.assertEqual(result, "download_page_no_actionable_control")

    def test_download_one_returns_wanfang_non_ok_status(self):
        with patch.object(gpd, "resolve_publisher", return_value=None), \
             patch.object(gpd, "_download_wanfang", return_value="pdf_probe_unknown"):
            path, status, pub = gpd.download_one(
                9225,
                "wanfang.demo",
                "paper-temp",
                article_url="https://d.wanfangdata.com.cn/periodical/demo123",
            )

        self.assertIsNone(path)
        self.assertEqual(status, "pdf_probe_unknown")
        self.assertEqual(pub, "wanfang")

    def test_cnki_download_expression_only_auto_clicks_pdf_entries(self):
        js = gpd._cnki_download_click_expression()

        self.assertIn("captcha_required", js)
        self.assertIn("/verify/home", js)
        for blocked in ("AI阅读", "原版阅读", "CAJ下载", "章节下载", "我是作者", "免费下载"):
            self.assertIn(blocked, js)
            self.assertNotIn(f"clickNode(findByText(['{blocked}'])", js)
            self.assertNotIn(f"clickNode(findByText([\"{blocked}\"])", js)
        self.assertEqual(js.count("clickNode(pdf,"), 1)
        self.assertIn("clickNode(pdf, 'PDF下载')", js)
        self.assertNotIn("clickNode(findBarDownload()", js)
        self.assertLess(js.index("clickNode(pdf, 'PDF下载')"), js.index("if (hasChapterMode())"))
        self.assertIn("bar.cnki.net/bar/download/order", js)

    def test_cnki_status_from_click_result_preserves_precise_states(self):
        self.assertEqual(
            gpd._cnki_status_from_click_result("captcha_required"),
            "captcha_required",
        )
        self.assertEqual(
            gpd._cnki_status_from_click_result("chapter_download_mode"),
            "chapter_download_mode",
        )
        self.assertIsNone(gpd._cnki_status_from_click_result("clicked:PDF下载:https://x"))

    def test_find_reusable_cnki_tab_ignores_unrelated_verify_page(self):
        target_url = "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=target"
        tabs = [
            {"id": "old-verify", "url": "https://kns.cnki.net/verify/home?filename=other"},
            {"id": "target-tab", "url": target_url},
        ]

        def fake_probe(_port, tab_id, _title=""):
            if tab_id == "old-verify":
                return {
                    "url": "https://kns.cnki.net/verify/home?filename=other",
                    "title": "安全验证",
                    "body": "请完成安全验证",
                    "captcha": True,
                    "pdfVisible": False,
                }
            return {
                "url": target_url,
                "title": "CNKI demo",
                "body": "CNKI demo PDF下载",
                "captcha": False,
                "pdfVisible": True,
            }

        with patch.object(gpd, "list_tabs", return_value=tabs), \
             patch.object(gpd, "_cnki_probe_tab", side_effect=fake_probe):
            tab_id, status = gpd._find_reusable_cnki_tab(9223, target_url, title="CNKI demo")

        self.assertEqual(tab_id, "target-tab")
        self.assertIsNone(status)

    def test_cnki_wait_for_download_archives_browser_pdf(self):
        article_url = "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=demo"
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(gpd.time, "sleep", return_value=None), \
             patch("glob.glob", side_effect=[
                 [os.path.join(tmpdir, "paper.pdf")],
                 [],
             ]), \
             patch("os.path.getsize", return_value=6001), \
             patch.object(gpd, "_archive_browser_download", side_effect=lambda _src, dest: dest) as archive:
            result = gpd._cnki_wait_for_download(
                tmpdir,
                set(),
                "paper-temp",
                article_url,
                timeout=1,
            )

        self.assertTrue(result.startswith("paper-temp/cnki."))
        archive.assert_called_once()

    def test_cnki_download_reuses_verified_detail_tab_without_creating_target(self):
        with patch.object(gpd, "_find_reusable_cnki_tab", return_value=("tab-1", None)), \
             patch.object(gpd, "_cnki_create_detail_tab") as create_tab, \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://tab-1"), \
             patch.object(gpd, "_cnki_evaluate_tab", return_value="clicked:PDF下载:https://bar.cnki.net/x"), \
             patch.object(gpd, "_cnki_wait_for_download", return_value="paper-temp/cnki.demo.pdf"), \
             patch.object(gpd, "close_tab") as close_tab:
            result = gpd._download_cnki(
                9223,
                "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
                {"strategy": "chinese_cdp"},
                output_dir="paper-temp",
                title="CNKI demo",
            )

        self.assertEqual(result, "paper-temp/cnki.demo.pdf")
        create_tab.assert_not_called()
        close_tab.assert_not_called()

    def test_cnki_download_keeps_matching_captcha_tab_open(self):
        with patch.object(gpd, "_find_reusable_cnki_tab", return_value=("tab-verify", "captcha_required")), \
             patch.object(gpd, "_cnki_create_detail_tab") as create_tab, \
             patch.object(gpd, "close_tab") as close_tab:
            result = gpd._download_cnki(
                9223,
                "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
                {"strategy": "chinese_cdp"},
                output_dir="paper-temp",
                title="CNKI demo",
            )

        self.assertEqual(result, "captcha_required")
        create_tab.assert_not_called()
        close_tab.assert_not_called()

    def test_cnki_download_falls_back_to_new_detail_tab_when_no_reusable_tab(self):
        with patch.object(gpd, "_find_reusable_cnki_tab", return_value=(None, None)), \
             patch.object(gpd, "_cnki_create_detail_tab", return_value="new-tab") as create_tab, \
             patch.object(gpd, "get_tab_ws_url", return_value="ws://new-tab"), \
             patch.object(gpd, "_cnki_evaluate_tab", return_value="clicked:PDF下载:https://bar.cnki.net/x"), \
             patch.object(gpd, "_cnki_wait_for_download", return_value=None), \
             patch.object(gpd, "close_tab") as close_tab, \
             patch.object(gpd.time, "sleep", return_value=None):
            result = gpd._download_cnki(
                9223,
                "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
                {"strategy": "chinese_cdp"},
                output_dir="paper-temp",
                title="CNKI demo",
            )

        self.assertEqual(result, "manual_required")
        create_tab.assert_called_once()
        close_tab.assert_not_called()

    def test_download_one_returns_cnki_captcha_required(self):
        with patch.object(gpd, "resolve_publisher", return_value=None), \
             patch.object(gpd, "_download_cnki", return_value="captcha_required"):
            path, status, pub = gpd.download_one(
                9225,
                "cnki.demo",
                "paper-temp",
                article_url="https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
            )

        self.assertIsNone(path)
        self.assertEqual(status, "captcha_required")
        self.assertEqual(pub, "cnki")

    def test_download_one_returns_cnki_chapter_download_mode(self):
        with patch.object(gpd, "resolve_publisher", return_value=None), \
             patch.object(gpd, "_download_cnki", return_value="chapter_download_mode"):
            path, status, pub = gpd.download_one(
                9225,
                "cnki.thesis",
                "paper-temp",
                article_url="https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CMFD&filename=test",
            )

        self.assertIsNone(path)
        self.assertEqual(status, "chapter_download_mode")
        self.assertEqual(pub, "cnki")

    def test_chinese_paper_once_passes_title_for_cnki_reusable_tab_matching(self):
        paper = {
            "title": "CNKI demo title",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
            "doi": "cnki.demo",
        }
        with patch.object(router, "resolve_publisher", return_value=None), \
             patch.object(router, "generic_download_one", return_value=("paper-temp/cnki.demo.pdf", "ok", "cnki")) as download_one:
            result = router._download_chinese_paper_once(paper, "paper-temp", 9223)

        self.assertEqual(result, ("paper-temp/cnki.demo.pdf", "ok", "cnki"))
        self.assertEqual(download_one.call_args.kwargs["title"], "CNKI demo title")

    def test_sciencedirect_generic_adapter_downloads_via_generic_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(gpd, "_navigate_and_capture_pdf", return_value=b"%PDF" + b"x" * 25000) as capture, \
                 patch("batch_resolve_pii._resolve_pii_from_crossref", return_value="S0000000000000001"):
                result_path, status = gpd._download_sciencedirect(
                    9223, "10.1016/j.demo.2026.01.001", tmp
                )

            self.assertEqual(status, "ok")
            self.assertTrue(Path(result_path).exists())
            capture.assert_called_once_with(
                9223,
                "https://www.sciencedirect.com/science/article/pii/S0000000000000001/pdfft",
                referrer="https://www.sciencedirect.com/science/article/pii/S0000000000000001",
                timeout=gpd.DEFAULT_TIMEOUT,
            )

    def test_sciencedirect_article_page_only_prompts_login_retry(self):
        with patch.object(gpd, "_navigate_and_capture_pdf", return_value=None), \
             patch("batch_resolve_pii._resolve_pii_from_crossref", return_value="S0000000000000001"), \
             patch("sd_download.diagnose_sd_pii", return_value={"kind": "article_page_only"}):
            result_path, status = gpd._download_sciencedirect(
                9223, "10.1016/j.demo.2026.01.001", "paper-temp"
            )

        self.assertIsNone(result_path)
        self.assertEqual(status, "pdf_probe_unknown")

    def test_sciencedirect_download_one_routes_through_generic_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(gpd, "_download_sciencedirect", return_value=(str(Path(tmp) / "paper.pdf"), "ok")) as sd_adapter:
                result_path, status, pub = gpd.download_one(
                    9223, "10.1016/j.demo.2026.01.001", tmp
                )

        self.assertEqual(status, "ok")
        self.assertEqual(pub, "sd_elsevier")
        self.assertTrue(result_path.endswith("paper.pdf"))
        sd_adapter.assert_called_once_with(9223, "10.1016/j.demo.2026.01.001", tmp)

    def test_rsc_config_builds_direct_articlepdf_url(self):
        publisher = gpd.resolve_publisher("10.1039/d5ra02870a")

        self.assertEqual(publisher["_key"], "rsc")
        self.assertEqual(
            gpd._build_pdf_url("10.1039/d5ra02870a", publisher),
            "https://pubs.rsc.org/en/content/articlepdf/10.1039/d5ra02870a",
        )

    def test_mdpi_config_routes_through_generic_cdp_without_direct_template(self):
        publisher = gpd.resolve_publisher("10.3390/microorganisms17060118")

        self.assertEqual(publisher["_key"], "mdpi")
        self.assertEqual(publisher["strategy"], "generic")
        self.assertEqual(publisher["requires_auth"], "none")
        self.assertIsNone(gpd._build_pdf_url("10.3390/microorganisms17060118", publisher))
        self.assertIn("a.UD_ArticlePDF", publisher["selectors"])

    def test_mdpi_selector_extracts_versioned_pdf_url(self):
        class FakeWs:
            def __init__(self):
                self.sent = []

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def settimeout(self, _timeout):
                return None

            def recv(self):
                return json.dumps({
                    "id": 1,
                    "result": {
                        "result": {
                            "value": "PDF_URL:https://www.mdpi.com/2036-7481/17/6/118/pdf?version=1782145976"
                        }
                    },
                })

            def close(self):
                return None

        fake_ws = FakeWs()

        with patch.object(gpd, "get_tab_ws_url", return_value="ws://tab"), \
             patch.object(gpd.websocket, "create_connection", return_value=fake_ws):
            result = gpd._extract_pdf_url_from_dom(9223, "tab-1", [
                "a.UD_ArticlePDF",
                "a[href*=\"/pdf?version=\"]",
            ])

        self.assertEqual(
            result,
            "https://www.mdpi.com/2036-7481/17/6/118/pdf?version=1782145976",
        )
        js_expr = fake_ws.sent[0]["params"]["expression"]
        self.assertIn("a.UD_ArticlePDF", js_expr)

    def test_mdpi_download_one_uses_article_page_pdf_capture(self):
        publisher = {
            "strategy": "generic",
            "_key": "mdpi",
            "requires_auth": "none",
            "publisher_domain": "www.mdpi.com",
            "selectors": ["a.UD_ArticlePDF"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(gpd, "resolve_publisher", return_value=publisher), \
                 patch.object(gpd, "_strategy_direct_pdf", return_value=None), \
                 patch.object(gpd, "_strategy_article_page", return_value=self._valid_pdf_bytes()) as article_page:
                path, status, pub = gpd.download_one(
                    9223, "10.3390/microorganisms17060118", tmp
                )

            self.assertEqual(status, "ok")
            self.assertEqual(pub, "mdpi")
            self.assertTrue(Path(path).exists())
            article_page.assert_called_once()

    def test_mdpi_capture_failure_returns_manual_required(self):
        publisher = {
            "_key": "mdpi",
            "publisher_domain": "www.mdpi.com",
            "selectors": ["a.UD_ArticlePDF"],
        }

        with patch.object(gpd, "_build_article_url", return_value="https://www.mdpi.com/2036-7481/17/6/118"), \
             patch.object(gpd, "create_tab", side_effect=[(None, "article-tab"), (None, "manual-tab")]) as create_tab, \
             patch.object(gpd, "_detect_access_barrier", return_value=(None, "")), \
             patch.object(gpd, "_extract_pdf_url_from_dom", return_value="https://www.mdpi.com/2036-7481/17/6/118/pdf?version=1782145976"), \
             patch.object(gpd, "_navigate_and_capture_pdf", return_value=None), \
             patch.object(gpd, "close_tab") as close_tab, \
             patch.object(gpd.time, "sleep"):
            result = gpd._strategy_article_page(
                9223, "10.3390/microorganisms17060118", publisher, timeout=1
            )

        self.assertEqual(result, "MANUAL_REQUIRED")
        self.assertEqual(create_tab.call_count, 2)
        close_tab.assert_called_once_with(9223, "article-tab")

    def test_article_page_login_wall_keeps_tab_open_for_manual_login(self):
        publisher = {
            "_key": "springer",
            "selectors": ["a.pdf-link"],
            "article_url_template": "https://example.com/{doi}",
        }

        with patch.object(gpd, "_build_article_url", return_value="https://example.com/article"), \
             patch.object(gpd, "create_tab", return_value=(None, "tab-1")), \
             patch.object(gpd, "_detect_access_barrier", return_value=("login_wall", "title matched")), \
             patch.object(gpd, "_extract_pdf_url_from_dom", return_value="LOGIN_REQUIRED"), \
             patch.object(gpd, "close_tab") as close_tab:
            result = gpd._strategy_article_page(9223, "10.1007/demo", publisher, timeout=1)

        self.assertEqual(result, "LOGIN_REQUIRED")
        close_tab.assert_called_once_with(9223, "tab-1")

    def test_download_one_returns_manual_required_for_login_wall(self):
        with patch.object(gpd, "resolve_publisher", return_value={"strategy": "generic", "_key": "springer"}), \
             patch.object(gpd, "_strategy_direct_pdf", return_value=None), \
             patch.object(gpd, "_strategy_article_page", return_value="MANUAL_REQUIRED"):
            path, status, pub = gpd.download_one(9223, "10.1007/demo", "paper-temp")

        self.assertIsNone(path)
        self.assertEqual(status, "manual_required")
        self.assertEqual(pub, "springer")

    def test_download_one_uses_ieee_generic_fallback_after_a_b_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(gpd, "resolve_publisher", return_value={"strategy": "generic", "_key": "ieee"}), \
                 patch.object(gpd, "_strategy_direct_pdf", return_value=None), \
                 patch.object(gpd, "_strategy_article_page", return_value=None), \
                 patch.object(gpd, "_download_ieee_via_generic_fallback", return_value=str(Path(tmp) / "ieee.pdf")) as fallback:
                path, status, pub = gpd.download_one(9223, "10.1109/tvt.2018.2880138", tmp)

        self.assertEqual(status, "ok")
        self.assertEqual(pub, "ieee")
        self.assertTrue(path.endswith("ieee.pdf"))
        fallback.assert_called_once()

    def test_springer_institutional_login_entry_is_documented(self):
        matrix = (ROOT / "references" / "publisher-access-matrix.md").read_text(encoding="utf-8")
        step5 = (ROOT / "agents" / "step_5_download.md").read_text(encoding="utf-8")

        self.assertIn("https://idp.springer.com/authorize?response_type=cookie&client_id=springerlink", matrix)
        self.assertIn("https://wayf.springernature.com/?redirect_uri=https%3A%2F%2Flink.springer.com%2F", matrix)
        self.assertIn("https://wayf.springernature.com/?redirect_uri=https%3A%2F%2Fwww.nature.com%2F", matrix)
        self.assertIn("https://idp.springer.com/authorize?response_type=cookie&client_id=springerlink", step5)
        self.assertIn("skip", step5)
        self.assertIn("支持弹窗/结构化交互", matrix)
        self.assertIn("若宿主支持弹窗/结构化选项", step5)
        self.assertIn("跳过登录", step5)
        self.assertIn("只有部分权限也选 1", step5)

    def test_login_gates_allow_skip_without_fatal_stop(self):
        with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", return_value="2"):
            self.assertFalse(router.show_english_login_gate(["10.1007/demo"]))

    def test_show_english_login_gate_defer_returns_none_like_chinese_gate(self):
        for value in ("3", "later", "retry", "稍后", "重试", "稍后重试"):
            with self.subTest(value=value), \
                 patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}), \
                 patch("builtins.input", return_value=value):
                self.assertIsNone(router.show_english_login_gate(["10.1007/demo"]))

    def test_show_english_login_gate_unrecognized_returns_none(self):
        with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", return_value="maybe tomorrow"):
            self.assertIsNone(router.show_english_login_gate(["10.1007/demo"]))

    def test_login_gate_prompts_offer_three_choices(self):
        with patch.object(router, "open_chinese_login_tabs", return_value={"opened": [], "failed": []}), \
             patch("builtins.input", return_value="3") as inp:
            self.assertIsNone(router.show_chinese_login_gate([{"source": "cnki", "article_url": "https://kns.cnki.net", "title": "x"}]))
        self.assertTrue(inp.called)

    def test_generic_round_recovers_from_single_item_exception(self):
        with patch.object(router, "resolve_publisher", return_value={"strategy": "generic", "_key": "springer", "publisher_domain": "link.springer.com"}), \
             patch.object(router, "generic_download_one", side_effect=RuntimeError("502") ), \
             patch.object(router, "ensure_cdp_running", return_value=True):
            downloaded, remaining, reasons = router.run_generic_round(["10.1007/demo"], "paper-temp", 9223)

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1007/demo"])
        self.assertEqual(reasons["10.1007/demo"], "generic_failed")

    def test_generic_round_keeps_manual_required_item_for_rerun(self):
        with patch.object(router, "resolve_publisher", return_value={"strategy": "generic", "_key": "springer", "publisher_domain": "link.springer.com"}), \
             patch.object(router, "generic_download_one", return_value=(None, "manual_required", "springer")):
            downloaded, remaining, reasons = router.run_generic_round(["10.1007/demo"], "paper-temp", 9223)

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1007/demo"])
        self.assertEqual(reasons["10.1007/demo"], "manual_required")

    def test_generic_round_attempts_mdpi_instead_of_skipping(self):
        with patch.object(router, "resolve_publisher", return_value={
                "strategy": "generic",
                "_key": "mdpi",
                "publisher_domain": "www.mdpi.com",
                "requires_auth": "none",
             }), \
             patch.object(router, "generic_download_one", return_value=(None, "manual_required", "mdpi")) as download_one:
            downloaded, remaining, reasons = router.run_generic_round(
                ["10.3390/microorganisms17060118"], "paper-temp", 9223
            )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.3390/microorganisms17060118"])
        self.assertEqual(reasons["10.3390/microorganisms17060118"], "manual_required")
        download_one.assert_called_once()

    def test_generic_round_keeps_captcha_reason_for_rerun(self):
        with patch.object(router, "resolve_publisher", return_value={"strategy": "generic", "_key": "wiley", "publisher_domain": "onlinelibrary.wiley.com"}), \
             patch.object(router, "generic_download_one", return_value=(None, "captcha_required", "wiley")):
            downloaded, remaining, reasons = router.run_generic_round(["10.1002/demo"], "paper-temp", 9223)

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1002/demo"])
        self.assertEqual(reasons["10.1002/demo"], "captcha_required")

    def test_group_english_cdp_dois_prioritizes_known_publishers_and_unknown_last(self):
        dois = [
            "10.9999/unknown",
            "10.1007/springer-one",
            "10.1016/j.sd-one",
            "10.1007/springer-two",
            "10.1016/j.sd-two",
            "10.1002/wiley-one",
        ]
        pub_map = {
            "10.1016/j.sd-one": {"strategy": "generic", "_key": "sd_elsevier", "publisher_domain": "www.sciencedirect.com"},
            "10.1016/j.sd-two": {"strategy": "generic", "_key": "sd_elsevier", "publisher_domain": "www.sciencedirect.com"},
            "10.1007/springer-one": {"strategy": "generic", "_key": "springer", "publisher_domain": "link.springer.com"},
            "10.1007/springer-two": {"strategy": "generic", "_key": "springer", "publisher_domain": "link.springer.com"},
            "10.1002/wiley-one": {"strategy": "generic", "_key": "wiley", "publisher_domain": "onlinelibrary.wiley.com"},
        }

        with patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map.get(doi)):
            groups = router.group_english_cdp_dois(dois)

        self.assertEqual([name for name, _domain, _dois in groups], ["sd_elsevier", "springer", "wiley", "unknown"])
        self.assertEqual(groups[0][2], ["10.1016/j.sd-one", "10.1016/j.sd-two"])
        self.assertEqual(groups[1][2], ["10.1007/springer-one", "10.1007/springer-two"])
        self.assertEqual(groups[-1][2], ["10.9999/unknown"])

    def test_generic_round_downloads_by_publisher_group_order(self):
        dois = [
            "10.1007/springer-one",
            "10.1016/j.sd-one",
            "10.1002/wiley-one",
            "10.1016/j.sd-two",
            "10.1007/springer-two",
        ]
        pub_map = {
            "10.1016/j.sd-one": {"strategy": "generic", "_key": "sd_elsevier", "publisher_domain": "www.sciencedirect.com"},
            "10.1016/j.sd-two": {"strategy": "generic", "_key": "sd_elsevier", "publisher_domain": "www.sciencedirect.com"},
            "10.1007/springer-one": {"strategy": "generic", "_key": "springer", "publisher_domain": "link.springer.com"},
            "10.1007/springer-two": {"strategy": "generic", "_key": "springer", "publisher_domain": "link.springer.com"},
            "10.1002/wiley-one": {"strategy": "generic", "_key": "wiley", "publisher_domain": "onlinelibrary.wiley.com"},
        }
        call_order = []

        def fake_download(port, doi, output_dir, include_si=False):
            call_order.append(doi)
            return None, "manual_required", pub_map[doi]["_key"]

        with patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map.get(doi)), \
             patch.object(router, "generic_download_one", side_effect=fake_download):
            downloaded, remaining, reasons = router.run_generic_round(dois, "paper-temp", 9223)

        self.assertEqual(downloaded, [])
        self.assertEqual(call_order, [
            "10.1016/j.sd-one",
            "10.1016/j.sd-two",
            "10.1007/springer-one",
            "10.1007/springer-two",
            "10.1002/wiley-one",
        ])
        self.assertEqual(remaining, call_order)
        self.assertEqual(set(reasons.values()), {"manual_required"})

    def test_english_cdp_prompts_and_retries_first_login_required_failure(self):
        first = ([], ["10.1007/demo", "10.1021/demo"], {
            "10.1007/demo": "manual_confirmation_required",
            "10.1021/demo": "generic_failed",
        })
        second = (["10.1007/demo"], [], {})

        with patch.object(router, "run_generic_round", side_effect=[first, second]) as run_generic, \
             patch.object(router, "show_english_login_gate", return_value=True) as login_gate:
            downloaded, remaining, results, reasons = router.run_english_cdp(
                ["10.1007/demo", "10.1021/demo"], "paper-temp", 9223
            )

        self.assertEqual(downloaded, ["10.1007/demo"])
        self.assertEqual(remaining, ["10.1021/demo"])
        self.assertEqual(reasons, {"10.1021/demo": "generic_failed"})
        login_gate.assert_called_once_with(["10.1007/demo"], skip_sd=False, port=9223, interactive=False)
        self.assertEqual(run_generic.call_args_list[1].args[0], ["10.1007/demo"])
        self.assertEqual(results[-1]["round"], "Generic CDP (after login)")

    def test_english_cdp_gate_runs_once_after_first_grouped_pass(self):
        dois = ["10.1016/j.sd-one", "10.1007/springer-one", "10.1002/wiley-one"]
        first = ([], list(dois), {
            "10.1016/j.sd-one": "manual_required",
            "10.1007/springer-one": "generic_failed",
            "10.1002/wiley-one": "access_denied",
        })
        second = (["10.1016/j.sd-one"], ["10.1002/wiley-one"], {
            "10.1002/wiley-one": "access_denied",
        })

        with patch.object(router, "run_generic_round", side_effect=[first, second]) as run_generic, \
             patch.object(router, "show_english_login_gate", return_value=True) as login_gate, \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            downloaded, remaining, results, reasons = router.run_english_cdp(dois, "paper-temp", 9223)

        self.assertEqual(downloaded, ["10.1016/j.sd-one"])
        self.assertEqual(remaining, ["10.1007/springer-one", "10.1002/wiley-one"])
        self.assertEqual(reasons["10.1007/springer-one"], "generic_failed")
        self.assertEqual(reasons["10.1002/wiley-one"], "access_denied")
        self.assertEqual(run_generic.call_count, 2)
        self.assertEqual(run_generic.call_args_list[0].args[0], dois)
        self.assertEqual(run_generic.call_args_list[1].args[0], ["10.1016/j.sd-one", "10.1002/wiley-one"])
        login_gate.assert_called_once_with(
            ["10.1016/j.sd-one", "10.1002/wiley-one"],
            skip_sd=False,
            port=9223,
            interactive=False,
        )
        self.assertIn("First grouped English CDP pass completed", stdout.getvalue())
        self.assertEqual(results[-1]["round"], "Generic CDP (after login)")

    def test_english_cdp_skip_does_not_retry_login_failures(self):
        first = ([], ["10.1007/demo"], {"10.1007/demo": "manual_required"})

        with patch.object(router, "run_generic_round", return_value=first) as run_generic, \
             patch.object(router, "show_english_login_gate", return_value=False) as login_gate:
            downloaded, remaining, results, reasons = router.run_english_cdp(["10.1007/demo"], "paper-temp", 9223)

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1007/demo"])
        self.assertEqual(reasons, {"10.1007/demo": "manual_required"})
        self.assertEqual(run_generic.call_count, 1)
        login_gate.assert_called_once()

    def test_english_cdp_noninteractive_writes_login_checkpoint_and_marks_pending(self):
        first = ([], ["10.1007/demo", "10.1021/demo"], {
            "10.1007/demo": "manual_confirmation_required",
            "10.1021/demo": "generic_failed",
        })

        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(router, "run_generic_round", return_value=first), \
             patch.object(router, "show_english_login_gate", return_value=None):
            downloaded, remaining, results, reasons = router.run_english_cdp(
                ["10.1007/demo", "10.1021/demo"], tmp, 9223
            )
            checkpoint = json.loads((Path(tmp) / "login_checkpoint.json").read_text(encoding="utf-8"))

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1007/demo", "10.1021/demo"])
        self.assertEqual(reasons["10.1007/demo"], "pending_user_login")
        self.assertEqual(reasons["10.1021/demo"], "generic_failed")
        self.assertEqual(checkpoint["status"], "pending_user_login")
        self.assertEqual(checkpoint["items"][0]["doi"], "10.1007/demo")
        self.assertEqual(results, [{"round": "Generic CDP", "downloaded": []}])

    def test_english_cdp_checkpoint_contains_only_login_required_failures(self):
        first = ([], ["10.1007/demo", "10.1021/demo", "10.1002/demo"], {
            "10.1007/demo": "manual_required",
            "10.1021/demo": "generic_failed",
            "10.1002/demo": "access_denied",
        })

        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(router, "run_generic_round", return_value=first), \
             patch.object(router, "show_english_login_gate", return_value=None):
            downloaded, remaining, results, reasons = router.run_english_cdp(
                ["10.1007/demo", "10.1021/demo", "10.1002/demo"], tmp, 9223
            )
            checkpoint = json.loads((Path(tmp) / "login_checkpoint.json").read_text(encoding="utf-8"))

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1007/demo", "10.1021/demo", "10.1002/demo"])
        self.assertEqual([item["doi"] for item in checkpoint["items"]], ["10.1007/demo", "10.1002/demo"])
        self.assertEqual(reasons["10.1007/demo"], "pending_user_login")
        self.assertEqual(reasons["10.1021/demo"], "generic_failed")
        self.assertEqual(reasons["10.1002/demo"], "pending_user_login")

    def test_english_login_candidate_dois_excludes_direct_http_skip_and_auth_none(self):
        pub_map = {
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
            "10.3389/demo": {
                "strategy": "direct_http",
                "_key": "frontiers",
                "publisher_domain": "www.frontiersin.org",
                "requires_auth": "none",
            },
            "10.9999/oa-generic": {
                "strategy": "generic",
                "_key": "oa_generic",
                "publisher_domain": "example.org",
                "requires_auth": "none",
            },
            "10.3390/demo": {
                "strategy": "generic",
                "_key": "mdpi",
                "publisher_domain": "www.mdpi.com",
                "requires_auth": "none",
            },
        }

        with patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]):
            candidates = router._english_login_candidate_dois(list(pub_map))

        self.assertEqual(candidates, ["10.1007/demo"])

    def test_english_login_candidates_exclude_oa_whitelist_items(self):
        pub_map = {
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
            "10.3390/demo": {
                "strategy": "generic",
                "_key": "mdpi",
                "publisher_domain": "www.mdpi.com",
                "requires_auth": "none",
            },
            "10.1109/demo": {
                "strategy": "generic",
                "_key": "ieee",
                "publisher_domain": "ieeexplore.ieee.org",
                "requires_auth": "sso",
            },
        }
        oa_hints = {
            "10.3390/demo": {"oa_status": "gold"},
            "10.1109/demo": {"oa_status": "gold", "journal": "IEEE Access"},
        }

        with patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]):
            candidates = router._english_login_candidate_dois(list(pub_map), oa_hints=oa_hints)

        self.assertEqual(candidates, ["10.1007/demo"])

    def test_english_login_dois_without_trusted_session_uses_pdf_probe_not_cookie_only(self):
        pub_map = {
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
            "10.1016/demo": {
                "strategy": "generic",
                "_key": "sd_elsevier",
                "publisher_domain": "www.sciencedirect.com",
                "requires_auth": "ip_or_sso",
            },
        }

        def fake_session(_port, publisher):
            if publisher["_key"] == "sd_elsevier":
                return {"probe_status": "ok"}
            return {"probe_status": "cookie_present", "has_session": True}

        with patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]), \
             patch.object(router, "describe_publisher_session", side_effect=fake_session):
            pending = router._english_login_dois_without_trusted_session(list(pub_map), 9223)

        self.assertEqual(pending, ["10.1007/demo"])


    def test_generate_download_log_includes_reason_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "10.1007_demo.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n" + b"x" * 6000)
            log_path = router.generate_download_log(
                tmp,
                ["10.1007/demo", "10.1016/j.demo"],
                [{"round": "Generic CDP", "downloaded": ["10.1007/demo"]}],
                {"10.1016/j.demo": "manual_verification_required"},
            )
            text = Path(log_path).read_text(encoding="utf-8")

        self.assertIn("| # | DOI | Status | Source | Reason | Size | Path |", text)
        self.assertIn("manual_verification_required", text)

    def test_write_failed_doi_sidecar_writes_structured_retry_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = router.write_failed_doi_sidecar(
                tmp,
                ["10.1002/er.7775"],
                {"10.1002/er.7775": "captcha_required"},
            )
            data = json.loads(Path(sidecar).read_text(encoding="utf-8"))

        self.assertEqual(data["items"][0]["doi"], "10.1002/er.7775")
        self.assertEqual(data["items"][0]["failure_reason"], "captcha_required")
        self.assertIn("--papers", data["items"][0]["retry_hint"])

    def test_write_step5_outputs_writes_manifest_attempts_and_pdf_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "10.1007_demo.pdf"
            pdf_path.write_bytes(self._valid_pdf_bytes())

            paths = router.write_step5_outputs(
                tmp,
                [
                    {"id": "10.1007/demo", "doi": "10.1007/demo", "publisher": "springer"},
                    {"id": "10.1002/demo", "doi": "10.1002/demo", "publisher": "wiley"},
                ],
                ["10.1007/demo"],
                ["10.1002/demo"],
                [{"round": "Generic CDP", "downloaded": ["10.1007/demo"]}],
                {"10.1002/demo": "captcha_required"},
            )
            manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
            pool = json.loads(Path(paths["pdf_pool"]).read_text(encoding="utf-8"))
            attempts = Path(paths["attempts"]).read_text(encoding="utf-8")

        self.assertEqual(manifest["schema_version"], "step5-download.v1")
        self.assertEqual(manifest["readiness"], "partial")
        self.assertEqual(manifest["recovery_buckets"]["needs_user_action"], ["10.1002/demo"])
        self.assertEqual(manifest["recommended_next_step"], "solve_captcha_or_manual_download_then_resume")
        self.assertEqual(manifest["items"][0]["status"], "downloaded")
        self.assertEqual(manifest["items"][0]["quality"], "pdf_verified")
        self.assertEqual(manifest["items"][1]["failure_reason"], "captcha_required")
        self.assertIn("local_index", attempts)
        self.assertEqual(pool["schema_version"], "pdf-pool.v1")
        self.assertEqual(pool["items"][0]["quality"], "pdf_verified")
        self.assertEqual(pool["items"][0]["pdf_diagnostics"]["issue"], "ok")

    def test_write_step5_outputs_adds_summary_and_failure_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = router.write_step5_outputs(
                tmp,
                [{
                    "id": "10.1002/demo",
                    "doi": "10.1002/demo",
                    "publisher": "wiley",
                    "article_url": "https://onlinelibrary.wiley.com/doi/10.1002/demo",
                }],
                [],
                ["10.1002/demo"],
                [],
                {"10.1002/demo": "manual_required"},
                preflight_summary={"total_items": 1, "local_pdf_hits": 0},
            )
            manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
            debug_exists = Path(paths["debug_snapshots"]).exists()

        self.assertEqual(manifest["summary"]["publisher_summary"]["wiley"]["failure_reasons"]["manual_required"], 1)
        self.assertEqual(manifest["summary"]["domain_summary"]["onlinelibrary.wiley.com"]["failed_or_pending"], 1)
        self.assertEqual(manifest["summary"]["preflight"]["total_items"], 1)
        self.assertTrue(debug_exists)

    def test_diagnose_pdf_file_detects_html_saved_as_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_pdf = Path(tmp) / "paper.pdf"
            fake_pdf.write_bytes(b"<!doctype html><html>login</html>" + b"x" * 6000)
            diagnostics = router.diagnose_pdf_file(fake_pdf)

        self.assertTrue(diagnostics["looks_like_html"])
        self.assertEqual(diagnostics["issue"], "html_saved_as_pdf")
        self.assertEqual(router._safe_pdf_quality(fake_pdf), "pdf_unverified")

    def test_step5_preflight_summary_is_non_blocking(self):
        with patch.object(router, "check_cdp", return_value=False):
            summary = router.build_step5_preflight_summary(
                [{"doi": "10.1007/demo"}], "paper-temp", 9223, "chrome", local_hits=["10.1007/demo"]
            )

        self.assertEqual(summary["total_items"], 1)
        self.assertEqual(summary["local_pdf_hits"], 1)
        self.assertFalse(summary["cdp"]["ok"])

    def test_reconcile_pdf_pool_updates_manual_downloaded_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "download_manifest.json").write_text(json.dumps({
                "schema_version": "step5-download.v1",
                "readiness": "partial",
                "summary": {"total": 1, "downloaded": 0, "remaining": 1},
                "items": [{
                    "id": "10.1007/demo",
                    "doi": "10.1007/demo",
                    "title": "Demo Paper",
                    "status": "blocked",
                    "quality": "none",
                    "failure_reason": "manual_required",
                    "attempts": [],
                }],
            }), encoding="utf-8")
            (output / "10.1007_demo.user.pdf").write_bytes(self._valid_pdf_bytes())
            report = reconcile.reconcile_pdf_pool(output)
            manifest = json.loads((output / "download_manifest.json").read_text(encoding="utf-8"))
            pool = json.loads((output / "pdf-附件池索引.json").read_text(encoding="utf-8"))

        self.assertEqual(report["reconciled"][0]["quality"], "pdf_verified")
        self.assertEqual(manifest["readiness"], "complete")
        self.assertEqual(manifest["items"][0]["status"], "downloaded")
        self.assertEqual(manifest["items"][0]["failure_reason"], "")
        self.assertEqual(pool["items"][0]["pdf_diagnostics"]["issue"], "ok")

    def test_reconcile_rejects_invalid_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "download_manifest.json").write_text(json.dumps({
                "schema_version": "step5-download.v1",
                "run_id": "test-run",
                "readiness": "blocked",
                "summary": {"total": 1, "downloaded": 0, "remaining": 1},
                "items": [{
                    "id": "10.1007/demo", "doi": "10.1007/demo", "status": "manual_required",
                    "quality": "none", "failure_reason": "manual_required", "attempts": [],
                }],
            }), encoding="utf-8")
            (output / "10.1007_demo.pdf").write_bytes(b"<html>login</html>" + b"x" * 6000)
            report = reconcile.reconcile_pdf_pool(output)
            manifest = json.loads((output / "download_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(report["invalid"][0]["reason"], "html_saved_as_pdf")
        self.assertEqual(manifest["items"][0]["status"], "invalid_pdf")
        self.assertEqual(manifest["readiness"], "blocked")

    def test_reconcile_title_only_match_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "download_manifest.json").write_text(json.dumps({
                "schema_version": "step5-download.v1",
                "run_id": "test-run",
                "readiness": "blocked",
                "summary": {"total": 1, "downloaded": 0, "remaining": 1},
                "items": [{
                    "id": "item-1", "title": "A sufficiently distinctive research paper title",
                    "status": "manual_required", "quality": "none", "failure_reason": "manual_required", "attempts": [],
                }],
            }), encoding="utf-8")
            (output / "A sufficiently distinctive research paper title.pdf").write_bytes(self._valid_pdf_bytes())
            report = reconcile.reconcile_pdf_pool(output)
            manifest = json.loads((output / "download_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report["reconciled"]), 0)
        self.assertEqual(len(report["pending_matches"]), 1)
        self.assertEqual(manifest["items"][0]["status"], "manual_required")

    def test_filter_local_pdf_hits_skips_existing_pdf_without_changing_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "10.1007_demo.custom-name.pdf"
            existing.write_bytes(self._valid_pdf_bytes())
            dois, chinese, downloaded = router.filter_local_pdf_hits(
                ["10.1007/demo", "10.1002/demo"], [], tmp
            )

        self.assertEqual(dois, ["10.1002/demo"])
        self.assertEqual(chinese, [])
        self.assertEqual(downloaded, ["10.1007/demo"])

    def test_main_local_pdf_hit_does_not_call_download_rounds_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            (Path(tmp) / "10.1007_demo.pdf").write_bytes(self._valid_pdf_bytes())
            argv = ["unified_download_router.py", "--papers", "10.1007/demo", "--output", tmp]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "run_scihub_round") as scihub, \
                 patch.object(router, "run_oa_fast_round") as oa, \
                 patch.object(router, "run_english_cdp") as english, \
                 patch("sys.stdout", new_callable=io.StringIO):
                router.main()

            manifest = json.loads((Path(tmp) / "download_manifest.json").read_text(encoding="utf-8"))

        scihub.assert_not_called()
        oa.assert_not_called()
        english.assert_not_called()
        self.assertEqual(manifest["readiness"], "complete")
        self.assertEqual(manifest["items"][0]["status"], "downloaded")

    def test_write_login_checkpoint_writes_pending_login_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = router.write_login_checkpoint(
                tmp,
                stage="english_cdp_retry",
                dois=["10.1016/j.ecmx.2026.101960"],
                failure_reasons={"10.1016/j.ecmx.2026.101960": "institution_login_required"},
            )
            data = json.loads(Path(checkpoint).read_text(encoding="utf-8"))

        self.assertEqual(data["status"], "pending_user_login")
        self.assertEqual(data["items"][0]["failure_reason"], "institution_login_required")
        self.assertIn("--resume-login-checkpoint", data["rerun_hint"])

    def test_write_chinese_login_checkpoint_writes_pending_items(self):
        papers = [{
            "title": "中文论文",
            "source": "cnki",
            "doi": "cnki.demo",
            "source_id": "cnki.demo",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = router.write_chinese_login_checkpoint(tmp, papers)
            data = json.loads(Path(checkpoint).read_text(encoding="utf-8"))

        self.assertEqual(data["checkpoint_type"], "chinese_publisher_login")
        self.assertEqual(data["status"], "pending_user_login")
        self.assertEqual(data["items"][0]["failure_reason"], "pending_user_login")
        self.assertEqual(data["items"][0]["article_url"], papers[0]["article_url"])
        self.assertIn("--resume-chinese-login-checkpoint", data["rerun_hint"])

    def test_write_chinese_login_checkpoint_preserves_captcha_reason(self):
        papers = [{
            "title": "中文论文",
            "source": "cnki",
            "doi": "cnki.demo",
            "source_id": "cnki.demo",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?dbcode=CJFD&filename=test",
            "failure_reason": "captcha_required",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = router.write_chinese_login_checkpoint(tmp, papers)
            data = json.loads(Path(checkpoint).read_text(encoding="utf-8"))

        self.assertEqual(data["status"], "pending_captcha_verification")
        self.assertEqual(data["items"][0]["failure_reason"], "captcha_required")

    def test_sort_chinese_papers_cnki_then_wanfang_stably(self):
        papers = [
            {"title": "wf-1", "source": "wanfang"},
            {"title": "cnki-1", "source": "cnki"},
            {"title": "other-1", "source": "vip"},
            {"title": "wf-2", "source": "wanfang"},
            {"title": "cnki-2", "source": "cnki"},
            {"title": "other-2", "source": "unknown"},
        ]

        sorted_papers = router.sort_chinese_papers_for_download(papers)

        self.assertEqual(
            [p["title"] for p in sorted_papers],
            ["cnki-1", "cnki-2", "wf-1", "wf-2", "other-1", "other-2"],
        )

    def test_write_chinese_login_checkpoint_uses_sorted_papers_when_caller_sorts(self):
        papers = router.sort_chinese_papers_for_download([
            {
                "title": "万方一",
                "source": "wanfang",
                "doi": "wanfang.1",
                "article_url": "https://d.wanfangdata.com.cn/periodical/wf1",
            },
            {
                "title": "知网一",
                "source": "cnki",
                "doi": "cnki.1",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
            },
            {
                "title": "万方二",
                "source": "wanfang",
                "doi": "wanfang.2",
                "article_url": "https://d.wanfangdata.com.cn/thesis/wf2",
            },
            {
                "title": "知网二",
                "source": "cnki",
                "doi": "cnki.2",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki2",
            },
        ])
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = router.write_chinese_login_checkpoint(tmp, papers)
            data = json.loads(Path(checkpoint).read_text(encoding="utf-8"))

        self.assertEqual(
            [item["source"] for item in data["items"]],
            ["cnki", "cnki", "wanfang", "wanfang"],
        )
        self.assertEqual(
            [item["doi"] for item in data["items"]],
            ["cnki.1", "cnki.2", "wanfang.1", "wanfang.2"],
        )

    def test_step5_download_lock_acquire_and_release(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(Path(tmp) / "step5.lock")}):
            acquired, lock_path, blocker = router.acquire_step5_download_lock("batch_download", 9223)
            self.assertTrue(acquired)
            self.assertEqual(blocker, {})
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(data["pid"], router.os.getpid())
            self.assertEqual(data["mode"], "batch_download")

            router.release_step5_download_lock(lock_path)

            self.assertFalse(lock_path.exists())

    def test_step5_download_lock_blocks_live_process(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(Path(tmp) / "step5.lock")}):
            lock_path = Path(tmp) / "step5.lock"
            lock_path.write_text(json.dumps({
                "pid": router.os.getpid(),
                "mode": "batch_download",
                "started_at": "2026-06-22T10:00:00",
            }), encoding="utf-8")

            acquired, path, blocker = router.acquire_step5_download_lock("resume_chinese_login_checkpoint", 9223)

        self.assertFalse(acquired)
        self.assertEqual(path, lock_path)
        self.assertEqual(blocker["mode"], "batch_download")

    def test_step5_download_lock_prints_wait_message(self):
        blocker = {
            "pid": 12345,
            "mode": "batch_download",
            "started_at": "2026-06-22T10:00:00",
        }
        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            router._print_download_lock_blocker(Path("/tmp/step5.lock"), blocker)

        text = stdout.getvalue()
        self.assertIn("上一进程下载中", text)
        self.assertIn("请等一等", text)
        self.assertIn("Lock: /tmp/step5.lock", text)
        self.assertIn("Running process: pid=12345", text)
        self.assertIn("如确认没有 Step 5 下载进程仍在运行", text)

    def test_step5_download_lock_replaces_stale_lock(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(Path(tmp) / "step5.lock")}), \
             patch.object(router, "_pid_is_running", return_value=False):
            lock_path = Path(tmp) / "step5.lock"
            lock_path.write_text(json.dumps({
                "pid": 999999,
                "mode": "old_download",
                "started_at": "2026-06-22T09:00:00",
            }), encoding="utf-8")

            acquired, path, blocker = router.acquire_step5_download_lock("batch_download", 9223)
            data = json.loads(path.read_text(encoding="utf-8"))

            router.release_step5_download_lock(path)

        self.assertTrue(acquired)
        self.assertEqual(blocker, {})
        self.assertEqual(data["pid"], router.os.getpid())
        self.assertEqual(data["mode"], "batch_download")

    def test_chinese_resume_lock_blocked_does_not_run_chinese_round(self):
        checkpoint = {
            "checkpoint_type": "chinese_publisher_login",
            "status": "pending_user_login",
            "items": [{
                "title": "中文论文",
                "source": "wanfang",
                "doi": "wanfang.demo",
                "article_url": "https://d.wanfangdata.com.cn/periodical/demo123",
                "failure_reason": "pending_user_login",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_path = Path(tmp) / "chinese_login_checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            lock_path = Path(tmp) / "step5.lock"
            lock_path.write_text(json.dumps({
                "pid": router.os.getpid(),
                "mode": "batch_download",
                "started_at": "2026-06-22T10:00:00",
            }), encoding="utf-8")
            argv = [
                "unified_download_router.py",
                "--resume-chinese-login-checkpoint", str(checkpoint_path),
                "--output", tmp,
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "run_chinese_round") as run_chinese, \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                with self.assertRaises(SystemExit) as cm:
                    router.main()

        self.assertEqual(cm.exception.code, 2)
        run_chinese.assert_not_called()
        self.assertIn("上一进程下载中", stdout.getvalue())

    def test_resume_from_chinese_login_checkpoint_retries_only_chinese_papers(self):
        checkpoint = {
            "checkpoint_type": "chinese_publisher_login",
            "status": "pending_user_login",
            "items": [{
                "title": "中文论文",
                "source": "wanfang",
                "doi": "wanfang.demo",
                "article_url": "https://d.wanfangdata.com.cn/periodical/demo123",
                "failure_reason": "pending_user_login",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_path = Path(tmp) / "chinese_login_checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            with patch.object(router, "show_chinese_login_gate", return_value=True) as gate, \
                 patch.object(router, "run_chinese_round", return_value=(["wanfang.demo"], [])) as run_chinese:
                downloaded, remaining = router.resume_from_chinese_login_checkpoint(
                    str(checkpoint_path), tmp, 9223
                )

        self.assertEqual(downloaded, ["wanfang.demo"])
        self.assertEqual(remaining, [])
        gate.assert_called_once()
        self.assertEqual(gate.call_args.kwargs["port"], 9223)
        run_chinese.assert_called_once()
        self.assertEqual(run_chinese.call_args.args[0][0]["source"], "wanfang")

    def test_resume_from_chinese_login_checkpoint_sorts_cnki_before_wanfang(self):
        checkpoint = {
            "checkpoint_type": "chinese_publisher_login",
            "status": "pending_user_login",
            "items": [
                {
                    "title": "万方一",
                    "source": "wanfang",
                    "doi": "wanfang.1",
                    "article_url": "https://d.wanfangdata.com.cn/periodical/wf1",
                    "failure_reason": "pending_user_login",
                },
                {
                    "title": "知网一",
                    "source": "cnki",
                    "doi": "cnki.1",
                    "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
                    "failure_reason": "pending_user_login",
                },
                {
                    "title": "万方二",
                    "source": "wanfang",
                    "doi": "wanfang.2",
                    "article_url": "https://d.wanfangdata.com.cn/thesis/wf2",
                    "failure_reason": "pending_user_login",
                },
                {
                    "title": "知网二",
                    "source": "cnki",
                    "doi": "cnki.2",
                    "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki2",
                    "failure_reason": "pending_user_login",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_path = Path(tmp) / "chinese_login_checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            with patch.object(router, "show_chinese_login_gate", return_value=True) as gate, \
                 patch.object(router, "run_chinese_round", return_value=(["cnki.1"], [])) as run_chinese:
                router.resume_from_chinese_login_checkpoint(str(checkpoint_path), tmp, 9223)

        gate.assert_called_once()
        self.assertEqual(gate.call_args.kwargs["port"], 9223)
        self.assertEqual(
            [paper["doi"] for paper in run_chinese.call_args.args[0]],
            ["cnki.1", "cnki.2", "wanfang.1", "wanfang.2"],
        )

    def test_chinese_round_pauses_and_retries_current_paper_on_captcha(self):
        paper = {
            "title": "知网一",
            "source": "cnki",
            "doi": "cnki.1",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
        }
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "cnki.1.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n" + b"x" * 6000)
            results = [
                (None, "captcha_required", "cnki"),
                (str(pdf_path), "ok", "cnki"),
            ]
            with patch.object(router, "_download_chinese_paper_once", side_effect=results) as download_one, \
                 patch.object(router, "_wait_for_cnki_captcha_resolution", return_value="ready") as wait_captcha:
                downloaded, remaining = router.run_chinese_round([paper], tmp, 9223)

        self.assertEqual(downloaded, ["cnki.1"])
        self.assertEqual(remaining, [])
        self.assertEqual(download_one.call_count, 2)
        wait_captcha.assert_called_once_with(paper, 9223)

    def test_chinese_round_captcha_retry_keeps_precise_failure_reason(self):
        paper = {
            "title": "知网二",
            "source": "cnki",
            "doi": "cnki.2",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki2",
        }
        with tempfile.TemporaryDirectory() as tmp:
            results = [
                (None, "captcha_required", "cnki"),
                (None, "manual_required", "cnki"),
            ]
            with patch.object(router, "_download_chinese_paper_once", side_effect=results) as download_one, \
                 patch.object(router, "_wait_for_cnki_captcha_resolution", return_value="ready"), \
                 patch.object(
                     router,
                     "_auto_retry_cnki_current_paper",
                     return_value=(None, "manual_required", 0.2),
                 ) as auto_retry, \
                 patch.object(router, "_confirm_chinese_manual_retry", return_value=False) as manual_retry:
                downloaded, remaining, failure_reasons = router.run_chinese_round_with_reasons(
                    [paper], tmp, 9223
                )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["cnki.2"])
        self.assertEqual(failure_reasons["cnki.2"], "manual_required")
        self.assertEqual(download_one.call_count, 2)
        auto_retry.assert_called_once_with(paper, tmp, 9223, "manual_required")
        manual_retry.assert_called_once_with("知网二", "cnki", "manual_required")

    def test_chinese_round_cnki_manual_status_auto_recovers_before_prompt(self):
        paper = {
            "title": "知网三",
            "source": "cnki",
            "doi": "cnki.3",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki3",
        }
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(
                 router,
                 "_download_chinese_paper_once",
                 return_value=(None, "manual_required", "cnki"),
             ) as download_one, \
             patch.object(
                 router,
                 "_auto_retry_cnki_current_paper",
                 return_value=(str(Path(tmp) / "cnki.3.pdf"), "ok", 0.4),
             ) as auto_retry, \
             patch.object(router, "_confirm_chinese_manual_retry") as manual_retry, \
             patch.object(router.os.path, "getsize", return_value=6144):
            downloaded, remaining, failure_reasons = router.run_chinese_round_with_reasons(
                [paper], tmp, 9223
            )

        self.assertEqual(downloaded, ["cnki.3"])
        self.assertEqual(remaining, [])
        self.assertEqual(failure_reasons, {})
        download_one.assert_called_once_with(paper, tmp, 9223)
        auto_retry.assert_called_once_with(paper, tmp, 9223, "manual_required")
        manual_retry.assert_not_called()

    def test_wait_for_cnki_captcha_resolution_keeps_watching_same_tab_during_transition(self):
        paper = {
            "title": "知网一",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
        }
        fake_times = iter([0, 0, 1, 1, 2, 2, 3, 3])
        with patch.object(
            router,
            "_find_reusable_cnki_tab",
            side_effect=[("tab-1", "captcha_required"), (None, None), ("tab-1", None)],
        ), patch.object(router, "get_tab_ws_url", side_effect=["ws://tab-1"]), \
             patch.object(router.time, "time", side_effect=lambda: next(fake_times)), \
             patch.object(router.time, "sleep", return_value=None):
            result = router._wait_for_cnki_captcha_resolution(
                paper, 9223, timeout_seconds=10, poll_interval=1
            )

        self.assertEqual(result, "ready")

    def test_wait_for_cnki_captcha_resolution_only_fails_after_tab_really_disappears(self):
        paper = {
            "title": "知网一",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
        }
        fake_times = iter([0, 0, 1, 1, 3, 3, 6, 6, 9, 9, 12, 12])
        with patch.object(
            router,
            "_find_reusable_cnki_tab",
            side_effect=[("tab-1", "captcha_required"), (None, None), (None, None), (None, None), (None, None)],
        ), patch.object(router, "get_tab_ws_url", side_effect=["ws://tab-1", None, None, None]), \
             patch.object(router.time, "time", side_effect=lambda: next(fake_times)), \
             patch.object(router.time, "sleep", return_value=None):
            result = router._wait_for_cnki_captcha_resolution(
                paper, 9223, timeout_seconds=20, poll_interval=1
            )

        self.assertEqual(result, "page_lost")

    def test_chinese_round_captcha_timeout_writes_checkpoint_for_remaining_items(self):
        papers = [
            {
                "title": "知网一",
                "source": "cnki",
                "doi": "cnki.1",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
            },
            {
                "title": "万方一",
                "source": "wanfang",
                "doi": "wanfang.1",
                "article_url": "https://d.wanfangdata.com.cn/periodical/wf1",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_path = Path(tmp) / "chinese_login_checkpoint.json"
            with patch.object(
                router,
                "_download_chinese_paper_once",
                return_value=(None, "captcha_required", "cnki"),
            ) as download_one, \
                 patch.object(router, "_wait_for_cnki_captcha_resolution", return_value="timeout"), \
                 patch.object(router, "write_chinese_login_checkpoint", return_value=str(checkpoint_path)) as write_checkpoint:
                downloaded, remaining, failure_reasons = router.run_chinese_round_with_reasons(
                    papers, tmp, 9223
                )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["cnki.1", "wanfang.1"])
        self.assertEqual(failure_reasons["cnki.1"], "captcha_required")
        self.assertEqual(failure_reasons["wanfang.1"], "captcha_required")
        download_one.assert_called_once_with(papers[0], tmp, 9223)
        write_checkpoint.assert_called_once()
        checkpoint_papers = write_checkpoint.call_args.args[1]
        self.assertEqual(checkpoint_papers[0]["failure_reason"], "captcha_required")
        self.assertEqual(checkpoint_papers[1]["failure_reason"], "captcha_required")

    def test_wait_for_cnki_captcha_resolution_retries_until_verified_tab_returns(self):
        paper = {
            "title": "CNKI demo",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=test",
        }
        probe_results = [
            ("tab-1", "captcha_required"),
            ("tab-1", "captcha_required"),
            ("tab-1", None),
        ]
        time_points = [0, 0, 0, 2, 2, 4, 4]
        with patch.object(router, "_find_reusable_cnki_tab", side_effect=probe_results) as reusable_tab, \
             patch.object(router.time, "time", side_effect=time_points), \
             patch.object(router.time, "sleep", return_value=None):
            status = router._wait_for_cnki_captcha_resolution(
                paper, 9223, timeout_seconds=10, poll_interval=2
            )

        self.assertEqual(status, "ready")
        self.assertEqual(reusable_tab.call_count, 3)

    def test_wait_for_cnki_captcha_resolution_stops_when_page_is_lost(self):
        paper = {
            "title": "CNKI demo",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=test",
        }
        with patch.object(
            router,
            "_find_reusable_cnki_tab",
            side_effect=[("tab-1", "captcha_required"), (None, None), (None, None), (None, None), (None, None)],
        ), patch.object(router, "get_tab_ws_url", side_effect=[None, None, None, None]), \
             patch.object(router.time, "time", side_effect=[0, 0, 3, 3, 6, 6, 9, 9, 12, 12]), \
             patch.object(router.time, "sleep", return_value=None):
            status = router._wait_for_cnki_captcha_resolution(
                paper, 9223, timeout_seconds=20, poll_interval=2
            )

        self.assertEqual(status, "page_lost")

    def test_cnki_evaluate_tab_requests_return_by_value(self):
        class FakeWs:
            def __init__(self):
                self.sent = []

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def recv(self):
                return json.dumps({
                    "result": {
                        "result": {
                            "value": {"captcha": False, "pdfVisible": True}
                        }
                    }
                })

            def close(self):
                pass

        fake_ws = FakeWs()
        with patch.object(gpd.websocket, "create_connection", return_value=fake_ws):
            value = gpd._cnki_evaluate_tab("ws://tab", "({captcha:false})")

        self.assertEqual(value, {"captcha": False, "pdfVisible": True})
        self.assertTrue(fake_ws.sent[0]["params"]["returnByValue"])

    def test_wanfang_detail_click_expression_handles_fulltext_delivery(self):
        expression = gpd._wanfang_detail_click_expression("periodical")

        self.assertIn("原文传递", expression)
        self.assertIn("delivery:", expression)
        delivery_block = expression.split("if (delivery.indexOf", 1)[1]
        delivery_block = delivery_block.split("return 'pdf_probe_unknown'", 1)[0]
        self.assertNotIn(".click()", delivery_block)

    def test_wanfang_detail_target_expression_returns_click_target_metadata(self):
        expression = gpd._wanfang_detail_target_expression("thesis")

        self.assertIn('"status": \'click_target\''.replace('"', ''), expression.replace('"', "'"))
        self.assertIn("rect.left + rect.width / 2", expression)
        self.assertIn("visible: rect.width > 0 && rect.height > 0", expression)

    def test_wanfang_classify_download_page_url_covers_known_variants(self):
        self.assertEqual(
            gpd._classify_wanfang_download_page_url(
                "https://f.wanfangdata.com.cn/download/pc/thesis/D03731170?transaction=x"
            ),
            "pc_download_page",
        )
        self.assertEqual(
            gpd._classify_wanfang_download_page_url(
                "https://oss.wanfangdata.com.cn/Fulltext/Download?filename=test.pdf"
            ),
            "oss_fulltext_download",
        )
        self.assertEqual(
            gpd._classify_wanfang_download_page_url(
                "https://www.wanfangdata.com.cn/NewFulltext?download=1"
            ),
            "newfulltext_download",
        )
        self.assertEqual(
            gpd._classify_wanfang_download_page_url("https://www.wanfangdata.com.cn/details/detail.do?id=demo"),
            "not_download_page",
        )

    def test_dispatch_mouse_click_sends_pressed_and_released_events(self):
        class FakeTabWs:
            def __init__(self):
                self.sent = []

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def recv(self):
                return json.dumps({"result": {}})

        fake_ws = FakeTabWs()
        ok = gpd._dispatch_mouse_click(fake_ws, 12.5, 88.0)

        self.assertTrue(ok)
        methods = [item["method"] for item in fake_ws.sent]
        self.assertEqual(methods, ["Input.dispatchMouseEvent", "Input.dispatchMouseEvent"])
        self.assertEqual(fake_ws.sent[0]["params"]["type"], "mousePressed")
        self.assertEqual(fake_ws.sent[1]["params"]["type"], "mouseReleased")

    def test_wanfang_real_click_target_uses_mouse_click_when_coordinates_visible(self):
        class FakeTabWs:
            def __init__(self):
                self.sent = []
                self.responses = [
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "click_target",
                        "text": "下载",
                        "x": 100,
                        "y": 80,
                        "visible": True,
                    })}}}),
                    json.dumps({"result": {}}),
                    json.dumps({"result": {}}),
                ]

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def recv(self):
                return self.responses.pop(0)

        result = gpd._wanfang_real_click_target(FakeTabWs(), "periodical")
        self.assertEqual(result, "clicked_real:下载")

    def test_wanfang_real_click_target_falls_back_to_dom_click_when_target_not_visible(self):
        class FakeTabWs:
            def __init__(self):
                self.sent = []
                self.responses = [
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "click_target",
                        "text": "整篇下载",
                        "x": 0,
                        "y": 0,
                        "visible": False,
                    })}}}),
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "clicked",
                        "text": "整篇下载",
                    })}}}),
                ]

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def recv(self):
                return self.responses.pop(0)

        result = gpd._wanfang_real_click_target(FakeTabWs(), "thesis")
        self.assertEqual(result, "clicked_dom:整篇下载")

    def test_wanfang_real_click_target_returns_detail_click_no_effect_when_both_paths_fail(self):
        class FakeTabWs:
            def __init__(self):
                self.responses = [
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "click_target",
                        "text": "下载",
                        "x": 1,
                        "y": 1,
                        "visible": False,
                    })}}}),
                    json.dumps({"result": {"result": {"value": json.dumps({
                        "status": "pdf_probe_unknown",
                    })}}}),
                ]

            def send(self, _payload):
                pass

            def recv(self):
                return self.responses.pop(0)

        result = gpd._wanfang_real_click_target(FakeTabWs(), "periodical")
        self.assertEqual(result, "detail_click_no_effect")

    def test_wanfang_fulltext_delivery_is_non_ok_skip_status(self):
        self.assertIn("fulltext_delivery_mode", gpd.WANFANG_NON_OK_STATUSES)
        self.assertNotIn("fulltext_delivery_mode", router.CHINESE_MANUAL_RETRY_STATUSES)
        self.assertIn("detail_click_no_effect", gpd.WANFANG_NON_OK_STATUSES)
        self.assertIn("download_page_no_actionable_control", gpd.WANFANG_NON_OK_STATUSES)
        self.assertNotIn("detail_click_no_effect", router.CHINESE_MANUAL_RETRY_STATUSES)
        self.assertNotIn("download_page_no_actionable_control", router.CHINESE_MANUAL_RETRY_STATUSES)

    def test_chinese_round_records_fulltext_delivery_mode_reason(self):
        paper = {
            "title": "万方原文传递",
            "source": "wanfang",
            "doi": "wanfang.delivery",
            "article_url": "https://d.wanfangdata.com.cn/periodical/wf-delivery",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                router,
                "_download_chinese_paper_once",
                return_value=(None, "fulltext_delivery_mode", "wanfang"),
            ) as download_one, \
                 patch.object(router, "_safe_gate_input") as gate_input:
                downloaded, remaining, failure_reasons = router.run_chinese_round_with_reasons(
                    [paper], tmp, 9223
                )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["wanfang.delivery"])
        self.assertEqual(failure_reasons["wanfang.delivery"], "fulltext_delivery_mode")
        download_one.assert_called_once()
        gate_input.assert_not_called()

    def test_chinese_round_records_new_wanfang_status_without_manual_retry_prompt(self):
        paper = {
            "title": "万方点击无效",
            "source": "wanfang",
            "doi": "wanfang.noeffect",
            "article_url": "https://d.wanfangdata.com.cn/periodical/wf-noeffect",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                router,
                "_download_chinese_paper_once",
                return_value=(None, "detail_click_no_effect", "wanfang"),
            ) as download_one, \
                 patch.object(router, "_safe_gate_input") as gate_input:
                downloaded, remaining, failure_reasons = router.run_chinese_round_with_reasons(
                    [paper], tmp, 9223
                )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["wanfang.noeffect"])
        self.assertEqual(failure_reasons["wanfang.noeffect"], "detail_click_no_effect")
        download_one.assert_called_once()
        gate_input.assert_not_called()

    def test_parallel_phase1_is_ignored_and_chinese_runs_after_english(self):
        events = []
        chinese_papers = [
            {
                "title": "万方一",
                "source": "wanfang",
                "doi": "wanfang.1",
                "article_url": "https://d.wanfangdata.com.cn/periodical/wf1",
            },
            {
                "title": "知网一",
                "source": "cnki",
                "doi": "cnki.1",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
            },
            {
                "title": "万方二",
                "source": "wanfang",
                "doi": "wanfang.2",
                "article_url": "https://d.wanfangdata.com.cn/thesis/wf2",
            },
            {
                "title": "知网二",
                "source": "cnki",
                "doi": "cnki.2",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki2",
            },
        ]
        received_chinese_order = []

        def fake_scihub(dois, output, port):
            events.append("scihub")
            return [], list(dois)

        def fake_oa(dois, output, oa_hints=None):
            events.append("oa")
            return [], list(dois), {}

        def fake_english(dois, output, port, skip_sd=False, include_si=False, sd_browser="chrome"):
            events.append("english")
            return [], [], [{"round": "Generic CDP", "downloaded": []}], {}

        def fake_chinese(papers, output, port):
            events.append("chinese")
            received_chinese_order.extend(paper["doi"] for paper in papers)
            return ["cnki.demo"], [], {}

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--papers", "10.1007/demo",
                "--chinese-input", "dummy.json",
                "--output", tmp,
                "--parallel-phase1",
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "parse_chinese_papers", return_value=chinese_papers), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "_scihub_eligible_dois", return_value=["10.1007/demo"]), \
                 patch.object(router, "run_scihub_round", side_effect=fake_scihub), \
                 patch.object(router, "run_oa_fast_round", side_effect=fake_oa), \
                 patch.object(router, "_english_login_dois_without_trusted_session", return_value=[]), \
                 patch.object(router, "run_english_cdp", side_effect=fake_english), \
                 patch.object(router, "run_chinese_round_with_reasons", side_effect=fake_chinese), \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")), \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                router.main()

        self.assertEqual(events, ["scihub", "oa", "english", "chinese"])
        self.assertEqual(received_chinese_order, ["cnki.1", "cnki.2", "wanfang.1", "wanfang.2"])
        self.assertIn("--parallel-phase1 is deprecated and ignored", stdout.getvalue())

    def test_pending_english_login_checkpoint_defers_chinese_round(self):
        chinese_papers = [{
            "title": "中文论文",
            "source": "cnki",
            "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=test",
        }]

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--papers", "10.1007/demo",
                "--chinese-input", "dummy.json",
                "--output", tmp,
                "--require-login-confirm",
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "parse_chinese_papers", return_value=chinese_papers), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "_scihub_eligible_dois", return_value=[]), \
                 patch.object(router, "run_oa_fast_round", return_value=([], ["10.1007/demo"], {})), \
                 patch.object(router, "show_english_login_gate", return_value=None), \
                 patch.object(router, "write_login_checkpoint", return_value=str(Path(tmp) / "login_checkpoint.json")), \
                 patch.object(router, "run_chinese_round") as run_chinese, \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")), \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                router.main()

        run_chinese.assert_not_called()
        self.assertIn("English login is still pending", stdout.getvalue())

    def test_main_preflight_login_gate_writes_checkpoint_before_generic_loop(self):
        pub_map = {
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--papers", "10.1007/demo",
                "--output", tmp,
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "_scihub_eligible_dois", return_value=[]), \
                 patch.object(router, "run_oa_fast_round", return_value=([], ["10.1007/demo"], {})), \
                 patch.object(router, "describe_publisher_session", return_value={"probe_status": "unknown"}), \
                 patch.object(router, "show_english_login_gate", return_value=None) as login_gate, \
                 patch.object(router, "run_english_cdp") as run_english, \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")), \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                router.main()

            checkpoint = json.loads((Path(tmp) / "login_checkpoint.json").read_text(encoding="utf-8"))

        run_english.assert_not_called()
        login_gate.assert_called_once_with(["10.1007/demo"], skip_sd=False, port=9223)
        self.assertEqual([item["doi"] for item in checkpoint["items"]], ["10.1007/demo"])
        self.assertEqual(checkpoint["status"], "pending_user_login")
        self.assertIn("before the grouped download loop", stdout.getvalue())

    def test_main_preflight_login_skip_continues_non_login_remainder(self):
        pub_map = {
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
            "10.9999/oa-generic": {
                "strategy": "generic",
                "_key": "oa_generic",
                "publisher_domain": "example.org",
                "requires_auth": "none",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--papers", "10.1007/demo,10.9999/oa-generic",
                "--output", tmp,
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "_scihub_eligible_dois", return_value=[]), \
                 patch.object(router, "run_oa_fast_round", return_value=([], list(pub_map), {})), \
                 patch.object(router, "describe_publisher_session", return_value={"probe_status": "unknown"}), \
                 patch.object(router, "show_english_login_gate", return_value=False), \
                 patch.object(router, "run_english_cdp", return_value=([], [], [{"round": "Generic CDP", "downloaded": []}], {})) as run_english, \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")):
                router.main()

        run_english.assert_called_once()
        self.assertEqual(run_english.call_args.args[0], ["10.9999/oa-generic"])

    def test_main_preflight_login_confirmed_skips_prompt_and_runs_cdp(self):
        pub_map = {
            "10.1109/demo": {
                "strategy": "ieee_cdp",
                "_key": "ieee",
                "publisher_domain": "ieeexplore.ieee.org",
                "requires_auth": "sso",
            },
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--papers", "10.1109/demo,10.1007/demo",
                "--output", tmp,
                "--confirmed",
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "_scihub_eligible_dois", return_value=[]), \
                 patch.object(router, "run_oa_fast_round", return_value=([], ["10.1109/demo", "10.1007/demo"], {})), \
                 patch.object(router, "describe_publisher_session", return_value={"probe_status": "unknown"}), \
                 patch.object(router, "show_english_login_gate") as login_gate, \
                 patch.object(router, "run_ieee_round", return_value=(["10.1109/demo"], ["10.1007/demo"])) as run_ieee, \
                 patch.object(router, "run_english_cdp", return_value=([], ["10.1007/demo"], [{"round": "Generic CDP", "downloaded": []}], {"10.1007/demo": "generic_failed"})) as run_english, \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")), \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                router.main()

        login_gate.assert_not_called()
        run_ieee.assert_called_once()
        run_english.assert_called_once()
        self.assertEqual(run_english.call_args.args[0], ["10.1007/demo"])
        self.assertIn("--confirmed supplied", stdout.getvalue())

    def test_main_preflight_login_checkpoint_includes_ieee_and_generic(self):
        pub_map = {
            "10.1109/demo": {
                "strategy": "ieee_cdp",
                "_key": "ieee",
                "publisher_domain": "ieeexplore.ieee.org",
                "requires_auth": "sso",
            },
            "10.1007/demo": {
                "strategy": "generic",
                "_key": "springer",
                "publisher_domain": "link.springer.com",
                "requires_auth": "institution",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--papers", "10.1109/demo,10.1007/demo",
                "--output", tmp,
                "--require-login-confirm",
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "resolve_publisher", side_effect=lambda doi: pub_map[doi]), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "_scihub_eligible_dois", return_value=[]), \
                 patch.object(router, "run_oa_fast_round", return_value=([], ["10.1109/demo", "10.1007/demo"], {})), \
                 patch.object(router, "show_english_login_gate", return_value=None), \
                 patch.object(router, "run_english_cdp", return_value=([], [], [{"round": "Generic CDP", "downloaded": []}], {})) as run_english, \
                 patch.object(router, "run_ieee_round") as run_ieee, \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")):
                router.main()

            checkpoint = json.loads((Path(tmp) / "login_checkpoint.json").read_text(encoding="utf-8"))

        self.assertEqual(
            [item["doi"] for item in checkpoint["items"]],
            ["10.1109/demo", "10.1007/demo"],
        )
        run_english.assert_not_called()
        run_ieee.assert_not_called()

    def test_main_writes_chinese_checkpoint_in_sorted_order(self):
        chinese_papers = [
            {
                "title": "万方一",
                "source": "wanfang",
                "doi": "wanfang.1",
                "article_url": "https://d.wanfangdata.com.cn/periodical/wf1",
            },
            {
                "title": "知网一",
                "source": "cnki",
                "doi": "cnki.1",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki1",
            },
            {
                "title": "万方二",
                "source": "wanfang",
                "doi": "wanfang.2",
                "article_url": "https://d.wanfangdata.com.cn/thesis/wf2",
            },
            {
                "title": "知网二",
                "source": "cnki",
                "doi": "cnki.2",
                "article_url": "https://kns.cnki.net/kcms/detail/detail.aspx?filename=cnki2",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "step5.lock"
            argv = [
                "unified_download_router.py",
                "--chinese-input", "dummy.json",
                "--output", tmp,
                "--require-login-confirm",
            ]
            with patch.dict(router.os.environ, {"MORE_PAPER_STEP5_LOCK_PATH": str(lock_path)}), \
                 patch.object(sys, "argv", argv), \
                 patch.object(router, "parse_chinese_papers", return_value=chinese_papers), \
                 patch.object(router, "ensure_cdp_running", return_value=True), \
                 patch.object(router, "check_required_deps", return_value=True), \
                 patch.object(router, "show_chinese_login_gate", return_value=None) as gate, \
                 patch.object(router, "generate_download_log", return_value=str(Path(tmp) / "download_log.md")):
                router.main()

            checkpoint = json.loads((Path(tmp) / "chinese_login_checkpoint.json").read_text(encoding="utf-8"))

        self.assertEqual(
            [item["doi"] for item in checkpoint["items"]],
            ["cnki.1", "cnki.2", "wanfang.1", "wanfang.2"],
        )
        gate.assert_called_once()
        self.assertEqual(gate.call_args.kwargs["port"], 9223)

    def test_resume_from_login_checkpoint_retries_only_pending_english_dois(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = {
                "checkpoint_type": "publisher_login",
                "status": "pending_user_login",
                "stage": "english_cdp_retry",
                "items": [
                    {"doi": "10.1007/demo", "failure_reason": "pending_user_login"},
                    {"doi": "10.1016/j.demo.2026.01.001", "failure_reason": "pending_user_login"},
                ],
            }
            checkpoint_path = Path(tmp) / "login_checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            resumed = (["10.1007/demo"], ["10.1016/j.demo.2026.01.001"], {
                "10.1016/j.demo.2026.01.001": "generic_failed",
            })

            with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}) as open_tabs, \
                 patch.object(router, "run_generic_round", return_value=resumed) as run_generic:
                downloaded, remaining, results, reasons = router.resume_from_login_checkpoint(
                    str(checkpoint_path), tmp, 9223
                )

        self.assertEqual(downloaded, ["10.1007/demo"])
        self.assertEqual(remaining, ["10.1016/j.demo.2026.01.001"])
        self.assertEqual(reasons, {"10.1016/j.demo.2026.01.001": "generic_failed"})
        self.assertEqual(results[-1]["round"], "Generic CDP (resume login checkpoint)")
        run_generic.assert_called_once_with(
            ["10.1007/demo", "10.1016/j.demo.2026.01.001"], tmp, 9223, include_si=False
        )
        open_tabs.assert_called_once_with(
            9223, ["10.1007/demo", "10.1016/j.demo.2026.01.001"]
        )

    def test_resume_from_login_checkpoint_confirmed_does_not_refresh_pending_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint = {
                "checkpoint_type": "publisher_login",
                "status": "pending_user_login",
                "stage": "english_cdp_retry",
                "items": [
                    {"doi": "10.1039/d5ra02870a", "failure_reason": "pending_user_login"},
                ],
            }
            checkpoint_path = Path(tmp) / "login_checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            resumed = ([], ["10.1039/d5ra02870a"], {
                "10.1039/d5ra02870a": "pdf_probe_unknown",
            })

            with patch.object(router, "open_english_login_tabs", return_value={"opened": [], "failed": []}), \
                 patch.object(router, "run_generic_round", return_value=resumed), \
                 patch.object(router, "write_login_checkpoint") as write_checkpoint:
                downloaded, remaining, results, reasons = router.resume_from_login_checkpoint(
                    str(checkpoint_path), tmp, 9223, confirmed_login=True
                )

        self.assertEqual(downloaded, [])
        self.assertEqual(remaining, ["10.1039/d5ra02870a"])
        self.assertEqual(reasons, {"10.1039/d5ra02870a": "generic_failed"})
        self.assertEqual(results[-1]["round"], "Generic CDP (resume login checkpoint)")
        write_checkpoint.assert_not_called()

    def test_check_all_sessions_reports_weak_cookie_probe(self):
        with patch.object(router, "_PUBLISHER_CONFIGS", {"sd_elsevier": {"publisher_domain": "www.sciencedirect.com", "strategy": "generic", "_key": "sd_elsevier"}}), \
             patch.object(router, "describe_publisher_session", return_value={
                 "publisher": "sd_elsevier",
                 "domain": "www.sciencedirect.com",
                 "strategy": "generic",
                 "has_session": False,
                 "cookie_count": 0,
                 "signal_strength": "pdf_probe",
                 "probe_status": "blocked",
                 "probe_reason": "pdf probe unknown",
             }), \
             patch.object(router, "check_cdp", return_value=True), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            router.check_all_sessions(9223)

        text = stdout.getvalue()
        self.assertIn("pdf_probe (0)", text)
        self.assertIn("weak signal", text.lower() if "weak signal" in text.lower() else "cookie count is a weak signal")
        self.assertIn("需要先人工登录/验证", text)

    def test_check_all_sessions_prints_three_state_readiness_labels(self):
        signals = iter([
            {
                "publisher": "wiley",
                "domain": "onlinelibrary.wiley.com",
                "strategy": "generic",
                "has_session": True,
                "cookie_count": 0,
                "signal_strength": "article_probe",
                "probe_status": "ok",
                "probe_reason": "pdf_link_present",
            },
            {
                "publisher": "springer",
                "domain": "link.springer.com",
                "strategy": "generic",
                "has_session": False,
                "cookie_count": 0,
                "signal_strength": "weak_cookie_probe",
                "probe_status": "unknown",
                "probe_reason": "cookie probe only",
            },
        ])
        with patch.object(router, "_PUBLISHER_CONFIGS", {
            "wiley": {"publisher_domain": "onlinelibrary.wiley.com", "strategy": "generic", "_key": "wiley"},
            "springer": {"publisher_domain": "link.springer.com", "strategy": "generic", "_key": "springer"},
        }), \
             patch.object(router, "describe_publisher_session", side_effect=lambda port, cfg: next(signals)), \
             patch.object(router, "check_cdp", return_value=True), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout:
            router.check_all_sessions(9223)

        text = stdout.getvalue()
        self.assertIn("可直接尝试下载", text)
        self.assertIn("信号不足，需实际下载验证", text)

    def test_step5_doctor_blocked_when_cdp_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(doctor, "check_cdp", return_value=False), \
             patch.object(doctor, "check_required_deps", return_value=True), \
             patch.object(doctor, "_lock_status", return_value={"status": "absent", "running": False, "path": "lock"}):
            report = doctor.build_doctor_report(port=9223, browser="chrome", output_dir=tmp)

        self.assertEqual(report["status"], "blocked")
        self.assertIn("cdp_not_running", report["blocking"])

    def test_step5_doctor_partial_when_sessions_are_untrusted(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(doctor, "check_cdp", return_value=True), \
             patch.object(doctor, "get_cdp_browser_product", return_value="Chrome/120"), \
             patch.object(doctor, "cdp_browser_matches", return_value=True), \
             patch.object(doctor, "check_required_deps", return_value=True), \
             patch.object(doctor, "_lock_status", return_value={"status": "absent", "running": False, "path": "lock"}), \
             patch.object(doctor, "_PUBLISHER_CONFIGS", {"springer": {"_key": "springer", "publisher_domain": "link.springer.com"}}), \
             patch.object(doctor, "describe_publisher_session", return_value={"probe_status": "unknown", "probe_reason": "cookie probe only", "has_session": False}):
            report = doctor.build_doctor_report(port=9223, browser="chrome", output_dir=tmp)

        self.assertEqual(report["status"], "partial")
        self.assertIn("no_trusted_publisher_session", report["warnings"])

    def test_get_all_cookies_via_tab_uses_tab_scoped_network_domain(self):
        class FakeWs:
            def __init__(self):
                self.sent = []

            def send(self, payload):
                self.sent.append(json.loads(payload))

            def settimeout(self, _timeout):
                pass

            def recv(self):
                last_id = self.sent[-1]["id"]
                last_method = self.sent[-1]["method"]
                if last_method == "Network.enable":
                    return json.dumps({"id": last_id, "result": {}})
                if last_method == "Network.getAllCookies":
                    return json.dumps({
                        "id": last_id,
                        "result": {"cookies": [{"domain": ".ieee.org"}]},
                    })
                raise AssertionError(f"unexpected method {last_method}")

            def close(self):
                pass

        fake_ws = FakeWs()
        with patch.object(cdp_utils, "create_tab", return_value=(None, "tab-1")), \
             patch.object(cdp_utils, "get_tab_ws_url", return_value="ws://tab-1"), \
             patch.object(cdp_utils.websocket, "create_connection", return_value=fake_ws), \
             patch.object(cdp_utils, "close_tab") as close_tab:
            cookies = cdp_utils.get_all_cookies_via_tab(9223)

        self.assertEqual(cookies, [{"domain": ".ieee.org"}])
        self.assertEqual(
            [msg["method"] for msg in fake_ws.sent],
            ["Network.enable", "Network.getAllCookies"],
        )
        close_tab.assert_called_once_with(9223, "tab-1")

    def test_check_publisher_session_uses_tab_cookie_probe(self):
        publisher = {"publisher_domain": "ieee.org"}
        cookies = [
            {"domain": ".example.org"},
            {"domain": ".ieee.org"},
        ]
        with patch.object(gpd, "get_all_cookies_via_tab", return_value=cookies):
            has_session, count = gpd.check_publisher_session(9223, publisher)

        self.assertTrue(has_session)
        self.assertEqual(count, 1)

    def test_download_via_ieee_check_session_uses_tab_cookie_probe(self):
        cookies = [
            {"domain": ".ieee.org"},
            {"domain": ".sciencedirect.com"},
        ]
        with patch.object(ieee, "get_all_cookies_via_tab", return_value=cookies):
            total_c, ieee_c, all_cookies = ieee.check_session(9223)

        self.assertEqual(total_c, 2)
        self.assertEqual(ieee_c, 1)
        self.assertEqual(all_cookies, cookies)

    def test_check_wiley_access_reports_pdf_link_present(self):
        publisher = {
            "_key": "wiley",
            "selectors": ['a[href*="pdfdirect"]'],
            "publisher_domain": "onlinelibrary.wiley.com",
        }
        with patch.object(gpd, "check_cdp", return_value=True), \
             patch.object(gpd, "create_tab", return_value=(None, "tab-1")), \
             patch.object(gpd, "_detect_access_barrier", return_value=(None, "")), \
             patch.object(gpd, "_extract_pdf_url_from_dom", return_value="https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/ente.202301205"), \
             patch.object(gpd, "close_tab"), \
             patch.object(gpd.time, "sleep", return_value=None):
            status, reason = gpd.check_wiley_access(9223, publisher)

        self.assertEqual(status, "ok")
        self.assertIn("pdf_link_present", reason)

    def test_describe_publisher_session_uses_wiley_article_probe(self):
        publisher = {
            "_key": "wiley",
            "publisher_domain": "onlinelibrary.wiley.com",
            "strategy": "generic",
            "selectors": ['a[href*="pdfdirect"]'],
        }
        with patch.object(gpd, "check_publisher_session", return_value=(False, 0)), \
             patch.object(gpd, "check_wiley_access", return_value=("ok", "pdf_link_present")):
            signal = gpd.describe_publisher_session(9223, publisher)

        self.assertEqual(signal["signal_strength"], "article_probe")
        self.assertEqual(signal["probe_status"], "ok")
        self.assertTrue(signal["has_session"])

    def test_describe_publisher_session_uses_wanfang_page_probe_even_with_zero_cookies(self):
        publisher = {
            "_key": "wanfang",
            "publisher_domain": "d.wanfangdata.com.cn",
            "strategy": "chinese_cdp",
            "login_url": "https://www.wanfangdata.com.cn/",
        }
        with patch.object(gpd, "check_publisher_session", return_value=(False, 0)), \
             patch.object(gpd, "check_wanfang_access", return_value=("ok", "logged_in_marker_present")):
            signal = gpd.describe_publisher_session(9223, publisher)

        self.assertEqual(signal["signal_strength"], "page_probe")
        self.assertEqual(signal["probe_status"], "ok")
        self.assertTrue(signal["has_session"])


if __name__ == "__main__":
    unittest.main()
