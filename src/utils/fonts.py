from __future__ import annotations

import os
from pathlib import Path


DEFAULT_FONT_SEARCH_DIRS = [
    Path("assets/fonts"),
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
]

KOREAN_FONT_FALLBACKS = [
    "malgun.ttf",
    "malgunbd.ttf",
    "NanumGothic.ttf",
    "NanumSquareRound.ttf",
    "batang.ttc",
    "gulim.ttc",
]


def resolve_font_path(
    channel_config: dict | None,
    *,
    search_dirs: list[Path] | None = None,
) -> str | None:
    configured_font = None
    if isinstance(channel_config, dict):
        configured_font = channel_config.get("font")

    font_names: list[str] = []
    if configured_font:
        font_names.append(str(configured_font))
    font_names.extend(
        fallback for fallback in KOREAN_FONT_FALLBACKS if fallback != configured_font
    )

    directories = list(search_dirs or DEFAULT_FONT_SEARCH_DIRS)

    for font_name in font_names:
        raw_path = Path(font_name)
        if raw_path.is_file():
            return str(raw_path.resolve())

        for directory in directories:
            candidate = directory / font_name
            if candidate.is_file():
                return str(candidate.resolve())

    return None
