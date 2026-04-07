# AWS ECS n8n Terraform Design

**Date:** 2026-04-03

## Goal

이 프로젝트의 AWS 인프라를 Terraform으로 구성한다. `n8n` 자체와 Python 기반 영상 렌더 서비스 `automation`을 모두 ECS Fargate에 배포하고, `n8n`이 AI/TTS/이미지 생성과 업로드 워크플로우를 담당한 뒤 `automation`에는 최종 영상 합성만 요청하는 구조를 만든다.

## Confirmed Decisions

- 단일 환경만 운영한다. `dev/test/prod` 분리는 하지 않는다.
- AWS provider profile은 `runner`를 사용한다.
- ECS cluster 이름은 `n8n`으로 한다.
- 렌더 API ECS service 이름은 `automation`으로 한다.
- 렌더 API task family 이름은 `project1`으로 한다.
- `n8n`도 이번 Terraform 범위에 포함한다.
- 배포 방식은 `ALB + ECS Service + S3`를 기본으로 한다.
- `automation`은 동기식이 아니라 비동기식으로 동작한다.
- 결과 영상은 `S3`에 저장하고, YouTube 업로드는 `n8n` 워크플로우에서 처리한다.
- OpenAI, 이미지 생성, TTS 같은 외부 API 호출은 `n8n`에서 수행한다.
- `automation`은 Python + `ffmpeg` 기반 최종 합성 서비스로만 사용한다.
- `n8n` 메타데이터 저장소는 기존 RDS PostgreSQL 인스턴스를 사용한다.
- `n8n` DB 연결은 다음 값으로 구성한다.
  - Host: `runnerpoker-test.cmhs16pmizic.ap-northeast-2.rds.amazonaws.com`
  - Database: `n8n`
  - User: `runner_dev`
  - Schema: `public`
- DB 비밀번호와 런타임 인프라 비밀값은 Terraform 코드에 직접 넣지 않고 `Secrets Manager`를 통해 주입한다.

## Recommended Architecture

### 1. Public entrypoint

- 외부에 공개되는 진입점은 `Application Load Balancer` 하나로 둔다.
- `n8n` UI와 Webhook는 ALB를 통해 접근한다.
- `automation` 렌더 API는 외부에 직접 공개하지 않는다.

### 2. ECS services

- ECS Cluster: `n8n`
- ECS Service A: `n8n`
  - 역할: 웹 UI, Webhook, 워크플로우 엔진, 외부 API 오케스트레이션
  - Task family: `n8n`
- ECS Service B: `automation`
  - 역할: 렌더 요청 수신, Python + `ffmpeg` 기반 최종 영상 합성, 결과 저장, 상태 조회
  - Task family: `project1`

두 서비스는 같은 클러스터에 배치하되, 책임을 분리한다.

## Networking

### 1. Subnets

- ALB는 퍼블릭 서브넷에 둔다.
- ECS 태스크는 프라이빗 서브넷에 둔다.
- ECS 태스크에는 퍼블릭 IP를 붙이지 않는다.

### 2. Security groups

- ALB 보안 그룹
  - 인바운드: `80`, `443`
  - 아웃바운드: `n8n` 서비스 포트로 허용
- `n8n` ECS 보안 그룹
  - 인바운드: ALB에서 `n8n` 포트만 허용
  - 아웃바운드: RDS, 외부 API, 내부 `automation` 호출 허용
- `automation` ECS 보안 그룹
  - 인바운드: `n8n` 서비스 보안 그룹에서만 허용
  - 아웃바운드: S3 접근 허용

### 3. Internal service discovery

- `automation`은 외부 ALB에 연결하지 않는다.
- 내부 호출은 ECS Service Discovery 또는 Cloud Map을 사용해 `n8n`이 내부 DNS로 호출하도록 한다.
- 권장 내부 주소 예시:
  - `http://automation.n8n.local:<port>`

## Storage and Secrets

### 1. S3

- 공용 산출물 저장용 버킷 1개를 만든다.
- 저장 대상:
  - `n8n`이 만든 오디오, 이미지, 자막 같은 중간 산출물
  - 최종 mp4
  - 썸네일
  - 요청/응답 메타데이터 JSON
  - 로그 또는 산출물 보조 파일

### 2. RDS PostgreSQL

- `n8n`만 기존 RDS PostgreSQL을 사용한다.
- n8n 설정값:
  - `DB_TYPE=postgresdb`
  - `DB_POSTGRESDB_HOST=runnerpoker-test.cmhs16pmizic.ap-northeast-2.rds.amazonaws.com`
  - `DB_POSTGRESDB_PORT=5432`
  - `DB_POSTGRESDB_DATABASE=n8n`
  - `DB_POSTGRESDB_USER=runner_dev`
  - `DB_POSTGRESDB_SCHEMA=public`
- 비밀번호는 Secrets Manager에서 주입한다.

### 3. Secrets Manager

Secrets Manager에서 관리할 주요 값:

- `n8n` DB 비밀번호
- `N8N_ENCRYPTION_KEY`
- `AUTOMATION_SHARED_TOKEN`
- 필요 시 기타 인프라 런타임 비밀값

외부 AI/API 자격증명은 기본적으로 `n8n` credentials 저장소에서 관리한다. 즉 OpenAI, 이미지 생성, TTS 같은 값은 `automation` 서비스에 직접 주입하지 않는다.

## Runtime behavior

### 1. n8n responsibility

`n8n`은 오케스트레이터 역할을 수행한다.

- 스케줄 또는 외부 이벤트로 워크플로우 시작
- OpenAI, 이미지 생성, TTS 등 외부 API 호출
- 중간 산출물 `S3` 업로드
- `automation` API 호출
- 작업 상태 조회
- 완료 후 YouTube 업로드
- 실패 시 알림 또는 재시도 흐름 실행

