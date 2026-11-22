"""사용법: python -m studio <cut|subtitle|draft|pipeline> ..."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import core


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="studio", description="콘텐츠 스튜디오")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cut", help="재인코딩 없이 영상 자르기")
    c.add_argument("src"); c.add_argument("start"); c.add_argument("end"); c.add_argument("-o", "--out", required=True)

    s = sub.add_parser("subtitle", help="Whisper로 SRT 자막 만들기")
    s.add_argument("src"); s.add_argument("-o", "--out")
    s.add_argument("--model", default="small"); s.add_argument("--lang", default="ko")

    d = sub.add_parser("draft", help="SRT 자막으로 Ollama 초안 만들기")
    d.add_argument("srt"); d.add_argument("--kind", default="summary", choices=list(core.KINDS))
    d.add_argument("--model", default="llama3.2"); d.add_argument("-o", "--out")

    pl = sub.add_parser("pipeline", help="자르기 → 자막 → 초안 한 번에")
    pl.add_argument("src"); pl.add_argument("start"); pl.add_argument("end")
    pl.add_argument("--outdir", default="output"); pl.add_argument("--kind", default="summary", choices=list(core.KINDS))
    pl.add_argument("--whisper-model", default="small"); pl.add_argument("--llm", default="llama3.2")

    a = p.parse_args(argv)

    if a.cmd == "cut":
        print(core.cut(a.src, a.start, a.end, a.out))
    elif a.cmd == "subtitle":
        out = Path(a.out or Path(a.src).with_suffix(".srt"))
        out.write_text(core.segments_to_srt(core.transcribe(a.src, a.model, a.lang)), encoding="utf-8")
        print(out)
    elif a.cmd == "draft":
        text = core.srt_to_text(Path(a.srt).read_text(encoding="utf-8"))
        result = core.ollama_generate(core.build_draft_prompt(text, a.kind), a.model)
        if a.out:
            Path(a.out).write_text(result, encoding="utf-8")
        print(result)
    elif a.cmd == "pipeline":
        outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
        clip = core.cut(a.src, a.start, a.end, str(outdir / f"clip{Path(a.src).suffix}"))
        segs = core.transcribe(str(clip), a.whisper_model)
        srt = core.segments_to_srt(segs)
        (outdir / "clip.srt").write_text(srt, encoding="utf-8")
        draft = core.ollama_generate(core.build_draft_prompt(core.srt_to_text(srt), a.kind), a.llm)
        (outdir / f"{a.kind}.md").write_text(draft, encoding="utf-8")
        print(f"완료: {outdir}")


if __name__ == "__main__":
    main()
