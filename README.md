# shortz

세로형 쇼츠 영상 자동 생성 도구입니다.

## 사전 요구사항

시스템에 ffmpeg가 설치되어 있어야 합니다.

```
apt-get install ffmpeg
```

## 설치

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env.example`을 `.env`로 복사한 뒤 값을 조정하세요.

## 사용법

```
python -m src.shortz.main scripts/sample_script.txt --out shorts.mp4
```

배경 이미지를 지정하려면 `--background 경로` 옵션을 추가하세요.

## 구조

- `src/shortz/tts.py` 나레이션 음성 합성
- `src/shortz/subtitles.py` 자막 분할
- `src/shortz/video.py` 영상 합성
- `src/shortz/main.py` 실행 진입점
- `scripts/` 나레이션 스크립트 모음
- `assets/` 폰트와 배경 음악
- `output/` 생성된 영상 출력 위치
