---
name: shorts-meta
description: Generate YouTube Shorts upload metadata (title candidates, description, hashtags, pinned comment) from a shortz scene JSON or script. Trigger phrases are "메타 만들어줘" "제목 뽑아줘" "해시태그 만들어줘" optionally with a script name. Use after a video is rendered or whenever the user needs upload text.
---

# 쇼츠 업로드 메타데이터 작성

완성된 영상에 붙일 제목 설명 해시태그를 대본 기반으로 만듭니다.

## 입력

`scripts/<이름>_scenes.json` 또는 `scripts/<이름>.txt`를 읽습니다. 이름이 없으면 가장 최근에 만든 파일을 씁니다 (`ls -t scripts/`).

## 출력 형식

아래 형식 그대로 사용자에게 보여주고 `scripts/<이름>_meta.md`로도 저장합니다.

```
## 제목 후보 (3개)
1. (호기심형 30자 이내)
2. (숫자/사실형 30자 이내)
3. (감성형 30자 이내)

## 설명
(첫 두 줄에 핵심 요약. 그 다음 줄에 대본 요약 3~4문장. 마지막 줄에 해시태그 3개)

## 해시태그 (15개)
#쇼츠 #Shorts 를 포함해 주제 관련 한국어 10개 영어 5개

## 고정 댓글
(시청자 질문 유도 한 문장)
```

## 규칙

- 제목은 대본의 첫 문장이나 가장 강한 문장에서 뽑습니다. 낚시성 과장은 피합니다
- 쉼표는 쓰지 않습니다
- 해시태그는 띄어쓰기 없이 붙여 씁니다
- 설명 첫 줄은 검색 결과에 노출되므로 주제 키워드를 앞에 둡니다
- 영상 길이가 60초를 넘으면 설명에 "쇼츠가 아닌 일반 영상으로 업로드" 라고 안내합니다

## 저장

```
scripts/<이름>_meta.md
```

커밋 메시지는 "<이름> 업로드 메타데이터 추가" 로 하고 푸시합니다.
