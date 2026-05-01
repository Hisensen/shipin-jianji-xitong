# Remotion 视频生成 — 5 个版本调用说明

## 5 个版本风格对照

| ID                          | 风格                                               | 适合           |
| --------------------------- | -------------------------------------------------- | -------------- |
| `PublishVideo14`            | 基础：封面 + 章节条 + Hashtag + 字幕高亮 + Pexels 角落配图 | 朋友圈/中规中矩 |
| `PublishVideo14NoImages`    | 极简：同上去掉所有配图，只字幕 + 章节                | 强调内容本身    |
| `PublishVideo14V3`          | 智能：每句 LLM 决策（图/Callout 卡/Emoji/纯字幕）     | 内容丰富        |
| `PublishVideo14V4`          | 爆款：V3 + 金句卡 + 章节白闪转场 + 关键词弹跳放大     | 抖音节奏感      |
| `PublishVideo14V5`          | 顶配：V4 + 音频踩点 zoom + 全屏 B-roll + **黑白黄爆款配色** | 抖音爆款冲击力 |

## 流程

每个版本都是 **两步**：先生成数据（Python），再渲染 MP4（Remotion）。

### 步骤 1：生成数据

每个版本对应一个 Python 脚本，传入视频路径：

```bash
# 在项目根目录执行（视频字幕封面系统v3/）

# V1 / V2 共用同一份数据
.venv/bin/python remotion/make_cues.py "/path/to/video.mp4"

# V3
.venv/bin/python remotion/make_cues_v3.py "/path/to/video.mp4"

# V4
.venv/bin/python remotion/make_cues_v4.py "/path/to/video.mp4"

# V5
.venv/bin/python remotion/make_cues_v5.py "/path/to/video.mp4"
```

执行后会：
- 转录视频（faster-whisper）
- 调 DeepSeek 生成标题、章节、形式决策、金句
- 搜 Pexels 配图（如需）
- 拷视频到 `remotion/public/source.mp4`
- 抽封面背景帧到 `remotion/public/cover_bg.jpg`
- 写 props 到 `remotion/src/realCues*.ts`

### 步骤 2：渲染 MP4

```bash
cd remotion

# 渲染单个版本
npx remotion render PublishVideo14V5 ../output/remotion/my_v5.mp4 --timeout=60000

# 把上面的 PublishVideo14V5 换成其他 id 就是其他版本
```

预计渲染时间：每个版本约 **1.5-2 分钟**（27 秒视频，1260×1680，Chromium 逐帧渲染）。

### 一键全跑（5 个版本一起出）

```bash
cd remotion
for v in PublishVideo14 PublishVideo14NoImages PublishVideo14V3 PublishVideo14V4 PublishVideo14V5; do
  npx remotion render "$v" "../output/remotion/${v}.mp4" --timeout=60000
done
```

## 实时预览（不出 MP4，浏览器实时调）

```bash
cd remotion
npm run dev
```

浏览器打开 `http://localhost:3000`，左侧选 Composition，时间轴拖动即看。

调字幕、配色、动画时刻先在 Studio 试，满意再出 MP4。

## 关键文件

```
remotion/
├── make_cues.py          # V1/V2 数据生成
├── make_cues_v3.py       # V3 数据生成
├── make_cues_v4.py       # V4 数据生成
├── make_cues_v5.py       # V5 数据生成（含音频重音分析）
├── src/
│   ├── Root.tsx                # 5 个 Composition 的注册中心
│   ├── SubtitleWithImages.tsx  # 所有视觉组件（字幕、封面、章节、Callout、金句卡等）
│   ├── realCues.ts             # V1/V2 props
│   ├── realCuesV3.ts           # V3 props
│   ├── realCuesV4.ts           # V4 props
│   └── realCuesV5.ts           # V5 props
└── public/
    ├── source.mp4         # 当前处理的视频
    ├── cover_bg.jpg       # 封面背景帧
    ├── fonts/             # 得意黑、庞门正道
    └── images*/           # 各版本下载的 Pexels 配图

app/
├── transcribe.py    # faster-whisper 转录
├── llm.py           # DeepSeek 标题 + 章节生成
├── imagery.py       # 形式决策、金句挑选、Pexels 搜图
└── audio_beats.py   # 音频波形 → 真重音帧（V5 专用）
```

## 换视频用

跑数据生成脚本时，第一个参数换成你的新视频路径即可。会自动覆盖 `source.mp4`、`cover_bg.jpg`、`realCues*.ts`，再 render 出来就是新视频。

## 输出位置

所有渲染好的 MP4 在 `output/remotion/`。

## 上传抖音

直接拿 `output/remotion/v5_viral_beats.mp4`（或任何你喜欢的版本）传抖音/视频号即可。
首帧已经是封面，缩略图会自动用它。
