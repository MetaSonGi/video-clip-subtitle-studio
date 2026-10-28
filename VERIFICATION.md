# 검증 결과

2026-10-26 / Python 3.12, Linux 환경

- 단위 테스트 2개 통과
- 실제 FFmpeg 합성 MP4 생성 후 copy/reencode 추출 성공
- 0.5~2.5초 구간: copy 출력 2.2초, reencode 출력 2.0초
- SRT에서 템플릿 Markdown 출력 성공
- 실제 Whisper 음성 인식 및 Ollama 추론은 미검증

## 2026-10-28 작업본 검증 (GitHub 미푸시, 로컬 작업본 기준)

- 단위 테스트 12개 통과 (기존 2개 유지 + 모의 Whisper·Ollama 등 10개 추가), `python -m unittest -v`, Python 3.12.3
- 실제 FFmpeg 합성 MP4 자르기 스모크 확인: 0.5~2.5초 구간, stream-copy 2.23초, 재인코딩 2.00초
- SRT → 템플릿 Markdown 출력 성공, CLI `doctor`/`draft` 진입점 동작 확인
- 실제 Whisper 음성 인식 및 실제 Ollama 추론은 여전히 미검증 (모의 테스트로 대체했으며, 실제 검증이 아님)
