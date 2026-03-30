# 시스템 아키텍처 상세 설계

## 파이프라인 설계 원칙

1. **단일 책임**: 각 모듈은 하나의 역할만 담당
2. **실패 격리**: 한 단계 실패가 전체 파이프라인을 중단하지 않음
3. **재시도 가능**: 모든 단계는 멱등성(idempotent) 유지 — 같은 Job을 두 번 실행해도 안전
4. **설정 주도**: 채널별 동작 차이는 코드가 아닌 YAML 설정으로 제어
5. **채널 무한 확장**: 채널 수는 코드에 하드코딩하지 않음 — YAML 항목 수가 곧 운영 채널 수

---

## 모듈 인터페이스

### scripter.py

```python
def generate_script(topic: str, channel: str) -> dict:
    """
    Returns:
        {
            "title": str,
            "description": str,
            "segments": [{"id": int, "text": str, "image_prompt": str}],
            "tags": list[str],
            "thumbnail_prompt": str
        }
    """
```

### voice_gen.py

```python
async def generate_audio(segment: dict, channel_config: dict, output_dir: Path) -> Path:
    """
    Returns: Path to generated .mp3 file
    """
```

### subtitle_gen.py

```python
def extract_timestamps(audio_path: Path) -> list[dict]:
    """
    Returns:
        [{"word": str, "start": float, "end": float}, ...]
    """
```

### asset_manager.py

```python
def fetch_assets(segments: list[dict], channel_config: dict, output_dir: Path) -> list[Path]:
    """
    Returns: List of image/video file paths (1 per segment)
    """
```

### editor.py

```python
def compose_video(
    segments: list[dict],
    audio_paths: list[Path],
    asset_paths: list[Path],
    timestamps: list[dict],
    channel_config: dict,
    output_path: Path
) -> Path:
    """
    Returns: Path to final .mp4 file
    """
```

### uploader.py

```python
def upload_video(
    video_path: Path,
    metadata: dict,
    channel_config: dict,
    schedule_time: datetime | None = None
) -> str:
    """
    Returns: YouTube video ID
    """
```

---

## Job 상태 머신

```
PENDING → SCRIPTING → VOICING → EDITING → UPLOADING → DONE
                                                   ↓
                                                FAILED (어느 단계에서든)
```

각 상태 전환 시 `jobs.db`에 타임스탬프와 에러 메시지 기록.

---

## 병렬 처리 전략

Voice Gen과 Asset Manager는 동일 세그먼트 데이터를 입력으로 받아 독립적으로 동작 → **병렬 실행 가능**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def run_pipeline(script: dict, config: dict):
    with ThreadPoolExecutor() as executor:
        # Voice Gen과 Asset Fetch 병렬 실행
        audio_task = asyncio.get_event_loop().run_in_executor(
            executor, generate_all_audio, script, config
        )
        asset_task = asyncio.get_event_loop().run_in_executor(
            executor, fetch_all_assets, script, config
        )
        audio_paths, asset_paths = await asyncio.gather(audio_task, asset_task)

    # Editor는 두 결과를 받아 순차 실행
    timestamps = extract_timestamps(audio_paths)
    video_path = compose_video(script, audio_paths, asset_paths, timestamps, config)
    return video_path
```

---

## 설정 로딩 패턴 (동적 채널 지원)

채널 수가 바뀌어도 코드 수정이 필요 없도록, 설정 로더가 YAML을 동적으로 읽고 `defaults`를 각 채널에 병합한다.

```python
# src/config_loader.py
import yaml
from pathlib import Path

_CONFIG_PATH = Path("configs/channel_settings.yaml")

def _load_raw() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)

def load_channel_config(channel: str) -> dict:
    """특정 채널 설정 반환 (defaults 자동 병합)"""
    raw = _load_raw()
    defaults = raw.get("defaults", {})
    channel_cfg = raw["channels"].get(channel)
    if channel_cfg is None:
        raise ValueError(f"Unknown channel: '{channel}'. Check channel_settings.yaml")
    return {**defaults, **channel_cfg}  # 채널 값이 defaults를 override

def get_active_channels() -> list[str]:
    """enabled: true인 채널 ID 목록만 반환"""
    raw = _load_raw()
    return [
        name
        for name, cfg in raw["channels"].items()
        if cfg.get("enabled", raw.get("defaults", {}).get("enabled", True))
    ]

def get_all_channels() -> list[str]:
    """비활성 포함 전체 채널 ID 목록"""
    raw = _load_raw()
    return list(raw["channels"].keys())
```

스케줄러는 `get_active_channels()`만 호출하면 되므로, 채널 추가/삭제/비활성화가 즉시 반영된다:

```python
# src/scheduler.py 핵심 로직
from config_loader import get_active_channels, load_channel_config

def schedule_all():
    for channel_id in get_active_channels():
        cfg = load_channel_config(channel_id)
        scheduler.add_job(
            run_pipeline,
            trigger="cron",
            hour=cfg["upload_schedule"].split(":")[0],
            minute=cfg["upload_schedule"].split(":")[1],
            args=[channel_id],
            id=channel_id,
            replace_existing=True,  # YAML 변경 후 재시작 시 자동 업데이트
        )
```

---

## 에러 핸들링 패턴

각 Worker는 동일한 패턴으로 에러를 처리:

```python
def run_step(job_id: str, step_name: str, func, *args):
    tracker.update_status(job_id, step_name)
    try:
        result = func(*args)
        return result
    except Exception as e:
        tracker.mark_failed(job_id, step_name, str(e))
        logger.error(f"[{job_id}] {step_name} failed: {e}")
        raise
```
