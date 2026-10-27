# 효기 로컬 콘텐츠 스튜디오

개발 시연 녹화에서 필요한 구간을 자르고, 음성을 자막으로 바꾸고, 30초 콘텐츠 초안을 만드는 Python CLI입니다. **자막 합성·영상 생성·자동 SNS 발행은 아직 없습니다.**

## 기본 실행 — Python 3.11+

```bash
python studio.py doctor
python studio.py draft demo.srt output/draft.md
```

기본 draft는 **AI 생성이 아닌 편집 템플릿**입니다. 외부 결제·가입·API 없이 실행됩니다. Windows에서 `python` 대신 `py` 사용 가능.

## 영상 구간 자르기

[FFmpeg 공식 안내](https://ffmpeg.org/download.html)에서 FFmpeg/ffprobe를 설치하고 PATH에 넣으세요.

```bash
python studio.py trim input.mp4 output/clip.mp4 --start 3 --end 30
python studio.py trim input.mp4 output/exact.mp4 --start 3 --end 30 --accurate
```

기본은 stream-copy: 화질을 재압축하지 않지만 키프레임 때문에 시작점 오차가 생길 수 있습니다. `--accurate`는 H.264/AAC 재인코딩이며 화질 무손실이 아닙니다. 시간을 검사하고 기존 출력은 덮어쓰지 않습니다.

## 실제 음성 자막 — 선택 설치

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install openai-whisper
python studio.py transcribe input.mp4 --model base --language ko --output-dir output/subtitles
```

첫 모델 다운로드에는 인터넷과 저장 공간이 필요합니다. SRT/TXT를 출력합니다. 음성이 없는 샘플 파일로 인식 품질을 검증했다고 주장하지 않습니다. 모델의 인식 오류를 검토하세요.

## Ollama로 AI 초안 — 선택 기능

[Ollama](https://ollama.com/)에 본인 PC에서 실행 가능한 로컬 모델을 미리 설치한 후:

```bash
python studio.py draft output/subtitles/input.srt output/ai-draft.md --model YOUR_LOCAL_MODEL
```

`YOUR_LOCAL_MODEL`을 실제 설치된 모델명으로 바꾸세요. 요청은 `http://127.0.0.1:11434/api/generate`로 전송됩니다. Ollama에서 클라우드 모델을 선택하면 외부 전송·과금 조건이 달라집니다. 이 앱은 API 키를 수집하거나 원격 서버 주소를 받지 않습니다.

## 검증과 개발

```bash
python -m unittest -v
```

실제 FFmpeg 합성 영상 자르기 검증은 `VERIFICATION.md` 참고. Whisper 실음성 인식과 실제 Ollama 추론은 사용자 PC에서 별도 확인해야 합니다. 프로세스는 shell 없이 인자 배열로 실행합니다.

참조: [Whisper](https://github.com/openai/whisper), [Ollama generate API](https://docs.ollama.com/api/generate). 타사 소스 복제 없이 작성한 연결 코드입니다.
