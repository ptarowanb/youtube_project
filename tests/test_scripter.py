import json
from pathlib import Path

from src.config_loader import load_channel_config
from src.scripter import generate_script, save_script_payload


CONFIG_PATH = Path("configs/channel_settings.yaml")


def test_generate_script_returns_normalized_fallback_payload():
    channel_config = load_channel_config("knowledge", config_path=CONFIG_PATH)

    payload = generate_script(
        topic="ChatGPT 활용법",
        channel="knowledge",
        channel_config=channel_config,
        use_openai=False,
    )

    assert payload.title
    assert payload.channel == "knowledge"
    assert payload.format == "longform"
    assert len(payload.segments) >= 3
    assert [segment.id for segment in payload.segments] == [1, 2, 3]


def test_generate_script_reflects_topic_and_channel():
    channel_config = load_channel_config("mystery", config_path=CONFIG_PATH)

    payload = generate_script(
        topic="사라진 마을 이야기",
        channel="mystery",
        channel_config=channel_config,
        use_openai=False,
    )

    assert "사라진 마을 이야기" in payload.title
    assert payload.channel == "mystery"
    assert any("사라진 마을 이야기" in segment.text for segment in payload.segments)


def test_save_script_payload_writes_json(tmp_path: Path):
    channel_config = load_channel_config("healing", config_path=CONFIG_PATH)
    payload = generate_script(
        topic="아침 명상",
        channel="healing",
        channel_config=channel_config,
        use_openai=False,
    )

    output_path = save_script_payload(payload, tmp_path)

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_path.name == "script.json"
    assert written["channel"] == "healing"
    assert written["segments"][0]["id"] == 1
