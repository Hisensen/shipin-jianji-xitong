# 🎬 视频剪辑系统 · AI 一键产出抖音爆款

> 上传一条口播视频 → 自动转录、生成爆款标题、智能配图、合成封面、烧录字幕、一键输出 5 套抖音风格的爆款成片。

把"花 3 小时手动剪辑一条视频"压缩到"上传后 1-3 分钟出 5 个版本"。

---

## ✨ 5 套模板任你选

| 版本 | 风格 | 包含元素 |
|------|------|---------|
| **V1 基础** | 朋友圈友好 | 封面 + 章节进度条 + Hashtag + 字幕高亮 + AI 角落配图 |
| **V2 极简** | 强内容 | 同 V1，**去掉所有图片** |
| **V3 智能** | 抖音节奏 | LLM 决策每句视觉形式（image / callout 卡 / emoji / 纯字幕）|
| **V4 爆款** | 信息密度 | V3 + 金句全屏卡 + 章节白闪转场 + 关键词弹跳放大 |
| **V5 顶配** | 抖音爆款 | V4 + 音频踩点 zoom + 全屏 B-roll + 黑白黄硬核配色 |

---

## 🎯 核心功能

- **AI 转录**：faster-whisper（large-v3-turbo + int8）支持中/英/混合
- **智能切句**：长句按标点自动切成 ≤12 字短句，时间按字数比例分
- **爆款标题**：DeepSeek 生成 ≤6 字爆款标题
- **章节切分**：DeepSeek 把视频分 3-5 段，每段 2-6 字小标题
- **金句挖掘**：从字幕里找 1-3 句最具冲击力的金句，全屏黑底大字闪现
- **形式决策**：LLM 给每句字幕挑最合适的视觉强化方式
- **音频踩点**：分析音频波形提取真重音点，视觉打点跟你说话节奏同步
- **自动配图**：优先用 OpenAI GPT Image 生成真实生活感场景图，失败再降级 Pexels
- **5 版本输出**：一次上传，5 个风格全产出
- **黑白黄爆款配色**：高对比度，撕裂感强，对齐头部账号视觉

---

## 🏗️ 技术栈

```
┌─────────────────────────────────────────────────┐
│  Web UI: FastAPI + Jinja2                       │
│  ├─ /         主页（原始烧字幕流水线）          │
│  └─ /remotion 5 套模板批量处理                  │
├─────────────────────────────────────────────────┤
│  Pipeline (Python)                              │
│  ├─ faster-whisper      转录                    │
│  ├─ DeepSeek API        标题/章节/形式决策      │
│  ├─ OpenAI Images       真实场景配图生成        │
│  ├─ Pexels API          搜图兜底                │
│  ├─ Edge-TTS            promo 配音（可选）      │
│  └─ ffmpeg / ffprobe    音视频处理              │
├─────────────────────────────────────────────────┤
│  Renderer (Node.js)                             │
│  └─ Remotion 4.x        React 视频组合          │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 0. 前置依赖

```bash
# macOS（推荐）
brew install ffmpeg node python@3.10

# 验证
ffmpeg -version
node --version    # 需要 v18+
python3 --version # 需要 3.10+
```

### 1. 克隆项目

```bash
git clone https://github.com/<你的用户名>/<本仓库名>.git
cd <本仓库名>
```

### 2. Python 环境

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Node 环境（Remotion）

```bash
cd remotion
npm install
cd ..
```

第一次跑会自动下载 Chromium Headless Shell（~100MB），约 1-2 分钟。

### 4. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，至少填好 DEEPSEEK_API_KEY
# 推荐再填 OPENAI_API_KEY，让系统直接生成真实感配图
```

获取地址：
- DeepSeek：https://platform.deepseek.com/（有送几百万免费 token）
- OpenAI：https://platform.openai.com/
- Pexels：https://www.pexels.com/api/（可选兜底，完全免费）

### 5. 字体准备

`fonts/` 文件夹需要包含：
- `SmileySans-Oblique.ttf`（得意黑，字幕用）
- `PangMen.ttf`（庞门正道标题体，封面/标题用）

可从这些字体的官方页面下载：
- Smiley Sans: https://github.com/atelier-anchor/smiley-sans
- 庞门正道：https://www.pmzdmedia.com/

放好后还要复制到 `remotion/public/fonts/`：
```bash
cp fonts/SmileySans-Oblique.ttf remotion/public/fonts/
cp fonts/PangMen.ttf remotion/public/fonts/
```

### 6. 启动 Web 服务

```bash
.venv/bin/python run.py
# 浏览器打开 http://127.0.0.1:8800
```

主页（原始烧字幕流水线）：`http://127.0.0.1:8800/`
Remotion 5 套模板批量：`http://127.0.0.1:8800/remotion`

---

## 💻 使用方式

### Web UI（推荐）

1. 浏览器打开 `http://127.0.0.1:8800/remotion`
2. 选版本（默认 V5 顶配）
3. 上传一个或多个视频
4. 点"开始处理"，任务串行处理（一次跑一个）
5. 处理完显示 ▶ 播放 / ⬇ 下载

### CLI（脚本化）

