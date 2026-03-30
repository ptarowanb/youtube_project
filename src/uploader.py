from __future__ import annotations

from datetime import datetime
from pathlib import Path


def upload_video(
    video_path: Path,
    metadata: dict,
    channel_config: dict,
    schedule_time: datetime | None = None,
) -> str:
    raise NotImplementedError("YouTube upload is planned for a later phase.")
