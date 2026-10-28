"""로컬 웹 UI 테스트. 실제 서버를 임시 포트(127.0.0.1)로 띄우고
urllib로 호출한다. 테스트 후 서버를 반드시 종료한다.
Whisper·Ollama 실제 실행은 검증하지 않는다. trim 테스트는 로컬
FFmpeg 합성 영상만 쓴다."""

import json
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from web import create_server


def _call(base, path, method="GET", body=None):
    req = urllib.request.Request(
        base + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


SRT = ("1\n00:00:00,000 --> 00:00:03,000\n"
       "Unity에서 로봇 관절의 목표 각도를 설정합니다.\n")


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = create_server("127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def test_index_and_doctor(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("콘텐츠 스튜디오", resp.read().decode())
        status, body = _call(self.base, "/api/doctor")
        self.assertEqual(status, 200)
        self.assertIn("ffmpeg", body)
        self.assertFalse(body["whisper_verified"])
        self.assertFalse(body["ollama_verified"])

    def test_draft_preview_and_save_no_overwrite(self):
        status, body = _call(self.base, "/api/draft-preview", "POST", {"srt_text": SRT})
        self.assertEqual(status, 200)
        self.assertIn("오프라인 편집 템플릿", body["markdown"])
        self.assertIn("로봇 관절의 목표 각도", body["markdown"])
        out = str(Path(self.tmp.name) / "draft.md")
        status, body = _call(self.base, "/api/draft", "POST", {"srt_text": SRT, "output": out})
        self.assertEqual(status, 201)
        self.assertTrue(Path(out).exists())
        # 같은 경로로 다시 생성하면 덮어쓰기 금지로 거부된다.
        status, body = _call(self.base, "/api/draft", "POST", {"srt_text": SRT, "output": out})
        self.assertEqual(status, 400)
        self.assertIn("덮어쓰지", body["error"])

    def test_trim_with_local_ffmpeg(self):
        src = Path(self.tmp.name) / "in.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=128x72:rate=10",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                       check=True, capture_output=True, timeout=60)
        out = str(Path(self.tmp.name) / "out.mp4")
        status, body = _call(self.base, "/api/trim", "POST",
                             {"input": str(src), "output": out, "start": 0.5, "end": 2.5})
        self.assertEqual(status, 200, body)
        self.assertTrue(Path(out).exists())
        self.assertGreater(Path(out).stat().st_size, 0)

    def test_server_binds_localhost_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
