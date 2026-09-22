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

배경 이미지나 동영상을 지정하려면 `--background 경로` 옵션을 추가하세요. 지정하지 않으면 움직이는 그라디언트 배경이 자동 생성됩니다.

배경음악을 넣으려면 `--music 경로` 옵션을 쓰세요. 파일 없이 은은한 앰비언트 사운드만 깔고 싶으면 `--auto-music`을 추가하세요.

목소리 톤은 `--voice-preset 발랄|귀여운|차분|기본` 중 선택합니다.

정지 이미지 배경은 자동으로 천천히 줌인되는 켄번즈 효과가 적용됩니다. 나레이션 음량은 자동 정규화되고 영상과 오디오 모두 시작과 끝에 페이드가 들어갑니다.

`--topic 주제` 옵션을 쓰면 Openverse에서 주제와 관련된 무료 이미지를 자동으로 찾아 슬라이드쇼 배경으로 사용합니다. 이미지 개수는 `--topic-count`로 조절합니다.

## 구조

- `src/shortz/tts.py` 나레이션 음성 합성
- `src/shortz/audio.py` 나레이션과 배경음악 믹싱
- `src/shortz/subtitles.py` 자막 분할
- `src/shortz/video.py` 영상 합성 및 배경 처리
- `src/shortz/background.py` 자동 배경 이미지 다운로드
- `src/shortz/main.py` 실행 진입점
- `scripts/` 나레이션 스크립트 모음
- `assets/` 폰트와 배경 음악
- `output/` 생성된 영상 출력 위치
