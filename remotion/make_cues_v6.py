"""V6 情感纪实版：更真实、更克制，适合女性情感口播。

用法:
    .venv/bin/python remotion/make_cues_v6.py "/path/to/video.mp4"
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

from app.imagery import materialize_image, pick_image_cues, pick_quotes_and_emphasis  # noqa: E402
from app.llm import extract_chapters, generate_title  # noqa: E402
from app.subtitle import split_segments  # noqa: E402
from app.transcribe import transcribe  # noqa: E402

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


def video_dimensions(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x", str(path),
        ],
        text=True,
    ).strip()
    w, h = out.split("x")
    return int(w), int(h)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法: python make_cues_v6.py <video>")
    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.exists():
        sys.exit(f"视频不存在: {src}")

    duration = video_duration_seconds(src)
    duration_frames = int(round(duration * FPS))
    vid_w, vid_h = video_dimensions(src)
    print(f"      尺寸 {vid_w}x{vid_h}, 时长 {duration:.1f}s")

    print(f"[1/8] 转录 {src.name}...")
    raw_segments, _ = transcribe(src)
    segments = split_segments(raw_segments)
    texts = [t for _, _, t in segments]
    transcript_joined = "".join(texts)
    print(f"      原始 {len(raw_segments)} 段 / 切短后 {len(segments)} 段")

    print("[2/8] 生成标题 + 章节...")
    title, _ = generate_title(transcript_joined)
    chapters_raw, _ = extract_chapters(segments, duration)
    chapters = [
        {
            "title": c["title"],
            "startFrame": max(0, int(round(c["start"] * FPS))),
            "endFrame": min(duration_frames, int(round(c["end"] * FPS))),
        }
        for c in chapters_raw
    ]
    hashtag = f"#{title}"
    print(f"      标题「{title}」 / {len(chapters_raw)} 章节")

    print("[3/8] 挑情绪配图句...")
    picks = pick_image_cues(texts)
    for idx, kw in picks:
        print(f"      #{idx:02d} {texts[idx]} -> {kw!r}")

    print("[4/8] 挖金句 + 关键词强调...")
    quote_emph = pick_quotes_and_emphasis(texts)
    n_quotes = sum(1 for q in quote_emph if q.get("isQuote"))
    print(f"      金句 {n_quotes} 句")

    print("[5/8] 生成/下载生活感配图...")
    images_dir = ROOT / "public" / "images_v6"
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True)

    image_for_idx: dict[int, str] = {}
    for idx, kw in picks:
        dst = images_dir / f"{idx:02d}.jpg"
        provider = materialize_image(
            keyword=kw,
            context_text=texts[idx],
            dst=dst,
            orientation="portrait",
        )
        if provider:
            image_for_idx[idx] = f"images_v6/{dst.name}"
            print(f"      #{idx:02d} -> {dst.name} ({provider})")
        else:
            print(f"      #{idx:02d} -> 跳过")

    print("[6/8] 整理 cues...")
    cues = []
    for i, ((start, end, text), q) in enumerate(zip(segments, quote_emph)):
        cue: dict = {
            "startFrame": max(0, int(round(start * FPS))),
            "endFrame": min(duration_frames, int(round(end * FPS))),
            "text": text,
            "isQuote": bool(q.get("isQuote")),
            "emphasis": q.get("emphasis", []),
        }
        if i in image_for_idx and not cue["isQuote"]:
            cue["imageSrc"] = image_for_idx[i]
            cue["imageMode"] = "corner"
        cues.append(cue)

    print("[7/8] 拷视频 + 抽封面...")
    public_dir = ROOT / "public"
    public_dir.mkdir(exist_ok=True)
    dst_video = public_dir / "source.mp4"
    shutil.copyfile(src, dst_video)
    cover_bg = public_dir / "cover_bg.jpg"
    cover_t = max(0.5, duration * 0.32)
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", f"{cover_t:.3f}", "-i", str(dst_video),
            "-frames:v", "1", "-q:v", "2", str(cover_bg),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("[8/8] 写 src/realCuesV6.ts")
    cover_frames = COVER_FRAMES
    total_frames = duration_frames + cover_frames
    cues_ts = ROOT / "src" / "realCuesV6.ts"
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
        "emotionMode": True,
        "width": vid_w,
        "height": vid_h,
    }
    body = (
        "// Auto-generated by make_cues_v6.py — do not edit by hand.\n"
        "import type { SubtitleProps } from './SubtitleWithImages';\n\n"
        "export const realPropsV6: SubtitleProps = "
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + " as unknown as SubtitleProps;\n"
    )
    cues_ts.write_text(body, encoding="utf-8")

    print(f"\nV6 情感纪实版完成。共 {len(image_for_idx)} 张图 / {n_quotes} 句金句。")


if __name__ == "__main__":
    main()
