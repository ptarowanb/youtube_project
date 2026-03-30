from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import ScriptPayload
from src.utils.fonts import DEFAULT_FONT_SEARCH_DIRS, resolve_font_path


_FONT_SEARCH_DIRS = list(DEFAULT_FONT_SEARCH_DIRS)


def _resolve_font_path(channel_config: dict[str, Any]) -> str | None:
    return resolve_font_path(channel_config, search_dirs=_FONT_SEARCH_DIRS)


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


def _load_moviepy_bindings() -> dict[str, Any]:
    from moviepy import (
        AudioFileClip,
        ColorClip,
        CompositeVideoClip,
        ImageClip,
        TextClip,
        concatenate_videoclips,
    )

    return {
        "AudioFileClip": AudioFileClip,
        "ColorClip": ColorClip,
        "CompositeVideoClip": CompositeVideoClip,
        "ImageClip": ImageClip,
        "TextClip": TextClip,
        "concatenate_videoclips": concatenate_videoclips,
    }


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
    raise RuntimeError(f"Video rendering failed for '{script_payload.title}'.")


def _compose_with_moviepy(
    script_payload: ScriptPayload,
    audio_paths: list[Path],
    channel_config: dict[str, Any],
    output_path: Path,
    asset_paths: list[Path] | None = None,
) -> Path:
    try:
        bindings = _load_moviepy_bindings()
    except Exception:  # pragma: no cover - optional dependency fallback path
        raise RuntimeError("MoviePy is unavailable or could not be imported.")

    AudioFileClip = bindings["AudioFileClip"]
    ColorClip = bindings["ColorClip"]
    CompositeVideoClip = bindings["CompositeVideoClip"]
    ImageClip = bindings.get("ImageClip")
    TextClip = bindings["TextClip"]
    concatenate_videoclips = bindings["concatenate_videoclips"]

    resolution = tuple(channel_config.get("resolution", [1920, 1080]))
    width, height = resolution
    font_path = _resolve_font_path(channel_config)

    clips = []
    audio_clips = []

    for index, (segment, audio_path) in enumerate(zip(script_payload.segments, audio_paths)):
        audio_clip = AudioFileClip(str(audio_path))
        audio_clips.append(audio_clip)
        clip_duration = max(1, int(segment.duration_hint), int(getattr(audio_clip, "duration", 0) or 0))
        asset_path = None
        if asset_paths and index < len(asset_paths):
            asset_path = asset_paths[index]

        if asset_path and ImageClip and Path(asset_path).exists():
            bg = ImageClip(str(asset_path)).with_duration(clip_duration)
        else:
            bg = ColorClip(size=(width, height), color=(30, 30, 30)).with_duration(clip_duration)
        txt = (
            TextClip(
                text=segment.text,
                font=font_path,
                font_size=channel_config.get("font_size", 42),
                color=channel_config.get("font_color", "white"),
                size=(width, height),
                method="caption",
            )
            .with_position("center")
            .with_duration(clip_duration)
        )
        clip = CompositeVideoClip([bg, txt]).with_duration(clip_duration).with_audio(audio_clip)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
    video.close()
    for clip in clips:
        close = getattr(clip, "close", None)
        if callable(close):
            close()
    for audio_clip in audio_clips:
        audio_clip.close()
    return output_path


def compose_video(
    script_payload: ScriptPayload,
    audio_paths: list[Path],
    channel_config: dict[str, Any],
    output_dir: Path,
    dry_run: bool = False,
    asset_paths: list[Path] | None = None,
) -> Path:
    output_dir = Path(output_dir)
    _validate_segment_audio_count(script_payload, audio_paths)
    output_path = _plan_output_path(script_payload, output_dir)

    if dry_run:
        return _write_dry_run_payload(output_path, script_payload, audio_paths, channel_config)

    if not audio_paths:
        raise ValueError("At least one audio path is required to compose a video.")

    return _compose_with_moviepy(
        script_payload,
        audio_paths,
        channel_config,
        output_path,
        asset_paths=asset_paths,
    )
