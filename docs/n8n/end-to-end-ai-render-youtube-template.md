# AI To Render To YouTube Template

이 템플릿은 전체 파이프라인 기준입니다.

- 주제 입력
- `Gemini 2.5 Flash`로 시나리오/메타데이터 생성
- `Typecast`로 나레이션/TTS 생성
- `Gemini Image` + `Veo Lite`로 비주얼 생성
- S3 key manifest 준비
- `automation` 렌더 호출
- YouTube 업로드

Webhook 경로:

- `POST /webhook/ai-render-youtube`

입력 예시:

```json
{
  "topic": "abandoned house mystery",
  "style": "mysterious",
  "duration_seconds": 30,
  "voice_id": "typecast-korean-female-01",
  "visual_style": "cinematic stills",
  "hook_clip_count": 2,
  "youtube_title": "The Empty House Mystery",
  "youtube_description": "Short-form mystery story",
  "youtube_tags": [
    "shorts",
    "mystery"
  ],
  "youtube_privacy_status": "private",
  "bgm_key": "shared/bgm/default.mp3"
}
```

현재 템플릿은 아래 구간이 실제 공급자 노드로 들어가 있습니다.

- `Gemini Scenario Planner`
- `Typecast Narration`
- `Upload Narration to S3`
- `Build Subtitle File`
- `Upload Subtitle to S3`
- `Gemini Still Image`
- `Upload Image to S3`
- `Veo Lite Hook Clip`
- `Upload Hook Video to S3`

균형형 운영 기준:

- `Veo Lite`는 앞쪽 훅 장면 `1~2개`만 생성
- 나머지 장면은 `Gemini Image` 결과를 `automation`에서 패닝/줌/자막으로 처리
- `Gemini`는 `title`, `description`, `tags`까지 같이 생성
- 현재 JSON은 기본 예시로 `still 1장 + hook clip 1개`를 생성한다
- 장면을 늘리려면 이미지/비디오 생성 블록을 복제하거나 `Loop Over Items`로 확장하면 된다

`automation`에 보내는 렌더 payload 형태:

```json
{
  "job_id": "yt_20260408103000_abc123",
  "video_keys": [
    "jobs/yt_20260408103000_abc123/videos/01.mp4",
    "jobs/yt_20260408103000_abc123/videos/02.mp4"
  ],
  "image_keys": [
    "jobs/yt_20260408103000_abc123/images/01.png",
    "jobs/yt_20260408103000_abc123/images/02.png"
  ],
  "audio_keys": [
    "jobs/yt_20260408103000_abc123/audio/narration.mp3"
  ],
  "subtitle_key": "jobs/yt_20260408103000_abc123/subtitles/captions.srt",
  "bgm_key": "shared/bgm/default.mp3",
  "output_prefix": "jobs/yt_20260408103000_abc123/output/"
}
```

`automation` 상태 조회 응답은 최종적으로 아래를 만족해야 합니다.

```json
{
  "job_id": "yt_20260408103000_abc123",
  "status": "done",
  "video_url": "https://example-bucket.s3.ap-northeast-2.amazonaws.com/jobs/yt_20260408103000_abc123/output/final.mp4"
}
```

실사용 전 확인할 것:

- `Google Gemini` 노드에 `googlePalmApi` credential 연결
- `AWS S3` 노드들에 `aws` credential 연결
- `YouTube Upload` 노드에 YouTube OAuth2 credential 연결
- `TYPECAST_API_KEY`, `AUTOMATION_SHARED_TOKEN`, `RENDER_BUCKET_NAME`이 n8n 런타임 env에서 보이는지 확인
- `regionCode`와 `categoryId`를 채널 정책에 맞게 조정
- `veo_model`을 계정에서 실제 사용 가능한 Veo Lite 계열 모델 ID로 맞추기
