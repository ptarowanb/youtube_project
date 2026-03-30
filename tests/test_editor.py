from pathlib import Path

import pytest

import src.editor as editor_module
from src.models import ScriptPayload, ScriptSegment


def build_payload(segment_count: int = 2, title: str = "테스트 주제") -> ScriptPayload:
    return ScriptPayload(
        title=title,
        description="설명",
        channel="knowledge",
        format="shorts",
        segments=[
            ScriptSegment(
                id=index,
                text=f"{index}번째 세그먼트",
                image_prompt=f"prompt {index}",
                duration_hint=5,
            )
            for index in range(1, segment_count + 1)
        ],
        tags=["test"],
        thumbnail_prompt="thumbnail",
    )


def test_compose_video_rejects_mismatched_segment_and_audio_counts(tmp_path: Path):
    payload = build_payload(segment_count=2)
    output_dir = tmp_path
    audio_paths = [tmp_path / "audio_01.mp3"]

    with pytest.raises(ValueError, match="segment"):
        editor_module.compose_video(payload, audio_paths, {}, output_dir, dry_run=True)


def test_compose_video_plans_output_under_output_dir(tmp_path: Path):
    payload = build_payload(segment_count=1)
    output_dir = tmp_path
    audio_path = tmp_path / "audio_01.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"")

    output_path = editor_module.compose_video(payload, [audio_path], {"format": "shorts"}, output_dir, dry_run=True)

    assert output_path.exists()
    assert output_path.parent == output_dir
    assert output_path.suffix == ".mp4"


def test_compose_video_dry_run_is_lightweight(tmp_path: Path):
    payload = build_payload(segment_count=2, title="아침 루틴 루틴")
    output_dir = tmp_path
    audio_paths = [
        output_dir / "audio" / "segment_01.wav",
        output_dir / "audio" / "segment_02.wav",
    ]
    for path in audio_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")

    output_path = editor_module.compose_video(payload, audio_paths, {"format": "shorts"}, output_dir, dry_run=True)
    metadata_path = output_path.with_suffix(".json")

    assert output_path.name == "video.mp4"
    assert output_path.exists()
    assert metadata_path.exists()
    assert "dry_run" in metadata_path.read_text(encoding="utf-8")


def test_compose_video_uses_all_audio_paths_when_rendering(tmp_path: Path, monkeypatch):
    payload = build_payload(segment_count=2)
    audio_paths = [
        tmp_path / "audio" / "segment_01.wav",
        tmp_path / "audio" / "segment_02.wav",
    ]
    for path in audio_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF0000")

    audio_calls: list[str] = []
    audio_close_calls: list[str] = []
    clip_audio_bindings: list[str] = []
    write_calls: list[str] = []

    class FakeAudioClip:
        def __init__(self, path: str):
            self.path = path
            self.duration = 2
            audio_calls.append(path)

        def close(self):
            audio_close_calls.append(self.path)

    class FakeVisualClip:
        def with_position(self, *_args, **_kwargs):
            return self

        def with_duration(self, _duration):
            return self

    class FakeCompositeClip(FakeVisualClip):
        def __init__(self, _clips):
            self.audio_path = None

        def with_audio(self, audio_clip):
            self.audio_path = audio_clip.path
            clip_audio_bindings.append(audio_clip.path)
            return self

    class FakeFinalClip:
        def __init__(self, clips):
            self.clips = clips

        def write_videofile(self, path: str, fps: int, codec: str, audio_codec: str):
            write_calls.append(path)
            Path(path).write_bytes(b"video")

        def close(self):
            return None

    def fake_bindings():
        def fake_color_clip(*_args, **_kwargs):
            return FakeVisualClip()

        def fake_text_clip(*_args, **_kwargs):
            return FakeVisualClip()

        def fake_concatenate_videoclips(clips, method="compose"):
            assert method == "compose"
            return FakeFinalClip(clips)

        return {
            "AudioFileClip": FakeAudioClip,
            "ColorClip": fake_color_clip,
            "CompositeVideoClip": FakeCompositeClip,
            "TextClip": fake_text_clip,
            "concatenate_videoclips": fake_concatenate_videoclips,
        }

    monkeypatch.setattr(editor_module, "_load_moviepy_bindings", fake_bindings)

    output_path = editor_module.compose_video(
        payload,
        audio_paths,
        {"format": "shorts", "resolution": [1080, 1920]},
        tmp_path,
        dry_run=False,
    )

    assert output_path.exists()
    assert output_path.name == "video.mp4"
    assert audio_calls == [str(audio_paths[0]), str(audio_paths[1])]
    assert clip_audio_bindings == [str(audio_paths[0]), str(audio_paths[1])]
    assert audio_close_calls == [str(audio_paths[0]), str(audio_paths[1])]
    assert write_calls == [str(output_path)]


