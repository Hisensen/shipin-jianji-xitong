"""挑"精彩帧"：清晰度 + 人脸 + 非首尾。"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.config import (
    FRAME_CANDIDATE_COUNT,
    FRAME_HEAD_SKIP,
    FRAME_KEEP_TOP_N,
    FRAME_TAIL_SKIP,
)

_face_cascade: cv2.CascadeClassifier | None = None


def _get_face_cascade() -> cv2.CascadeClassifier:
    global _face_cascade
    if _face_cascade is None:
        path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(str(path))
    return _face_cascade


@dataclass
class FrameScore:
    time: float
    clarity: float      # Laplacian 方差
    has_face: bool
    brightness_ok: bool
    score: float        # 综合分
    path: Path

    def to_dict(self) -> dict:
        return {
            "time": round(self.time, 3),
            "clarity": round(self.clarity, 2),
            "has_face": self.has_face,
            "brightness_ok": self.brightness_ok,
            "score": round(self.score, 3),
            "path": str(self.path.name),
        }


def _extract_frame(video: Path, t: float, out: Path) -> bool:
    cmd = [
        "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
        "-vframes", "1", "-q:v", "2", str(out),
    ]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 0


def _score_image(path: Path) -> tuple[float, bool, bool]:
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return 0.0, False, False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clarity = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean = float(gray.mean())
    std = float(gray.std())
    brightness_ok = 20 < mean < 235 and std > 15
    faces = _get_face_cascade().detectMultiScale(gray, 1.2, 4, minSize=(80, 80))
    has_face = len(faces) > 0
    return clarity, has_face, brightness_ok


def pick_best_frame(
    video: Path, duration: float, debug_dir: Path
) -> tuple[FrameScore, list[FrameScore]]:
    """扫候选 → 评分 → 选最好 → 把 top N 落盘到 debug_dir。"""
    debug_dir.mkdir(parents=True, exist_ok=True)
    t_start = duration * FRAME_HEAD_SKIP
    t_end = duration * (1 - FRAME_TAIL_SKIP)
    if t_end - t_start < 0.5:
        t_start, t_end = 0.0, max(duration - 0.1, 0.1)
    times = np.linspace(t_start, t_end, FRAME_CANDIDATE_COUNT).tolist()

    candidates: list[FrameScore] = []
    for i, t in enumerate(times):
        out = debug_dir / f"cand_{i:02d}_{t:.2f}.jpg"
        if not _extract_frame(video, t, out):
            continue
        clarity, face, bright = _score_image(out)
        # 综合分：清晰度 log 归一 + 人脸加 100 + 合适亮度加 20
        import math
        score = math.log1p(max(clarity, 1.0)) * 10
        if face:
            score += 100
        if bright:
            score += 20
        candidates.append(FrameScore(t, clarity, face, bright, score, out))

    if not candidates:
        raise RuntimeError(f"未能从视频抽出任何帧: {video}")

    candidates.sort(key=lambda x: x.score, reverse=True)
    keep = candidates[:FRAME_KEEP_TOP_N]
    # 删掉落选帧
    kept_paths = {c.path for c in keep}
    for c in candidates:
        if c.path not in kept_paths and c.path.exists():
            c.path.unlink()
    return keep[0], keep


def write_pick_reason(best: FrameScore, top: list[FrameScore], out: Path) -> None:
    lines = [
        "=== 封面挑帧决策 ===",
        f"选中: {best.path.name}",
        f"时间: {best.time:.2f}s",
        f"清晰度(Laplacian 方差): {best.clarity:.2f}",
        f"含人脸: {best.has_face}",
        f"亮度合格: {best.brightness_ok}",
        f"综合分: {best.score:.2f}",
        "",
        "=== Top 候选明细 ===",
    ]
    for i, c in enumerate(top, 1):
        lines.append(
            f"{i}. {c.path.name}  t={c.time:.2f}s  clarity={c.clarity:.1f}  "
            f"face={c.has_face}  bright={c.brightness_ok}  score={c.score:.2f}"
        )
    out.write_text("\n".join(lines), encoding="utf-8")
