"""字幕 → 关键词 → Pexels 搜图 → 下载到本地。"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import httpx

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

log = logging.getLogger(__name__)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
PEXELS_SEARCH = "https://api.pexels.com/v1/search"

KEYWORD_SYSTEM = (
    "你是图库搜图关键词生成器。给一组中文短句，为每句生成一个英文关键词，"
    "用于在 Pexels 图库搜配图。要求：1-3 个英文单词；具象、可视化、避免抽象；"
    "情绪/动作类优先（如 angry man, sad woman, couple argue, broken heart）。"
    "输出严格 JSON 数组，长度等于输入句数，元素是字符串。不要 markdown 围栏。"
)

PICK_SYSTEM = (
    "你是口播短视频导演。给一组按时间排列的中文字幕，从中精挑 2-4 句最适合配辅助图片的"
    "（这是真人口播视频，背景是人在讲话，图只作短暂强调，不能抢戏）。"
    "评判标准：(a) 句子有具象画面感（人物、动作、场景） (b) 是核心论点或情绪高点 "
    "(c) 不是承接/总结/连接句（如'所以说'、'就这么简单'、'因为这样'）。"
    "输出严格 JSON 数组：[{\"index\": 0, \"keyword\": \"angry man\"}, ...]。"
    "index 是输入句子的 0-based 序号。最多 4 项，最少 2 项。不要 markdown 围栏。"
)


FORM_SYSTEM = (
    "你是爆款短视频特效导演。给一组中文字幕，为有视觉强化必要的句子决定形式："
    "(1) image: 配实物/人物/场景图 — 给英文搜图关键词。 "
    "(2) callout: 大字卡片强调核心概念 — 给 emoji + 4 字内中文 + 底色（red/green/yellow/blue/purple/orange）。 "
    "(3) emoji: 单 emoji 装饰情绪/动作 — 给 emoji。 "
    "**视觉密度要求**：约 25-35% 句子用 image、15-25% 用 callout、30-40% 用 emoji。"
    "**只输出有形式的项，跳过 none**（纯承接连接词如'所以说'、'就这么简单'就跳过）。"
    "分布交错有节奏，不要连续 3 句同形式。"
    "输出严格 JSON 数组，每项："
    '{"index":0,"form":"image","keyword":"angry man"} / '
    '{"index":4,"form":"callout","emoji":"❌","text":"PUA","color":"red"} / '
    '{"index":7,"form":"emoji","emoji":"💔"}。'
    "按 index 升序。不要 markdown 围栏。"
)


QUOTE_SYSTEM = (
    "你是抖音爆款短视频金句策划。给一组中文字幕，做两件事："
    "(1) 从中挑 1-3 个最具冲击力的「金句」（短≤14字、情绪饱满/观点犀利、转发欲望强、非承接解释句）。"
    "(2) 为有需要强调的字幕标出 1-2 个汉字关键词（必须是该句已出现的字符）。"
    "**只输出有内容的项**：没有金句也没有强调词的句子直接跳过，不要写进数组。"
    "输出严格 JSON 数组，每项："
    '{"index":5,"isQuote":true,"emphasis":["滚"]} 或 {"index":3,"emphasis":["贬低"]}。'
    "isQuote 至多 3 项为 true。不要 markdown 围栏。"
)


def pick_quotes_and_emphasis(texts: list[str]) -> list[dict]:
    """每句返回 {"isQuote": bool, "emphasis": [...]}，长度 == len(texts)。无 key 时全 false。"""
    if not texts:
        return []
    fallback = [{"isQuote": False, "emphasis": []} for _ in texts]
    if not DEEPSEEK_API_KEY:
        return fallback
    try:
        from openai import OpenAI

        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        user = "字幕：\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": QUOTE_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        raw = (resp.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        items = json.loads(raw)
        out = [{"isQuote": False, "emphasis": []} for _ in texts]
        n_quotes = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            idx = it.get("index")
            if not isinstance(idx, int) or not (0 <= idx < len(texts)):
                continue
            is_q = bool(it.get("isQuote", False)) and n_quotes < 3
            if is_q:
                n_quotes += 1
            emphasis = it.get("emphasis", [])
            if not isinstance(emphasis, list):
                emphasis = []
            # 只保留实际出现在原句里的关键词
            text = texts[idx]
            emphasis = [str(w).strip() for w in emphasis if str(w).strip() and str(w).strip() in text]
            out[idx] = {"isQuote": is_q, "emphasis": emphasis[:2]}
        return out
    except Exception as e:
        log.warning("pick_quotes_and_emphasis 失败 (%s)，全部 false", e)
        return fallback


CALLOUT_COLORS = {
    "red": ("#FF3838", "#FFFFFF"),
    "green": ("#10B981", "#FFFFFF"),
    "yellow": ("#FACC15", "#1F2937"),
    "blue": ("#3B82F6", "#FFFFFF"),
    "purple": ("#A855F7", "#FFFFFF"),
    "orange": ("#F97316", "#FFFFFF"),
}


def _decide_forms_one_batch(
    texts: list[str], offset: int, total: int
) -> list[dict]:
    """对一批字幕做 form 决策。texts 是这一批，offset 是这批在全局的起点。
    返回稀疏决策（只含有形式的，索引是全局索引）。
    """
    from openai import OpenAI

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    user = (
        f"全片共 {total} 句。这是第 {offset+1}-{offset+len(texts)} 句：\n"
        + "\n".join(f"{offset + i}. {t}" for i, t in enumerate(texts))
    )
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": FORM_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    raw = (resp.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    return json.loads(raw)


def decide_per_cue_forms(texts: list[str]) -> list[dict]:
    """每句返回一个 form 决策 dict，长度 == len(texts)。分批调用避免输出截断。"""
    if not texts:
        return []
    fallback = [{"form": "none"} for _ in texts]
    if not DEEPSEEK_API_KEY:
        log.warning("DEEPSEEK_API_KEY 未设置，全部 none")
        return fallback

    out: list[dict] = [{"form": "none"} for _ in texts]
    BATCH = 50
    for batch_start in range(0, len(texts), BATCH):
        batch_texts = texts[batch_start:batch_start + BATCH]
        try:
            items = _decide_forms_one_batch(batch_texts, batch_start, len(texts))
        except Exception as e:
            log.warning("decide_per_cue_forms 第 %d 批失败 (%s)", batch_start, e)
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            idx = it.get("index")
            if not isinstance(idx, int) or not (0 <= idx < len(texts)):
                continue
            form = str(it.get("form", "none"))
            if form == "image":
                kw = str(it.get("keyword", "")).strip()
                out[idx] = {"form": "image", "keyword": kw}
            elif form == "callout":
                color = str(it.get("color", "yellow")).lower()
                if color not in CALLOUT_COLORS:
                    color = "yellow"
                out[idx] = {
                    "form": "callout",
                    "emoji": str(it.get("emoji", "")).strip()[:4],
                    "text": str(it.get("text", "")).strip()[:6],
                    "color": color,
                }
            elif form == "emoji":
                out[idx] = {"form": "emoji", "emoji": str(it.get("emoji", "")).strip()[:4]}
    return out


def pick_image_cues(texts: list[str]) -> list[tuple[int, str]]:
    """让 LLM 从字幕里挑 2-4 句关键句，返回 [(index, english_keyword), ...]。

    无 key/失败时降级：每隔几句挑一句，关键词留空（不会真的去搜图）。
    """
    if not texts:
        return []
    if not DEEPSEEK_API_KEY:
        log.warning("DEEPSEEK_API_KEY 未设置，按等距挑 3 句兜底")
        n = len(texts)
        if n <= 3:
            return [(i, "") for i in range(n)]
        idxs = [int(i * (n - 1) / 2) for i in range(3)]
        return [(i, "") for i in sorted(set(idxs))]
    try:
        from openai import OpenAI

        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        user = "字幕（按时间）：\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": PICK_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        raw = (resp.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        items = json.loads(raw)
        out: list[tuple[int, str]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            idx = it.get("index")
            kw = str(it.get("keyword", "")).strip()
            if not isinstance(idx, int) or not (0 <= idx < len(texts)):
                continue
            out.append((idx, kw))
        out = out[:4]
        if len(out) < 2:
            raise ValueError(f"挑出的句数太少 {len(out)}")
        return out
    except Exception as e:
        log.warning("pick_image_cues 失败 (%s)，降级等距挑 3 句", e)
        n = len(texts)
        idxs = [int(i * (n - 1) / 2) for i in range(3)]
        return [(i, "") for i in sorted(set(idxs))]


def extract_keywords(texts: list[str]) -> list[str]:
    """每句出一个英文搜图关键词。无 key/失败则降级返回空字符串。"""
    if not DEEPSEEK_API_KEY:
        log.warning("DEEPSEEK_API_KEY 未设置，关键词全空")
        return [""] * len(texts)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        user = "句子列表（按顺序）：\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": KEYWORD_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        raw = (resp.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        kws = json.loads(raw)
        if not isinstance(kws, list) or len(kws) != len(texts):
            raise ValueError(f"长度不匹配 {len(kws)} vs {len(texts)}")
        return [str(k).strip() for k in kws]
    except Exception as e:
        log.warning("提关键词失败 (%s)，降级空关键词", e)
        return [""] * len(texts)


def search_pexels(keyword: str, orientation: str = "portrait") -> str | None:
    """返回首张图的 src.large URL，失败返回 None。"""
    if not PEXELS_API_KEY or not keyword:
        return None
    try:
        with httpx.Client(timeout=15) as c:
            r = c.get(
                PEXELS_SEARCH,
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": keyword, "per_page": 1, "orientation": orientation},
            )
            r.raise_for_status()
            data = r.json()
            photos = data.get("photos") or []
            if not photos:
                return None
            return photos[0]["src"]["large"]
    except Exception as e:
        log.warning("Pexels 搜 %r 失败: %s", keyword, e)
        return None


def download(url: str, dst: Path) -> bool:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
            dst.write_bytes(r.content)
        return True
    except Exception as e:
        log.warning("下载 %s 失败: %s", url, e)
        return False
