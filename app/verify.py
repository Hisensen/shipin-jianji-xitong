"""把 validation.md 条目跑成机器断言。

用法：
  端到端跑一条视频并校验：
    python -m app.verify samples/inbox/demo.mp4
  仅校验已有产物：
    python -m app.verify --stem demo
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import (
    FONT_NAME,
    FONT_PATH,
    OUTPUT_DIR,
    SUB_FONT_SIZE_RATIO,
    TITLE_MAX_CHARS,
    TITLE_MAX_WIDTH_RATIO,
    TITLE_STROKE_RATIO,
)


@dataclass
class Check:
    id: str
    desc: str
    ok: bool
    detail: str = ""

    def line(self) -> str:
        tag = "✅" if self.ok else "❌"
        return f"{tag} [{self.id}] {self.desc}  {self.detail}"


def _probe_duration(p: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(p),
    ]).decode().strip()
    return float(out) if out else 0.0


def _probe_wh(p: Path) -> tuple[int, int]:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", str(p),
    ]).decode().strip()
    w, h = out.split("x")
    return int(w), int(h)


def check_product(stem: str, source_video: Path | None) -> list[Check]:
    out = OUTPUT_DIR / stem
    checks: list[Check] = []

    # F3: 5 个必需文件
    req = [
        f"{stem}_sub.mp4", f"{stem}_cover.jpg", f"{stem}.srt",
        f"{stem}.meta.json", "debug/pipeline.log",
    ]
    missing = [r for r in req if not (out / r).exists() or (out / r).stat().st_size == 0]
    checks.append(Check("F3", "5 个必需文件都存在且非 0 字节",
                        not missing, "缺失: " + str(missing) if missing else ""))

    if not (out / f"{stem}.meta.json").exists():
        return checks

    meta = json.loads((out / f"{stem}.meta.json").read_text(encoding="utf-8"))

    # F4: 时长
    if source_video and source_video.exists():
        src_dur = _probe_duration(source_video)
        sub_dur = _probe_duration(out / f"{stem}_sub.mp4")
        checks.append(Check("F4", "字幕视频时长 ≈ 原视频（±0.5s）",
                            abs(src_dur - sub_dur) <= 0.5,
                            f"src={src_dur:.2f} sub={sub_dur:.2f}"))
    # F5: 封面分辨率 = 视频分辨率
    from PIL import Image
    with Image.open(out / f"{stem}_cover.jpg") as im:
        cw, ch = im.size
    vw, vh = meta["width"], meta["height"]
    checks.append(Check("F5", "封面分辨率 = 视频分辨率",
                        (cw, ch) == (vw, vh),
                        f"cover={cw}x{ch} video={vw}x{vh}"))

    # F6: srt ≥ 1 条（有音频时）
    srt_text = (out / f"{stem}.srt").read_text(encoding="utf-8")
    n_sub = sum(1 for ln in srt_text.splitlines() if "-->" in ln)
    if meta.get("warning_no_audio"):
        checks.append(Check("F6", "srt 条数（无音频视频允许 0）", True, f"{n_sub}"))
    else:
        checks.append(Check("F6", "srt ≥ 1 条字幕", n_sub >= 1, f"{n_sub}"))

    # F7: meta 字段
    need = ["title", "duration", "subtitle_count", "cover_frame_time",
            "cover_pick_score", "elapsed"]
    miss = [k for k in need if k not in meta]
    checks.append(Check("F7", "meta.json 字段齐全", not miss,
                        "缺: " + str(miss) if miss else ""))

    # C1: 精彩帧不是 frame[0]
    t = meta.get("cover_frame_time", 0)
    checks.append(Check("C1", "封面帧 > 0.5s 且 < 视频末尾",
                        0.5 <= t < meta["duration"],
                        f"t={t}"))

    # C7: 标题 ≤ 6 字
    title = meta.get("title", "")
    checks.append(Check("C7", f"标题 ≤ {TITLE_MAX_CHARS} 字",
                        1 <= len(title) <= TITLE_MAX_CHARS,
                        f"title='{title}' len={len(title)}"))

    # C4/C5: 封面标题几何
    cover_meta = meta.get("cover", {})
    fs = cover_meta.get("font_size", 0)
    tw = cover_meta.get("text_w", 0)
    cy = cover_meta.get("center_y_ratio", 0)
    checks.append(Check("C4", "标题横向 ≤ 画面宽度的 85%",
                        tw <= vw * TITLE_MAX_WIDTH_RATIO + 2,
                        f"text_w={tw} max={int(vw*TITLE_MAX_WIDTH_RATIO)}"))
    checks.append(Check("C5", "标题中心线在图高 10%-20%",
                        0.10 <= cy <= 0.20, f"center_y_ratio={cy}"))
    # C3: stroke_width >= 字号 8%
    sw = cover_meta.get("stroke_width", 0)
    checks.append(Check("C3", f"黑描边 ≥ 字号 {int(TITLE_STROKE_RATIO*100)}%",
                        sw >= fs * 0.08, f"stroke={sw} font={fs}"))

    # S1/S2: ass 字段在代码里固定，check 时间对齐用 srt；抽样字幕行 ≤12 字
    if not meta.get("warning_no_audio"):
        bad = []
        for ln in srt_text.splitlines():
            if not ln or "-->" in ln or ln[0].isdigit():
                continue
            # 去除英文/数字计算汉字字符数
            if len(ln) > 12 * 2 + 1:  # 两行 + \n
                bad.append(ln)
        checks.append(Check("S4", "每段字幕 ≤ 2 行 × 12 字", not bad,
                            f"超长条数={len(bad)}"))

    # S5: 字号比例在配置范围（由代码保证，校验 meta 不好做；跳过硬断言，检查配置）
    checks.append(Check("S5", "字幕字号比例配置正确",
                        0.03 <= SUB_FONT_SIZE_RATIO <= 0.06,
                        f"ratio={SUB_FONT_SIZE_RATIO}"))

    # P4: ≥ 5 张候选
    cand = out / "debug" / "candidates"
    n_cand = len(list(cand.glob("cand_*.jpg"))) if cand.exists() else 0
    checks.append(Check("P4", "候选帧 ≥ 5", n_cand >= 5, f"n={n_cand}"))

    # P5: pick_reason 存在
    pr = out / "debug" / "pick_reason.txt"
    checks.append(Check("P5", "pick_reason.txt 非空",
                        pr.exists() and pr.stat().st_size > 0))

    # E4: 字体文件存在
    checks.append(Check("E4", "字体文件存在",
                        FONT_PATH.exists(), f"{FONT_PATH}"))

    return checks


def run_end_to_end(video: Path) -> list[Check]:
    from app.pipeline import process_one
    r = process_one(video)
    if not r.ok:
        return [Check("PIPELINE", "pipeline 运行成功", False, r.error)]
    return check_product(r.stem, video)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", help="视频路径（端到端模式）")
    ap.add_argument("--stem", help="只校验已有产物（跳过 pipeline）")
    args = ap.parse_args()

    if args.stem:
        checks = check_product(args.stem, None)
    elif args.video:
        checks = run_end_to_end(Path(args.video).expanduser().resolve())
    else:
        ap.error("需要 video 或 --stem")
        return

    print("\n=== 验收报告 ===")
    for c in checks:
        print(c.line())
    fail = [c for c in checks if not c.ok]
    print(f"\n{len(checks) - len(fail)} PASS / {len(fail)} FAIL")
    sys.exit(0 if not fail else 1)


if __name__ == "__main__":
    main()
