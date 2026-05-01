"""音频波形分析：找出"真重音"帧 —— 用作 zoom + 闪光的踩点。

策略：
1. ffmpeg 提取 16kHz 单声道 PCM
2. 100ms 窗口算 RMS 能量
3. 用滑动中位数做相对参考（去掉整体音量趋势）
4. 找局部峰值，且能量比邻域中位数高 60% 以上
5. dedupe 相邻 < 0.4 秒的峰
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np


def _extract_audio_pcm(video: Path, sample_rate: int = 16000) -> np.ndarray:
    proc = subprocess.run(
        [
            "ffmpeg", "-i", str(video),
            "-vn", "-ac", "1", "-ar", str(sample_rate),
            "-f", "s16le", "-",
        ],
        capture_output=True,
        check=True,
    )
    raw = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return raw


def extract_beat_frames(
    video: Path,
    fps: int = 30,
    window_ms: int = 80,
    rolling_ms: int = 800,
    rel_thresh: float = 2.0,
    abs_thresh: float = 0.07,
    min_gap_frames: int = 24,
) -> list[int]:
    """返回视频帧索引列表（视频时间，未含封面偏移），表示"真重音"瞬间。

    rel_thresh: 当前窗口能量 / 邻域中位数 至少这么大才算峰
    abs_thresh: 当前窗口 RMS 至少这么大（避开静音段假峰）
    min_gap_frames: 两个峰之间最少差这么多帧
    """
    audio = _extract_audio_pcm(video)
    sample_rate = 16000
    window_size = max(1, int(sample_rate * window_ms / 1000))
    n_windows = len(audio) // window_size
    if n_windows < 3:
        return []

    rms = np.zeros(n_windows)
    for i in range(n_windows):
        chunk = audio[i * window_size:(i + 1) * window_size]
        rms[i] = float(np.sqrt(np.mean(chunk**2) + 1e-12))

    # 用滚动中位数当邻域参考
    rolling_windows = max(1, int(rolling_ms / window_ms))
    half = rolling_windows // 2

    def neighborhood_median(idx: int) -> float:
        lo = max(0, idx - half)
        hi = min(n_windows, idx + half + 1)
        return float(np.median(rms[lo:hi]) + 1e-12)

    # 找局部峰：当前 > 左右邻居 且 ratio + 绝对都达标
    peaks: list[int] = []
    for i in range(1, n_windows - 1):
        if rms[i] <= rms[i - 1] or rms[i] <= rms[i + 1]:
            continue
        if rms[i] < abs_thresh:
            continue
        med = neighborhood_median(i)
        if rms[i] / med < rel_thresh:
            continue
        # 转视频帧（窗口起点对应的秒 → 帧）
        sec = i * window_size / sample_rate
        frame = int(round(sec * fps))
        peaks.append(frame)

    # dedupe 相邻太近的（保留更强的）
    if not peaks:
        return []
    deduped: list[tuple[int, float]] = []
    rms_at = lambda f: rms[int(round(f * sample_rate / fps / window_size))]  # noqa: E731
    for f in peaks:
        if not deduped:
            deduped.append((f, rms_at(f)))
            continue
        last_f, last_e = deduped[-1]
        if f - last_f < min_gap_frames:
            cur_e = rms_at(f)
            if cur_e > last_e:
                deduped[-1] = (f, cur_e)
        else:
            deduped.append((f, rms_at(f)))
    return [f for f, _ in deduped]
