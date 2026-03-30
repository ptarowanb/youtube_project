# Phase 1 Bootstrap Design

**Status:** Approved for initial implementation

**Goal**

문서-only 상태의 워크스페이스를, Phase 1 MVP를 실제로 실행할 수 있는 Python 프로젝트 골격으로 전환한다. 단, 이후 Phase 2~4 확장을 위해 파일 경계와 설정 구조는 처음부터 분리한다.

**Design Summary**

- 프로젝트 구조는 `src/`, `configs/`, `assets/`, `database/`, `tests/`를 기준으로 고정한다.
- Phase 1에서 실제 동작하는 경로는 `src/main.py`가 `config_loader`, `scripter`, `voice_gen`, `editor`를 순차 오케스트레이션하는 형태로 시작한다.
- 향후 확장 모듈인 `asset_manager`, `subtitle_gen`, `job_tracker`, `scheduler`, `uploader`는 지금 파일 경계와 인터페이스만 먼저 두고, 내부는 최소 스텁 또는 얇은 구현으로 남긴다.

**Why This Shape**

- `docs/PROJECT_OVERVIEW.md`와 `docs/ARCHITECTURE.md`는 이미 `src/` 기반 구조와 설정 주도 설계를 전제로 한다.
- 아직 코드가 없으므로 지금 모듈 경계를 잘 고정하는 편이, 나중에 기능이 늘어난 뒤 구조를 다시 뜯는 것보다 비용이 낮다.
- 다만 이벤트 큐, Redis, Celery 같은 실제 비동기 인프라는 현재 단계에서 과설계다. Phase 1은 동기식 파이프라인으로 시작하고 인터페이스만 확장 가능하게 둔다.

**Directory Layout**

```text
youtube_automation/
├── src/
│   ├── main.py
│   ├── config_loader.py
│   ├── models.py
│   ├── scripter.py
│   ├── voice_gen.py
│   ├── editor.py
│   ├── subtitle_gen.py
│   ├── asset_manager.py
│   ├── job_tracker.py
│   ├── scheduler.py
│   ├── uploader.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── validators.py
├── configs/
│   ├── channel_settings.yaml
│   └── prompts/
│       ├── knowledge.txt
│       ├── mystery.txt
│       └── healing.txt
├── assets/
│   ├── bgm/
│   ├── outputs/
│   └── temp/
├── database/
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

**Runtime Flow**

1. CLI entrypoint receives `--topic` and either `--channel` or `--all-channels`.
2. `config_loader.py` loads `configs/channel_settings.yaml`, merges `defaults`, and validates enabled channels.
3. `scripter.py` produces a normalized script payload and saves `script.json` under the run directory.
4. `voice_gen.py` converts each segment into audio files and returns ordered paths.
5. `editor.py` combines placeholder visuals, audio, and simple text subtitles into a single `.mp4`.
6. `main.py` writes all outputs under `assets/outputs/{channel}/{YYYY-MM-DD}/{run_id}/`.

**Phase 1 Scope**

- In scope
  - Config-driven multi-channel support
  - Structured script generation with a deterministic offline fallback
  - Segment audio generation
  - Basic MP4 rendering with static visual backgrounds and subtitles
  - CLI orchestration
  - Unit tests for config loading, script normalization, and pipeline orchestration
- Out of scope
  - Real asset sourcing from Pexels
  - Whisper word timestamps
  - Job DB persistence
  - Scheduler automation
  - YouTube upload

**Component Decisions**

`src/models.py`
- Keep shared typed structures here using `dataclass`es so modules exchange stable shapes from day one.

`src/scripter.py`
- Support two paths:
  - OpenAI path when `OPENAI_API_KEY` is present
  - Deterministic local fallback for development/testing when credentials are absent
- This avoids blocking basic CLI/tests on external credentials while preserving the intended production path.

`src/voice_gen.py`
- Prefer a provider abstraction:
  - Real provider: `edge-tts`
  - Fallback provider: generated silent or tone-based audio for tests/dev
- The CLI should stay runnable in constrained environments.

`src/editor.py`
- Use MoviePy with simple solid-color or generated title-card visuals for Phase 1.
- Do not implement Ken Burns or per-word karaoke yet.

`src/job_tracker.py`, `src/subtitle_gen.py`, `src/asset_manager.py`, `src/uploader.py`, `src/scheduler.py`
- Provide explicit public functions/classes and `NotImplementedError` or no-op placeholders where appropriate.
- This preserves future import paths and keeps follow-up work incremental.

**Data Contracts**

`ScriptSegment`
- `id: int`
- `text: str`
- `image_prompt: str`
- `duration_hint: int`

`ScriptPayload`
- `title: str`
- `description: str`
- `channel: str`
- `format: str`
- `segments: list[ScriptSegment]`
- `tags: list[str]`
- `thumbnail_prompt: str`

**Error Handling**

- Unknown channel: fail fast with clear CLI error.
- Disabled channel when explicitly requested: fail fast and explain the setting.
- Missing external dependency or credentials: either use documented fallback or raise a targeted setup error.
- Empty script or segment mismatch: fail before editor stage.

**Testing Strategy**

- `pytest` 기반.
- Pure logic first:
  - config merge/validation
  - script normalization
  - output path planning
- Integration-light tests:
  - pipeline orchestration with fake providers
- Avoid brittle media snapshot tests in Phase 1.

**Execution Notes**

- Current workspace is not a git repository, so worktree setup and commit checkpoints from the process skills cannot be applied yet.
- Implementation should still follow TDD locally and keep the file layout ready for later git initialization.
