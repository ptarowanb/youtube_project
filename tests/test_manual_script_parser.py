from pathlib import Path

import pytest

from src.manual_script_parser import parse_manual_script_file, parse_manual_script_text


SAMPLE_TEXT = """# Video Script Form

## Meta
channel: knowledge
title: ChatGPT를 실무에 활용하는 5가지 방법
video_type: longform
visibility: private
publish_at: 2026-03-31 09:00
tags:
- chatgpt
- ai

## Description
이 영상에서는 ChatGPT를 실무에 적용하는 기본 패턴을 간단하고 명확하게 설명합니다.

## Segments

### Segment 1
narration: ChatGPT는 검색 도구라기보다 초안 작성과 정리에 강한 업무 보조 도구입니다.
visual_hint: 사무실 책상, 노트북 화면, 생산성 있는 분위기
duration_hint: 8

### Segment 2
narration: 첫 번째 활용법은 회의록이나 메모를 빠르게 정리 가능한 초안으로 바꾸는 것입니다.
visual_hint: 회의실, 메모, 팀 협업 장면
duration_hint: 7
"""


def test_parse_manual_script_text_returns_script_payload():
    payload = parse_manual_script_text(SAMPLE_TEXT)

    assert payload.channel == "knowledge"
    assert payload.title == "ChatGPT를 실무에 활용하는 5가지 방법"
    assert payload.format == "longform"
    assert payload.visibility == "private"
    assert payload.publish_at == "2026-03-31 09:00"
    assert payload.tags == ["chatgpt", "ai"]
    assert len(payload.segments) == 2
    assert payload.segments[0].image_prompt == "사무실 책상, 노트북 화면, 생산성 있는 분위기"
    assert payload.segments[1].duration_hint == 7


def test_parse_manual_script_file_reads_utf8_file(tmp_path: Path):
    script_path = tmp_path / "script.md"
    script_path.write_text(SAMPLE_TEXT, encoding="utf-8")

    payload = parse_manual_script_file(script_path)

    assert payload.description.startswith("이 영상에서는")
    assert payload.segments[0].id == 1
    assert payload.segments[1].id == 2


@pytest.mark.parametrize(
    "broken_text",
    [
        SAMPLE_TEXT.replace("title: ChatGPT를 실무에 활용하는 5가지 방법\n", ""),
        SAMPLE_TEXT.replace("channel: knowledge\n", ""),
        SAMPLE_TEXT.split("## Segments")[0],
    ],
)
def test_parse_manual_script_text_rejects_missing_required_sections(broken_text: str):
    with pytest.raises(ValueError):
        parse_manual_script_text(broken_text)
