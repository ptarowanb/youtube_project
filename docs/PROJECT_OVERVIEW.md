# AI 유튜브 자동화 시스템 — 프로젝트 개요

> Python 기반 동적 멀티채널 유튜브 자동화 파이프라인
> 채널 수에 관계없이 YAML 설정만으로 추가/제거 가능

---

## 1. 프로젝트 목표

AI 기술(LLM, TTS, Image Gen, Auto-Editing)을 파이프라인으로 연결해 **N개의 유튜브 채널**을 동시에 운영할 수 있는 자동화 시스템을 구축한다.

채널 수는 고정되지 않으며, `channel_settings.yaml`에 항목을 추가하거나 `enabled: false`로 비활성화하는 것만으로 운영 채널을 자유롭게 조정한다. 코드 수정 불필요.

### 현재 운영 채널 예시 (언제든 변경 가능)

| 채널 ID | 컨셉 | 핵심 요소 |
|---------|------|-----------|
| `knowledge` | 지식/비즈니스 | 스톡 영상 + 깔끔한 자막 + 중립적 성우 |
| `mystery` | 미스터리/바이럴 | AI 생성 이미지 + 드라마틱 BGM + 남성 성우 |
| `healing` | 힐링/자기계발 | 자연 풍경 영상 + 잔잔한 BGM + 차분한 성우 |

> 새 채널 추가 시: YAML에 새 항목 작성 → 즉시 파이프라인에서 인식
> 채널 중단 시: `enabled: false` 설정 → 스케줄러가 해당 채널 건너뜀

---

## 2. 핵심 개선 방향 (기존 계획 대비)

### 2-1. 아키텍처: 선형 → 이벤트 기반 파이프라인

기존 계획은 스크립트가 순차 실행되는 구조였으나, 실제 운영 시 병목과 재시도 관리가 어렵다.

**권장 구조: Task Queue 기반 파이프라인**

```
[Scheduler] → [Job Queue] → [Worker: Scripter]
                          → [Worker: Voice Gen]   (병렬 가능)
                          → [Worker: Asset Fetch]  (병렬 가능)
                          → [Worker: Editor]
                          → [Worker: Uploader]
```

- 각 단계를 독립 Worker로 분리 → 특정 단계 실패 시 해당 단계만 재시도
- 향후 Celery + Redis 또는 간단히 `concurrent.futures`로 병렬화 가능

### 2-2. 상태 관리: DB 기반 Job 추적

현재 계획에는 작업 상태 추적이 없다. 운영 중 실패한 영상이 어떤 단계에서 멈췄는지 알 수 없다.

**SQLite (MVP) → PostgreSQL (확장) 기반 Job 테이블 도입**

```sql
jobs (id, channel, topic, status, created_at, completed_at, error_msg)
-- status: pending | scripting | voicing | editing | uploading | done | failed
```

### 2-3. 자막: whisper 기반 정확한 타임스탬프

기존: TTS 오디오 길이를 단순 분할해 자막 타이밍을 맞춤 → 부정확
개선: `openai-whisper` 또는 `faster-whisper`로 생성된 오디오를 역분석해 **단어 단위 타임스탬프** 추출

```python
# faster-whisper (로컬, 무료)
segments, _ = model.transcribe("audio.mp3", word_timestamps=True)
```

### 2-4. 영상 포맷: 쇼츠/롱폼 자동 분기

채널 설정에 `format: shorts | longform` 추가, Editor가 자동으로 해상도와 길이를 조절

| 포맷 | 해상도 | 목표 길이 |
|------|--------|-----------|
| Shorts | 1080×1920 (9:16) | 30~60초 |
| Longform | 1920×1080 (16:9) | 5~15분 |

### 2-5. 트렌드 기반 주제 자동 발굴

수동으로 주제를 입력하는 대신 외부 데이터 소스에서 자동 수집:

