---
name: write-scenes
description: Write only the narration script and scene JSON for a shortz video so the user can review the text before rendering. Trigger phrases are "대본 써줘 주제는 X" or "씬 만들어줘 주제는 X". Use when the user wants to check or edit the script first rather than render immediately. Does not give relay render commands.
---

# 대본과 씬 JSON만 작성하기

렌더링 없이 대본만 먼저 만들어 검토받는 절차입니다. 검토가 끝나면 `make-shorts` 절차 4번(relay 실행)부터 이어갑니다.

## 절차

1. 주제 길이 톤을 확인합니다. 길이가 없으면 1분 기준으로 씁니다.

2. `scripts/<이름>_scenes.json`에 아래 형식으로 작성합니다.

   ```json
   [
     {"text": "장면 대본 문장들. ", "query": "english stock search keywords"}
   ]
   ```

   규칙:
   - 한국어 문장은 쉼표 없이 짧게 끊습니다
   - 한 장면은 2~4문장으로 하나의 시각적 장면에 대응하게 묶습니다
   - `text` 끝에 공백 한 칸을 두고 마지막 장면만 공백 없이 끝냅니다
   - `query`는 영어로 배경 행동 분위기까지 구체적으로 씁니다 (예: "old man reading newspaper cafe morning")
   - 분량은 한국어 기준 초당 약 6.5자 (차분/기본) 또는 7.9자 (발랄)로 계산합니다

3. 작성 후 아래를 실행해 검증하고 결과를 사용자에게 보고합니다.

   ```
   python3 -c "
   import json
   scenes = json.load(open('scripts/<이름>_scenes.json', encoding='utf-8'))
   total = ''.join(s['text'] for s in scenes)
   print('쉼표 포함:', ',' in total)
   print('글자수:', len(total), '예상 길이(초):', round(len(total)/6.5), '~', round(len(total)/7.9))
   "
   ```

4. 대본 전문을 장면 번호와 함께 사용자에게 보여주고 수정할 부분을 물어봅니다. 수정 요청이 오면 파일을 고치고 3번을 다시 실행합니다.

5. 사용자가 확정하면 커밋하고 푸시한 뒤 `make-shorts`의 relay 실행 명령을 안내합니다.
