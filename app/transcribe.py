"""faster-whisper 转录。"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from faster_whisper import WhisperModel  # noqa: E402

from app.config import WHISPER_COMPUTE, WHISPER_MODEL

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, compute_type=WHISPER_COMPUTE)
    return _model


def transcribe(video: Path) -> tuple[list[tuple[float, float, str]], str]:
    """返回 (segments, detected_language)。segments = [(start, end, text), ...]"""
    model = _get_model()
    segs_iter, info = model.transcribe(
        str(video), vad_filter=True, beam_size=5,
    )
    out: list[tuple[float, float, str]] = []
    for s in segs_iter:
        text = s.text.strip()
        if text:
            out.append((s.start, s.end, text))
    return out, info.language or ""
