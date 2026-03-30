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

    def fake_generate_audio_segments(segments, channel_config: dict, output_dir: Path, provider=None):
        assert segments == payload.segments
        call_order.append("audio")
        return [output_dir / "audio" / "segment_01.mp3"]

    def fake_compose_video(script_payload, audio_paths, channel_config: dict, output_dir: Path, dry_run=False):
        assert script_payload is payload
        assert audio_paths == [output_dir / "audio" / "segment_01.mp3"]
        assert dry_run is False
        call_order.append("video")
        return fake_video_path

    monkeypatch.setattr(main_module, "load_channel_config", fake_load_channel_config)
    monkeypatch.setattr(main_module, "generate_script", fake_generate_script)
    monkeypatch.setattr(main_module, "save_script_payload", fake_save_script_payload)
    monkeypatch.setattr(main_module, "generate_audio_segments", fake_generate_audio_segments)
    monkeypatch.setattr(main_module, "compose_video", fake_compose_video)

    result = main_module.run_pipeline(
        topic="ChatGPT 활용법",
        channel="knowledge",
        output_root=tmp_path,
    )

    assert result == fake_video_path
    assert call_order == ["load:knowledge", "script", "save", "audio", "video"]
    assert (tmp_path / "knowledge").exists()


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