```bash
cd <项目根目录>

# 生成 V5 数据 + 渲染
.venv/bin/python remotion/make_cues_v5.py "/path/to/video.mp4"
cd remotion
npx remotion render PublishVideo14V5 ../output/remotion/my_v5.mp4 --timeout=180000

# 一键 5 个版本全跑
for v in PublishVideo14 PublishVideo14NoImages PublishVideo14V3 PublishVideo14V4 PublishVideo14V5; do
  npx remotion render "$v" "../output/remotion/${v}.mp4" --timeout=180000
done
```

各版本对应的脚本：

| 版本 | Python 脚本 | Composition ID |
|------|------------|----------------|
| V1 / V2 | `make_cues.py` | `PublishVideo14` / `PublishVideo14NoImages` |
| V3 | `make_cues_v3.py` | `PublishVideo14V3` |
| V4 | `make_cues_v4.py` | `PublishVideo14V4` |
| V5 | `make_cues_v5.py` | `PublishVideo14V5` |

### Remotion Studio（实时预览）

调样式时不想每次都渲染 5 分钟，用 Studio 实时预览：

```bash
cd remotion
npm run dev
# 浏览器打开 http://localhost:3000
```

左侧选 Composition，时间轴拖动看效果，右侧 props 编辑器可以实时改字幕/标题/颜色。

---

## 📂 项目结构

```
视频字幕封面系统v3/
├── app/                    # Python 后端
│   ├── cli.py              # 原始烧字幕流水线 CLI
│   ├── pipeline.py         # 烧字幕主流程
│   ├── transcribe.py       # faster-whisper 包装
│   ├── llm.py              # DeepSeek（标题、章节）
│   ├── imagery.py          # 视觉决策、金句、OpenAI/Pexels 配图
│   ├── audio_beats.py      # 音频波形 → 真重音帧
│   ├── subtitle.py         # ASS 字幕生成 + ffmpeg 烧录
│   ├── cover.py            # PIL 封面合成
│   ├── frames.py           # OpenCV 挑帧
│   ├── remotion_runner.py  # 调 Remotion 渲染
│   └── web.py              # FastAPI Web UI
├── remotion/               # Node.js + Remotion
│   ├── make_cues.py        # V1/V2 数据生成
│   ├── make_cues_v3.py     # V3 数据生成
│   ├── make_cues_v4.py     # V4 数据生成
│   ├── make_cues_v5.py     # V5 数据生成（含音频重音）
│   ├── src/
│   │   ├── Root.tsx                # 注册所有 Composition
│   │   ├── SubtitleWithImages.tsx  # 主组件（封面、字幕、章节、金句卡…）
│   │   └── Promo.tsx               # 项目宣传片组件
│   └── public/
│       └── fonts/                  # 得意黑、庞门正道
├── promo/                  # 宣传片素材
│   ├── script.txt          # 配音文案
│   └── make_voice.py       # Edge-TTS 生成配音
├── templates/              # Jinja2 模板
│   ├── index.html
│   └── remotion.html
├── requirements.txt
└── README.md
```

---

## ⚙️ 关键参数

修改 `app/config.py`：

| 参数 | 含义 | 默认 |
|------|------|------|
| `SUB_MAX_CHARS_PER_LINE` | 字幕单行最大字数 | 12 |
| `SUB_FONT_SIZE_RATIO` | 字幕字号 / 视频高度 | 0.042 |
| `SUB_BOTTOM_MARGIN_RATIO` | 字幕底边距比例 | 0.18 |
| `TITLE_MAX_CHARS` | 标题硬上限 | 6 |
| `TITLE_BASE_FONT_RATIO` | 标题字号 / 图高（5-6 字） | 0.13 |
| `TITLE_STROKE_RATIO` | 描边宽度 / 字号 | 0.12 |

修改 `remotion/remotion.config.ts` 调渲染速度：

```ts
Config.setConcurrency(4);                          // 并发数
Config.setHardwareAcceleration("if-possible");     // Mac VideoToolbox 编码加速
Config.setChromiumOpenGlRenderer("angle");         // Metal GL 渲染
Config.setJpegQuality(85);                         // 中间帧 JPEG 质量
```

---

## 🐛 调试

- 每个版本的数据在 `remotion/src/realCues*.ts`，可以手动改测试
- Remotion Studio (`npm run dev`) 可实时预览 + 改 props
- LLM 失败会自动降级（标题→截取转录头部，形式→全 none）
- OpenAI 图片生成失败时会自动降级到 Pexels；两者都失败则跳过该 cue
- 短字幕段（<0.4 秒）的动画时间已用 `safeRange` 保护，不会崩

---

## 📝 License

MIT

## 🙏 致谢

- [Remotion](https://www.remotion.dev/) - React-based programmatic video framework
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Whisper inference 4x faster
- [DeepSeek](https://www.deepseek.com/) - LLM API
- [OpenAI Image Generation](https://platform.openai.com/docs/guides/image-generation) - GPT Image
- [Pexels](https://www.pexels.com/) - Free stock images
- [Smiley Sans](https://github.com/atelier-anchor/smiley-sans) - 得意黑字体
- 庞门正道 - 标题字体

---

## 📬 联系

如果你拿这套工具做出了爆款短视频，欢迎来分享！
