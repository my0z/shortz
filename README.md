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

`--topic 주제` 옵션을 쓰면 주제와 관련된 무료 영상 클립을 자동 검색해 배경으로 이어붙입니다. 영상을 못 찾으면 Openverse 이미지 슬라이드쇼로 자동 대체됩니다. 이미지만 원하면 `--topic-media image`를 쓰고 개수는 `--topic-count`로 조절합니다.

### 고품질 스톡 영상 연동 (선택)

Pexels와 Pixabay에서 무료 API 키를 발급받으면 위키미디어 커먼즈보다 훨씬 관련성 높고 화질 좋은 영상을 받아옵니다. 키가 있으면 Pexels를 우선 사용하고 부족하면 Pixabay 위키미디어 순으로 자동 대체됩니다. 키가 없어도 위키미디어만으로 동작합니다.

1. Pexels: https://www.pexels.com/api/ 가입 후 API 키 발급
2. Pixabay: https://pixabay.com/api/docs/ 가입 후 API 키 발급
3. `.env`에 `PEXELS_API_KEY`, `PIXABAY_API_KEY` 값 입력

### 문장별 맞춤 영상 (선택)

`--topic` 대신 `--scenes JSON경로`를 쓰면 대본을 문장 구간으로 나눠 구간마다 다른 검색어로 영상을 찾아 붙입니다. JSON은 `[{"text": "구간 대본", "query": "영어 검색어"}, ...]` 형식이며 text를 순서대로 이어 붙인 값이 전체 나레이션이 됩니다. `scripts/animal_kingdom_scenes.json`을 예시로 참고하세요.

`--scene-photos 개수`를 함께 쓰면 각 장면 영상 뒤에 같은 검색어로 찾은 사진을 슬라이드로 이어 붙여 영상과 사진이 번갈아 나오는 구성이 됩니다.

### AI 그림으로 애니 쇼츠 만들기 (무료)

`--image-gen pollinations`를 쓰면 스톡 대신 장면마다 Pollinations(키 없이 무료)로 그림을 생성합니다. 씬 JSON은 아래 확장 형식을 지원합니다.

```json
{
  "style": "anime style illustration. soft cel shading. no text",
  "narrator": {"voice": "ko-KR-SunHiNeural", "voice_preset": "차분"},
  "characters": {
    "하린": {"look": "영어 외모 설명", "seed": 11, "voice": "ko-KR-SunHiNeural", "voice_preset": "귀여운"},
    "서준": {"look": "영어 외모 설명", "seed": 23, "voice": "ko-KR-InJoonNeural", "voice_preset": "차분"}
  },
  "scenes": [
    {"text": "나레이션 문장. ", "prompt": "{하린} standing under the moon"},
    {"text": "대사 문장. ", "speaker": "서준", "prompt": "close-up of {서준}"},
    {"text": "긴 장면. ", "prompts": ["wide shot", "{하린} and {서준} fighting"]}
  ]
}
```

- prompt 안의 `{이름}`은 그 캐릭터의 `look` 설명으로 치환되고 seed도 캐릭터 기준으로 고정되어 장면이 달라도 같은 인물로 그려집니다.
- `speaker`가 있는 장면은 그 캐릭터의 목소리로 읽습니다. 장면마다 따로 합성한 뒤 이어 붙이므로 자막과 그림이 실제 음성 길이에 정확히 맞춰집니다.
- `prompts` 목록을 주면 컷마다 다른 구도의 그림이 한 장씩 만들어집니다. `--scene-photos N`으로 컷당 장수를 바꿀 수 있습니다.
- 그림은 줌인 줌아웃 좌우 팬을 번갈아 적용해 움직임을 주고 컷 사이에 짧은 암전을 넣습니다.
- 이미 생성된 그림은 `output/scene_media`에 남아 재실행 시 다시 만들지 않습니다. 특정 장면만 다시 뽑으려면 그 폴더를 지우고 실행하세요.

#### Cloudflare Workers AI로 고화질 생성 (키 필요. 하루 1만 뉴런 무료)

`--image-gen cloudflare`를 쓰면 Pollinations 대신 Cloudflare Workers AI로 그림을 만듭니다. 로고가 없고 1080x1920을 바로 뽑으며 기본 모델 FLUX.2 klein 4B는 참조 이미지를 받아 캐릭터 얼굴을 장면마다 유지합니다. 캐릭터 시트를 먼저 만들어 두면 장면 생성 시 그 시트가 자동으로 참조 이미지로 들어갑니다.

