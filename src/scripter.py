from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from src.models import ScriptPayload, ScriptSegment


PROMPTS_DIR = Path("configs/prompts")


def _load_prompt_template(channel: str) -> str:
    prompt_path = PROMPTS_DIR / f"{channel}.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return "Return structured JSON for the requested YouTube script."


def _build_fallback_payload(topic: str, channel: str, channel_config: dict) -> ScriptPayload:
    display_name = channel_config.get("display_name", channel)
    script_format = channel_config.get("format", "shorts")
    segments = [
        ScriptSegment(
            id=index,
            text=f"{topic}에 대한 {display_name} {index}번째 핵심 포인트입니다.",
            image_prompt=f"{topic}, {display_name}, scene {index}",
            duration_hint=6 if script_format == "shorts" else 20,
        )
        for index in range(1, 4)
    ]
    return ScriptPayload(
        title=f"{topic} | {display_name}",
        description=f"{display_name}에서 다루는 주제: {topic}",
        channel=channel,
        format=script_format,
        segments=segments,
        tags=[topic, channel, script_format],
        thumbnail_prompt=f"{topic} thumbnail for {display_name}",
    )


def _generate_with_openai(topic: str, channel: str, channel_config: dict) -> ScriptPayload:
    raise NotImplementedError(
        "OpenAI-backed structured output is not implemented yet. Use fallback mode."
    )


def generate_script(
    topic: str,
    channel: str,
    channel_config: dict,
    use_openai: bool = True,
) -> ScriptPayload:
    _load_prompt_template(channel)
    if use_openai and os.getenv("OPENAI_API_KEY"):
        return _generate_with_openai(topic, channel, channel_config)
    return _build_fallback_payload(topic, channel, channel_config)


def save_script_payload(payload: ScriptPayload, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "script.json"
    output_path.write_text(
        json.dumps(asdict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
