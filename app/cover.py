"""封面合成：精彩帧底图 + 顶部大标题（白字 + 黑粗描边）。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import (
    COVER_FONT_INDEX,
    COVER_FONT_PATH,
    TITLE_BASE_FONT_RATIO,
    TITLE_BIG_FONT_RATIO,
    TITLE_CENTER_Y_RATIO,
    TITLE_ITALIC_SHEAR,
    TITLE_MAX_CHARS,
    TITLE_MAX_WIDTH_RATIO,
    TITLE_MID_FONT_RATIO,
    TITLE_SMALL_FONT_RATIO,
    TITLE_STROKE_RATIO,
)


def _load_cover_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(COVER_FONT_PATH), size, index=COVER_FONT_INDEX)


def _italicize(layer: Image.Image, shear: float) -> Image.Image:
    """对 RGBA 图层做水平剪切，模拟斜体（底部不动、顶部右倾）。"""
    if shear <= 0:
        return layer
    w, h = layer.size
    extra = int(shear * h)
    canvas = Image.new("RGBA", (w + extra, h), (0, 0, 0, 0))
    canvas.paste(layer, (0, 0))
    return canvas.transform(
        (w + extra, h),
        Image.AFFINE,
        (1, shear, -shear * h, 0, 1, 0),
        resample=Image.BICUBIC,
    )


def normalize_title(raw: str) -> str:
    """清掉标点/空格/引号，截断到 6 字。"""
    if not raw:
        return ""
    bad = set("，。！？,.!?、；;：:\"'\"\"''《》<>()（）[]【】 \t\n—-…·")
    cleaned = "".join(ch for ch in raw.strip() if ch not in bad)
    return cleaned[:TITLE_MAX_CHARS]


def _pick_font_ratio(n_chars: int) -> float:
    if n_chars <= 2:
        return TITLE_BIG_FONT_RATIO
    if n_chars <= 4:
        return TITLE_MID_FONT_RATIO
    return TITLE_BASE_FONT_RATIO


def _fit_font(
    draw: ImageDraw.ImageDraw, text: str, img_w: int, img_h: int
) -> tuple[ImageFont.FreeTypeFont, int, int, int]:
    """返回 (font, text_w, text_h, stroke_w)。"""
    n = len(text)
    max_text_w = int(img_w * TITLE_MAX_WIDTH_RATIO)
    ratio = _pick_font_ratio(n)
    for attempt in range(6):
        font_size = max(int(img_h * ratio), 20)
        font = _load_cover_font(font_size)
        stroke = max(int(font_size * TITLE_STROKE_RATIO), 2)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= max_text_w:
            return font, tw, th, stroke
        # 超宽 → 降档
        ratio *= 0.9
    # 兜底：以最小比例返回
    font_size = max(int(img_h * TITLE_SMALL_FONT_RATIO * 0.8), 20)
    font = _load_cover_font(font_size)
    stroke = max(int(font_size * TITLE_STROKE_RATIO), 2)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    return font, bbox[2] - bbox[0], bbox[3] - bbox[1], stroke


def compose_cover(
    base_frame: Path, title: str, out_path: Path
) -> dict:
    """在 base_frame 上合成标题（楷体 + 描边 + 合成斜体），写出 out_path。返回 meta。"""
    title = normalize_title(title)
    if not title:
        title = "视频"
    img = Image.open(base_frame).convert("RGBA")
    w, h = img.size
    measure = ImageDraw.Draw(img)
    font, tw, th, stroke = _fit_font(measure, title, w, h)

    bbox = measure.textbbox((0, 0), title, font=font, stroke_width=stroke)
    pad = stroke + 4
    layer_w = bbox[2] - bbox[0] + pad * 2
    layer_h = bbox[3] - bbox[1] + pad * 2
    layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(
        (pad - bbox[0], pad - bbox[1]),
        title,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=stroke,
        stroke_fill=(0, 0, 0, 255),
    )

    layer = _italicize(layer, TITLE_ITALIC_SHEAR)
    final_w, final_h = layer.size
    center_y = int(h * TITLE_CENTER_Y_RATIO)
    x = (w - final_w) // 2
    y = center_y - final_h // 2
    img.alpha_composite(layer, (x, y))
    img.convert("RGB").save(out_path, quality=92)
    return {
        "title": title,
        "title_chars": len(title),
        "font_size": font.size,
        "stroke_width": stroke,
        "italic_shear": TITLE_ITALIC_SHEAR,
        "text_w": tw,
        "text_h": th,
        "img_w": w,
        "img_h": h,
        "center_y_ratio": round(center_y / h, 3),
    }
