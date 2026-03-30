from pathlib import Path

import pytest

from src.editor import compose_video
from src.models import ScriptPayload, ScriptSegment


def build_payload(segment_count: int = 2, title: str = "테스트 주제") -> ScriptPayload:
    return ScriptPayload(
        title=title,
        description="설명",
        channel="knowledge",
        format="shorts",
        segments=[
            ScriptSegment(
                id=index,
                text=f"{index}번째 세그먼트",
                image_prompt=f"prompt {index}",
                duration_hint=5,
            )
            for index in range(1, segment_count + 1)
        ],
        tags=["test"],
        thumbnail_prompt="thumbnail",
    )


def test_compose_video_rejects_mismatched_segment_and_audio_counts(tmp_path: Path):
    payload = build_payload(segment_count=2)
    output_dir = tmp_path
    audio_paths = [tmp_path / "audio_01.mp3"]

    with pytest.raises(ValueError, match="segment"):
        compose_video(payload, audio_paths, {}, output_dir, dry_run=True)


def test_compose_video_plans_output_under_output_dir(tmp_path: Path):
    payload = build_payload(segment_count=1)
    output_dir = tmp_path
    audio_path = tmp_path / "audio_01.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"")

    output_path = compose_video(payload, [audio_path], {"format": "shorts"}, output_dir, dry_run=True)

    assert output_path.exists()
    assert output_path.parent == output_dir
    assert output_path.suffix == ".mp4"


def test_compose_video_dry_run_is_lightweight(tmp_path: Path):
    payload = build_payload(segment_count=2, title="아침 루틴 루틴")
    output_dir = tmp_path
    audio_paths = [
        output_dir / "audio" / "segment_01.mp3",
        output_dir / "audio" / "segment_02.mp3",
    ]
    for path in audio_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")

    output_path = compose_video(payload, audio_paths, {"format": "shorts"}, output_dir, dry_run=True)
    metadata_path = output_path.with_suffix(".json")

    assert output_path.name == "video.mp4"
    assert output_path.exists()
    assert metadata_path.exists()
    assert "dry_run" in metadata_path.read_text(encoding="utf-8")
