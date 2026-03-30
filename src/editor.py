from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import ScriptPayload


def _validate_segment_audio_count(
    script_payload: ScriptPayload,
    audio_paths: list[Path],
) -> None:
    if len(script_payload.segments) != len(audio_paths):
        raise ValueError(
            "Segment and audio count mismatch: "
            f"{len(script_payload.segments)} segments vs {len(audio_paths)} audio files."
        )


def _plan_output_path(script_payload: ScriptPayload, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "video.mp4"


def _build_clip_plan(
    script_payload: ScriptPayload,
    audio_paths: list[Path],
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for segment, audio_path in zip(script_payload.segments, audio_paths):
        plan.append(
            {
                "segment_id": segment.id,
                "segment_text": segment.text,
                "audio_path": str(audio_path),
                "duration_hint": segment.duration_hint,
            }
        )
    return plan


def _write_dry_run_payload(
    output_path: Path,
    script_payload: ScriptPayload,
    audio_paths: list[Path],
    channel_config: dict[str, Any],
) -> Path:
    clip_plan = _build_clip_plan(script_payload, audio_paths)
    manifest_path = output_path.with_suffix(".json")
    manifest_path.write_text(
        json.dumps(
            {
                "dry_run": True,
                "output_path": str(output_path),
                "channel": script_payload.channel,
                "segments": len(script_payload.segments),
                "clip_plan": clip_plan,
                "channel_config": channel_config,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    output_path.write_bytes(b"")
    return output_path


def _render_placeholder(output_path: Path, script_payload: ScriptPayload) -> Path:
    output_path.write_bytes(
        f"placeholder video for: {script_payload.title}".encode("utf-8")
    )
    return output_path


def _compose_with_moviepy(
    script_payload: ScriptPayload,
    audio_paths: list[Path],
    channel_config: dict[str, Any],
    output_path: Path,
) -> Path:
    try:
        from moviepy.editor import AudioFileClip, ColorClip, CompositeVideoClip, TextClip  # type: ignore
    except Exception:  # pragma: no cover - optional dependency fallback path
        _render_placeholder(output_path, script_payload)
        return output_path

    resolution = tuple(channel_config.get("resolution", [1920, 1080]))
    width, height = resolution

    clips = []
    for idx, segment in enumerate(script_payload.segments):
        duration_hint = max(1, int(segment.duration_hint))
        bg = ColorClip(size=(width, height), color=(30, 30, 30), duration=duration_hint)
        txt = (
            TextClip(
                txt=segment.text,
                fontsize=channel_config.get("font_size", 42),
                color=channel_config.get("font_color", "white"),
                size=(width, height),
                method="caption",
            )
            .set_position("center")
            .set_duration(duration_hint)
        )
        clips.append(CompositeVideoClip([bg, txt]).set_start(sum(
            max(1, int(s.duration_hint))
            for s in script_payload.segments[:idx]
        )))

    video = CompositeVideoClip(clips).set_duration(
        sum(max(1, int(segment.duration_hint)) for segment in script_payload.segments)
    )

    if audio_paths:
        audio_clip = AudioFileClip(str(audio_paths[0]))
        video = video.set_audio(audio_clip)

    video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    video.close()
    for clip in clips:
        clip.close()
    if audio_paths:
        audio_clip.close()  # type: ignore[name-defined]
    return output_path


def compose_video(
    script_payload: ScriptPayload,
    audio_paths: list[Path],
    channel_config: dict[str, Any],
    output_dir: Path,
    dry_run: bool = False,
) -> Path:
    output_dir = Path(output_dir)
    _validate_segment_audio_count(script_payload, audio_paths)
    output_path = _plan_output_path(script_payload, output_dir)

    if dry_run:
        return _write_dry_run_payload(output_path, script_payload, audio_paths, channel_config)

    if not audio_paths:
        raise ValueError("At least one audio path is required to compose a video.")

    try:
        return _compose_with_moviepy(script_payload, audio_paths, channel_config, output_path)
    except Exception:
        return _render_placeholder(output_path, script_payload)
