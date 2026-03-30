from pathlib import Path
import subprocess
import sys

from src import main as main_module
from src.models import ScriptPayload, ScriptSegment


def build_payload(channel: str = "knowledge") -> ScriptPayload:
    return ScriptPayload(
        title="테스트 제목",
        description="설명",
        channel=channel,
        format="longform",
        segments=[
            ScriptSegment(
                id=1,
                text="첫 번째 세그먼트",
                image_prompt="prompt 1",
                duration_hint=10,
            )
        ],
        tags=["test"],
        thumbnail_prompt="thumb",
    )


def test_build_parser_reads_topic_and_channel():
    parser = main_module.build_parser()

    args = parser.parse_args(["--topic", "ChatGPT 활용법", "--channel", "knowledge"])

    assert args.topic == "ChatGPT 활용법"
    assert args.channel == "knowledge"
    assert args.all_channels is False


def test_build_parser_reads_script_file():
    parser = main_module.build_parser()

    args = parser.parse_args(["--script-file", "docs/examples/sample-script.md"])

    assert args.script_file == "docs/examples/sample-script.md"
    assert args.topic is None


def test_build_parser_reads_upload_overrides():
    parser = main_module.build_parser()

    args = parser.parse_args(
        [
            "--script-file",
            "docs/examples/sample-script.md",
            "--upload",
            "--visibility",
            "unlisted",
            "--publish-at",
            "2026-03-31 09:00",
        ]
    )

    assert args.upload is True
    assert args.visibility == "unlisted"
    assert args.publish_at == "2026-03-31 09:00"


