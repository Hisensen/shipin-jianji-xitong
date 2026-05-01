"""V4 版生成器：V3 + 金句全屏卡 + 关键词弹跳放大 + 章节转场（白闪+标题）+ 视频zoom节奏。

用法:
    .venv/bin/python remotion/make_cues_v4.py "/path/to/video.mp4"
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.transcribe import transcribe  # noqa: E402
from app.imagery import (  # noqa: E402
    decide_per_cue_forms,
    pick_quotes_and_emphasis,
    search_pexels,
    download,
    CALLOUT_COLORS,
)
from app.llm import extract_chapters, generate_title  # noqa: E402

FPS = 30
COVER_FRAMES = 1


def video_duration_seconds(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1", str(path),
        ],
        text=True,
    )
    return float(out.strip())


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法: python make_cues_v4.py <video>")
    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.exists():
        sys.exit(f"视频不存在: {src}")

    duration = video_duration_seconds(src)
    duration_frames = int(round(duration * FPS))

    print(f"[1/8] 转录 {src.name}...")
    segments, lang = transcribe(src)
    texts = [t for _, _, t in segments]
    transcript_joined = "".join(texts)

    print("[2/8] 生成标题 + 章节...")
    title, _ = generate_title(transcript_joined)
    chapters_raw, _ = extract_chapters(segments, duration)
    print(f"      标题「{title}」 / {len(chapters_raw)} 章节")
    chapters = [
        {
            "title": c["title"],
            "startFrame": max(0, int(round(c["start"] * FPS))),
            "endFrame": min(duration_frames, int(round(c["end"] * FPS))),
        }
        for c in chapters_raw
    ]
    hashtag = f"#{title}"

    print("[3/8] 决策每句视觉形式 (image/callout/emoji/none)...")
    decisions = decide_per_cue_forms(texts)

    print("[4/8] 决策金句 + 关键词强调...")
    quote_emph = pick_quotes_and_emphasis(texts)

    n_quotes = sum(1 for q in quote_emph if q.get("isQuote"))
    print(f"      金句 {n_quotes} 句:")
    for i, q in enumerate(quote_emph):
        marks = []
        if q.get("isQuote"):
            marks.append("💎金句")
        if q.get("emphasis"):
            marks.append(f"放大词={q['emphasis']}")
        if marks:
            print(f"      #{i:2d} {' / '.join(marks)} 「{texts[i]}」")

    print("[5/8] 下载 image 类的图...")
    images_dir = ROOT / "public" / "images_v4"
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True)

    for i, d in enumerate(decisions):
        if d.get("form") != "image":
            continue
        kw = d.get("keyword", "")
        if not kw:
            d["form"] = "none"
            continue
        url = search_pexels(kw)
        if not url:
            d["form"] = "none"
            continue
        dst = images_dir / f"{i:02d}.jpg"
        if download(url, dst):
            d["imageSrc"] = f"images_v4/{dst.name}"
            print(f"      #{i} {kw!r} → {dst.name} ✓")
        else:
            d["form"] = "none"

    cues = []
    for i, ((start, end, text), d, q) in enumerate(zip(segments, decisions, quote_emph)):
        cue: dict = {
            "startFrame": max(0, int(round(start * FPS))),
            "endFrame": min(duration_frames, int(round(end * FPS))),
            "text": text,
            "isQuote": bool(q.get("isQuote")),
            "emphasis": q.get("emphasis", []),
        }
        f = d.get("form", "none")
        if not cue["isQuote"]:
            if f == "image":
                cue["imageSrc"] = d.get("imageSrc")
            elif f == "callout":
                color = d.get("color", "yellow")
                bg, fg = CALLOUT_COLORS.get(color, CALLOUT_COLORS["yellow"])
                cue["calloutEmoji"] = d.get("emoji", "")
                cue["calloutText"] = d.get("text", "")
                cue["calloutBg"] = bg
                cue["calloutFg"] = fg
            elif f == "emoji":
                cue["emoji"] = d.get("emoji", "")
        cues.append(cue)

    print("[6/8] 拷视频 + 抽封面...")
    public_dir = ROOT / "public"
    public_dir.mkdir(exist_ok=True)
    dst_video = public_dir / "source.mp4"
    if not dst_video.exists():
        shutil.copyfile(src, dst_video)
    cover_bg = public_dir / "cover_bg.jpg"
    if not cover_bg.exists():
        cover_t = max(0.5, duration * 0.3)
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", f"{cover_t:.3f}", "-i", str(dst_video),
                "-frames:v", "1", "-q:v", "2", str(cover_bg),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    cover_frames = COVER_FRAMES
    total_frames = duration_frames + cover_frames

    print("[7/8] 生成 zoom 节奏点（章节起始 + 金句起始 + callout 起始）...")
    zoom_frames = set()
    for c in chapters:
        if c["startFrame"] > 0:
            zoom_frames.add(c["startFrame"])
    for cue in cues:
        if cue.get("isQuote") or cue.get("calloutText"):
            zoom_frames.add(cue["startFrame"])
    zoom_list = sorted(zoom_frames)
    print(f"      共 {len(zoom_list)} 个 zoom 节奏点")

    print("[8/8] 写 src/realCuesV4.ts")
    cues_ts = ROOT / "src" / "realCuesV4.ts"
    payload = {
        "videoSrc": "source.mp4",
        "coverBgSrc": "cover_bg.jpg",
        "coverDurationInFrames": cover_frames,
        "videoDurationInFrames": duration_frames,
        "durationInFrames": total_frames,
        "title": title,
        "hashtag": hashtag,
        "chapters": chapters,
        "cues": cues,
        "zoomFrames": zoom_list,
    }
    body = (
        "// Auto-generated by make_cues_v4.py — do not edit by hand.\n"
        "import type { SubtitleProps } from './SubtitleWithImages';\n\n"
        "export const realPropsV4: SubtitleProps = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + " as unknown as SubtitleProps;\n"
    )
    cues_ts.write_text(body, encoding="utf-8")

    print(f"\nV4 完成。总帧数 {total_frames} / {n_quotes} 金句 / {len(zoom_list)} zoom 点。")


if __name__ == "__main__":
    main()
