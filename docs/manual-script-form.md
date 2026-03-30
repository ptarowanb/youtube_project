# Manual Script Form

이 문서는 수동 원고 입력의 표준 형식이다. 사람이 직접 써도 되고, ChatGPT 웹에 이 폼을 그대로 붙여 넣고 원고 생성을 요청해도 된다.

## 사용 규칙

- `channel`, `title`, `video_type`, `Description`, `Segments`는 필수다.
- 각 세그먼트는 최소 1개 이상이어야 한다.
- 각 세그먼트는 `narration`이 필수다.
- `visual_hint`는 영상 연출 힌트다. 이미지 소스가 없으면 자막/배경 카드 생성에 참고된다.
- `duration_hint`는 초 단위 정수다.
- `visibility` 기본값은 `private`다.
- `publish_at`은 선택 항목이며 `YYYY-MM-DD HH:MM` 형식을 권장한다.

## ChatGPT 프롬프트 예시

```text
아래 Markdown 폼 형식으로 유튜브 영상 원고를 작성해줘.
조건:
- 채널은 knowledge
- 설명과 세그먼트는 한국어로 작성
- 각 세그먼트는 narration, visual_hint, duration_hint를 포함
- duration_hint는 초 단위 정수
- 과장 없이 자연스럽게 작성

[여기에 아래 폼 템플릿 붙여넣기]
```

## 완성 예시

```md
# Video Script Form

## Meta
channel: knowledge
title: ChatGPT를 실무에 활용하는 5가지 방법
video_type: longform
visibility: private
publish_at: 2026-03-31 09:00
tags:
- chatgpt
- ai
- productivity

## Description
이 영상에서는 ChatGPT를 실무에 적용하는 기본 패턴을 간단하고 명확하게 설명합니다.

## Segments

### Segment 1
narration: ChatGPT는 검색 도구라기보다 초안 작성과 정리에 강한 업무 보조 도구입니다.
visual_hint: 사무실 책상, 노트북 화면, 생산성 있는 분위기
duration_hint: 8

### Segment 2
narration: 첫 번째 활용법은 회의록이나 메모를 빠르게 정리 가능한 초안으로 바꾸는 것입니다.
visual_hint: 회의실, 메모, 팀 협업 장면
duration_hint: 8

### Segment 3
narration: 두 번째 활용법은 이메일과 보고서 문장을 더 읽기 쉽게 다듬는 것입니다.
visual_hint: 이메일 작성 화면, 비즈니스 문서, 깔끔한 인터페이스
duration_hint: 7
```

## 빈 폼 템플릿

```md
# Video Script Form

## Meta
channel:
title:
video_type:
visibility: private
publish_at:
tags:
- 

## Description

## Segments

### Segment 1
narration:
visual_hint:
duration_hint:
```

## CLI 예시

```powershell
python src/main.py --script-file docs/examples/sample-script.md
python src/main.py --script-file docs/examples/sample-script.md --upload
python src/main.py --script-file docs/examples/sample-script.md --visibility private --publish-at "2026-03-31 09:00"
```
