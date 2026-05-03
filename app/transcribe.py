"""转录入口：根据 TRANSCRIBE_PROVIDER 路由到本地 faster-whisper / 阿里云 DashScope。

env:
    TRANSCRIBE_PROVIDER=local    # 默认，faster-whisper（本地，免费）
    TRANSCRIBE_PROVIDER=dashscope # 阿里云 paraformer（中文 95-97%，月免 600 分钟）
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def transcribe(video: Path) -> tuple[list[tuple[float, float, str]], str]:
    """返回 (segments, detected_language)。segments = [(start, end, text), ...]"""
    provider = os.getenv("TRANSCRIBE_PROVIDER", "local").strip().lower()
    if provider == "dashscope":
        from app.transcribe_dashscope import transcribe_dashscope
        return transcribe_dashscope(video)
    return _transcribe_local(video)


# ─── 本地 faster-whisper ───
_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        from app.config import WHISPER_COMPUTE, WHISPER_MODEL
        _model = WhisperModel(WHISPER_MODEL, compute_type=WHISPER_COMPUTE)
    return _model


def _transcribe_local(video: Path) -> tuple[list[tuple[float, float, str]], str]:
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
