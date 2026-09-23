---
name: check-video
description: Diagnose a rendered shortz video on the relay server. Trigger phrases are "영상 점검해줘" "자막이 안 보여" "사진이 안 들어갔어" "영상이 만들다 만 것 같아" or any complaint about a rendered mp4. Walks through integrity check, frame extraction, media folder check, and the known causes for each symptom.
---

# 완성 영상 점검

사용자가 영상 문제를 말하면 추측하지 말고 아래 순서로 증거를 확보한 뒤 판단합니다. 모든 명령은 relay의 `~/shortz`에서 실행하도록 안내합니다.

## 1. 파일 무결성

```
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 output/<이름>.mp4
ls -la output/<이름>.mp4
```

- `moov atom not found` → 렌더링 중 프로세스가 죽은 것. tmux 안에서 재실행 안내
- 용량이 같은 길이의 다른 영상보다 크게 작음 → 위와 같음
- duration이 대본 예상 길이와 크게 다름 → TTS 단계 확인 (`output/narration.mp3` 길이 비교)

## 2. 프레임 추출

문제 구간의 프레임을 뽑아 사용자에게 이미지로 올려달라고 합니다. 자막 문제면 서로 다른 시점 두 장을 뽑습니다.

```
ffmpeg -y -i output/<이름>.mp4 -vf "select=eq(n\,90)" -update 1 -vframes 1 frame_a.png
ffmpeg -y -i output/<이름>.mp4 -vf "select=eq(n\,900)" -update 1 -vframes 1 frame_b.png
```

Termux에서 받기:

```
scp ubuntu@relay:~/shortz/frame_a.png ~/storage/downloads/frame_a.png
```

## 3. 미디어 폴더 확인 (사진/영상이 안 보인다는 경우)

```
ls -la output/scene_media/scene_0/
ls -la output/scene_media/scene_3/
```

- 폴더가 없음 → 다른 디렉터리에서 실행됐거나 `--scenes` 없이 실행된 것. `pwd` 확인
- `topic_0.jpg`가 없음 → Openverse 검색 실패. 검색어를 더 일반적인 영어로 바꿔 재시도
- `pexels_0.mp4`가 없고 `commons_0.*`만 있음 → Pexels 키 미설정이거나 검색 결과 없음. `.env` 확인

## 4. 증상별 원인

| 증상 | 확인할 것 | 대응 |
|---|---|---|
| 자막이 검게 보임 | 얇은 폰트(손글씨)에 두꺼운 테두리 | `--font-preset 고딕` 또는 `video.py` stroke_width |
| 자막이 전혀 없음 | 프레임에서 확인. fast 렌더러면 fontconfig에 폰트 없음 | `fc-list :lang=ko` 확인. `fonts-nanum` 설치 |
| 화면이 검정 | 프레임 확인 후 배경 세그먼트 실패 | `--renderer classic`으로 재실행해 비교 |
| 사진이 안 보임 | 3번 폴더 확인 | 비중은 장면의 50%. 실제로는 들어간 경우가 대부분 |
| 목소리 없음 | `output/narration_mixed.mp3` 크기 | TTS 키나 네트워크 확인 |
| 영상이 짧게 끝남 | 1번 무결성 | tmux 재실행 |

## 5. 보고

확인된 증거(무결성 결과 프레임 이미지 폴더 목록)를 바탕으로 원인과 조치를 한 번에 정리해 알립니다. 코드 수정이 필요하면 고친 뒤 커밋 푸시하고 재실행 명령을 안내합니다.
