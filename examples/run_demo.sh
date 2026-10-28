#!/bin/sh
# 데모 실행 예시: 설치 없이 doctor 확인 + demo.srt로 오프라인 초안 생성.
# Windows에서는 start.bat(doctor 확인) 또는 아래와 같은 명령을 사용하세요:
#   py studio.py doctor
#   py studio.py draft demo.srt output/draft.md
set -e
cd "$(dirname "$0")/.."
python3 studio.py doctor
python3 studio.py draft demo.srt output/draft.md
echo "완료: output/draft.md 를 사람이 검토한 뒤에 사용하세요."
