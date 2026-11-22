"""콘텐츠 스튜디오 핵심 기능: 영상 자르기(ffmpeg), 자막(Whisper), 초안(Ollama)."""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path


# ---------- 시간 처리 ----------
def parse_time(value: str) -> float:
    """'90', '1:30', '00:01:30.5' 형식을 초로 변환."""
    parts = [float(p) for p in str(value).strip().split(":")]
    if not 1 <= len(parts) <= 3 or any(p < 0 for p in parts):
        raise ValueError(f"잘못된 시간 형식: {value}")
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------- 영상 자르기 ----------
def build_cut_command(src: str, start: str, end: str, out: str) -> list[str]:
    """재인코딩 없이(stream copy) 구간을 자르는 ffmpeg 명령."""
    s, e = parse_time(start), parse_time(end)
    if e <= s:
        raise ValueError("끝 시간은 시작 시간보다 커야 해요.")
    return ["ffmpeg", "-y", "-ss", f"{s:.3f}", "-i", src, "-t", f"{e - s:.3f}",
            "-c", "copy", "-avoid_negative_ts", "make_zero", out]


def cut(src: str, start: str, end: str, out: str) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg가 설치돼 있지 않아요.")
    subprocess.run(build_cut_command(src, start, end, out), check=True, capture_output=True)
    return Path(out)


# ---------- 자막 ----------
def segments_to_srt(segments: list[dict]) -> str:
    blocks = []
    for i, seg in enumerate(segments, 1):
        text = str(seg["text"]).strip()
        blocks.append(f"{i}\n{srt_timestamp(seg['start'])} --> {srt_timestamp(seg['end'])}\n{text}\n")
    return "\n".join(blocks)


def transcribe(src: str, model: str = "small", language: str = "ko") -> list[dict]:
    """openai-whisper로 음성 인식. `pip install openai-whisper` 필요."""
    try:
        import whisper  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Whisper가 없어요: pip install openai-whisper") from exc
    result = whisper.load_model(model).transcribe(src, language=language)
    return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in result["segments"]]


# ---------- 초안 ----------
DRAFT_PROMPT = """다음은 시연 영상의 자막이에요. 이 내용을 바탕으로 {kind}을 한국어로 작성해 주세요.
자막에 없는 사실은 지어내지 마세요.

자막:
{transcript}
"""

KINDS = {"summary": "3줄 요약", "description": "영상 설명글(유튜브용)", "script": "60초 쇼츠 대본"}


def build_draft_prompt(transcript: str, kind: str = "summary") -> str:
    if kind not in KINDS:
        raise ValueError(f"kind는 {list(KINDS)} 중 하나여야 해요.")
    return DRAFT_PROMPT.format(kind=KINDS[kind], transcript=transcript.strip())


def ollama_generate(prompt: str, model: str = "llama3.2",
                    host: str = "http://localhost:11434", timeout: int = 300) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())["response"]


def srt_to_text(srt: str) -> str:
    lines = []
    for line in srt.splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        lines.append(line)
    return " ".join(lines)
