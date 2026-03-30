# 개발 로드맵

## Phase 1 — MVP (목표: 영상 1개 수동 생성)

### 구현 목록
- [ ] `scripter.py`: GPT-4o Structured Output으로 JSON 대본 생성
- [ ] `voice_gen.py`: edge-tts로 세그먼트별 mp3 생성
- [ ] `editor.py`: 이미지 + 오디오 + 기본 자막 → mp4
- [ ] `channel_settings.yaml`: 3채널 기본 설정
- [ ] `.env` + `requirements.txt` 세팅
- [ ] `main.py`: CLI `python main.py --topic "주제" --channel knowledge`

### 완료 기준
```
$ python src/main.py --topic "ChatGPT 활용법" --channel knowledge
→ assets/outputs/knowledge/2026-03-26/video.mp4 생성
```

---

## Phase 2 — 품질 개선

- [ ] `subtitle_gen.py`: `faster-whisper`로 단어 단위 자막 타임스탬프
- [ ] Editor에 Ken Burns 효과 (이미지 줌인/줌아웃 패닝)
- [ ] Pexels API 연동 (`asset_manager.py`)
- [ ] 인트로/아웃트로 클립 자동 삽입
- [ ] `job_tracker.py`: SQLite 기반 Job 상태 추적
- [ ] 로깅 시스템 (`utils/logger.py`)

---

## Phase 3 — 자동화

- [ ] `trend_finder.py`: pytrends + RSS 기반 주제 자동 발굴
- [ ] `scheduler.py`: APScheduler로 채널별 시간대 자동 실행
- [ ] `uploader.py`: YouTube Data API v3 자동 업로드
- [ ] 썸네일 자동 생성 및 업로드
- [ ] 예약 업로드 (`publishAt` 파라미터)

---

## Phase 4 — 분석 & 최적화

- [ ] YouTube Analytics API 데이터 수집
- [ ] 성과 지표(조회수, CTR, 시청 지속시간) DB 저장
- [ ] 고성과 영상 패턴 분석 → 프롬프트 자동 개선
- [ ] 제목/썸네일 A/B 테스트 자동화
- [ ] 대시보드 (Streamlit 또는 간단한 HTML 리포트)

---

## 기술 부채 관리

각 Phase 완료 후 다음을 검토:
1. 하드코딩된 값이 설정 파일로 이동되었는가
2. API 키가 `.env`에만 존재하는가
3. 단위 테스트가 핵심 모듈에 존재하는가
