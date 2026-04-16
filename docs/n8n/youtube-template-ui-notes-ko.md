# YouTube Template UI 메모

## 섹션 구성

워크플로우는 크게 5개 구간으로 나뉩니다.

1. 수집 / 승인
2. 승인 후 제작 준비
3. 장면별 이미지 생성
4. 장면별 영상 생성
5. 렌더 / 업로드

워크플로우 안에도 같은 제목의 스티키노트가 들어가 있으니, 화면에서 바로 따라가면 됩니다.

## 꼭 봐야 하는 노드

- `Build Production Input`
  - `scene_count`
  - `scene_video_duration_seconds`
  - `gemini_image_model`
  - `veo_model`
  - `render_bucket_name`

- `Expand Scenes`
  - `scene_video_prompts`와 `still_image_prompts`를 scene 단위 item으로 펼칩니다.
  - 여기서 내려온 값을 이후 이미지/영상 생성에서 참조합니다.

- `Loop Over Scenes`
  - `batchSize = 1`
  - scene를 한 번에 하나씩 처리합니다.

- `Gemini Still Image`
  - `still_image_prompt` 기준으로 이미지 생성

- `Veo Lite Hook Clip`
  - `Expand Scenes` 기준으로 다음 값을 읽습니다.
  - `veo_model`
  - `scene_video_prompt`
  - `scene_video_duration_seconds`

## 재시도 규칙

### 이미지

- `Check Image Output`에서 파일 크기를 확인합니다.
- 작거나 비어 있으면 `Image OK?`에서 false로 갑니다.
- false면 `Wait Before Image Retry`에서 8초 대기 후 한 번 더 생성합니다.
- 재시도도 실패하면 `Fail Image Scene`에서 종료합니다.

### 영상

- `Check Video Output`에서 파일 크기를 확인합니다.
- 실패면 `Wait Before Veo Retry`에서 8초 대기 후 한 번 더 생성합니다.
- 재시도도 실패하면 `Fail Video Scene`에서 종료합니다.

## 설정 확인 포인트

붙여넣기 후 아래만 빠르게 보면 됩니다.

1. `Loop Over Scenes`가 있는지
2. `Loop Over Scenes`의 `batchSize`가 `1`인지
3. `Image OK?` false 브랜치가 `Wait Before Image Retry`로 가는지
4. `Video OK?` false 브랜치가 `Wait Before Veo Retry`로 가는지
5. `Veo Lite Hook Clip`의 모델/프롬프트/길이 참조가 모두 `Expand Scenes` 기준인지
6. `Start Render Job`의 `JSON Body`에 `JSON.stringify(...)`가 들어있는지

## 참고

- scene 수가 많으면 Gemini / Veo quota에 걸릴 수 있습니다.
- 지금 구조는 병렬이 아니라 scene 단위 순차 처리입니다.
- 그래도 quota가 부족하면 장면 수를 줄이거나, 실제 API 한도를 올려야 합니다.
