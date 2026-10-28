"""로컬 웹 UI (표준 라이브러리만 사용).

이 서버는 GitHub Pages용이 아니다. Pages는 정적 사이트라 Python 서버가
돌아가지 않는다. 이 서버는 127.0.0.1 전용으로, 같은 PC의 브라우저에서만
열 수 있는 로컬 UI다.

재사용: doctor 상태, trim, draft 로직은 studio.py를 그대로 쓴다.
shell 명령을 새로 만들지 않고, studio.trim()이 인자 배열로 실행하는
규칙과 기존 출력 덮어쓰기 금지 규칙을 그대로 유지한다.
Whisper·Ollama 실제 실행은 여기서 새로 검증하지 않는다. draft는
기본적으로 오프라인 템플릿(미리보기)이며, Ollama 모델을 지정하면
로컬 Ollama에만 요청한다는 studio.py의 규칙을 따른다.

경로 주의: trim에 입력하는 경로는 브라우저가 있는 PC가 아니라
서버가 실행 중인 PC의 파일 경로다. 이 점을 UI에 명시한다.

실행:
    python3 web.py --port 8768
    # 브라우저에서 http://127.0.0.1:8768 접속
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import studio

PAGE = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>콘텐츠 스튜디오 (로컬)</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:20px auto;padding:0 16px}
section{border:1px solid #ccc;border-radius:12px;padding:16px;margin:16px 0}
input,textarea,button{padding:8px;margin:4px 2px;width:100%;box-sizing:border-box}
button{width:auto} pre{white-space:pre-wrap;background:#f4f4f4;padding:12px}
.warn{color:#a00}
</style></head><body>
<h1>콘텐츠 스튜디오 (로컬 전용)</h1>
<p>이 페이지는 127.0.0.1 로컬 서버에서만 열린다. 외부 전송은 없다.</p>

<section><h2>doctor 상태</h2><button onclick="loadDoctor()">상태 새로고침</button>
<pre id="doctor"></pre>
<p>Whisper·Ollama 실제 동작은 이 환경에서 검증하지 않았다. doctor는 설치 유무만 표시한다.</p></section>

<section><h2>SRT → 오프라인 draft 미리보기 / 생성</h2>
<textarea id="srt" rows="8" placeholder="SRT 텍스트를 붙여넣으세요 (번호·타임코드 포함 가능)"></textarea>
<input id="draft-out" placeholder="생성할 파일 경로 (비우면 미리보기만, 서버 PC 기준)">
<button onclick="draftPreview()">미리보기</button>
<button onclick="draftSave()">파일로 생성 (기존 파일이 있으면 거부됨)</button>
<pre id="draft-result"></pre></section>

<section><h2>영상 자르기 (trim)</h2>
<p class="warn">경로는 브라우저 PC가 아니라 서버가 실행 중인 PC의 파일 경로다.</p>
<input id="trim-in" placeholder="입력 영상 경로 (서버 PC 기준)">
<input id="trim-out" placeholder="출력 영상 경로 (기존 파일이 있으면 거부됨, 서버 PC 기준)">
<input id="trim-start" placeholder="시작 (초, 예: 0.5)">
<input id="trim-end" placeholder="끝 (초, 예: 2.5)">
<label><input type="checkbox" id="trim-accurate" style="width:auto"> 정확한 재인코딩 (기본은 stream-copy)</label>
<button onclick="doTrim()">자르기 실행</button>
<pre id="trim-result"></pre></section>

<script>
async function api(path, body){
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)});
  const data = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
  return data;
}
async function loadDoctor(){
  const r = await fetch('/api/doctor'); const d = await r.json();
  document.getElementById('doctor').textContent = JSON.stringify(d, null, 2);
}
async function draftPreview(){
  try{ const d = await api('/api/draft-preview', {srt_text: document.getElementById('srt').value});
    document.getElementById('draft-result').textContent = d.markdown; }
  catch(e){ document.getElementById('draft-result').textContent = '오류: ' + e.message; }
}
async function draftSave(){
  try{ const d = await api('/api/draft', {srt_text: document.getElementById('srt').value,
      output: document.getElementById('draft-out').value});
    document.getElementById('draft-result').textContent = '생성됨: ' + d.file + ' (' + d.mode + ')'; }
  catch(e){ document.getElementById('draft-result').textContent = '오류: ' + e.message; }
}
async function doTrim(){
  try{ const d = await api('/api/trim', {input: document.getElementById('trim-in').value,
      output: document.getElementById('trim-out').value,
      start: Number(document.getElementById('trim-start').value),
      end: Number(document.getElementById('trim-end').value),
      accurate: document.getElementById('trim-accurate').checked});
    document.getElementById('trim-result').textContent = JSON.stringify(d, null, 2); }
  catch(e){ document.getElementById('trim-result').textContent = '오류: ' + e.message; }
}
loadDoctor();
</script></body></html>
"""

