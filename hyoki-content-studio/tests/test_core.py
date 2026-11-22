import shutil
import subprocess

import pytest

from studio import core


def test_parse_time():
    assert core.parse_time("90") == 90
    assert core.parse_time("1:30") == 90
    assert core.parse_time("00:01:30.5") == 90.5
    with pytest.raises(ValueError):
        core.parse_time("1:2:3:4")


def test_srt_timestamp():
    assert core.srt_timestamp(3661.25) == "01:01:01,250"


def test_cut_command_rejects_reverse_range():
    with pytest.raises(ValueError):
        core.build_cut_command("a.mp4", "10", "5", "b.mp4")


def test_cut_command_uses_stream_copy():
    cmd = core.build_cut_command("a.mp4", "0:05", "0:15", "b.mp4")
    assert cmd[cmd.index("-c") + 1] == "copy"
    assert cmd[cmd.index("-t") + 1] == "10.000"


def test_segments_to_srt_roundtrip():
    srt = core.segments_to_srt([{"start": 0, "end": 1.5, "text": " 안녕하세요 "},
                                {"start": 1.5, "end": 3, "text": "로봇 시연입니다"}])
    assert "00:00:01,500 --> 00:00:03,000" in srt
    assert core.srt_to_text(srt) == "안녕하세요 로봇 시연입니다"


def test_draft_prompt():
    assert "3줄 요약" in core.build_draft_prompt("내용", "summary")
    with pytest.raises(ValueError):
        core.build_draft_prompt("내용", "poem")


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 없음")
def test_real_cut(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=6:size=160x120:rate=10",
                    "-pix_fmt", "yuv420p", str(src)], check=True, capture_output=True)
    out = core.cut(str(src), "1", "4", str(tmp_path / "clip.mp4"))
    assert out.exists() and out.stat().st_size > 0
