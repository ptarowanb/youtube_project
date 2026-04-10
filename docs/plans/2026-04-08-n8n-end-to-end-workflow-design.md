# N8N End-To-End Workflow Design

**Goal**

`n8n`에서 `Gemini 2.5 Flash` 기반 시나리오 생성, `Typecast` 나레이션 생성, `Gemini Image + Veo Lite` 비주얼 생성, S3 적재, `automation` 렌더 호출, YouTube 업로드까지 한 번에 오케스트레이션하는 워크플로우 템플릿을 만든다. 이번 버전은 placeholder가 아니라 실제 공급자 노드 구성을 포함한다.

**Scope**

- 입력은 `Webhook`으로 받는다.
- `n8n`이 AI 생성 단계 전체를 담당한다.
- `automation`은 `/render-jobs`와 상태 조회만 담당한다.
- 템플릿은 import 가능한 `n8n` workflow JSON 형식으로 저장한다.
- 템플릿은 실제 공급자 노드를 포함하되, 장면 수 확장은 후속 loop 구성으로 남긴다.

**Architecture**

- `Webhook`이 주제, 스타일, 길이, YouTube 메타데이터를 입력으로 받는다.
- `n8n`은 `Google Gemini` 노드로 장면 구성, 제목, 설명, 태그, 이미지/영상 프롬프트를 만든다.
- 나레이션은 `Typecast` HTTP API, 정적 비주얼은 `Google Gemini` 이미지 생성 노드, 동적 훅 장면은 `Google Gemini` 비디오 생성 노드로 처리한다.
- 생성된 오디오, 자막, 이미지, 비디오는 모두 `AWS S3` 노드로 업로드한다.
- 생성 단계의 최종 산출물은 `audio_keys`, `image_keys`, `video_keys`, `subtitle_key`, `bgm_key`, `output_prefix` 형태의 S3 manifest로 정리한다.
- 이후 `automation`에 `POST /render-jobs`를 보내고, `Wait + GET /render-jobs/{id}`로 완료까지 폴링한다.
- 완료 시 렌더된 영상을 다운로드하고 YouTube 노드로 업로드한다.

**Data Contract**

입력 payload는 최소한 아래 값을 받는다.

- `topic`
- `youtube_title`

선택값:

- `style`
- `duration_seconds`
- `voice_id`
- `visual_style`
- `hook_clip_count`
- `youtube_description`
- `youtube_tags`
- `youtube_privacy_status`
- `bgm_key`

`automation` 요청 payload는 아래 형태로 정리한다.

- `job_id`
- `video_keys`
- `image_keys`
- `audio_keys`
- `subtitle_key`
- `bgm_key`
- `output_prefix`

`automation` 상태 조회는 최종적으로 아래를 반환해야 한다.

- `status`
- `video_url` 또는 `output_url`
- 실패 시 `error`

**Tradeoffs**

- 균형형 운영에서는 `Veo Lite`를 전 장면에 쓰지 않고 앞쪽 훅 장면 `1~2개`에만 제한한다.
- 나머지 장면은 `Gemini Image`와 `automation` 모션 합성으로 처리해서 비용을 낮춘다.
- 현재 템플릿은 기본 예시로 `still 1장 + hook clip 1개`를 실제 생성하도록 설계하고, 장면 확장은 후속 loop 구성으로 넘긴다.

**Output Files**

- `docs/n8n/end-to-end-ai-render-youtube-template.json`
- `docs/n8n/end-to-end-ai-render-youtube-template.md`
