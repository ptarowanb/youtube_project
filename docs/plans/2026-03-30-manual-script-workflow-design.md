# Manual Script Workflow Design

**Status:** Approved for implementation

**Goal**

원고 생성은 사람 또는 ChatGPT 웹을 통해 수동으로 수행하고, 프로젝트는 그 원고를 표준 폼으로 받아 영상 렌더와 선택적 YouTube 업로드까지 수행한다.

**Design Summary**

- 입력 표준은 사람이 작성하기 쉬운 `Markdown + 고정 필드` 폼으로 고정한다.
- CLI는 `--topic` 기반 자동 fallback 생성과 `--script-file` 기반 수동 입력을 모두 지원하되, 수동 입력이 우선되는 실사용 경로가 된다.
- 업로드는 `--upload` 플래그가 있을 때만 실행해, 영상 렌더와 업로드를 분리된 제어점으로 둔다.

**Why This Shape**

- 사용자는 이미 ChatGPT 구독을 통해 수동으로 원고를 만들 수 있고, OpenAI API는 별도 과금이라 자동 원고 생성의 우선순위가 낮다.
- Markdown 폼은 ChatGPT 프롬프트로도 바로 재사용할 수 있고, JSON보다 사람이 다루기 쉽다.
- 업로드는 인증/정책 리스크가 있으므로 기본값은 비활성화가 안전하다.

**Input Form**

새 문서 `docs/manual-script-form.md`를 단일 소스로 둔다. 이 문서는:

- 필수 메타데이터
  - `channel`
  - `title`
  - `video_type`
- 선택 메타데이터
  - `visibility`
  - `publish_at`
  - `tags`
- 설명 블록
  - `Description`
- 세그먼트 반복 블록
  - `narration`
  - `visual_hint`
  - `duration_hint`

예시:

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
- productivity

## Description
이 영상에서는 ChatGPT를 업무에 적용하는 방법을 설명합니다.

## Segments

### Segment 1
narration: ChatGPT는 초안 작성과 정리에 특히 강합니다.
visual_hint: 사무실 책상, 노트북 화면, 생산성 있는 분위기
duration_hint: 8
```

**Parser Behavior**

새 모듈 `src/manual_script_parser.py`는 Markdown 폼을 읽어 `ScriptPayload`로 변환한다.

- 메타 섹션과 세그먼트 섹션이 없으면 실패한다.
- `title`, `channel`, 세그먼트는 필수다.
- `duration_hint`가 없으면 기본값을 부여한다.
- `visual_hint`는 내부적으로 기존 `image_prompt` 필드로 매핑한다.
- `publish_at`는 문자열로 유지하고, 업로드 직전 datetime으로 변환한다.

**CLI Changes**

`src/main.py`에 다음 인자를 추가한다.

- `--script-file <path>`
- `--upload`
- `--visibility <private|unlisted|public>` optional override
- `--publish-at "YYYY-MM-DD HH:MM"` optional override

동작 규칙:

- `--script-file`가 있으면 `--topic` 없이도 실행 가능하다.
- `--topic`과 `--script-file`를 동시에 주면 `--script-file`를 사용하고 경고하지 않는다.
- 업로드는 `--upload`가 있을 때만 수행한다.

**Uploader Behavior**

기존 `src/uploader.py` 스텁을 실제 업로드 경로로 교체한다.

- `google-api-python-client`, `google-auth-oauthlib` 기반
- `configs/client_secret.json`과 `token.json` 사용
- 메타데이터는 원고 폼과 CLI override에서 조합
- 기본 업로드 상태는 `private`
- `publish_at`이 있으면 예약 업로드로 전환

실제 네트워크 없는 테스트를 위해 업로드 요청 빌드 함수는 분리한다.

**Testing Strategy**

- `tests/test_manual_script_parser.py`
  - 정상 폼 파싱
  - 필수 필드 누락 실패
  - tags/duration 처리
- `tests/test_main.py`
  - `--script-file` 경로 실행
  - `--upload`가 uploader를 호출하는지
- `tests/test_uploader.py`
  - YouTube request body 생성
  - visibility / publishAt 매핑
  - 인증 경로 오류 처리

**Non-Goals For This Batch**

- 자동 원고 생성 품질 개선
- Pexels/실제 이미지 수집
- Whisper 자막 타임스탬프
- 스케줄러 자동 실행
- YouTube Analytics