def test_resolve_font_path_falls_back_to_korean_capable_font(tmp_path: Path, monkeypatch):
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    fallback_font = fonts_dir / "malgun.ttf"
    fallback_font.write_bytes(b"font")

    monkeypatch.setattr(editor_module, "_FONT_SEARCH_DIRS", [fonts_dir])

    resolved = editor_module._resolve_font_path({"font": "NanumSquareRound.ttf"})

    assert resolved == str(fallback_font)


def test_compose_video_passes_resolved_font_to_text_clip(tmp_path: Path, monkeypatch):
    payload = build_payload(segment_count=1)
    audio_path = tmp_path / "audio" / "segment_01.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"RIFF0000")

    text_clip_kwargs: list[dict] = []

    class FakeAudioClip:
        def __init__(self, path: str):
            self.path = path
            self.duration = 2

        def close(self):
            return None

    class FakeVisualClip:
        def with_position(self, *_args, **_kwargs):
            return self

        def with_duration(self, _duration):
            return self

        def close(self):
            return None

    class FakeCompositeClip(FakeVisualClip):
        def __init__(self, _clips):
            return None

        def with_audio(self, _audio_clip):
            return self

    class FakeFinalClip:
        def write_videofile(self, path: str, fps: int, codec: str, audio_codec: str):
            Path(path).write_bytes(b"video")

        def close(self):
            return None

    def fake_bindings():
        def fake_color_clip(*_args, **_kwargs):
            return FakeVisualClip()

        def fake_text_clip(*_args, **kwargs):
            text_clip_kwargs.append(kwargs)
            return FakeVisualClip()

        def fake_concatenate_videoclips(_clips, method="compose"):
            assert method == "compose"
            return FakeFinalClip()

        return {
            "AudioFileClip": FakeAudioClip,
            "ColorClip": fake_color_clip,
            "CompositeVideoClip": FakeCompositeClip,
            "TextClip": fake_text_clip,
            "concatenate_videoclips": fake_concatenate_videoclips,
        }

    monkeypatch.setattr(editor_module, "_load_moviepy_bindings", fake_bindings)
    monkeypatch.setattr(editor_module, "_resolve_font_path", lambda _config: "C:/Windows/Fonts/malgun.ttf")

    editor_module.compose_video(
        payload,
        [audio_path],
        {"format": "longform", "resolution": [1920, 1080]},
        tmp_path,
        dry_run=False,
    )

    assert text_clip_kwargs[0]["font"] == "C:/Windows/Fonts/malgun.ttf"


def test_compose_video_uses_asset_images_when_provided(tmp_path: Path, monkeypatch):
    payload = build_payload(segment_count=1)
    audio_path = tmp_path / "audio" / "segment_01.wav"
    asset_path = tmp_path / "assets" / "segment_01.png"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"RIFF0000")
    asset_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    image_calls: list[str] = []
    color_clip_calls: list[int] = []

    class FakeAudioClip:
        def __init__(self, path: str):
            self.path = path
            self.duration = 2

        def close(self):
            return None

    class FakeVisualClip:
        def with_position(self, *_args, **_kwargs):
            return self

        def with_duration(self, _duration):
            return self

        def close(self):
            return None

    class FakeImageClip(FakeVisualClip):
        def __init__(self, path: str):
            image_calls.append(path)

    class FakeCompositeClip(FakeVisualClip):
        def __init__(self, _clips):
            return None

        def with_audio(self, _audio_clip):
            return self

    class FakeFinalClip:
        def write_videofile(self, path: str, fps: int, codec: str, audio_codec: str):
            Path(path).write_bytes(b"video")

        def close(self):
            return None

    def fake_bindings():
        def fake_color_clip(*_args, **_kwargs):
            color_clip_calls.append(1)
            return FakeVisualClip()

        def fake_text_clip(*_args, **_kwargs):
            return FakeVisualClip()

        def fake_concatenate_videoclips(_clips, method="compose"):
            assert method == "compose"
            return FakeFinalClip()

        return {
            "AudioFileClip": FakeAudioClip,
            "ColorClip": fake_color_clip,
            "CompositeVideoClip": FakeCompositeClip,
            "ImageClip": FakeImageClip,
            "TextClip": fake_text_clip,
            "concatenate_videoclips": fake_concatenate_videoclips,
        }

    monkeypatch.setattr(editor_module, "_load_moviepy_bindings", fake_bindings)
    monkeypatch.setattr(editor_module, "_resolve_font_path", lambda _config: "C:/Windows/Fonts/malgun.ttf")

    editor_module.compose_video(
        payload,
        [audio_path],
        {"format": "longform", "resolution": [1920, 1080]},
        tmp_path,
        dry_run=False,
        asset_paths=[asset_path],
    )

    assert image_calls == [str(asset_path)]
    assert color_clip_calls == []
