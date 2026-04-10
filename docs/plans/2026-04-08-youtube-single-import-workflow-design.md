# YouTube Single Import Workflow Design

**Goal**

`n8n`에 한 번에 import 가능한 단일 workflow JSON 하나로 `채널 수집 -> Gemini 분석 -> Telegram 승인 -> 쇼츠 제작 -> YouTube 업로드`까지 모두 연결한다.

**Why This Direction**

- 운영자는 여러 workflow를 따로 import하거나 연결하지 않고 `youtube-template.json` 하나만 붙여넣고 시작할 수 있어야 한다.
- 감시 채널 변경은 `Google Sheets`에서 하고, 비용이 드는 제작 단계는 `Telegram` 승인 뒤에만 실행되게 해야 한다.
- 제작 단계는 기존 스택인 `Gemini + Typecast + Veo Lite + S3 + automation + YouTube`를 유지한다.

**Scope**

- 단일 `n8n` workflow JSON으로 구성한다.
- 같은 workflow 안에 `Schedule Trigger`와 `Telegram Trigger`를 함께 둔다.
- `Google Sheets`를 운영 데이터 저장소로 사용한다.
- 승인된 아이디어만 `S3` 기반 렌더 파이프라인으로 보낸다.

**Out of Scope**

- 경쟁 채널 원본 영상 다운로드/재편집
- Google Drive 기반 저장소 전환
- 다중 workflow 분리 운영
- 템플릿 import 이후의 credential 실제 연결 자동화

## Architecture

하나의 workflow 안에 두 개의 진입점을 둔다.

1. `Scheduled Daily Trigger`
- `channels` 시트에서 `enabled=TRUE` 채널을 읽는다.
- 최근 업로드 영상을 수집해 `source_videos` 시트에 적재한다.
- 신규 영상만 `Gemini`로 분석해 `ideas` 시트에 `draft` 아이디어를 생성한다.
- 텔레그램으로 아이디어 요약과 `Approve / Hold / Reject` 버튼을 전송한다.

2. `Telegram Trigger`
- callback query를 받는다.
- `approve|idea_id`, `hold|idea_id`, `reject|idea_id`를 파싱한다.
- `ideas` 시트 상태를 업데이트한다.
- `Approve`일 때만 즉시 제작 구간으로 진입한다.

## Data Flow

### Harvest + Analysis

- `channels`
  - `channel_name`
  - `channel_id`
  - `enabled`
  - `category`
  - `notes`

- `source_videos`
  - `video_id`
  - `channel_id`
  - `channel_name`
  - `title`
  - `url`
  - `published_at`
  - `harvested_at`
  - `status`

- `ideas`
  - `idea_id`
  - `source_video_id`
  - `channel_name`
  - `source_url`
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

수집 단계는 최근 3일 기준으로 영상을 가져오고, `video_id` 기준으로 중복을 제거한다. 분석 단계는 신규 영상만 대상으로 하고, `Gemini`는 `topic`, `hook`, `angle`, `summary`, `suggested_*` 필드를 반환한다.

### Approval + Production

텔레그램 메시지는 아래 정보를 포함한다.

- 채널명
- 원본 영상 URL
- 추출된 `topic`
- 제안된 `hook`
- 제안된 `angle`
- 짧은 `summary`

버튼 규칙:

- `Approve` -> `ideas.status=approved`
- `Hold` -> `ideas.status=hold`
- `Reject` -> `ideas.status=rejected`

`Approve`된 아이디어만 제작 단계로 진입한다.

제작 단계는 아래 순서로 진행한다.

1. `Gemini`로 대본/장면/제목/설명/태그 생성
2. `Typecast`로 나레이션 생성
3. `Gemini Image`로 정적 장면 생성
4. `Veo Lite`로 훅 장면 1~2개 생성
5. 오디오/이미지/영상/자막을 `S3`에 저장
6. `automation`에 `/render-jobs` 요청
7. `Wait + polling`으로 렌더 완료 확인
8. YouTube 업로드

## Contracts

`automation` 요청 payload는 `S3` key 기준으로 유지한다.

```json
{
  "job_id": "yt_20260408_idea_001",
  "video_keys": [
    "jobs/yt_20260408_idea_001/videos/01.mp4"
  ],
  "image_keys": [
    "jobs/yt_20260408_idea_001/images/01.png"
  ],
  "audio_keys": [
    "jobs/yt_20260408_idea_001/audio/narration.mp3"
  ],
  "subtitle_key": "jobs/yt_20260408_idea_001/subtitles/captions.srt",
  "bgm_key": "shared/bgm/default.mp3",
  "output_prefix": "jobs/yt_20260408_idea_001/output/"
}
```

`automation` 상태 조회는 아래를 반환해야 한다.

- `job_id`
- `status`
- `video_url` 또는 `output_url`
- 실패 시 `error`

## Error Handling

- 채널 수집 실패:
  - 실패 채널만 건너뛰고 다른 채널은 계속 진행
- `Gemini` 분석 실패:
  - `source_videos.status=analysis_failed`
- 텔레그램 전송 실패:
  - `ideas.status=draft` 유지
- 제작 실패:
  - n8n execution failed 상태로 종료
  - operator가 실행 로그에서 실패 원인을 확인

## Output Files

- `docs/n8n/youtube-template.json`
- `docs/n8n/youtube-template.md`
- `docs/plans/2026-04-08-youtube-single-import-workflow.md`
