"""ASS 字幕生成（白字 + 黑色圆角底框）+ ffmpeg 烧录。"""
from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import (
    CHAPTER_BAR_BG_ACTIVE,
    CHAPTER_BAR_BG_INACTIVE,
    CHAPTER_BAR_DIVIDER,
    CHAPTER_BAR_DIVIDER_WIDTH,
    CHAPTER_BAR_ENABLED,
    CHAPTER_BAR_FONT_BORDER_RATIO,
    CHAPTER_BAR_FONT_RATIO,
    CHAPTER_BAR_HEIGHT_RATIO,
    CHAPTER_BAR_TEXT_BORDER_COLOR,
    CHAPTER_BAR_TEXT_COLOR,
    CHAPTER_BAR_TOP_SHADOW_PX,
    ENCODE_AUDIO_BITRATE,
    ENCODE_CRF,
    ENCODE_PRESET,
    FONT_NAME,
    FONT_PATH,
    FONTS_DIR,
    PROGRESS_BAR_BG,
    PROGRESS_BAR_ENABLED,
    PROGRESS_BAR_FG,
    PROGRESS_BAR_HEIGHT_RATIO,
    SPLIT_PUNCT,
    SUB_BACK_ALPHA,
    SUB_BOTTOM_MARGIN_RATIO,
    SUB_FONT_SIZE_RATIO,
    SUB_MAX_CHARS_PER_LINE,
    SUB_OUTLINE,
    SUB_SIDE_MARGIN_RATIO,
)


def _ff_text_escape(s: str) -> str:
    """drawtext text 参数里需要转义的字符。"""
    return (
        s.replace("\\", "\\\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
    )


def _chapter_bar_clauses(
    chapters: list[dict], video_w: int, video_h: int, duration: float,
) -> list[str]:
    """章节进度条：顶部一条横条，分段，当前段高亮，每段中间一个标题。
    chapters: [{"title": str, "start": float, "end": float}, ...]
    """
    if not CHAPTER_BAR_ENABLED or not chapters or duration <= 0:
        return []
    bar_h = max(int(video_h * CHAPTER_BAR_HEIGHT_RATIO), 40)
    font_size = max(int(bar_h * CHAPTER_BAR_FONT_RATIO), 18)
    border_w = max(int(font_size * CHAPTER_BAR_FONT_BORDER_RATIO), 2)
    div_w = max(CHAPTER_BAR_DIVIDER_WIDTH, 1)
    shadow_h = max(CHAPTER_BAR_TOP_SHADOW_PX, 1)
    font_path_escaped = str(FONT_PATH).replace("\\", "\\\\").replace(":", r"\:")
    clauses: list[str] = []
    # 1) 全宽底色（深灰，未选中段都是这个色）
    clauses.append(
        f"drawbox=x=0:y=0:w=iw:h={bar_h}"
        f":color={CHAPTER_BAR_BG_INACTIVE}:t=fill"
    )
    # 2) 当前段高亮：每章节一个 drawbox，用 enable 表达式按 t 切换
    for c in chapters:
        s = max(0.0, float(c["start"]))
        e = min(float(duration), float(c["end"]))
        if e <= s:
            continue
        x_px = int(s / duration * video_w)
        w_px = max(int((e - s) / duration * video_w), 1)
        # enable 表达式里逗号必须转义，否则 ffmpeg 当滤镜分隔
        clauses.append(
            f"drawbox=x={x_px}:y=0:w={w_px}:h={bar_h}"
            f":color={CHAPTER_BAR_BG_ACTIVE}:t=fill"
            rf":enable=between(t\,{s:.3f}\,{e:.3f})"
        )
    # 3) 段间分隔（垂直细白线）
    for c in chapters[:-1]:
        e = min(float(duration), float(c["end"]))
        x_div = int(e / duration * video_w) - div_w // 2
        clauses.append(
            f"drawbox=x={x_div}:y=0:w={div_w}:h={bar_h}"
            f":color={CHAPTER_BAR_DIVIDER}:t=fill"
        )
    # 4) 顶部细暗线（章节条上沿阴影感）
    clauses.append(
        f"drawbox=x=0:y=0:w=iw:h={shadow_h}:color=black@0.4:t=fill"
    )
    # 5) 每段标题（楷体描边白字；文字水平居中于该段）
    for c in chapters:
        s = max(0.0, float(c["start"]))
        e = min(float(duration), float(c["end"]))
        if e <= s:
            continue
        cx = int((s + e) / 2 / duration * video_w)
        title = _ff_text_escape(str(c["title"])[:6])
        clauses.append(
            f"drawtext=fontfile={font_path_escaped}:text='{title}'"
            f":x={cx}-text_w/2:y={bar_h // 2}-text_h/2"
            f":fontsize={font_size}"
            f":fontcolor={CHAPTER_BAR_TEXT_COLOR}"
            f":bordercolor={CHAPTER_BAR_TEXT_BORDER_COLOR}"
            f":borderw={border_w}"
        )
    return clauses


def _progress_bar_subgraph(video_h: int, duration: float) -> tuple[str, str, str]:
    """返回三段 filtergraph 片段：(主链尾的 split, bar 子链, overlay 起始)。
    drawbox 在 ffmpeg 8 不会每帧重求表达式；改用 split→crop→geq→overlay：
    geq 只对底部 bar_h 行计算（每像素），保证进度条随 t 线性增长。
    bar 的非进度区按原像素 *0.4 暗化模拟半透明黑底。
    """
    bar_h = max(int(video_h * PROGRESS_BAR_HEIGHT_RATIO), 8)
    dur = max(duration, 0.001)
    head = "split=2[main][bar]"
    sub = (
        f"[bar]crop=iw:{bar_h}:0:ih-{bar_h},"
        f"geq="
        f"r='if(lte(X,W*T/{dur:.3f}),255,r(X,Y)*0.4)':"
        f"g='if(lte(X,W*T/{dur:.3f}),255,g(X,Y)*0.4)':"
        f"b='if(lte(X,W*T/{dur:.3f}),255,b(X,Y)*0.4)'"
        "[bar2]"
    )
    tail = "[main][bar2]overlay=0:H-h"
    return head, sub, tail


def probe_size(path: Path) -> tuple[int, int]:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", str(path),
    ]).decode().strip()
    w, h = out.split("x")
    return int(w), int(h)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(path),
    ]).decode().strip()
    return float(out) if out else 0.0


