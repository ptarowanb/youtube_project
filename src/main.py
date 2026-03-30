from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

if __package__ in {None, ""}:  # Support `python src/main.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config_loader import get_active_channels, load_channel_config
from src.manual_script_parser import parse_manual_script_file
from src.scripter import generate_script, save_script_payload
from src.uploader import parse_publish_at, upload_video

try:
    from src.editor import compose_video
except ImportError:  # pragma: no cover - resolved once editor lands
    compose_video = None

try:
    from src.voice_gen import generate_audio_segments
except ImportError:  # pragma: no cover - resolved once voice_gen lands
    generate_audio_segments = None


DEFAULT_OUTPUT_ROOT = Path("assets/outputs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube automation CLI")
    parser.add_argument("--topic")
    parser.add_argument("--script-file")
    parser.add_argument("--channel")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--visibility")
    parser.add_argument("--publish-at")
    parser.add_argument("--all-channels", action="store_true")
    parser.add_argument("--list-channels", action="store_true")
    return parser


def _require_stage(stage_callable, stage_name: str):
    if stage_callable is None:
        raise RuntimeError(f"{stage_name} is not available yet.")
    return stage_callable


def _build_run_directory(output_root: Path, channel: str) -> Path:
    run_dir = output_root / channel / date.today().isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _build_upload_metadata(
    script_payload,
    visibility_override: str | None = None,
) -> dict:
    return {
        "title": script_payload.title,
        "description": script_payload.description,
        "tags": script_payload.tags,
        "visibility": visibility_override or script_payload.visibility or "private",
    }


def _maybe_upload_video(
    video_path: Path,
    script_payload,
    channel_config: dict,
    upload: bool,
    visibility_override: str | None = None,
    publish_at_override: str | None = None,
) -> None:
    if not upload:
        return

    metadata = _build_upload_metadata(
        script_payload,
        visibility_override=visibility_override,
    )
    publish_at_value = publish_at_override or script_payload.publish_at
    schedule_time = parse_publish_at(publish_at_value) if publish_at_value else None
    upload_video(
        video_path,
        metadata,
        channel_config,
        schedule_time=schedule_time,
    )


def run_pipeline(
    topic: str,
    channel: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    upload: bool = False,
    visibility_override: str | None = None,
    publish_at_override: str | None = None,
) -> Path:
    channel_config = load_channel_config(channel)
    run_dir = _build_run_directory(output_root, channel)

    script_payload = generate_script(
        topic=topic,
        channel=channel,
        channel_config=channel_config,
    )
    save_script_payload(script_payload, run_dir)

    audio_stage = _require_stage(generate_audio_segments, "voice generation")
    audio_paths = audio_stage(
        script_payload.segments,
        channel_config,
        run_dir,
    )

    video_stage = _require_stage(compose_video, "video composition")
    video_path = video_stage(
        script_payload,
        audio_paths,
        channel_config,
        run_dir,
    )
    _maybe_upload_video(
        video_path,
        script_payload,
        channel_config,
        upload=upload,
        visibility_override=visibility_override,
        publish_at_override=publish_at_override,
    )
    return video_path


def run_script_file_pipeline(
    script_path: Path,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    upload: bool = False,
    visibility_override: str | None = None,
    publish_at_override: str | None = None,
) -> Path:
    script_payload = parse_manual_script_file(Path(script_path))
    channel = script_payload.channel
    channel_config = load_channel_config(channel)
    run_dir = _build_run_directory(output_root, channel)

    save_script_payload(script_payload, run_dir)

    audio_stage = _require_stage(generate_audio_segments, "voice generation")
    audio_paths = audio_stage(
        script_payload.segments,
        channel_config,
        run_dir,
    )

    video_stage = _require_stage(compose_video, "video composition")
    video_path = video_stage(
        script_payload,
        audio_paths,
        channel_config,
        run_dir,
    )
    _maybe_upload_video(
        video_path,
        script_payload,
        channel_config,
        upload=upload,
        visibility_override=visibility_override,
        publish_at_override=publish_at_override,
    )
    return video_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_channels:
        for channel in get_active_channels():
            print(channel)
        return 0

    if args.script_file:
        run_script_file_pipeline(
            Path(args.script_file),
            upload=args.upload,
            visibility_override=args.visibility,
            publish_at_override=args.publish_at,
        )
        return 0

    if not args.topic:
        parser.error("--topic is required unless --list-channels or --script-file is used")

    if args.all_channels:
        for channel in get_active_channels():
            run_pipeline(
                args.topic,
                channel,
                upload=args.upload,
                visibility_override=args.visibility,
                publish_at_override=args.publish_at,
            )
        return 0

    if not args.channel:
        parser.error("--channel is required unless --all-channels is used")

    run_pipeline(
        args.topic,
        args.channel,
        upload=args.upload,
        visibility_override=args.visibility,
        publish_at_override=args.publish_at,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
