"""V3 版生成器：每句字幕智能决策形式（image/callout/emoji/none），写到 src/realCuesV3.ts。

用法:
    .venv/bin/python remotion/make_cues_v3.py "/path/to/video.mp4"

依赖 make_cues.py 的产物（cover_bg.jpg, source.mp4, images/）—— 先跑 make_cues.py 再跑这个。
或独立跑：会自己拷视频、抽封面帧、搜图。
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
    CALLOUT_COLORS,
    decide_per_cue_forms,
    materialize_image,
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
        sys.exit("用法: python make_cues_v3.py <video>")
    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.exists():
        sys.exit(f"视频不存在: {src}")

    duration = video_duration_seconds(src)
    duration_frames = int(round(duration * FPS))

    print(f"[1/7] 转录 {src.name}...")
    segments, lang = transcribe(src)
    texts = [t for _, _, t in segments]
    transcript_joined = "".join(texts)
    print(f"      {len(segments)} 段")

    print("[2/7] 生成标题 + 章节...")
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

    print("[3/7] DeepSeek 决策每句视觉形式...")
    decisions = decide_per_cue_forms(texts)
    counter: dict[str, int] = {"image": 0, "callout": 0, "emoji": 0, "none": 0}
    for i, d in enumerate(decisions):
        f = d.get("form", "none")
        counter[f] = counter.get(f, 0) + 1
        if f == "image":
            print(f"      #{i:2d} 🖼️  「{texts[i]}」 → {d.get('keyword', '')!r}")
        elif f == "callout":
            print(
                f"      #{i:2d} 🔖 「{texts[i]}」 → {d.get('emoji', '')} {d.get('text', '')} ({d.get('color', '')})"
            )
        elif f == "emoji":
            print(f"      #{i:2d} 😀 「{texts[i]}」 → {d.get('emoji', '')}")
        else:
            print(f"      #{i:2d}     「{texts[i]}」")
    print(
        f"      统计：image {counter['image']} / callout {counter['callout']} / "
        f"emoji {counter['emoji']} / none {counter['none']}"
    )

    print("[4/7] 生成/下载 image 类的图...")
    images_dir = ROOT / "public" / "images_v3"
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True)

    for i, d in enumerate(decisions):
        if d.get("form") != "image":
            continue
        kw = d.get("keyword", "")
        dst = images_dir / f"{i:02d}.jpg"
        provider = materialize_image(
            keyword=kw,
            context_text=texts[i],
            dst=dst,
            orientation="portrait",
        )
        if provider:
            d["imageSrc"] = f"images_v3/{dst.name}"
            print(f"      #{i} {kw!r} → {dst.name} ✓ ({provider})")
        else:
            d["form"] = "none"
            print(f"      #{i} {kw!r} → 失败，降级 none")

    cues = []
    for i, ((start, end, text), d) in enumerate(zip(segments, decisions)):
        cue: dict = {
            "startFrame": max(0, int(round(start * FPS))),
            "endFrame": min(duration_frames, int(round(end * FPS))),
            "text": text,
        }
        f = d.get("form", "none")
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

    print("[5/7] 拷视频...")
    public_dir = ROOT / "public"
    public_dir.mkdir(exist_ok=True)
    dst_video = public_dir / "source.mp4"
    if not dst_video.exists():
        shutil.copyfile(src, dst_video)

    print("[6/7] 抽封面背景帧...")
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

    print("[7/7] 写 src/realCuesV3.ts")
    cues_ts = ROOT / "src" / "realCuesV3.ts"
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
    }
    body = (
        "// Auto-generated by make_cues_v3.py — do not edit by hand.\n"
        "import type { SubtitleProps } from './SubtitleWithImages';\n\n"
        "export const realPropsV3: SubtitleProps = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + " as unknown as SubtitleProps;\n"
    )
    cues_ts.write_text(body, encoding="utf-8")

    print(f"\nV3 完成。总帧数 {total_frames}。")


if __name__ == "__main__":
    main()
