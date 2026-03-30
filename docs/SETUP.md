# 개발 환경 설정 가이드

## 사전 요구사항

- Python 3.10+
- ffmpeg (MoviePy 백엔드)
  ```bash
  # Windows (winget)
  winget install ffmpeg
  # macOS
  brew install ffmpeg
  ```

## 설치

```bash
git clone <repo>
cd youtube_automation
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## requirements.txt (전체)

```
openai>=1.0.0
edge-tts>=6.1.0
faster-whisper>=0.10.0
moviepy>=2.0.0
pydub>=0.25.0
requests>=2.31.0
python-dotenv>=1.0.0
pyyaml>=6.0
pytrends>=4.9.0
apscheduler>=3.10.0
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
```

## .env 설정

```env
OPENAI_API_KEY=sk-...
PEXELS_API_KEY=...
YOUTUBE_CLIENT_SECRET_PATH=configs/client_secret.json
```

## YouTube API OAuth 설정

1. Google Cloud Console에서 프로젝트 생성
2. YouTube Data API v3 활성화
3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. `client_secret.json` 다운로드 → `configs/` 폴더에 저장
5. 최초 실행 시 브라우저 인증 → `token.json` 자동 저장

## 실행 방법

```bash
# 특정 채널로 단일 영상 생성
python src/main.py --topic "ChatGPT 활용법 5가지" --channel knowledge

# 현재 활성화된 모든 채널에 동일 주제로 영상 생성
python src/main.py --topic "2026 재테크 트렌드" --all-channels

# 활성 채널 목록 확인
python src/main.py --list-channels

# 자동 스케줄러 시작 (활성 채널 전체 자동 처리)
python src/scheduler.py
```

## 채널 운영 조정 방법

코드를 전혀 건드리지 않고 `configs/channel_settings.yaml`만 수정:

```yaml
# 채널 비활성화 (일시 중단)
mystery:
  enabled: false   # 이것만 바꾸면 스케줄러가 자동으로 제외

# 새 채널 추가 (항목 추가 후 스케줄러 재시작)
finance:
  enabled: true
  display_name: "재테크채널"
  voice: ko-KR-InJoonNeural
  format: longform
  ...
```

스케줄러를 재시작하면 변경 사항이 즉시 반영된다.
