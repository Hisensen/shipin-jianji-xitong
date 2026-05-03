"""阿里云 DashScope paraformer 转录（中文最准）。

定价（2026）：
- paraformer-realtime-v2: ¥0.00015/秒，每月 36000 秒（10 小时）免费额度
- 中文准确率 95-97%（含方言、行业词）

用法：
- 配 .env: DASHSCOPE_API_KEY=sk-xxx
- TRANSCRIBE_PROVIDER=dashscope 切到这里

实现：先用 ffmpeg 把视频抽成 16kHz 单声道 mp3，再走 Recognition.call 一次拿回
带时间戳的句子级结果。"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def transcribe_dashscope(
    video: Path,
) -> tuple[list[tuple[float, float, str]], str]:
    """返回 (segments, language)。segments = [(start, end, text), ...]"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未设置")

    import dashscope
    from dashscope.audio.asr import Recognition

    dashscope.api_key = api_key

    # 1) 抽音频：16kHz 单声道 mp3（DashScope 支持，体积小）
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        audio_path = Path(tmp.name)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video),
                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
                str(audio_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 2) 调 paraformer-realtime-v2（接受本地文件，返回带时间戳）
        result = Recognition.call(
            model=os.getenv("DASHSCOPE_ASR_MODEL", "paraformer-realtime-v2"),
            format="mp3",
            sample_rate=16000,
            file_path=str(audio_path),
            language_hints=["zh"],
            disfluency_removal_enabled=False,
        )

        if not result or result.status_code != 200:
            raise RuntimeError(
                f"DashScope ASR 失败: status={getattr(result, 'status_code', 'n/a')} "
                f"msg={getattr(result, 'message', 'n/a')}"
            )

        # 3) 解析结果 — sentences 每条含 begin_time/end_time（毫秒）+ text
        segments: list[tuple[float, float, str]] = []
        sentences = []
        if hasattr(result, "output") and result.output:
            sentences = result.output.get("sentence", []) or []
        for s in sentences:
            text = (s.get("text") or "").strip()
            if not text:
                continue
            start = float(s.get("begin_time", 0)) / 1000.0
            end = float(s.get("end_time", 0)) / 1000.0
            if end <= start:
                end = start + 1.0
            segments.append((start, end, text))

        return segments, "zh"
    finally:
        audio_path.unlink(missing_ok=True)
