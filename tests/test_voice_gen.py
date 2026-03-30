from pathlib import Path

from src.models import ScriptSegment
from src.voice_gen import generate_audio_segments


def _build_segments() -> list[ScriptSegment]:
    return [
        ScriptSegment(
            id=1,
            text="첫 번째 내레이션",
            image_prompt="image 1",
            duration_hint=4,
        ),
        ScriptSegment(
            id=2,
            text="두 번째 내레이션",
            image_prompt="image 2",
            duration_hint=5,
        ),
    ]


def test_generate_audio_segments_creates_ordered_mp3s_in_audio_dir(tmp_path: Path):
    channel_config = {"voice": "en-US-AriaNeural"}

    paths = generate_audio_segments(
        segments=_build_segments(),
        channel_config=channel_config,
        output_dir=tmp_path,
    )

    assert len(paths) == 2
    assert paths[0] == tmp_path / "audio" / "segment_01.mp3"
    assert paths[1] == tmp_path / "audio" / "segment_02.mp3"
    assert [path.exists() for path in paths] == [True, True]
    assert [path.is_file() for path in paths] == [True, True]


def test_generate_audio_segments_uses_provider_in_order(tmp_path: Path):
    channel_config = {"voice": "en-US-AriaNeural"}
    call_order: list[str] = []

    class TrackingProvider:
        def generate(self, segment: ScriptSegment, output_path: Path, *, voice: str | None = None, channel_config=None) -> Path:
            call_order.append(str(segment.id))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"generated:{segment.id}", encoding="utf-8")
            return output_path

    paths = generate_audio_segments(
        segments=_build_segments(),
        channel_config=channel_config,
        output_dir=tmp_path,
        provider=TrackingProvider(),
    )

    assert call_order == ["1", "2"]
    assert [path.name for path in paths] == ["segment_01.mp3", "segment_02.mp3"]
    assert all(path.exists() for path in paths)
