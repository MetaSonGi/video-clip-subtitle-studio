# 효기 로컬 콘텐츠 스튜디오

> **관련 저장소 구분** — 이 저장소는 **정식판**입니다: 환경 점검(doctor), 로컬 웹 UI, AI 없이 쓰는 오프라인 초안 템플릿, 안전 규칙(덮어쓰기 금지·shell 미사용)을 포함합니다.
> 자르기→자막→Ollama 초안을 명령 하나로 끝내는 **원스텝 CLI판**은 [hyoki-content-studio](https://github.com/MetaSonGi/hyoki-content-studio)입니다.


개발 시연 녹화에서 필요한 구간을 자르고, 음성을 자막으로 바꾸고,
30초 콘텐츠 초안을 만드는 Python CLI입니다.
기본 동작은 외부 결제·가입·API 키 없이 로컬에서 실행됩니다.

## 하는 일 / 하지 않는 일

| 하는 일 | 하지 않는 일 |
|---|---|
| FFmpeg으로 영상 구간 자르기 (stream-copy / 재인코딩) | 자막 합성(영상에 자막 굽기) |
| Whisper로 음성 → SRT/TXT 자막 생성 (선택 설치) | 영상 생성 |
| 자막 → 30초 초안 Markdown 생성 (오프라인 템플릿 또는 로컬 Ollama) | 자동 SNS 발행 |

**기본 draft는 AI 생성이 아닙니다.** 오프라인 편집 템플릿이며,
출력 첫 줄에도 `AI 생성 아님`과 `게시 전 사람이 검토`가 명시됩니다.
Ollama를 지정했을 때만 로컬 모델 생성 초안이 되며, 그 경우에도
게시 전 사람이 검토해야 합니다.

## 요구 사항

| 구분 | 필요 항목 | 비고 |
|---|---|---|
| 필수 | Python 3.11+ | 이 작업본은 Python 3.12에서 확인 |
| 필수 (자르기만) | FFmpeg / ffprobe | [FFmpeg 공식 안내](https://ffmpeg.org/download.html), PATH 등록 |
| 선택 (자막) | openai-whisper | `python -m pip install openai-whisper`, 첫 모델 다운로드에 인터넷·저장 공간 필요 |
| 선택 (AI 초안) | Ollama + 로컬 모델 | 본인 PC에서 실행 가능한 모델을 미리 설치, 요청은 `http://127.0.0.1:11434/api/generate` 고정 |

이 앱은 API 키를 수집하지 않고, 원격 서버 주소를 인자로 받지 않으며,
외부 프로세스는 shell 없이 인자 배열로 실행합니다.
Ollama에서 클라우드 모델을 선택하면 외부 전송·과금 조건이 달라지므로,
로컬 모델 사용을 전제로 합니다.

## 빠른 시작

```bash
# 1) 환경 확인 (ffmpeg/ffprobe/whisper 유무를 JSON으로 출력)
python studio.py doctor
# Windows: py studio.py doctor  (또는 start.bat 더블클릭)

# 2) 데모 자막으로 오프라인 초안 만들기 (AI 생성 아님)
python studio.py draft demo.srt output/draft.md

# 3) 한 번에 실행하는 예시 (macOS/Linux)
sh examples/run_demo.sh
```

## 로컬 웹 UI (127.0.0.1 전용, Python 표준 라이브러리만)

```bash
python3 web.py --port 8768
# 브라우저에서 http://127.0.0.1:8768 접속
```

- 기능: doctor 상태 표시, SRT 텍스트로 오프라인 draft 미리보기/파일 생성,
  로컬 파일 경로 기준 trim 실행.
- 경로는 브라우저 PC가 아니라 서버가 실행 중인 PC의 파일 경로다.
- 기존 출력 덮어쓰기 금지, shell 없이 인자 배열로 실행한다는 CLI 규칙을
  웹에서도 그대로 유지한다.
- Whisper·Ollama 실제 동작은 웹 UI에서도 새로 검증하지 않는다.
  draft 기본값은 오프라인 템플릿이다.
- **이 웹 UI는 GitHub Pages용이 아니다.** Pages는 정적 사이트라 Python
  서버가 돌아가지 않는다. 로컬에서만 쓰는 UI다.
- 웹 UI도 GitHub 저장소에 포함되어 있다.

가상환경을 쓰려면:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
```

## 명령어

### `doctor` — 환경 점검

```bash
python studio.py doctor
```

`python` 버전, `ffmpeg`/`ffprobe` 존재 여부, `whisper` 패키지 존재 여부를
출력합니다. Ollama는 별도 서버라서, `http://127.0.0.1:11434`에서
모델을 따로 실행해야 한다는 안내만 출력합니다.

### `trim` — 영상 구간 자르기

```bash
python studio.py trim input.mp4 output/clip.mp4 --start 3 --end 30
python studio.py trim input.mp4 output/exact.mp4 --start 3 --end 30 --accurate
```

- 기본은 stream-copy: 재압축하지 않지만 키프레임 때문에 시작점 오차가 생길 수 있습니다.
- `--accurate`는 H.264/AAC 재인코딩이며 화질 무손실이 아닙니다.
- 시간은 `0 <= 시작 < 끝`이어야 하고, 끝 시간은 원본 길이를 초과할 수 없습니다.
- 기존 출력 파일은 덮어쓰지 않습니다. 이미 있으면 오류로 종료합니다.

### `transcribe` — 실제 음성 자막 (선택 설치)

```bash
python -m pip install openai-whisper
python studio.py transcribe input.mp4 --model base --language ko --output-dir output/subtitles
```

SRT/TXT를 출력합니다. 이미 같은 이름의 자막이 있는 출력 디렉터리는
사용하지 않습니다. Whisper 모델의 인식 오류는 직접 검토하세요.
음성이 없는 샘플 파일로 인식 품질을 검증했다고 주장하지 않습니다.

### `draft` — 30초 초안 만들기

```bash
# 오프라인 템플릿 (AI 생성 아님)
python studio.py draft demo.srt output/draft.md

# 로컬 Ollama 모델로 생성 (YOUR_LOCAL_MODEL을 실제 설치된 모델명으로 교체)
python studio.py draft output/subtitles/input.srt output/ai-draft.md --model YOUR_LOCAL_MODEL
```

자막 텍스트가 비어 있으면 오류로 종료합니다. 기존 출력 파일은
덮어쓰지 않습니다.

## 동작 규칙과 종료 코드

- 성공 시 종료 코드 `0`, JSON 결과를 표준 출력으로 출력합니다.
- 실패 시 종료 코드 `1`, `오류: ...`를 표준 오류로 출력합니다.
- `source()`/`output()` 규칙: 입력 파일이 없으면 실패하고,
  이미 있는 출력 파일은 절대 덮어쓰지 않습니다.
- 자막 텍스트 추출은 SRT 번호 줄·타임코드 줄·`WEBVTT` 헤더를 제외하고,
  UTF-8이 아닌 자막 파일은 오류로 보고합니다.
- Ollama 요청 실패·빈 응답은 `ValueError`로 바꿔 한 줄 오류로 보고하며,
  실패 시 부분 초안 파일을 남기지 않습니다.

## 테스트

```bash
python -m unittest -v
```

- 외부 모델 없이 통과합니다. Whisper·Ollama는 모의(mock) 객체로 대체해
  테스트합니다. 실제 Whisper 음성 인식과 실제 Ollama 추론은
  이 테스트로 검증되지 않으며, 아래 검증 현황을 참고하세요.
- 테스트는 `test_studio.py`에 있습니다. 기존 테스트 2개를 유지하고,
  자막 필터링·Ollama 모의 요청·Whisper 모의 전사·trim 명령 구성·
  CLI 진입점(`doctor`/`draft`) 테스트를 추가했습니다.
- 웹 UI 테스트는 `test_web.py`에 있습니다. 임시 포트(127.0.0.1)로 실제
  서버를 띄워 doctor·draft 미리보기/생성·덮어쓰기 거부·FFmpeg trim을
  확인하고, 테스트 후 서버를 종료합니다.

## 검증 현황 (솔직한 범위)

| 항목 | 상태 |
|---|---|
| 단위 테스트 12개 | 통과 (2026-10-28 작업본, Python 3.12, `python -m unittest -v`) |
| 웹 UI 포함 전체 테스트 16개 | 통과 (2026-10-28 작업본, 기존 12개 + 웹 4개) |
| 실제 FFmpeg 합성 영상 자르기 | 통과 — 0.5~2.5초 구간: stream-copy 2.23초, 재인코딩 2.00초 (2026-10-28 작업본 스모크 확인) |
| SRT → 템플릿 Markdown | 통과 |
| 실제 Whisper 음성 인식 | **미검증** — 사용자 PC에서 실제 음성 파일로 별도 확인 필요 |
| 실제 Ollama 추론 | **미검증** — 로컬 Ollama 서버·모델 설치 후 별도 확인 필요 |

이전 검증 기록은 `VERIFICATION.md`에 그대로 보존되어 있습니다.

## 문제 해결

| 증상 | 확인 사항 |
|---|---|
| `ffmpeg 설치가 필요합니다` | FFmpeg/ffprobe 설치 후 PATH 등록, `doctor`로 재확인 |
| `openai-whisper 설치가 필요합니다` | 가상환경 활성화 여부, `pip install openai-whisper` |
| `Ollama 요청에 실패했습니다` | Ollama 서버 실행 여부, 모델명 정확 여부, `http://127.0.0.1:11434` 접속 여부 |
| `기존 파일을 덮어쓰지 않습니다` | 새 출력 경로·새 output-dir를 지정 (의도된 보호 동작) |
| `자막 파일이 UTF-8이 아닙니다` | 자막을 UTF-8로 다시 저장 |
| `끝 시간이 원본 영상 길이를 초과합니다` | `--end`를 원본 길이 안으로 조정 |

## 파일 구성

| 파일 | 설명 |
|---|---|
| `studio.py` | CLI 본체 (`doctor` / `trim` / `transcribe` / `draft`) |
| `web.py` | 로컬 웹 UI (127.0.0.1 전용, 표준 라이브러리만) |
| `test_studio.py` | 단위 테스트 (모의 Whisper·Ollama 포함) |
| `test_web.py` | 웹 UI 테스트 (임시 포트, 테스트 후 서버 종료) |
| `demo.srt` | 데모용 자막 (템플릿 초안 확인용) |
| `examples/run_demo.sh` | doctor + 데모 초안 실행 예시 |
| `start.bat` | Windows용 doctor 확인 실행기 |
| `VERIFICATION.md` | 검증 기록 |
| `LICENSE` | MIT |

참조: [Whisper](https://github.com/openai/whisper),
[Ollama generate API](https://docs.ollama.com/api/generate).
타사 소스 복제 없이 작성한 연결 코드입니다.

라이선스: MIT (`LICENSE` 참고).
