# YouTube Research To Telegram Approval Design

**Goal**

경쟁 채널 영상을 직접 재편집하지 않고, `YouTube -> Google Sheets -> Gemini 분석 -> Telegram 승인 -> 우리 쇼츠 생성` 흐름으로 운영 가능한 리서치 기반 제작 파이프라인을 설계한다.

**Why This Direction**

- 경쟁 채널의 원본 영상을 그대로 재편집해서 재업로드하는 방식은 저작권/재사용 콘텐츠 리스크가 크다.
- 대신 경쟁 채널의 제목, 훅, 설명, 주제, 업로드 패턴을 수집해서 분석하고, 그 분석 결과를 기반으로 새로운 쇼츠를 만드는 구조가 더 안전하다.
- 비용도 `approved` 상태의 아이디어만 제작 단계로 보내도록 제한하면 통제하기 쉽다.

**Scope**

- 감시 채널 목록은 `Google Sheets`에서 관리한다.
- 최신 영상 목록은 `source_videos` 시트에 적재한다.
- `Gemini`가 신규 영상을 분석해서 `ideas` 시트에 후보를 생성한다.
- `Telegram` 메시지에서 `Approve / Hold / Reject` 버튼으로 아이디어를 승인한다.
- `approved` 아이디어만 `Gemini + Typecast + Veo Lite + automation + YouTube` 제작 파이프라인으로 넘긴다.

**Out of Scope**

- 타 채널 원본 영상 다운로드/재편집 자동화
- fair use 판정 자동화
- 장면 수 무제한 확장
- 자동 제작 결과의 완전 무검수 게시

## Architecture

전체 구조는 6개 워크플로우로 분리한다.

1. `Channel Sync`
- `channels` 시트에서 활성 채널 목록을 읽는다.
- 채널별 `channel_id`, `channel_name`, `enabled`, `category`를 사용한다.

2. `Video Harvest`
- 각 채널의 최신 영상을 `YouTube` 노드로 수집한다.
- `source_videos` 시트에 `video_id`, `channel_id`, `title`, `url`, `published_at`를 저장한다.
- 같은 `video_id`는 중복 저장하지 않는다.

3. `Idea Analysis`
- 신규 `source_videos`만 `Gemini`로 분석한다.
- 출력은 `hook`, `angle`, `summary`, `suggested_title`, `suggested_tags`, `source_video_id`를 포함한다.
- 결과는 `ideas` 시트에 `status=draft`로 적재한다.

4. `Telegram Review`
- `draft` 아이디어를 읽어서 텔레그램으로 전송한다.
- 메시지에는 `Approve`, `Hold`, `Reject` inline button을 포함한다.
- 각 메시지는 `idea_id`를 callback data에 담는다.

5. `Approval Update`
- `Telegram Trigger`가 callback query를 받는다.
- 버튼 액션에 따라 `ideas.status`를 `approved`, `hold`, `rejected`로 변경한다.
- `telegram_message_id`, `approved_at`, `review_action`도 같이 기록한다.

6. `Approved Production`
- `ideas.status=approved`만 읽는다.
- 이 아이디어를 기반으로 기존 제작 파이프라인을 실행한다.
- 즉 `Gemini`로 대본/메타데이터 생성, `Typecast`로 나레이션 생성, `Veo Lite`와 `Gemini Image`로 비주얼 생성, `S3` 업로드, `/render-jobs`, YouTube 업로드를 수행한다.

## Google Sheets Schema

### Sheet: `channels`

- `channel_name`
- `channel_id`
- `enabled`
- `category`
- `notes`

운영 규칙:
- `enabled=TRUE`인 채널만 수집한다.
- 채널 추가/삭제는 이 시트만 수정한다.

### Sheet: `source_videos`

- `video_id`
- `channel_id`
- `channel_name`
- `title`
- `url`
- `published_at`
- `harvested_at`
- `status`

운영 규칙:
- `video_id`를 유니크 키처럼 취급한다.
- `status`는 `new`, `analyzed`, `ignored` 정도로 관리한다.

### Sheet: `ideas`

- `idea_id`
- `source_video_id`
- `channel_name`
- `topic`
- `hook`
- `angle`
- `summary`
- `suggested_title`
- `suggested_description`
- `suggested_tags`
- `status`
- `telegram_message_id`
- `approved_at`
- `review_action`

운영 규칙:
- 초기 상태는 `draft`
- 버튼 클릭으로 `approved`, `hold`, `rejected`
- `approved`만 제작 워크플로우에서 읽는다.

## Telegram Approval Design

텔레그램 메시지는 아이디어 후보를 짧게 요약해서 전송한다.

메시지 예시:

```text
[Idea] idea_20260408_001
Channel: Example Channel
Source: https://www.youtube.com/watch?v=abc123
Topic: abandoned apartment mystery
Hook: "문을 열었는데 냉장고만 켜져 있었다"
Angle: 실화형 미스터리 쇼츠
Summary: 경쟁 채널의 훅 구조를 차용하되, 배경 설정과 결말을 완전히 새로 구성
```

버튼:

- `Approve`
- `Hold`
- `Reject`

callback data 예시:

- `approve|idea_20260408_001`
- `hold|idea_20260408_001`
- `reject|idea_20260408_001`

승인 시 처리:

- `ideas.status=approved`
- `approved_at` 저장
- 필요하면 같은 메시지를 수정해서 현재 상태를 표시

## Generation Pipeline Contract

`approved` 아이디어는 기존 쇼츠 생성 파이프라인으로 넘긴다.

입력 필드:

- `idea_id`
- `topic`
- `hook`
- `angle`
- `suggested_title`
- `suggested_description`
- `suggested_tags`

이후 생성 스택:

- `Gemini 2.5 Flash`: 시나리오/대본/제목/설명/태그
- `Typecast`: 나레이션
- `Gemini Image`: 정적 장면
- `Veo Lite`: 훅 장면 1~2개
- `AWS S3`: 중간 파일 저장
- `automation`: 최종 렌더
- `YouTube`: 업로드

## Error Handling

- `YouTube` 수집 실패:
  - 채널 단위로 계속 진행
  - 실패 채널은 로그로 남긴다.

- `Gemini` 분석 실패:
  - `source_videos.status=analysis_failed`
  - 재시도 대상만 별도 조회 가능하게 둔다.

- `Telegram` 전송 실패:
  - `ideas.status=draft` 유지
  - 다음 알림 워크플로우에서 재전송 가능하게 둔다.

- 승인 이후 제작 실패:
  - `ideas.status=production_failed`
  - 실패 이유를 기록한다.

## Recommended Workflow Split

운영 복잡도를 낮추려면 한 개 거대한 워크플로우보다 아래처럼 나누는 것이 맞다.

- `wf_channel_harvest`
- `wf_video_analysis`
- `wf_telegram_review`
- `wf_telegram_callback`
- `wf_approved_production`

이렇게 분리하면:

- 수집과 제작이 분리된다.
- 비용이 `approved` 단계에서만 발생한다.
- 장애가 나도 어떤 단계에서 멈췄는지 바로 알 수 있다.

## Output Files

- `docs/n8n/youtube-template.json`
- `docs/n8n/end-to-end-ai-render-youtube-template.json`
- `docs/plans/2026-04-08-youtube-research-telegram-approval.md`
