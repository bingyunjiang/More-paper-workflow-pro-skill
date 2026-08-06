from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_update_prompt.py"


class RenderUpdatePromptTest(unittest.TestCase):
    def test_renders_standard_prompt_from_json_file(self):
        payload = {
            "should_prompt": True,
            "skill_version": "v1.0.14-20260618",
            "remote_version": "v1.0.15-20260620",
            "remote_head": "abcdef1234567890",
            "update_command": "cd /tmp/repo && git pull --ff-only",
            "messages": ["- 远程仓库已有新提交：本地 1111111，远程 abcdef1。"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(payload_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout
        for token in [
            "检测到 more-paper-workflow 有新版本可用。",
            "当前版本：v1.0.14-20260618",
            "远程版本：v1.0.15-20260620",
            "远程提交：abcdef1",
            "建议更新命令：cd /tmp/repo && git pull --ff-only",
            "请选择其一：",
            "1. 升级",
            "2. 本次跳过",
            "3. 今日不再提醒",
        ]:
            self.assertIn(token, text)

    def test_renders_nothing_when_prompt_is_not_requested(self):
        payload = {
            "should_prompt": False,
            "skill_version": "v1.0.27-20260806",
            "remote_head": None,
            "update_command": None,
        }
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