def test_main_lists_channels(capsys):
    exit_code = main_module.main(["--list-channels"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "knowledge" in captured.out
    assert "mystery" in captured.out


def test_run_pipeline_calls_stages_in_order(tmp_path: Path, monkeypatch):
    call_order: list[str] = []
    payload = build_payload()
    fake_video_path = tmp_path / "video.mp4"

    def fake_load_channel_config(channel: str):
        call_order.append(f"load:{channel}")
        return {"display_name": "지식채널", "format": "longform"}

    def fake_generate_script(topic: str, channel: str, channel_config: dict):
        assert topic == "ChatGPT 활용법"
        assert channel == "knowledge"
        call_order.append("script")
        return payload

    def fake_save_script_payload(script_payload: ScriptPayload, output_dir: Path):
        assert script_payload is payload
        call_order.append("save")
        return output_dir / "script.json"

    def fake_fetch_assets(segments, channel_config: dict, output_dir: Path):
        assert segments == payload.segments
        call_order.append("assets")
        return [output_dir / "assets" / "segment_01.png"]

    def fake_generate_audio_segments(segments, channel_config: dict, output_dir: Path, provider=None):
        assert segments == payload.segments
        call_order.append("audio")
        return [output_dir / "audio" / "segment_01.mp3"]

    def fake_compose_video(script_payload, audio_paths, channel_config: dict, output_dir: Path, dry_run=False, asset_paths=None):
        assert script_payload is payload
        assert audio_paths == [output_dir / "audio" / "segment_01.mp3"]
        assert asset_paths == [output_dir / "assets" / "segment_01.png"]
        assert dry_run is False
        call_order.append("video")
        return fake_video_path

    monkeypatch.setattr(main_module, "load_channel_config", fake_load_channel_config)
    monkeypatch.setattr(main_module, "generate_script", fake_generate_script)
    monkeypatch.setattr(main_module, "save_script_payload", fake_save_script_payload)
    monkeypatch.setattr(main_module, "fetch_assets", fake_fetch_assets)
    monkeypatch.setattr(main_module, "generate_audio_segments", fake_generate_audio_segments)
    monkeypatch.setattr(main_module, "compose_video", fake_compose_video)

    result = main_module.run_pipeline(
        topic="ChatGPT 활용법",
        channel="knowledge",
        output_root=tmp_path,
    )

    assert result == fake_video_path
    assert call_order == ["load:knowledge", "script", "save", "assets", "audio", "video"]
    assert (tmp_path / "knowledge").exists()


def test_run_script_file_pipeline_uses_script_metadata_channel(tmp_path: Path, monkeypatch):
    call_order: list[str] = []
    payload = build_payload(channel="mystery")
    fake_video_path = tmp_path / "video.mp4"

    def fake_parse_manual_script_file(script_path: Path):
        assert script_path == Path("docs/examples/sample-script.md")
        call_order.append("parse")
        return payload

    def fake_load_channel_config(channel: str):
        assert channel == "mystery"
        call_order.append(f"load:{channel}")
        return {"display_name": "미스터리채널", "format": "shorts"}

    def fake_save_script_payload(script_payload: ScriptPayload, output_dir: Path):
        assert script_payload is payload
        call_order.append("save")
        return output_dir / "script.json"

    def fake_fetch_assets(segments, channel_config: dict, output_dir: Path):
        assert segments == payload.segments
        call_order.append("assets")
        return [output_dir / "assets" / "segment_01.png"]

    def fake_generate_audio_segments(segments, channel_config: dict, output_dir: Path, provider=None):
        assert segments == payload.segments
        call_order.append("audio")
        return [output_dir / "audio" / "segment_01.wav"]

    def fake_compose_video(script_payload, audio_paths, channel_config: dict, output_dir: Path, dry_run=False, asset_paths=None):
        assert script_payload is payload
        assert audio_paths == [output_dir / "audio" / "segment_01.wav"]
        assert asset_paths == [output_dir / "assets" / "segment_01.png"]
        call_order.append("video")
        return fake_video_path

    monkeypatch.setattr(main_module, "parse_manual_script_file", fake_parse_manual_script_file)
    monkeypatch.setattr(main_module, "load_channel_config", fake_load_channel_config)
    monkeypatch.setattr(main_module, "save_script_payload", fake_save_script_payload)
    monkeypatch.setattr(main_module, "fetch_assets", fake_fetch_assets)
    monkeypatch.setattr(main_module, "generate_audio_segments", fake_generate_audio_segments)
    monkeypatch.setattr(main_module, "compose_video", fake_compose_video)

    result = main_module.run_script_file_pipeline(
        script_path=Path("docs/examples/sample-script.md"),
        output_root=tmp_path,
    )

    assert result == fake_video_path
    assert call_order == ["parse", "load:mystery", "save", "assets", "audio", "video"]


def test_run_script_file_pipeline_uploads_with_cli_overrides(tmp_path: Path, monkeypatch):
    call_order: list[str] = []
    payload = build_payload(channel="knowledge")
    payload.visibility = "private"
    payload.publish_at = "2026-03-31 09:00"
    fake_video_path = tmp_path / "video.mp4"

    def fake_parse_manual_script_file(script_path: Path):
        call_order.append("parse")
        return payload

    def fake_load_channel_config(channel: str):
        call_order.append(f"load:{channel}")
        return {"display_name": "지식채널", "format": "longform"}

    def fake_save_script_payload(script_payload: ScriptPayload, output_dir: Path):
        call_order.append("save")
        return output_dir / "script.json"

    def fake_fetch_assets(segments, channel_config: dict, output_dir: Path):
        call_order.append("assets")
        return [output_dir / "assets" / "segment_01.png"]

    def fake_generate_audio_segments(segments, channel_config: dict, output_dir: Path, provider=None):
        call_order.append("audio")
        return [output_dir / "audio" / "segment_01.wav"]

    def fake_compose_video(script_payload, audio_paths, channel_config: dict, output_dir: Path, dry_run=False, asset_paths=None):
        call_order.append("video")
        assert asset_paths == [output_dir / "assets" / "segment_01.png"]
        return fake_video_path

    def fake_parse_publish_at(value: str):
        call_order.append(f"publish_at:{value}")
        return "PARSED"

    def fake_upload_video(video_path, metadata: dict, channel_config: dict, schedule_time=None):
        call_order.append("upload")
        assert video_path == fake_video_path
        assert metadata["visibility"] == "unlisted"
        assert metadata["title"] == payload.title
        assert schedule_time == "PARSED"
        return "video-id-123"

    monkeypatch.setattr(main_module, "parse_manual_script_file", fake_parse_manual_script_file)
    monkeypatch.setattr(main_module, "load_channel_config", fake_load_channel_config)
    monkeypatch.setattr(main_module, "save_script_payload", fake_save_script_payload)
    monkeypatch.setattr(main_module, "fetch_assets", fake_fetch_assets)
    monkeypatch.setattr(main_module, "generate_audio_segments", fake_generate_audio_segments)
    monkeypatch.setattr(main_module, "compose_video", fake_compose_video)
    monkeypatch.setattr(main_module, "parse_publish_at", fake_parse_publish_at)
    monkeypatch.setattr(main_module, "upload_video", fake_upload_video)

    result = main_module.run_script_file_pipeline(
        script_path=Path("docs/examples/sample-script.md"),
        output_root=tmp_path,
        upload=True,
        visibility_override="unlisted",
        publish_at_override="2026-04-01 10:00",
    )

    assert result == fake_video_path
    assert call_order == [
        "parse",
        "load:knowledge",
        "save",
        "assets",
        "audio",
        "video",
        "publish_at:2026-04-01 10:00",
        "upload",
    ]


def test_python_src_main_list_channels_smoke():
    completed = subprocess.run(
        [sys.executable, "src/main.py", "--list-channels"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "knowledge" in completed.stdout