- **Google Trends API** (pytrends): 실시간 트렌드 키워드
- **YouTube Data API**: 경쟁 채널 인기 영상 분석
- **RSS 피드**: 뉴스/블로그 최신 글 수집

---

## 3. 기술 스택

| 역할 | 라이브러리/서비스 | 비고 |
|------|-----------------|------|
| LLM (대본) | OpenAI API `gpt-4o` | Structured Output으로 JSON 보장 |
| TTS | `edge-tts` | 무료, 고품질 한국어 지원 |
| 자막 타임스탬프 | `faster-whisper` | 로컬 실행, 무료 |
| 이미지 생성 | DALL-E 3 (OpenAI) / Stable Diffusion | 채널별 선택 |
| 실사 영상 | Pexels API | 무료 플랜 가능 |
| 영상 편집 | `moviepy` v2 | ffmpeg 백엔드 |
| 스케줄링 | APScheduler / cron | 시간 기반 자동 실행 |
| 상태 관리 | SQLite → PostgreSQL | Job 추적 |
| 환경 변수 | `python-dotenv` | `.env` 파일 |
| 업로드 | YouTube Data API v3 | 자동 업로드 + 예약 |

---

## 4. 폴더 구조 (개선안)

```
youtube_automation/
├── src/
│   ├── main.py              # CLI 진입점 + 파이프라인 오케스트레이터
│   ├── scheduler.py         # 채널별 자동 스케줄링 (APScheduler)
│   ├── trend_finder.py      # 트렌드 주제 자동 발굴 (신규)
│   ├── scripter.py          # LLM 대본 생성
│   ├── voice_gen.py         # TTS 오디오 생성
│   ├── subtitle_gen.py      # faster-whisper 자막 타임스탬프 (신규)
│   ├── asset_manager.py     # Pexels/AI 이미지 수집
│   ├── editor.py            # MoviePy 영상 합성
│   ├── uploader.py          # YouTube API 업로드 (신규)
│   ├── job_tracker.py       # SQLite Job 상태 관리 (신규)
│   └── utils/
│       ├── logger.py        # 중앙 로깅
│       └── validators.py    # 입력 유효성 검사
├── assets/
│   ├── fonts/               # 채널별 폰트 파일
│   ├── bgm/                 # 채널별 배경음악
│   └── outputs/             # 생성된 영상 (날짜/채널별 정리)
│       └── {channel}/{YYYY-MM-DD}/
├── configs/
│   ├── channel_settings.yaml  # 채널별 설정 (성우, 스타일, 포맷)
│   └── prompts/               # LLM 프롬프트 템플릿 (신규)
│       ├── knowledge.txt
│       ├── mystery.txt
│       └── healing.txt
├── database/
│   └── jobs.db              # SQLite DB (신규)
├── tests/                   # 단위 테스트 (신규)
├── .env
├── requirements.txt
└── docs/                    # 이 문서들
```

---

## 5. 데이터 구조

### 5-1. 대본 JSON (개선안)

```json
{
  "title": "영상 제목",
  "description": "유튜브 업로드용 설명글",
  "channel": "knowledge",
  "format": "shorts",
  "segments": [
    {
      "id": 1,
      "text": "내레이션 문구",
      "image_prompt": "영어 이미지 생성 프롬프트",
      "duration_hint": 5
    }
  ],
  "tags": ["#tag1", "#tag2"],
  "thumbnail_prompt": "썸네일용 이미지 프롬프트"
}
```

> `thumbnail_prompt` 추가: 썸네일 이미지를 별도 생성해 CTR 최적화

### 5-2. 채널 설정 YAML

채널 수는 고정되지 않는다. YAML에 항목 추가/삭제만으로 파이프라인이 자동으로 인식한다.
`enabled: false`로 설정하면 코드 수정 없이 해당 채널을 일시 중단할 수 있다.

