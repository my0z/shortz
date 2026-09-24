---
name: anime-shorts
description: Create a Korean anime style shorts episode with recurring AI generated characters using the shortz pipeline and free Pollinations image generation. Trigger phrases are "애니 쇼츠 만들어줘" "애니 만들어줘 주제는 X" "달그림자 2화 만들어줘" "캐릭터 시트 뽑아줘" or any request for an animated episode with characters and dialogue. Writes the character block and scene JSON with speakers and per-scene prompts and then gives the relay commands for the character sheet check and the full render.
---

# 애니 쇼츠 제작 스킬

AI 그림 생성과 캐릭터 고정 기능으로 애니 느낌의 에피소드를 만듭니다. 렌더링은 relay 서버에서만 합니다.

그림 백엔드는 두 가지입니다. 기본은 `cloudflare`(Workers AI. 하루 1만 뉴런 무료. 로고 없음. 캐릭터 시트를 참조 이미지로 넣어 얼굴 유지)이고 키가 없으면 `pollinations`(키 없이 무료. 화질 낮고 로고 자름)를 씁니다. relay `.env`에 `CLOUDFLARE_ACCOUNT_ID`와 `CLOUDFLARE_API_TOKEN`이 있으면 항상 cloudflare를 씁니다.

## 절차

1. **캐릭터 정의**: `characters` 블록에 캐릭터마다 `look`(영어 외모 설명) `seed`(정수) `voice` `voice_preset`을 씁니다. 기존 시리즈면 이전 화의 characters 블록을 그대로 복사합니다. 외모 설명은 머리 눈 옷 소품 순으로 구체적으로 쓰고 쉼표 대신 마침표로 끊습니다.
   - 여성 목소리 `ko-KR-SunHiNeural` 남성 목소리 `ko-KR-InJoonNeural`
   - 프리셋 `발랄` `귀여운` `차분` `기본`

2. **씬 작성**: `scripts/<시리즈>_ep<N>_scenes.json`에 아래 규칙으로 씁니다.
   - 나레이션 장면은 `speaker` 없이 `prompt`만 씁니다.
   - 대사 장면은 `speaker`에 캐릭터 이름을 넣고 text는 대사만 씁니다. 짧게 한두 문장이 좋습니다.
   - prompt에는 `{캐릭터이름}`으로 인물을 넣습니다. 클로즈업 와이드 액션을 섞어 구도를 바꿉니다.
   - 긴 장면은 `prompts` 목록으로 컷을 나눕니다.
   - 모든 text와 prompt에 쉼표를 쓰지 않습니다. text는 마침표 뒤 공백으로 끝냅니다.
   - 분량은 한국어 기준 초당 약 6자입니다. 2분이면 약 700자입니다.

3. **커밋/푸시** 후 relay 명령을 안내합니다. 캐릭터 시트 확인을 먼저 권합니다.

   ```
   tmux new -s shortz
   cd ~/shortz && source .venv/bin/activate
   git pull origin <브랜치>
   find . -name __pycache__ -exec rm -rf {} +
   python -m src.shortz.main --scenes scripts/<파일>.json --image-gen cloudflare --character-sheet
   ```

   시트가 마음에 안 들면 `rm -rf output/characters/<이름>` 후 seed를 바꿔 다시 뽑습니다. 이 시트가 본 렌더의 참조 이미지가 되므로 여기서 확정하는 게 중요합니다.

   시트 다운로드는 relay에서 나온 뒤 로컬에서 합니다.

   ```
   scp ubuntu@relay:~/shortz/output/characters/character_sheet.jpg <로컬 다운로드 폴더>/character_sheet.jpg
   ```

4. **본 렌더**: 캐릭터가 확정되면 tmux 안에서 실행합니다.

   ```
   time python -m src.shortz.main --scenes scripts/<파일>.json --image-gen auto --auto-music --font-preset 고딕 --out <이름>.mp4
   ```

   cloudflare는 장당 몇 초라 그림 30장에 5분 안팎이고 pollinations는 20분 전후입니다. 실패한 그림은 그라디언트로 대체되며 같은 명령을 다시 실행하면 빠진 그림만 다시 요청합니다. `auto`는 cloudflare 한도(HTTP 429)에 걸리면 남은 그림을 pollinations로 자동 전환해 끝까지 만듭니다. 전환된 장면은 참조 이미지가 없어 캐릭터가 조금 다를 수 있으니 다음 날(한국 오전 9시 이후) 그 장면 폴더를 지우고 재실행하면 cloudflare로 다시 채워집니다.

5. **확인과 다운로드**: `ffprobe`로 duration을 확인한 뒤 scp로 받습니다. 캐릭터가 장면마다 달라 보이면 `look`을 더 구체적으로 쓰거나 seed를 바꿔 시트부터 다시 뽑습니다.

## 팔다리 오류

cloudflare 백엔드는 비전 모델 검수로 팔다리 오류를 자동으로 걸러 다시 그립니다. 그래도 남으면 prompt를 단순하게 바꿉니다. 한 컷에 인물은 둘까지만 넣고 "both full bodies visible"처럼 몸 전체가 보이게 쓰며 손을 겹치는 동작은 피합니다.

## 재생성 요령

- 특정 장면만 다시 그리기: `rm -rf output/scene_media/scene_<번호-1>` 후 같은 명령 재실행
- 캐릭터 시트 다시 뽑기: `rm -rf output/characters/<이름>` 후 `--character-sheet` 재실행
- 화풍 바꾸기: JSON의 `style` 수정 후 `output/scene_media` 전체 삭제