`.env`에 아래 두 값을 넣습니다.

```
CLOUDFLARE_ACCOUNT_ID=대시보드 우측 Account ID
CLOUDFLARE_API_TOKEN=Workers AI 읽기/편집 권한으로 만든 API 토큰
```

무료 한도는 하루 1만 뉴런이고 1080x1920 한 장이 약 250뉴런이라 하루 30~40장이 무료입니다. 한 편에 그림 30장 안팎이면 하루 한 편이 무료 범위입니다. 한도는 UTC 자정에 초기화됩니다. `CLOUDFLARE_IMAGE_MODEL`로 모델을 바꿀 수 있습니다 (`@cf/bytedance/stable-diffusion-xl-lightning`은 더 싸지만 참조 이미지를 못 씁니다).

cloudflare 백엔드는 그림을 만든 뒤 Llama 3.2 비전 모델에 보여 팔다리와 머리 개수를 검수합니다. 오류가 나오면 seed를 바꿔 최대 두 번 다시 그립니다. 검수 한 번은 약 10뉴런이라 부담이 없습니다. `--no-image-check`로 끌 수 있습니다.

본 렌더 전에 캐릭터 외모를 먼저 확인하려면 캐릭터 시트만 뽑을 수 있습니다.

```bash
python -m src.shortz.main --scenes scripts/dalgrimja_ep1_scenes.json --image-gen cloudflare --character-sheet
```

`output/characters/character_sheet.jpg`에 캐릭터별 전신 그림이 나란히 저장됩니다. 마음에 안 드는 캐릭터는 JSON의 `seed`나 `look`을 바꿔 다시 뽑으면 됩니다.

### Google Cloud TTS 연동 (선택)

`--tts-engine google`을 쓰면 edge-tts 대신 Google Cloud Text-to-Speech로 나레이션을 생성합니다. Neural2 고품질 음성을 사용하며 `.env`에 `GOOGLE_TTS_API_KEY` 값이 필요합니다. 키가 없으면 기본값인 `edge`를 그대로 쓰면 됩니다.

### 자막 폰트

`--font-preset 라운드|고딕|바른고딕|명조|손글씨` 로 자막 폰트를 고를 수 있습니다. 기본값은 부드러운 느낌의 라운드체입니다.

### 렌더링 속도

기본 렌더러(`--renderer fast`)는 moviepy 프레임 루프 없이 ffmpeg만으로 영상을 만듭니다. 배경 구간은 ffmpeg `scale`/`crop`/`zoompan`/`gradients`로 각각 인코딩한 뒤 concat으로 이어붙이고 색보정(`eq` `colorchannelmixer`) 비네트(`vignette`) 페이드(`fade` `afade`) 음량 정규화(`loudnorm`)와 자막을 마지막 한 번의 ffmpeg 패스에서 처리합니다. 자막은 ASS 파일로 만들어 libass로 굽기 때문에 한글 폰트가 시스템에 설치돼 있어야 하고 ffmpeg가 `--enable-libass`로 빌드돼 있어야 합니다. 4분 영상 기준 기존 방식보다 대략 8~10배 빠릅니다.

fast 렌더러가 실패하면 자동으로 기존 moviepy 방식(`--renderer classic`)으로 다시 렌더링합니다. classic은 자막 박스 모서리가 둥글고 fast는 각진 박스라는 시각적 차이가 있습니다. `output/_work_*` `output/_prepared_*`는 중간 산출물이라 지워도 됩니다.

## 구조

- `src/shortz/tts.py` 나레이션 음성 합성
- `src/shortz/audio.py` 나레이션과 배경음악 믹싱
- `src/shortz/subtitles.py` 자막 분할
- `src/shortz/video.py` 영상 합성 및 배경 처리
- `src/shortz/ffmpeg_utils.py` ffmpeg 직접 호출로 영상 리사이즈/자르기
- `src/shortz/background.py` 자동 배경 이미지 다운로드
- `src/shortz/main.py` 실행 진입점
- `scripts/` 나레이션 스크립트 모음
- `assets/` 폰트와 배경 음악
- `output/` 생성된 영상 출력 위치