```yaml
# configs/channel_settings.yaml

# 전체 공통 기본값 — 각 채널에서 필요한 항목만 override
defaults:
  format: shorts
  resolution: [1080, 1920]
  font: NanumSquareRound.ttf
  font_size: 52
  font_color: white
  bgm_volume: 0.15
  image_source: pexels        # pexels | dalle | stable_diffusion
  upload_schedule: "10:00"    # 매일 업로드 시각 (KST)
  enabled: true

channels:
  knowledge:
    enabled: true
    display_name: "지식채널"
    voice: ko-KR-SunHiNeural
    format: longform
    resolution: [1920, 1080]
    font_size: 52
    font_color: white
    bgm: bgm/knowledge_calm.mp3
    bgm_volume: 0.15
    image_source: pexels
    upload_schedule: "09:00"

  mystery:
    enabled: true
    display_name: "미스터리채널"
    voice: ko-KR-InJoonNeural
    format: shorts
    resolution: [1080, 1920]
    font: BlackHanSans.ttf
    font_size: 60
    font_color: "#FF3333"
    bgm: bgm/mystery_tense.mp3
    bgm_volume: 0.25
    image_source: dalle
    upload_schedule: "18:00"

  healing:
    enabled: true
    display_name: "힐링채널"
    voice: ko-KR-SunHiNeural
    format: shorts
    resolution: [1080, 1920]
    font: NanumMyeongjo.ttf
    font_size: 50
    font_color: "#F5F0E8"
    bgm: bgm/healing_nature.mp3
    bgm_volume: 0.20
    image_source: pexels
    upload_schedule: "07:00"

  # 새 채널 추가 예시 — 아래 블록 복사 후 값만 바꾸면 바로 동작
  # finance:
  #   enabled: false           # true로 바꾸면 즉시 활성화
  #   display_name: "재테크채널"
  #   voice: ko-KR-InJoonNeural
  #   format: longform
  #   ...
```

---

## 6. 단계별 상세 로직

### Step 0: 트렌드 발굴 (trend_finder.py)

```python
# pytrends로 실시간 트렌드 수집
# 채널 컨셉에 맞는 키워드 필터링
# LLM에 "이 트렌드를 바탕으로 영상 주제 5개 추천" 요청
```

### Step 1: 대본 생성 (scripter.py)

- `gpt-4o`의 **Structured Output** (response_format=JSON) 사용 → 파싱 오류 방지
- 채널별 프롬프트 템플릿 분리 (`configs/prompts/`)
- 세그먼트 수 = 영상 목표 길이 / 평균 읽기 속도(3초/문장) 로 자동 계산

### Step 2: 음성 생성 (voice_gen.py)

- `edge-tts`로 세그먼트별 `.mp3` 생성
- 채널별 `voice`, `rate`, `pitch` 설정 적용
- 생성 후 `pydub`으로 무음 구간 트리밍

### Step 3: 자막 타임스탬프 (subtitle_gen.py) — 신규

```python
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu")
segments, _ = model.transcribe("narration.mp3", word_timestamps=True)
# → [(word, start_time, end_time), ...] 반환
```

### Step 4: 에셋 수집 (asset_manager.py)

- `image_source` 설정에 따라 Pexels 또는 DALL-E 3 호출
- 각 세그먼트의 `image_prompt`로 이미지 생성/다운로드
- 이미지 캐싱: 동일 프롬프트 재사용 시 API 비용 절감

### Step 5: 영상 합성 (editor.py)

1. 세그먼트별 이미지 + 오디오 → `ImageClip` + `AudioFileClip`
2. Ken Burns 효과 (줌인/줌아웃 패닝) 적용 — 정지 이미지의 단조로움 해소
3. `faster-whisper` 타임스탬프로 단어 단위 자막 오버레이
4. BGM 믹싱 (내레이션 볼륨 1.0, BGM 볼륨 채널 설정값)
5. 인트로/아웃트로 클립 자동 삽입
6. `ffmpeg` 렌더링 (H.264, AAC)

### Step 6: 업로드 (uploader.py) — 신규

