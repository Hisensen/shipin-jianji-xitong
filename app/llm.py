"""调 DeepSeek 生成 ≤6 字爆款标题；以及视频章节切分。失败/无 key 降级。"""
from __future__ import annotations

import json
import logging
import re

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    TITLE_MAX_CHARS,
)
from app.cover import normalize_title

log = logging.getLogger(__name__)

SYSTEM = (
    "你是爆款短视频标题撰稿人。读视频转录，产一条抓眼球的中文标题。"
    "严格要求：仅 1-6 个汉字；不要标点；不要空格；不要引号；不要前后缀。"
    "只输出标题本身，不要别的。"
)


def _call_deepseek(transcript: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, max_retries=5)
    user = f"视频转录如下，给一个 1-6 字爆款标题：\n\n{transcript[:1500]}"
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=30,
    )
    return (resp.choices[0].message.content or "").strip()


def _fallback_from_transcript(transcript: str) -> str:
    """没 key 或调用失败时：取转录头部清洗后前 6 字。"""
    t = transcript.strip()
    clean = normalize_title(t)
    return clean or "视频"


CHAPTER_SYSTEM = (
    "你是短视频章节切分专家。基于带时间戳的字幕，把视频分成 3-5 段叙事章节，"
    "每段给一个简洁有力的中文小标题（2-6 个汉字，不带标点空格），并给出每段的起止秒数。"
    "标题要概括该段核心内容，常用词如：现状痛点 / 底层逻辑 / 路径方法 / 案例 / 总结 / 对比。"
)


def _call_deepseek_chapters(transcript_with_ts: str, duration: float) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, max_retries=5)
    user = (
        f"视频总时长 {duration:.1f} 秒。下面是带时间戳的字幕：\n\n"
        f"{transcript_with_ts[:3500]}\n\n"
        "请输出 3-5 段章节的 JSON 数组，格式："
        '[{"title":"现状痛点","start":0,"end":12.5},{"title":"底层逻辑","start":12.5,"end":40},...]'
        f"\n要求：段必须连续覆盖 0 到 {duration:.1f} 秒，标题 2-6 个汉字。"
        "只输出 JSON 数组本身，不要 markdown 代码块、不要前后说明。"
    )
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": CHAPTER_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=400,
    )
    return (resp.choices[0].message.content or "").strip()


def _normalize_chapters(
    raw_list: list, duration: float
) -> list[dict] | None:
    valid: list[dict] = []
    for c in raw_list:
        if not isinstance(c, dict):
            continue
        title = str(c.get("title", "")).strip()
        try:
            s = float(c.get("start", 0))
            e = float(c.get("end", 0))
        except (TypeError, ValueError):
            continue
        if not title or e <= s:
            continue
        # 标题去标点、截断到 6 字
        title = re.sub(r"[\s，。！？,.!?、；;：:'\"《》<>()（）\[\]【】—\-…·]", "", title)[:6]
        if not title:
            continue
        valid.append({
            "title": title,
            "start": max(0.0, s),
            "end": min(duration, e),
        })
    if len(valid) < 2:
        return None
    valid.sort(key=lambda c: c["start"])
    # 拉伸首尾到 0/duration，并把相邻段衔接（避免缝隙/重叠）
    valid[0]["start"] = 0.0
    valid[-1]["end"] = duration
    for i in range(len(valid) - 1):
        valid[i]["end"] = valid[i + 1]["start"]
    return valid[:5]


def _fallback_chapters(duration: float) -> list[dict]:
    """无 AI 时按时长均分 4 段，给通用标题。"""
    titles = ["开场", "展开", "深入", "总结"]
    n = 4
    seg = duration / n
    return [
        {"title": titles[i], "start": i * seg, "end": (i + 1) * seg}
        for i in range(n)
    ]


def extract_chapters(
    segments: list[tuple[float, float, str]],
    duration: float,
) -> tuple[list[dict], str]:
    """返回 (chapters, source)。source ∈ {deepseek, fallback}。"""
    if duration <= 0:
        return [], "fallback"
    if not segments or not DEEPSEEK_API_KEY:
        return _fallback_chapters(duration), "fallback"
    transcript = "\n".join(f"[{a:.1f}s] {t}" for a, _, t in segments)
    try:
        raw = _call_deepseek_chapters(transcript, duration)
        # 去 markdown 围栏
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("not a list")
        chapters = _normalize_chapters(parsed, duration)
        if not chapters:
            raise ValueError("normalize empty")
        return chapters, "deepseek"
    except Exception as e:
        log.warning("DeepSeek extract_chapters 失败 (%s)，降级均分", e)
        return _fallback_chapters(duration), "fallback"


def generate_title(transcript: str) -> tuple[str, str]:
    """返回 (title, source)。source ∈ {deepseek, fallback}。"""
    if not transcript.strip():
        return "视频", "fallback"
    if not DEEPSEEK_API_KEY:
        log.warning("DEEPSEEK_API_KEY 未设置，降级用转录头部")
        return _fallback_from_transcript(transcript), "fallback"
    try:
        raw = _call_deepseek(transcript)
        cleaned = normalize_title(raw)
        if not cleaned:
            log.warning("DeepSeek 返回空/全是标点，降级")
            return _fallback_from_transcript(transcript), "fallback"
        if len(cleaned) > TITLE_MAX_CHARS:
            cleaned = cleaned[:TITLE_MAX_CHARS]
        return cleaned, "deepseek"
    except Exception as e:
        log.exception("DeepSeek 调用失败: %s", e)
        return _fallback_from_transcript(transcript), "fallback"
