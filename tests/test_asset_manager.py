from pathlib import Path

from src.asset_manager import fetch_assets
from src.models import ScriptSegment


def _build_segments() -> list[ScriptSegment]:
    return [
        ScriptSegment(
            id=1,
            text="첫 번째 세그먼트",
            image_prompt="도심 야경과 네온사인",
            duration_hint=5,
        ),
        ScriptSegment(
            id=2,
            text="두 번째 세그먼트",
            image_prompt="잔잔한 숲속 산책로",
            duration_hint=6,
        ),
    ]


def test_fetch_assets_creates_placeholder_images_in_order(tmp_path: Path):
    paths = fetch_assets(
        _build_segments(),
        {"resolution": [1280, 720], "font": "malgun.ttf"},
        tmp_path,
    )

    assert [path.name for path in paths] == ["segment_01.png", "segment_02.png"]
    assert all(path.exists() for path in paths)
    assert all(path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for path in paths)
