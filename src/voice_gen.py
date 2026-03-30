from __future__ import annotations

import asyncio
import wave
from pathlib import Path


_DEFAULT_VOICE = "en-US-AriaNeural"


def _segment_text(segment) -> str:
    if hasattr(segment, "text"):
        return str(segment.text)
    if isinstance(segment, dict) and "text" in segment:
        return str(segment["text"])
    raise TypeError("segment must have a text field")


class _AudioProviderError(RuntimeError):
    """Raised when an audio provider cannot be used."""


class _AudioProvider:
    def generate(
        self,
        segment,
        output_path: Path,
        *,
        voice: str | None = None,
        channel_config: dict | None = None,
    ) -> Path:
        raise NotImplementedError


class _FallbackAudioProvider(_AudioProvider):
    def generate(
        self,
        segment,
        output_path: Path,
        *,
        voice: str | None = None,
        channel_config: dict | None = None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_ms = int(getattr(segment, "duration_hint", 1_000)) * 1_000
        sample_rate = 16_000
        frame_count = max(int(sample_rate * (max(250, duration_ms) / 1000)), 1)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)

        return output_path


class _EdgeTTSProvider(_AudioProvider):
    def generate(
        self,
        segment,
        output_path: Path,
        *,
        voice: str | None = None,
        channel_config: dict | None = None,
    ) -> Path:
        selected_voice = voice or _DEFAULT_VOICE
        text = _segment_text(segment)

        try:
            import edge_tts
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            raise _AudioProviderError("edge-tts is unavailable") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(text, selected_voice)

        async def _write() -> None:
            await communicate.save(str(output_path))

        try:
            asyncio.run(_write())
        except Exception as exc:  # pragma: no cover - network/runtime failure fallback
            raise _AudioProviderError("edge-tts generation failed") from exc
        return output_path


def _resolve_provider(
    provider=None,
    channel_config: dict | None = None,
) -> tuple[_AudioProvider, str]:
    if provider is None:
        if channel_config and channel_config.get("audio_provider") == "edge-tts":
            return _EdgeTTSProvider(), ".mp3"
        return _FallbackAudioProvider(), ".wav"
    if isinstance(provider, str):
        if provider in {"edge", "edge-tts"}:
            return _EdgeTTSProvider(), ".mp3"
        if provider == "fallback":
            return _FallbackAudioProvider(), ".wav"
        raise ValueError("provider must be 'edge', 'fallback', or an AudioProvider instance")
    if not hasattr(provider, "generate"):
        raise TypeError("provider must expose a generate(segment, output_path, ...)")
    return provider, ".mp3"


def generate_audio_segments(
    segments,
    channel_config: dict,
    output_dir: Path,
    provider=None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    audio_paths: list[Path] = []
    audio_provider, output_suffix = _resolve_provider(provider=provider, channel_config=channel_config)
    fallback_provider = _FallbackAudioProvider()
    voice = channel_config.get("voice", _DEFAULT_VOICE) if isinstance(channel_config, dict) else _DEFAULT_VOICE

    for index, segment in enumerate(segments, start=1):
        output_path = audio_dir / f"segment_{index:02d}{output_suffix}"
        try:
            generated = audio_provider.generate(
                segment,
                output_path,
                voice=voice,
                channel_config=channel_config,
            )
        except Exception as exc:
            if isinstance(audio_provider, _FallbackAudioProvider):
                raise
            if provider is not None and not isinstance(provider, str):
                raise

            fallback_output_path = audio_dir / f"segment_{index:02d}.wav"
            if output_path != fallback_output_path and output_path.exists():
                output_path.unlink(missing_ok=True)
            generated = fallback_provider.generate(
                segment,
                fallback_output_path,
                voice=voice,
                channel_config=channel_config,
            )
        audio_paths.append(generated)

    return audio_paths
