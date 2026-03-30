from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScriptSegment:
    id: int
    text: str
    image_prompt: str
    duration_hint: int


@dataclass(slots=True)
class ScriptPayload:
    title: str
    description: str
    channel: str
    format: str
    segments: list[ScriptSegment] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    thumbnail_prompt: str = ""
