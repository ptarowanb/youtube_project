from __future__ import annotations

from pathlib import Path

from src.models import ScriptPayload, ScriptSegment


DEFAULT_DURATION_HINT = 8


def _split_sections(lines: list[str]) -> tuple[list[str], list[str], list[list[str]]]:
    meta_lines: list[str] = []
    description_lines: list[str] = []
    segment_blocks: list[list[str]] = []

    current_section: str | None = None
    current_segment: list[str] | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped == "## Meta":
            current_section = "meta"
            continue
        if stripped == "## Description":
            current_section = "description"
            continue
        if stripped == "## Segments":
            current_section = "segments"
            continue
        if stripped.startswith("### Segment "):
            current_section = "segments"
            if current_segment:
                segment_blocks.append(current_segment)
            current_segment = []
            continue

        if current_section == "meta":
            meta_lines.append(line)
        elif current_section == "description":
            description_lines.append(line)
        elif current_section == "segments" and current_segment is not None:
            current_segment.append(line)

    if current_segment:
        segment_blocks.append(current_segment)

    return meta_lines, description_lines, segment_blocks


def _parse_meta(meta_lines: list[str]) -> dict:
    meta: dict[str, object] = {"tags": []}
    parsing_tags = False

    for line in meta_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped == "tags:":
            parsing_tags = True
            continue

        if parsing_tags and stripped.startswith("- "):
            cast_tags = meta.setdefault("tags", [])
            cast_tags.append(stripped[2:].strip())
            continue

        parsing_tags = False
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip()] = value.strip()

    return meta


def _parse_segment(block: list[str], segment_id: int) -> ScriptSegment:
    fields: dict[str, str] = {}

    for line in block:
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        fields[key.strip()] = value.strip()

    narration = fields.get("narration")
    if not narration:
        raise ValueError(f"Segment {segment_id} is missing narration.")

    visual_hint = fields.get("visual_hint", narration)
    duration_hint = int(fields.get("duration_hint", DEFAULT_DURATION_HINT))

    return ScriptSegment(
        id=segment_id,
        text=narration,
        image_prompt=visual_hint,
        duration_hint=duration_hint,
    )


def parse_manual_script_text(text: str) -> ScriptPayload:
    lines = text.splitlines()
    meta_lines, description_lines, segment_blocks = _split_sections(lines)
    meta = _parse_meta(meta_lines)

    title = str(meta.get("title", "")).strip()
    channel = str(meta.get("channel", "")).strip()
    video_type = str(meta.get("video_type", "")).strip()
    description = "\n".join(line.strip() for line in description_lines if line.strip()).strip()

    if not title:
        raise ValueError("Manual script is missing title.")
    if not channel:
        raise ValueError("Manual script is missing channel.")
    if not video_type:
        raise ValueError("Manual script is missing video_type.")
    if not description:
        raise ValueError("Manual script is missing description.")
    if not segment_blocks:
        raise ValueError("Manual script must contain at least one segment.")

    segments = [
        _parse_segment(block, segment_id=index)
        for index, block in enumerate(segment_blocks, start=1)
    ]

    tags = [tag for tag in meta.get("tags", []) if tag]
    visibility = str(meta.get("visibility", "private") or "private").strip()
    publish_at = str(meta.get("publish_at", "")).strip() or None

    return ScriptPayload(
        title=title,
        description=description,
        channel=channel,
        format=video_type,
        segments=segments,
        tags=tags,
        thumbnail_prompt=f"{title} thumbnail",
        visibility=visibility,
        publish_at=publish_at,
    )


def parse_manual_script_file(path: Path) -> ScriptPayload:
    return parse_manual_script_text(Path(path).read_text(encoding="utf-8"))
