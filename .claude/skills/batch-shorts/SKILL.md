---
name: batch-shorts
description: Produce several shortz videos in one go. Trigger phrases are "쇼츠 여러 개 만들어줘" "배치로 만들어줘" or a list of topics. Writes one scene JSON per topic, then generates a single shell script the user runs once inside tmux on the relay to render everything sequentially and log results.
---

# 여러 편 한 번에 만들기

주제 목록을 받아 씬 JSON을 편수만큼 만들고 relay에서 한 번에 순차 렌더링하는 스크립트를 만듭니다.

## 절차

1. 주제 목록과 공통 옵션(길이 톤 폰트)을 확인합니다. 편별로 톤이 다르면 표로 정리해 확인받습니다.

2. 각 주제마다 `write-scenes` 규칙으로 `scripts/<이름>_scenes.json`을 작성합니다. 이름은 영문 소문자와 밑줄만 씁니다.

3. `scripts/batch_<날짜>.sh`를 아래 형식으로 만듭니다. 한 편이 실패해도 다음 편으로 넘어가고 결과를 로그에 남깁니다.

   ```bash
   #!/usr/bin/env bash
   cd ~/shortz || exit 1
   source .venv/bin/activate
   LOG=output/batch_<날짜>.log
   echo "batch start $(date)" >> "$LOG"

   run_one() {
     local name="$1"; shift
     echo "== $name start $(date)" >> "$LOG"
     if python -m src.shortz.main --scenes "scripts/${name}_scenes.json" "$@" --out "${name}.mp4"; then
       dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "output/${name}.mp4")
       echo "== $name ok ${dur}s $(date)" >> "$LOG"
     else
       echo "== $name FAILED $(date)" >> "$LOG"
     fi
   }

   run_one <이름1> --scene-photos 2 --voice-preset <톤> --font-preset <폰트> --auto-music
   run_one <이름2> --scene-photos 2 --voice-preset <톤> --font-preset <폰트> --auto-music

   echo "batch end $(date)" >> "$LOG"
   ```

4. 커밋하고 푸시합니다.

5. relay 실행 명령을 안내합니다.

   ```
   tmux new -s batch
   cd ~/shortz
   git pull origin <현재 브랜치>
   bash scripts/batch_<날짜>.sh
   ```

   진행 확인:

   ```
   tail -f output/batch_<날짜>.log
   ```

6. 끝나면 로그를 붙여달라고 해서 실패한 편이 있으면 `check-video` 절차로 원인을 찾습니다. 성공한 편은 다운로드 명령을 한 번에 정리해 줍니다.

   ```
   for n in <이름1> <이름2>; do scp ubuntu@relay:~/shortz/output/$n.mp4 ~/storage/downloads/$n.mp4; done
   ```

## 주의

- 편수가 많으면 relay CPU를 오래 점유하므로 밤 시간대 실행을 권합니다
- 같은 검색어를 여러 편이 공유하면 배경이 겹치므로 `query`를 편마다 다르게 씁니다
- 4분 이상 편이 섞여 있으면 fast 렌더러 기준 편당 5~8분을 예상해 총 소요 시간을 미리 알려줍니다
