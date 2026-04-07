# YouTube Automation

문서 초안 상태에서 시작한 워크스페이스를 Phase 1 MVP 기준으로 부트스트랩한 프로젝트다.

## 목표

- 채널 설정 기반으로 주제를 입력받아
- 스크립트를 만들고
- 세그먼트별 오디오를 만들고
- 기본 자막이 포함된 영상을 렌더링한다

## 구조

- `src/`: 파이프라인 코드
- `configs/`: 채널 설정과 프롬프트
- `assets/`: 렌더 산출물과 임시 파일
- `database/`: 향후 Job DB 위치
- `tests/`: pytest 테스트

## 실행

```powershell
python src/main.py --list-channels
python src/main.py --topic "ChatGPT 활용법" --channel knowledge
python src/main.py --script-file docs/examples/sample-script.md
```

## 수동 원고 입력

- 표준 입력 폼: `docs/manual-script-form.md`
- 예시 파일: `docs/examples/sample-script.md`
- 원고를 수동으로 준비할 때는 `--script-file` 경로를 사용한다.

## 현재 단계

- Phase 1 구현 진행 중
- OpenAI, edge-tts, ffmpeg가 없더라도 개발용 fallback 경로를 유지하는 방향으로 구현한다

## automation 배포

- `automation`은 별도 Python/ffmpeg 컨테이너로 배포한다.
- GitHub Actions가 `main` push 시 Docker 이미지를 빌드해 ECR `project1`에 push한다.
- 이어서 ECS cluster `n8n`의 service `automation`을 새 task revision으로 롤링 업데이트한다.
- 이후 `automation` 서비스의 task revision 이동은 GitHub Actions가 맡고, Terraform은 기본 인프라와 초기 bootstrap만 담당한다.
- GitHub repository secrets에는 최소한 아래 두 개가 필요하다.
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
