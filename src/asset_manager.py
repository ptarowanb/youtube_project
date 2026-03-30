from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.utils.fonts import resolve_font_path


def _segment_image_prompt(segment) -> str:
    if hasattr(segment, "image_prompt"):
        return str(segment.image_prompt)
    if isinstance(segment, dict) and "image_prompt" in segment:
        return str(segment["image_prompt"])
    return ""


def _segment_text(segment) -> str:
    if hasattr(segment, "text"):
        return str(segment.text)
    if isinstance(segment, dict) and "text" in segment:
        return str(segment["text"])
    return ""


def _hash_color(seed: str) -> tuple[int, int, int]:
    value = abs(hash(seed))
    return (
        40 + value % 90,
        60 + (value // 7) % 90,
        90 + (value // 17) % 90,
    )


def _load_font(channel_config: dict, size: int):
    font_path = resolve_font_path(channel_config)
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    if not text:
        return []

    lines: list[str] = []
    current = ""
    for char in text:
        candidate = f"{current}{char}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        width = bbox[2] - bbox[0]
        if current and width > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate

    if current:
        lines.append(current)
    return lines


def _draw_multiline_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font,
    fill: str,
    box: tuple[int, int, int, int],
    line_spacing: int,
) -> None:
    max_width = box[2] - box[0]
    lines = _wrap_text(draw, text, font, max_width=max_width)
    if not lines:
        return

    sample_bbox = draw.textbbox((0, 0), "가", font=font)
    line_height = (sample_bbox[3] - sample_bbox[1]) + line_spacing
    total_height = len(lines) * line_height - line_spacing
    y = box[1] + max((box[3] - box[1] - total_height) // 2, 0)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        x = box[0] + max((max_width - width) // 2, 0)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def _create_placeholder_image(segment, channel_config: dict, output_path: Path) -> Path:
    resolution = tuple(channel_config.get("resolution", [1920, 1080]))
    width, height = int(resolution[0]), int(resolution[1])
    prompt = _segment_image_prompt(segment)
    narration = _segment_text(segment)
    base_color = _hash_color(prompt or narration or str(getattr(segment, "id", "0")))

    image = Image.new("RGB", (width, height), color=base_color)
    draw = ImageDraw.Draw(image)

    for index in range(height):
        blend = index / max(height - 1, 1)
        color = (
            min(255, int(base_color[0] * (0.65 + blend * 0.35))),
            min(255, int(base_color[1] * (0.65 + blend * 0.35))),
            min(255, int(base_color[2] * (0.65 + blend * 0.35))),
        )
        draw.line([(0, index), (width, index)], fill=color)

    margin = max(width // 12, 48)
    panel_top = height // 7
    panel_bottom = height - panel_top
    draw.rounded_rectangle(
        (margin, panel_top, width - margin, panel_bottom),
        radius=28,
        fill=(12, 16, 24),
        outline=(255, 255, 255),
        width=2,
    )

    prompt_font = _load_font(channel_config, max(28, width // 30))
    narration_font = _load_font(channel_config, max(20, width // 42))

    _draw_multiline_text(
        draw,
        text=prompt or "Visual placeholder",
        font=prompt_font,
        fill="white",
        box=(margin + 40, panel_top + 40, width - margin - 40, panel_top + (panel_bottom - panel_top) // 2),
        line_spacing=10,
    )
    _draw_multiline_text(
        draw,
        text=narration,
        font=narration_font,
        fill="#d6deeb",
        box=(margin + 50, panel_top + (panel_bottom - panel_top) // 2, width - margin - 50, panel_bottom - 40),
        line_spacing=8,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def fetch_assets(segments: list[dict], channel_config: dict, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = output_dir / "assets"
    asset_paths: list[Path] = []

    for index, segment in enumerate(segments, start=1):
        output_path = asset_dir / f"segment_{index:02d}.png"
        asset_paths.append(_create_placeholder_image(segment, channel_config, output_path))

    return asset_paths
