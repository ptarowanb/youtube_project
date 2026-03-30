from pathlib import Path

import pytest

from src.config_loader import (
    ChannelConfigError,
    get_active_channels,
    load_channel_config,
)


CONFIG_PATH = Path("configs/channel_settings.yaml")


def test_load_channel_config_merges_defaults():
    config = load_channel_config("knowledge", config_path=CONFIG_PATH)

    assert config["display_name"] == "지식채널"
    assert config["enabled"] is True
    assert config["font"] == "NanumSquareRound.ttf"
    assert config["format"] == "longform"


def test_get_active_channels_returns_enabled_channel_ids():
    assert get_active_channels(config_path=CONFIG_PATH) == [
        "knowledge",
        "mystery",
        "healing",
    ]


def test_load_channel_config_raises_for_unknown_channel():
    with pytest.raises(ChannelConfigError, match="Unknown channel"):
        load_channel_config("unknown", config_path=CONFIG_PATH)


def test_load_channel_config_raises_for_disabled_channel(tmp_path: Path):
    config_path = tmp_path / "channel_settings.yaml"
    config_path.write_text(
        """
defaults:
  enabled: true
channels:
  quiet:
    enabled: false
    display_name: "조용한채널"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ChannelConfigError, match="disabled"):
        load_channel_config("quiet", config_path=config_path)
