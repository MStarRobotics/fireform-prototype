# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import os
from pathlib import Path

class TranscriptionError(RuntimeError):
    pass

def clean_audio(path: str) -> str:
    try:
        import noisereduce as nr
        import soundfile as sf
    except ImportError:
        # Gracefully skip if missing
        return path

    try:
        data, rate = sf.read(path)
        reduced = nr.reduce_noise(y=data, sr=rate)
        clean_path = str(Path(path).with_suffix("._clean" + Path(path).suffix))
        sf.write(clean_path, reduced, rate)
        return clean_path
    except Exception as exc:
        print(f"Noise reduction failed, skipping: {exc}")
        return path

def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    language: str | None = None,
) -> str:
    """Transcribe audio with faster-whisper.

    Set FIREFORM_MOCK_TRANSCRIPTION to force deterministic text in CI.
    """
    if os.getenv("FIREFORM_MOCK_TRANSCRIPTION"):
        return os.getenv("FIREFORM_MOCK_TRANSCRIPTION", "")

    clean_path = clean_audio(audio_path)

    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]
    except ImportError as exc:
        raise TranscriptionError(
            "faster-whisper is not installed. Add it to your environment."
        ) from exc

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, _ = model.transcribe(clean_path, language=language)
    text = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text.strip()
    )

    if not text.strip():
        raise TranscriptionError("Transcription yielded no text.")

    return text.strip()