```python
# YouTube Data API v3
# - 제목, 설명, 태그, 카테고리 자동 설정
# - publishAt으로 예약 업로드 지원
# - 썸네일 자동 업로드
```

---

## 7. 향후 확장 로드맵

### Phase 1 — MVP (현재 목표)
- [ ] 정지 이미지 + TTS 오디오 + 기본 자막 → MP4 생성
- [ ] 3개 채널 설정 분리
- [ ] `.env` 기반 API 키 관리

### Phase 2 — 품질 개선
- [ ] `faster-whisper` 단어 단위 자막 (Karaoke 스타일)
- [ ] Ken Burns 효과 (이미지 패닝/줌)
- [ ] Pexels 실사 영상 클립 자동 매칭
- [ ] 인트로/아웃트로 템플릿
- [ ] SQLite Job 상태 추적

### Phase 3 — 자동화 강화
- [ ] `trend_finder.py`: Google Trends/RSS 기반 주제 자동 발굴
- [ ] APScheduler: 채널별 시간대 자동 스케줄링
- [ ] YouTube Data API 자동 업로드 + 예약
- [ ] 썸네일 자동 생성 (DALL-E 3)

### Phase 4 — 분석 & 최적화
- [ ] YouTube Analytics API: 조회수/클릭률 데이터 수집
- [ ] 성과 데이터 기반 제목/썸네일 A/B 테스트 자동화
- [ ] 고성과 영상 패턴 분석 → LLM 프롬프트에 피드백

---

## 8. 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────┐
│                    Scheduler                        │
│         (APScheduler / 채널별 cron 설정)              │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────▼─────────┐
        │   Trend Finder    │  ← Google Trends, RSS, YouTube
        └─────────┬─────────┘
                  │ topic
        ┌─────────▼─────────┐
        │     Scripter      │  ← GPT-4o (Structured JSON)
        └─────────┬─────────┘
                  │ script.json
        ┌─────────┴──────────────────┐
        │                            │
┌───────▼────────┐        ┌─────────▼──────────┐
│   Voice Gen    │        │   Asset Manager    │
│  (edge-tts)    │        │ (Pexels / DALL-E)  │
└───────┬────────┘        └─────────┬──────────┘
        │ audio.mp3                 │ images/
        │         ┌─────────────────┘
        │  ┌──────▼──────┐
        │  │ Subtitle Gen│  ← faster-whisper
        │  └──────┬──────┘
        │         │ timestamps
        └────┬────┘
      ┌──────▼──────┐
      │    Editor   │  ← MoviePy + ffmpeg
      └──────┬──────┘
             │ output.mp4
      ┌──────▼──────┐
      │  Uploader   │  ← YouTube Data API v3
      └─────────────┘
```

---

## 9. 비용 추정 (월간 영상 100개 기준)

| 항목 | 단가 | 월 예상 비용 |
|------|------|-------------|
| GPT-4o (대본 생성) | ~$0.03/영상 | ~$3 |
| DALL-E 3 (이미지) | ~$0.04/장 × 5장 | ~$20 |
| edge-tts | 무료 | $0 |
| faster-whisper | 로컬 무료 | $0 |
| Pexels API | 무료 플랜 | $0 |
| YouTube API | 무료 할당량 내 | $0 |
| **합계** | | **~$23/월** |

> DALL-E 3 대신 로컬 Stable Diffusion 사용 시 이미지 비용 $0

---

## 10. 리스크 및 주의사항

| 리스크 | 대응 방안 |
|--------|-----------|
| YouTube 자동화 계정 정지 | 업로드 간격 최소 4시간, API 할당량 준수 |
| TTS 음성 단조로움 | `rate`, `pitch` 파라미터 랜덤 변주 |
| API 비용 초과 | 일별 생성 한도 설정, 비용 알림 |
| 저작권 문제 | CC0 에셋만 사용, AI 생성 이미지 우선 |
| 영상 품질 일관성 | 채널별 설정 파일로 스타일 고정 |
