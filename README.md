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

`--topic 주제` 옵션을 쓰면 위키미디어 커먼즈에서 주제와 관련된 무료 영상 클립을 자동 검색해 배경으로 이어붙입니다. 영상을 못 찾으면 Openverse 이미지 슬라이드쇼로 자동 대체됩니다. 이미지만 원하면 `--topic-media image`를 쓰고 개수는 `--topic-count`로 조절합니다.

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

## 익일 급등 후보 추천 (surge/)

평일 15:10 에 카카오톡으로 익일 +5% 이상 오를 확률이 높은 종목을 보낸다. 이 저장소만으로 동작하고 데이터도 여기에 따로 저장한다.

1. 15:00 세션 루틴이 `surge/run_request.txt` 를 갱신해 푸시한다
2. GitHub Actions (`.github/workflows/surge.yml`) 가 `python -m surge.live` 를 실행한다
   - 네이버 증권에서 코스피+코스닥 보통주 일봉 약 3년치 수집 (장중이면 오늘 봉은 현재가 기준)
   - aut.stock 의 3년치 KRX 기관/외국인 수급 패널을 `surge_data/history/krx_panel.parquet` 로 복사해 두고 실행 때마다 새 날짜만 증분 파일로 저장한다 (aut.stock 에는 쓰지 않는다). 15시에는 당일 수급을 모르므로 전일까지 수급만 쓴다
   - 차트 피처 (모멘텀 / 봉 모양 / 거래량 / 이평 정배열 / 신고가 / 변동성 수축) 로 HistGradientBoosting 학습
   - 점검: 상한가 도달 / 거래대금 10억 미만 / 스팩 / 우선주 제외. 최근 60일 홀드아웃 적중률 계산
   - `surge_data/picks/YYYYMMDD.json` 과 오늘 봉 스냅샷 `surge_data/daily/YYYYMMDD.csv` 를 커밋
3. 세션이 결과를 다시 점검한 뒤 말머리 `[종목 추천]` 으로 카카오톡을 보낸다. 휴장일은 보내지 않는다