def has_audio(path: Path) -> bool:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=nokey=1:noprint_wrappers=1", str(path),
    ]).decode().strip()
    return out == "audio"


def _split_text(text: str, max_len: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    lines: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in SPLIT_PUNCT and len(cur) >= max_len * 0.6:
            lines.append(cur.strip(" "))
            cur = ""
    if cur.strip():
        lines.append(cur.strip(" "))
    final: list[str] = []
    for ln in lines:
        if len(ln) <= max_len:
            final.append(ln)
            continue
        n = (len(ln) + max_len - 1) // max_len
        part_len = (len(ln) + n - 1) // n
        for i in range(0, len(ln), part_len):
            chunk = ln[i:i + part_len]
            if chunk:
                final.append(chunk)
    return [ln for ln in final if ln]


_TRIM_PUNCT = " ，。,.、；;：:"


def _strip_trim_punct(s: str) -> str:
    return s.strip(_TRIM_PUNCT)


def split_segments(
    raw: list[tuple[float, float, str]], max_len: int = SUB_MAX_CHARS_PER_LINE
) -> list[tuple[float, float, str]]:
    """把每段切成若干 *单行* 短句，按字数比例瓜分时间。不再叠多行。"""
    out: list[tuple[float, float, str]] = []
    for start, end, text in raw:
        chunks = [_strip_trim_punct(x) for x in _split_text(text, max_len)]
        chunks = [c for c in chunks if c]
        if not chunks:
            continue
        if len(chunks) == 1:
            out.append((start, end, chunks[0]))
            continue
        dur = max(end - start, 0.001)
        total = sum(len(x) for x in chunks)
        t = start
        for i, c in enumerate(chunks):
            if i == len(chunks) - 1:
                out.append((t, end, c))
            else:
                seg_dur = dur * len(c) / total
                out.append((t, t + seg_dur, c))
                t += seg_dur
    return out


def _ass_time(s: float) -> str:
    if s < 0:
        s = 0
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s - h * 3600 - m * 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def build_ass(segments: list[tuple[float, float, str]], w: int, h: int) -> str:
    font_size = max(int(h * SUB_FONT_SIZE_RATIO), 20)
    margin_v = max(int(h * SUB_BOTTOM_MARGIN_RATIO), 20)
    margin_side = max(int(w * SUB_SIDE_MARGIN_RATIO), 30)
    # BackColour 高字节 = alpha；ASS 格式 &HAABBGGRR
    back = f"&H{SUB_BACK_ALPHA:02X}000000"
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {w}\n"
        f"PlayResY: {h}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{FONT_NAME},{font_size},&H00FFFFFF,&H000000FF,"
        f"&H00000000,{back},1,0,0,0,100,100,0,0,3,{SUB_OUTLINE},0,2,"
        f"{margin_side},{margin_side},{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )
    events = [
        f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Default,,0,0,0,,{text}\n"
        for a, b, text in segments
    ]
    return header + "".join(events)


def build_srt(segments: list[tuple[float, float, str]]) -> str:
    def _srt_time(s: float) -> str:
        if s < 0:
            s = 0
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = s - h * 3600 - m * 60
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{int(sec):02d},{ms:03d}"

    out = []
    for i, (a, b, t) in enumerate(segments, 1):
        # SRT 里用换行；ASS 是 \N
        text = t.replace(r"\N", "\n")
        out.append(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{text}\n\n")
    return "".join(out)


def _sub_filter_clause(ass: Path) -> str:
    ass_escaped = str(ass).replace(":", r"\:").replace("'", r"\'")
    sf = f"subtitles='{ass_escaped}'"
    if FONTS_DIR.exists():
        fdir = str(FONTS_DIR).replace(":", r"\:")
        sf += f":fontsdir='{fdir}'"
    return sf


# 所有中间产物共用的严格编码参数（保证 concat stream-copy 能拼）
_V_COMMON = [
    "-c:v", "libx264", "-preset", ENCODE_PRESET, "-crf", str(ENCODE_CRF),
    "-pix_fmt", "yuv420p", "-video_track_timescale", "90000",
    "-profile:v", "high", "-level", "4.0",
]
_A_COMMON = [
    "-c:a", "aac", "-b:a", ENCODE_AUDIO_BITRATE,
    "-ar", "44100", "-ac", "2",
]


def burn_subtitles_only(
    video_in: Path,
    ass: Path | None,
    video_out: Path,
    has_audio_flag: bool,
    duration: float = 0.0,
    video_h: int = 0,
    video_w: int = 0,
    chapters: list[dict] | None = None,
) -> None:
    """烧字幕 + 顶部章节进度条（如有 chapters）+ 可选底部填充式进度条。
    产出作为后续拼封面的"raw"。
    强制 30fps / H.264 high@4.0 / yuv420p / SAR 1:1 / 音频 aac 44.1k stereo。
    """
    main_chain: list[str] = []
    if ass:
        main_chain.append(_sub_filter_clause(ass))
    if chapters and video_w > 0 and video_h > 0 and duration > 0:
        main_chain += _chapter_bar_clauses(chapters, video_w, video_h, duration)
    use_fill_bar = (
        PROGRESS_BAR_ENABLED and video_h > 0 and duration > 0
    )
    tail_chain = ["setsar=1", "fps=30", "format=yuv420p"]
    if use_fill_bar:
        head, sub, tail = _progress_bar_subgraph(video_h, duration)
        main_chain.append(head)
        merged_tail = ",".join([tail, *tail_chain])
        fg = ";".join([",".join(main_chain), sub, merged_tail])
    else:
        fg = ",".join([*main_chain, *tail_chain])
    cmd = [
        "ffmpeg", "-y", "-i", str(video_in),
        "-vf", fg,
        *_V_COMMON,
    ]
    if has_audio_flag:
        cmd += _A_COMMON
    cmd += ["-movflags", "+faststart", str(video_out)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def make_cover_clip(
    cover: Path, w: int, h: int,
    has_audio_flag: bool, out: Path,
    duration: float = 0.04,
) -> None:
    """把封面图编成 ~1 帧的 mp4，参数与 burn_subtitles_only 一致（便于拼接）。"""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{duration}", "-i", str(cover),
    ]
    if has_audio_flag:
        cmd += [
            "-f", "lavfi", "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", f"{duration}",
        ]
    cmd += [
        "-vf",
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p",
        *_V_COMMON,
    ]
    if has_audio_flag:
        cmd += _A_COMMON + ["-shortest"]
    cmd += [str(out)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _concat_stream_copy(parts: list[Path], out: Path) -> None:
    list_file = out.parent / ".concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in parts) + "\n",
        encoding="utf-8",
    )
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy", "-movflags", "+faststart",
            str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    finally:
        if list_file.exists():
            list_file.unlink()


def apply_cover_to_raw(
    cover: Path, raw: Path, video_out: Path,
    w: int, h: int, has_audio_flag: bool,
) -> None:
    """把封面贴到 raw 视频第一帧。
    先用一致参数编出 cover_clip.mp4，再 concat stream-copy → 秒级完成。
    """
    clip = video_out.parent / ".cover_clip.mp4"
    try:
        make_cover_clip(cover, w, h, has_audio_flag, clip)
        _concat_stream_copy([clip, raw], video_out)
    finally:
        if clip.exists():
            clip.unlink()
