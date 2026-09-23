---
name: make-shorts
description: Create a Korean vertical shorts video end to end using the shortz pipeline in this repo. Trigger phrase the user says is "쇼츠 영상 제작 주제는 X" (also matches "쇼츠 영상 만들어줘 주제는 X" and similar). Use whenever the user asks to make a shorts video, an AI-narrated video, or a video about a specific topic or story. Writes the narration script and scene JSON, commits and pushes them, then gives the exact relay commands to render and download the result.
---

# shortz 영상 제작 스킬

이 저장소(shortz)의 파이프라인으로 세로형 쇼츠 영상을 처음부터 끝까지 만드는 절차입니다.

## 실행 환경

모든 렌더링은 사용자의 relay 서버에서만 합니다. 이 세션에서는 스크립트 작성과 git 커밋/푸시만 하고 실제 실행 명령은 사용자에게 안내합니다. relay 외 다른 곳(로컬 Termux 등)에는 아무것도 설치하거나 실행하지 않습니다.

## 절차

1. **주제 파악**: 사용자가 준 주제 분량 톤을 확인합니다. 불명확하면 짧게 물어봅니다 (주제, 대략적인 길이, 분위기).

2. **대본 작성**: 자연스러운 한국어 문장으로 씁니다. 쉼표는 쓰지 않고 문장을 짧게 끊습니다. 영상 소스를 문장별로 다르게 붙이려면 `scripts/<이름>_scenes.json`에 아래 형식으로 씁니다.

   ```json
   [
     {"text": "장면 1 대본 문장들. ", "query": "english stock search keywords"},
     {"text": "장면 2 대본 문장들. ", "query": "english stock search keywords"}
   ]
   ```

   `text`를 순서대로 이어 붙인 문자열이 전체 나레이션이 되므로 띄어쓰기와 순서를 정확히 맞춥니다. `query`는 Pexels/Pixabay 검색에 쓰이므로 영어로 구체적으로 씁니다 (예: "couple walking rain street"). 분량 감은 한국어 기준 초당 약 6.5~8자입니다.

3. **커밋/푸시**: 작성한 스크립트나 씬 JSON 파일을 커밋하고 현재 브랜치에 푸시합니다.

4. **relay 실행 명령 안내**: 아래 형태로 tmux 안에서 실행하도록 안내합니다. tmux는 SSH가 끊겨도 렌더링이 계속되게 하므로 항상 포함합니다.

   ```
   tmux new -s shortz   # 세션 없으면 새로 생성, 있으면 attach
   cd shortz
   source .venv/bin/activate
   git pull origin <현재 브랜치>
   python -m src.shortz.main --scenes scripts/<이름>_scenes.json \
     --scene-photos 2 \
     --voice-preset <발랄|귀여운|차분|기본> \
     --font-preset <라운드|고딕|바른고딕|명조|손글씨> \
     --auto-music \
     --out <이름>.mp4
   ```

   씬 JSON 없이 단일 스크립트 파일이면 `--scenes` 대신 `scripts/<이름>.txt`를 위치 인자로 씁니다.

   옵션 선택 기준:
   - `--renderer`: 기본값 fast (ffmpeg+ASS 자막 4분 영상 5분 내외). 문제 시 `--renderer classic`으로 moviepy 방식 사용 (같은 영상 40분 내외)
   - `--voice-preset`: 로맨스/잔잔한 내용은 차분, 정보성/활기찬 내용은 발랄, 귀여운 소재는 귀여운
   - `--font-preset`: 정보성은 고딕/바른고딕, 감성적인 내용은 손글씨/명조
   - `.env`에 `PEXELS_API_KEY`/`PIXABAY_API_KEY`가 있으면 자동으로 더 좋은 영상을 받아오므로 별도 옵션 불필요
   - `.env`에 `GOOGLE_TTS_API_KEY`가 있으면 `--tts-engine google` 추가를 제안

5. **완료 후 무결성 확인**: 렌더링이 끝나면 바로 다운로드시키지 말고 먼저 확인합니다.

   ```
   ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 output/<이름>.mp4
   ```

   `moov atom not found` 등 에러가 나면 파일이 중간에 끊긴 것이므로 tmux 세션을 다시 만들어 재실행을 안내합니다.

6. **다운로드 안내**: relay 밖(사용자 로컬 기기)에서 실행하도록 안내합니다.

   Termux:
   ```
   scp ubuntu@relay:~/shortz/output/<이름>.mp4 ~/storage/downloads/<이름>.mp4
   ```

   Windows PowerShell:
   ```
   scp ubuntu@relay:~/shortz/output/<이름>.mp4 $env:USERPROFILE\Downloads\<이름>.mp4
   ```

## 자주 겪는 문제와 대응

- **`cd`가 안 먹었거나 `~/shortz/shortz` 같은 중첩 폴더에 있음**: `pwd`로 확인 후 `cd ~/shortz`로 이동.
- **`(.venv)` 표시가 없음**: `source .venv/bin/activate` 안 한 것이므로 다시 활성화.
- **SSH가 렌더링 중간에 끊김**: tmux 세션이면 렌더링은 계속되므로 재접속 후 `tmux attach -t shortz`.
- **`ModuleNotFoundError`**: Termux 로컬에서 실행 중이거나 venv 미활성화. relay의 `~/shortz`로 안내.
- **자막이 안 보임**: 폰트별 stroke_width 균형 문제일 수 있음. `src/shortz/video.py`의 TextClip stroke_width 확인.
- **주제 관련 영상/사진이 안 보임**: 실제로는 들어가 있는데 비중이 작아 눈에 안 띌 수 있음. `output/scene_media/scene_*/`에 파일이 받아졌는지 먼저 확인.
