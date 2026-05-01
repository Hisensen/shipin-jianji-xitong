"""集中配置：路径、字体、模型、各项视觉参数。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# 目录
INBOX_DIR = ROOT / "samples" / "inbox"
OUTPUT_DIR = ROOT / "output"
LOGS_DIR = ROOT / "logs"
SNAPSHOTS_DIR = ROOT / "snapshots"
REFS_DIR = ROOT / "samples" / "refs"
STATIC_DIR = ROOT / "static"
TEMPLATES_DIR = ROOT / "templates"

for d in (INBOX_DIR, OUTPUT_DIR, LOGS_DIR, SNAPSHOTS_DIR, STATIC_DIR, TEMPLATES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# 字体：字幕用得意黑（年轻向、自带右倾、紧凑），封面用庞门正道标题体（爆款标题字、有书法骨架）
FONT_PATH = ROOT / "fonts" / "SmileySans-Oblique.ttf"
FONT_NAME = "Smiley Sans"
FONTS_DIR = FONT_PATH.parent

# 封面专用字体
COVER_FONT_PATH = ROOT / "fonts" / "PangMen.ttf"
COVER_FONT_INDEX = 0
COVER_FONT_NAME = "PangMenZhengDao"

# Whisper
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
WHISPER_COMPUTE = "int8"

# 字幕视觉（对齐 samples/refs/subtitle_ref.jpg）
SUB_MAX_CHARS_PER_LINE = 12
SUB_FONT_SIZE_RATIO = 0.042        # 字号 / 视频高度
SUB_BOTTOM_MARGIN_RATIO = 0.18     # 底部边距 / 视频高度（对应下方约 82% 位置）
SUB_SIDE_MARGIN_RATIO = 0.06
SUB_OUTLINE = 3                    # opaque box 的 padding（越小越贴字）
SUB_BACK_ALPHA = 0x20              # 底框透明度（0x00=不透明, 0xFF=全透明）
SPLIT_PUNCT = "，。！？,.!?、；;：:"

# 视频底部播放进度条（线性填充式，已被章节条取代，默认关）
PROGRESS_BAR_ENABLED = False
PROGRESS_BAR_HEIGHT_RATIO = 0.012
PROGRESS_BAR_BG = "black@0.5"
PROGRESS_BAR_FG = "white"

# 顶部章节进度条（AI 自动分 3-5 段，每段标题 + 当前段高亮）
CHAPTER_BAR_ENABLED = True
CHAPTER_BAR_HEIGHT_RATIO = 0.055        # 章节条高度 / 视频高（≈5.5%）
CHAPTER_BAR_BG_INACTIVE = "0x3A3A3A"    # 未选中段背景：深灰
CHAPTER_BAR_BG_ACTIVE = "0xE5DDC8"      # 当前段背景：浅米色（高亮）
CHAPTER_BAR_DIVIDER = "white@0.55"      # 段间分隔色
CHAPTER_BAR_DIVIDER_WIDTH = 3           # 段间分隔宽度（px）
CHAPTER_BAR_TEXT_COLOR = "white"
CHAPTER_BAR_TEXT_BORDER_COLOR = "black"
CHAPTER_BAR_FONT_RATIO = 0.62           # 文字高 / 章节条高
CHAPTER_BAR_FONT_BORDER_RATIO = 0.10    # 描边 / 字号
CHAPTER_BAR_TOP_SHADOW_PX = 2           # 顶部细暗线高度

# 封面标题视觉（对齐 samples/refs/title_ref.jpg）
TITLE_MAX_CHARS = 6                # 硬约束
TITLE_CENTER_Y_RATIO = 0.15        # 文字中心线在图高的这一位置（固定）
TITLE_MAX_WIDTH_RATIO = 0.85       # 横向最多占画面宽度
TITLE_BASE_FONT_RATIO = 0.13       # 基础字号（5-6 字时用）
TITLE_SMALL_FONT_RATIO = 0.11      # 5-6 字超宽时降档
TITLE_BIG_FONT_RATIO = 0.17        # 1-2 字时用
TITLE_MID_FONT_RATIO = 0.15        # 3-4 字时用
TITLE_STROKE_RATIO = 0.12          # 描边宽度 / 字号（爆款黑体偏粗描边）
TITLE_ITALIC_SHEAR = 0.0           # 0=不斜（粗黑体不需要斜体）

# 挑帧
FRAME_CANDIDATE_COUNT = 20         # 扫多少个候选时间点
FRAME_KEEP_TOP_N = 5               # 保留前 N 张到 debug
FRAME_HEAD_SKIP = 0.05             # 跳过开头 5%
FRAME_TAIL_SKIP = 0.05             # 跳过结尾 5%

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 视频扩展名
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv"}

# 处理成功后自动删除 inbox 里的源视频（默认关，由用户手动删）
DELETE_SOURCE_ON_DONE = False

# 烧字幕后的视频编码参数（控制文件大小 vs 画质）
# CRF：18≈无损, 23≈高清, 26≈压得更狠, 28≈明显损失
# preset：slower>slow>medium>fast（越慢压缩率越高、编码越久）
ENCODE_CRF = 26
ENCODE_PRESET = "slow"
# 音频重压以省体积：96k 足够人声
ENCODE_AUDIO_BITRATE = "96k"


def assert_font_exists() -> None:
    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"字幕字体文件缺失: {FONT_PATH}。请确认 `视频自动配字幕/fonts/` 存在"
        )
    if not COVER_FONT_PATH.exists():
        raise FileNotFoundError(
            f"封面字体文件缺失: {COVER_FONT_PATH}"
        )
