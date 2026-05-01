"""串流水线：视频 → 字幕视频 + 封面图 + meta。"""
from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import (
    DELETE_SOURCE_ON_DONE,
    OUTPUT_DIR,
    VIDEO_EXTS,
    assert_font_exists,
)
from app.cover import compose_cover
from app.frames import pick_best_frame, write_pick_reason
from app.llm import extract_chapters, generate_title
from app.subtitle import (
    apply_cover_to_raw,
    build_ass,
    build_srt,
    burn_subtitles_only,
    has_audio,
    probe_duration,
    probe_size,
    split_segments,
)
from app.transcribe import transcribe


@dataclass
class Result:
    stem: str
    out_dir: Path
    video_sub: Path
    cover: Path
    srt: Path
    meta_path: Path
    meta: dict
    ok: bool
    error: str = ""


def _setup_file_logger(log_path: Path) -> tuple[logging.Logger, logging.FileHandler]:
    logger = logging.getLogger(f"pipeline.{log_path.stem}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    # 同时打到 stdout
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("  [%(levelname)s] %(message)s"))
    logger.addHandler(sh)
    return logger, handler


def process_one(video: Path, *, override_title: str | None = None) -> Result:
    """处理一条视频；产物落在 output/{stem}/。"""
    assert_font_exists()
    if video.suffix.lower() not in VIDEO_EXTS:
        raise ValueError(f"不支持的扩展名: {video.suffix}")
    stem = video.stem
    out_dir = OUTPUT_DIR / stem
    # 清掉旧产物（重入）
    if out_dir.exists():
        shutil.rmtree(out_dir)
    tmp_dir = OUTPUT_DIR / f".{stem}.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    debug_dir = tmp_dir / "debug"
    cand_dir = debug_dir / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    log_path = debug_dir / "pipeline.log"
    logger, fh = _setup_file_logger(log_path)
    t0 = time.time()
    meta: dict = {"stem": stem, "source": str(video)}
    try:
        logger.info("=== 开始处理 %s ===", video)
        duration = probe_duration(video)
        w, h = probe_size(video)
        meta.update({"duration": round(duration, 2), "width": w, "height": h})
        logger.info("时长 %.2fs  分辨率 %dx%d", duration, w, h)
        if duration < 1.0:
            raise RuntimeError(f"视频过短 ({duration:.2f}s)")

        # 1) 转录
        if has_audio(video):
            logger.info("转录中...")
            raw_segs, lang = transcribe(video)
            meta["language"] = lang
            logger.info("识别 %d 段  语言=%s", len(raw_segs), lang)
        else:
            logger.warning("无音频，跳过字幕")
            raw_segs, lang = [], ""
            meta["language"] = ""
            meta["warning_no_audio"] = True
        segs = split_segments(raw_segs)
        meta["subtitle_count"] = len(segs)

        # 2) 挑帧（先挑帧，封面要先于烧录生成）
        logger.info("挑精彩帧中...")
        best, top = pick_best_frame(video, duration, cand_dir)
        write_pick_reason(best, top, debug_dir / "pick_reason.txt")
        meta["cover_frame_time"] = round(best.time, 3)
        meta["cover_pick_score"] = round(best.score, 3)
        meta["cover_candidates"] = [c.to_dict() for c in top]
        logger.info("选中 %.2fs  clarity=%.1f  face=%s",
                    best.time, best.clarity, best.has_face)

        # 3) 标题
        if override_title:
            title, title_source = override_title, "override"
        else:
            transcript_text = " ".join(t for _, _, t in raw_segs)
            title, title_source = generate_title(transcript_text)
        logger.info("标题: %s (来源: %s)", title, title_source)
        meta["title"] = title
        meta["title_source"] = title_source

        # 4) 封面
        cover_path = tmp_dir / f"{stem}_cover.jpg"
        cover_meta = compose_cover(best.path, title, cover_path)
        meta["cover"] = cover_meta

        # 5a) AI 提取章节
        chapters, chapter_src = extract_chapters(raw_segs, duration)
        meta["chapters"] = chapters
        meta["chapters_source"] = chapter_src
        if chapters:
            titles = " / ".join(c["title"] for c in chapters)
            logger.info("章节 (%s): %s", chapter_src, titles)

        # 5b) 烧字幕 + 顶部章节进度条 → sub_raw.mp4
        has_audio_flag = has_audio(video)
        raw_path = debug_dir / f"{stem}_sub_raw.mp4"
        ass_path: Path | None = None
        if segs:
            ass_path = tmp_dir / f"{stem}.ass"
            ass_path.write_text(build_ass(segs, w, h), encoding="utf-8")
            logger.info("烧字幕 → sub_raw.mp4")
        else:
            logger.info("无字幕，仅编码 → sub_raw.mp4")
        burn_subtitles_only(
            video, ass_path, raw_path, has_audio_flag,
            duration=duration, video_h=h, video_w=w, chapters=chapters,
        )
        if ass_path and ass_path.exists():
            ass_path.unlink()

        # 6) 前置封面帧 → 最终 _sub.mp4（concat stream-copy，秒级）
        video_sub = tmp_dir / f"{stem}_sub.mp4"
        logger.info("拼封面 → %s", video_sub.name)
        apply_cover_to_raw(cover_path, raw_path, video_sub, w, h, has_audio_flag)
        meta["cover_prepended"] = True
        meta["cover_prepend_seconds"] = 0.04
        meta["has_audio"] = has_audio_flag

        # 7) SRT
        srt_path = tmp_dir / f"{stem}.srt"
        srt_path.write_text(build_srt(segs), encoding="utf-8")

        # 8) meta.json
        meta["elapsed"] = round(time.time() - t0, 2)
        meta_path = tmp_dir / f"{stem}.meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        # 原子落地
        fh.close()
        logger.removeHandler(fh)
        tmp_dir.rename(out_dir)

        # 成功后删源视频（按配置）
        if DELETE_SOURCE_ON_DONE:
            try:
                video.unlink()
            except Exception:
                pass

        return Result(
            stem=stem,
            out_dir=out_dir,
            video_sub=out_dir / f"{stem}_sub.mp4",
            cover=out_dir / f"{stem}_cover.jpg",
            srt=out_dir / f"{stem}.srt",
            meta_path=out_dir / f"{stem}.meta.json",
            meta=meta,
            ok=True,
        )
    except Exception as e:
        logger.exception("处理失败: %s", e)
        fh.close()
        logger.removeHandler(fh)
        # 失败：标 .FAILED 目录，保留 log 便于排查
        failed = OUTPUT_DIR / f"{stem}.FAILED"
        if failed.exists():
            shutil.rmtree(failed)
        tmp_dir.rename(failed)
        return Result(
            stem=stem,
            out_dir=failed,
            video_sub=Path(),
            cover=Path(),
            srt=Path(),
            meta_path=Path(),
            meta=meta,
            ok=False,
            error=str(e),
        )


def process_many(videos: list[Path]) -> list[Result]:
    results = []
    for v in videos:
        print(f"\n>>> {v.name}")
        r = process_one(v)
        print(f"    {'✅' if r.ok else '❌ ' + r.error}")
        results.append(r)
    return results


def collect_videos(p: Path) -> list[Path]:
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(x for x in p.iterdir() if x.suffix.lower() in VIDEO_EXTS)
    return []
