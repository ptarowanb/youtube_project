from __future__ import annotations


def is_channel_enabled(channel_config: dict, defaults: dict | None = None) -> bool:
    merged_defaults = defaults or {}
    return channel_config.get("enabled", merged_defaults.get("enabled", True))