### 2. automation responsibility

`automation`은 최종 렌더 엔진 역할을 수행한다.

- 렌더 요청 수신
- `job_id` 발급
- `S3`에서 오디오, 이미지, 자막, BGM 재료 다운로드
- Python 코드와 `ffmpeg`로 최종 영상 합성
- 결과물 `S3` 업로드
- 상태 조회 API 제공

## API contract

`automation`은 최소 다음 엔드포인트를 제공한다.

- `POST /render-jobs`
  - 렌더 요청 생성
  - 즉시 `job_id` 반환
- `GET /render-jobs/{id}`
  - 작업 상태 조회
- `GET /health`
  - ECS health check용

### Suggested render payload

`automation`에는 원본 파일을 직접 보내지 않고 `S3` 키 또는 URL만 전달한다.

예시:

```json
{
  "job_id": "job_123",
  "format": "shorts",
  "title": "sample",
  "audio_keys": ["jobs/job_123/audio/01.mp3"],
  "image_keys": ["jobs/job_123/images/01.png"],
  "subtitle_key": "jobs/job_123/subtitles/output.srt",
  "bgm_key": "shared/bgm/default.mp3",
  "output_prefix": "jobs/job_123/output/"
}
```

### Suggested job flow

1. `n8n`이 외부 API를 호출해 스크립트, 오디오, 이미지, 자막을 준비
2. 중간 산출물을 `S3`에 저장
3. `n8n`이 `POST /render-jobs` 호출
4. `automation`이 `job_id` 반환
5. `automation`이 내부 백그라운드 작업으로 렌더 수행
6. 완료 시 `S3`에 결과 저장
7. `n8n`이 `GET /render-jobs/{id}`를 반복 호출
8. 상태가 `done`이면 결과 S3 경로를 받아 YouTube 업로드

## n8n workflow shape

권장 워크플로우 순서는 다음과 같다.

1. Trigger
   - `Webhook` 또는 `Schedule Trigger`
2. Generate assets
   - OpenAI, 이미지 생성, TTS, 기타 MCP/API 노드 실행
3. Upload intermediates
   - 오디오, 이미지, 자막을 `S3`에 저장
4. Request render
   - `HTTP Request`로 `POST /render-jobs`
5. Wait
   - 일정 시간 대기
6. Poll status
   - `HTTP Request`로 `GET /render-jobs/{id}`
7. Branch
   - `IF`로 `done`, `failed`, `running` 분기
8. On done
   - 결과 S3 경로를 사용해 YouTube 업로드
9. On failed
   - 알림 또는 오류 워크플로우 분기

## Why not do final ffmpeg assembly inside n8n

`n8n` 내부에서 `ffmpeg` 최종 렌더까지 직접 수행하는 방식은 선택하지 않는다.

이유:

- `n8n` UI/엔진과 최종 렌더 실행 책임이 섞인다.
- `ffmpeg`, `moviepy` 같은 무거운 미디어 처리 작업이 `n8n` 안정성에 직접 영향을 준다.
- 장시간 작업과 장애 격리가 불리하다.
- 추후 렌더 API 단독 확장이나 디버깅이 어려워진다.

반대로 스크립트 생성, 이미지 생성, TTS, 업로드 같은 오케스트레이션 중심 작업은 `n8n`에서 수행하는 것이 맞다.

## Why not add queue mode now

`n8n`의 Redis queue mode는 이번 범위에서 제외한다.

이유:

- 현재 요구 수준에서는 ECS 서비스 2개와 RDS, S3만으로 충분하다.
- Redis와 별도 worker 구조를 추가하면 운영 복잡도가 커진다.
- 초기 목표는 빠르게 동작하는 단일 환경 인프라 구성이다.

## Terraform layout

단일 환경 기준으로 `terraform/` 루트 하나만 사용한다.

권장 파일 구성:

- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/networking.tf`
- `terraform/alb.tf`
- `terraform/ecr.tf`
- `terraform/iam.tf`
- `terraform/ecs.tf`
- `terraform/service-discovery.tf`
- `terraform/s3.tf`
- `terraform/secrets.tf`
- `terraform/cloudwatch.tf`
- `terraform/outputs.tf`
- `terraform/terraform.tfvars.example`
- `terraform/README.md`

## Risks and mitigations

### 1. Long render jobs

- HTTP 동기 요청으로 묶지 않는다.
- `job_id` 기반 비동기 처리로 분리한다.

### 2. Exposing automation API publicly

- 외부 ALB에 직접 연결하지 않는다.
- 내부 서비스 디스커버리와 shared token으로 보호한다.

### 3. Secret leakage

- DB 비밀번호와 인프라 비밀값은 코드에 넣지 않는다.
- Secrets Manager에서 ECS task secret으로 주입한다.

### 4. n8n persistence

- `n8n`은 SQLite 대신 기존 PostgreSQL을 사용한다.
- 워크플로우, 크리덴셜, 실행 기록을 안정적으로 유지한다.

## Final recommendation

이번 프로젝트는 다음 조합으로 시작하는 것이 가장 적절하다.

- ECS Fargate cluster `n8n`
- ECS service `n8n`
- ECS service `automation`
- Task family `n8n`
- Task family `project1`
- Public ALB
- Existing RDS PostgreSQL for n8n metadata
- Shared S3 bucket for intermediate and final assets
- Secrets Manager for runtime secrets
- CloudWatch Logs for logging

이 구조는 현재 요구사항을 충족하면서도, 이후 `n8n` 워크플로우 확장과 `automation` 렌더 엔진 고도화에 무리가 없다.
