from pathlib import Path

import pytest

from src.uploader import (
    build_upload_request_body,
    parse_publish_at,
    upload_video,
)


def test_build_upload_request_body_includes_visibility_and_metadata():
    body = build_upload_request_body(
        metadata={
            "title": "테스트 제목",
            "description": "설명",
            "tags": ["chatgpt", "ai"],
            "visibility": "private",
        }
    )

    assert body["snippet"]["title"] == "테스트 제목"
    assert body["snippet"]["description"] == "설명"
    assert body["snippet"]["tags"] == ["chatgpt", "ai"]
    assert body["status"]["privacyStatus"] == "private"


def test_build_upload_request_body_adds_publish_at_when_scheduled():
    scheduled = parse_publish_at("2026-03-31 09:00")

    body = build_upload_request_body(
        metadata={
            "title": "테스트 제목",
            "description": "설명",
            "tags": [],
            "visibility": "private",
        },
        schedule_time=scheduled,
    )

    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"].endswith("Z")


def test_upload_video_raises_when_client_secret_is_missing(tmp_path: Path):
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"video")

    with pytest.raises(FileNotFoundError):
        upload_video(
            video_path=video_path,
            metadata={"title": "테스트", "description": "", "tags": []},
            channel_config={
                "youtube_client_secret_path": str(tmp_path / "missing-client-secret.json"),
                "youtube_token_path": str(tmp_path / "token.json"),
            },
        )
