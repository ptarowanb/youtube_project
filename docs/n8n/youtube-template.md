# YouTube Research To Production Template

이 템플릿은 `youtube-template.json` 하나로 아래 흐름을 모두 포함합니다.

- 경쟁 채널 영상 수집
- `Gemini` 아이디어 분석
- `Telegram` 승인 요청
- `Approve` 시 쇼츠 제작
- `S3` 업로드
- `automation /render-jobs`
- YouTube 업로드

## Workflow Entry Points

이 workflow 안에는 두 개의 트리거가 있습니다.

1. `Scheduled Daily Trigger`
- `channels` 시트에서 활성 채널을 읽습니다.
- 최근 업로드 영상을 수집합니다.
- 신규 영상만 분석해서 `ideas` 시트에 `draft` 아이디어를 만듭니다.
- 텔레그램으로 `Approve / Hold / Reject` 버튼을 보냅니다.

2. `Telegram Callback Trigger`
- 승인 버튼 클릭을 받습니다.
- `ideas` 시트 상태를 갱신합니다.
- `Approve`일 때만 제작 구간으로 들어갑니다.

## Required Google Sheets

### Sheet: `channels`

- `channel_name`
- `channel_id`
- `enabled`
- `category`
- `notes`

운영 규칙:
- `enabled=TRUE`인 채널만 수집합니다.

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
- `video_id` 기준으로 중복을 제거합니다.

### Sheet: `ideas`

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
- `style_profile`
- `status`
- `telegram_message_id`
- `approved_at`
- `review_action`

운영 규칙:
- 신규 아이디어는 `draft`
- 버튼 클릭으로 `approved`, `hold`, `rejected`
- 제작은 `approved`만 진행

## Required Credentials

- `googleSheetsOAuth2Api` 또는 Google service account
- `youTubeOAuth2Api`
- `googlePalmApi`
- `telegramApi`
- `aws`

## Required Environment Variables

- `TELEGRAM_REVIEW_CHAT_ID`
- `TYPECAST_API_KEY`
- `AUTOMATION_SHARED_TOKEN`
- `RENDER_BUCKET_NAME`

## Provider Stack

- 리서치/분석/대본/메타데이터: `Gemini`
- TTS: `Typecast`
- 정적 비주얼: `Gemini Image`
- 훅 비디오: `Veo Lite`
- 중간/최종 파일 저장: `S3`
- 최종 렌더: `automation`
- 업로드: `YouTube`

## Setup Sequence

1. Google Sheets에 `channels`, `source_videos`, `ideas` 탭을 만든다.
2. `youtube-template.json`을 n8n에 import한다.
3. 각 노드에 credential을 연결한다.
4. 환경변수 `TELEGRAM_REVIEW_CHAT_ID`, `TYPECAST_API_KEY`, `AUTOMATION_SHARED_TOKEN`, `RENDER_BUCKET_NAME`을 넣는다.
5. 텔레그램 봇 callback이 동작하는지 확인한다.
6. workflow를 activate한다.

## Notes

- 기본 운영은 `Veo Lite`를 훅 장면 `1~2개`에만 쓰는 균형형 기준입니다.
- 렌더 입력은 `S3 key` 기준입니다.
- `automation` 응답은 `status`와 `video_url` 또는 `output_url`을 반환해야 합니다.
- 이 템플릿은 import 가능한 시작점입니다. 실제 실행 전에는 시트 ID, credential, 모델 ID, 버킷 이름을 연결해야 합니다.
