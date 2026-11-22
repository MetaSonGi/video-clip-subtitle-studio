# 콘텐츠 스튜디오 (hyoki-content-studio)

> **관련 저장소 구분** — 이 저장소는 **원스텝 CLI판**입니다: `pipeline` 명령 하나로 자르기→Whisper 자막→Ollama 초안(요약·설명·대본)을 끝냅니다.
> 웹 UI, 환경 점검, AI 없는 오프라인 초안이 필요하면 **정식판** [video-clip-subtitle-studio](https://github.com/MetaSonGi/video-clip-subtitle-studio)를 쓰세요.


시연 영상을 **자르고 → Whisper로 자막을 만들고 → Ollama로 요약·설명·대본 초안**을 쓰는 명령줄 도구예요. 모두 내 PC에서 실행돼요.

## 준비

```bash
# ffmpeg 설치 (Windows: winget install ffmpeg / macOS: brew install ffmpeg)
pip install openai-whisper pytest
# Ollama 설치 후
ollama pull llama3.2
```

## 사용법

```bash
# 1) 재인코딩 없이 자르기 (LosslessCut과 같은 방식)
python -m studio cut demo.mp4 0:10 1:25 -o clip.mp4

# 2) 자막 만들기
python -m studio subtitle clip.mp4 --model small

# 3) 초안 만들기: summary(3줄 요약) / description(유튜브 설명) / script(쇼츠 대본)
python -m studio draft clip.srt --kind description -o description.md

# 한 번에
python -m studio pipeline demo.mp4 0:10 1:25 --outdir output --kind script
```

## 참고

- stream copy 방식이라 시작점이 키프레임에 맞춰져 앞쪽이 약간 어긋날 수 있어요.
- Whisper `small` 모델은 CPU에서도 돌아가지만 느려요. GPU가 있으면 `medium` 이상을 추천해요.
- 초안 프롬프트는 자막에 없는 사실을 지어내지 않도록 지시하지만, 결과는 꼭 직접 확인하세요.

## 테스트

```bash
python -m pytest
```
