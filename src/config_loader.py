from __future__ import annotations

from pathlib import Path

import yaml

from src.utils.validators import is_channel_enabled


DEFAULT_CONFIG_PATH = Path("configs/channel_settings.yaml")


class ChannelConfigError(ValueError):
    """Raised when channel configuration cannot be resolved."""


def _load_raw_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    raw.setdefault("defaults", {})
    raw.setdefault("channels", {})
    return raw


def load_channel_config(channel: str, config_path: Path | None = None) -> dict:
    raw = _load_raw_config(config_path)
    defaults = raw["defaults"]
    channel_config = raw["channels"].get(channel)
    if channel_config is None:
        raise ChannelConfigError(f"Unknown channel: '{channel}'")
    if not is_channel_enabled(channel_config, defaults):
        raise ChannelConfigError(f"Channel '{channel}' is disabled.")
    return {**defaults, **channel_config}


def get_active_channels(config_path: Path | None = None) -> list[str]:
    raw = _load_raw_config(config_path)
    defaults = raw["defaults"]
    return [
        channel_name
        for channel_name, channel_config in raw["channels"].items()
        if is_channel_enabled(channel_config, defaults)
    ]


def get_all_channels(config_path: Path | None = None) -> list[str]:
    raw = _load_raw_config(config_path)
    return list(raw["channels"].keys())