OFFLINE_TEMPLATE = (
    "# 30초 개발 시연\n\n## 훅 (0–2초)\n[해결할 문제 한 문장]\n\n"
    "## 시연 (2–25초)\n{text}\n\n## 마무리 (25–30초)\n[재현 방법과 저장할 포인트]\n"
)


def doctor_status() -> dict:
    """studio.py main()의 doctor 분기와 같은 정보만 돌려준다."""
    return {
        "python": sys.version.split()[0],
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "whisper": bool(importlib.util.find_spec("whisper")),
        "ollama": "선택 기능. http://127.0.0.1:11434 에서 모델을 따로 실행하세요.",
        "whisper_verified": False,
        "ollama_verified": False,
    }


def draft_preview_markdown(srt_text: str) -> str:
    """SRT 텍스트에서 오프라인 draft 미리보기를 만든다. 파일을 쓰지 않는다.

    자막 텍스트 추출은 studio.transcript_text()를 그대로 재사용한다.
    템플릿은 studio.draft()의 오프라인 분기와 같은 문장이다.
    """
    if not isinstance(srt_text, str) or not srt_text.strip():
        raise ValueError("SRT 텍스트가 없습니다.")
    with tempfile.TemporaryDirectory() as tmp:
        srt_path = Path(tmp) / "preview.srt"
        srt_path.write_text(srt_text, encoding="utf-8")
        text = studio.transcript_text(str(srt_path))
    if not text:
        raise ValueError("자막에 텍스트가 없습니다.")
    kind = "오프라인 편집 템플릿 — AI 생성 아님"
    return f"<!-- {kind}; 게시 전 사람이 검토 -->\n\n" + OFFLINE_TEMPLATE.format(text=text)


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "ContentStudio/1.0"

    def log_message(self, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1_000_000:
            raise ValueError("요청 본문이 너무 큽니다 (1MB 제한).")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"JSON 형식이 올바르지 않습니다: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("요청 본문은 JSON 객체여야 합니다.")
        return data

    def do_GET(self):  # noqa: N802
        try:
            if self.path in ("/", "/index.html"):
                self._send_html()
            elif self.path == "/api/doctor":
                self._send_json(doctor_status())
            else:
                self._send_json({"error": "없는 경로입니다."}, 404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)

    def do_POST(self):  # noqa: N802
        try:
            body = self._read_json()
            if self.path == "/api/draft-preview":
                markdown = draft_preview_markdown(body.get("srt_text", ""))
                self._send_json({"markdown": markdown, "mode": "오프라인 편집 템플릿 — AI 생성 아님"})
            elif self.path == "/api/draft":
                srt_text = body.get("srt_text", "")
                output = body.get("output", "")
                if not output:
                    raise ValueError("생성할 파일 경로(output)를 입력하세요. 미리보기만 하려면 /api/draft-preview를 쓰세요.")
                # studio.draft()가 덮어쓰기 금지·파일 생성을 그대로 처리한다.
                with tempfile.TemporaryDirectory() as tmp:
                    srt_path = Path(tmp) / "input.srt"
                    srt_path.write_text(srt_text, encoding="utf-8")
                    result = studio.draft(str(srt_path), output, model=body.get("model"))
                self._send_json(result, 201)
            elif self.path == "/api/trim":
                start, end = body.get("start"), body.get("end")
                if isinstance(start, bool) or isinstance(end, bool) \
                        or not isinstance(start, (int, float)) \
                        or not isinstance(end, (int, float)):
                    raise ValueError("0 <= 시작 < 끝인 초 단위 구간을 입력하세요.")
                result = studio.trim(
                    body.get("input", ""), body.get("output", ""),
                    start, end, accurate=bool(body.get("accurate", False)))
                self._send_json(result)
            else:
                self._send_json({"error": "없는 경로입니다."}, 404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)


def create_server(host="127.0.0.1", port=0):
    server = ThreadingHTTPServer((host, port), StudioHandler)
    server.daemon_threads = True
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="콘텐츠 스튜디오 로컬 웹 UI (127.0.0.1 전용)")
    parser.add_argument("--host", default="127.0.0.1", help="바인드 주소 (기본값: 127.0.0.1, 바꾸지 마세요)")
    parser.add_argument("--port", type=int, default=8768, help="포트 (기본값: 8768)")
    args = parser.parse_args(argv)
    if args.host != "127.0.0.1":
        parser.error("이 서버는 127.0.0.1 전용입니다. 외부 노출용으로 바꾸지 마세요.")
    server = create_server(args.host, args.port)
    print(f"콘텐츠 스튜디오 로컬 웹 UI: http://127.0.0.1:{server.server_address[1]}")
    print("경로는 서버 PC 기준입니다. Ctrl+C로 종료하세요.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
