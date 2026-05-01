# 视频字幕封面系统 — 需求提案

## 目标
一条命令把一批视频加工成「带字幕的视频 + 带标题的封面」，风格对标爆款短视频模板。

## 输入
- 单个视频文件 或 一个目录（支持 `.mp4/.mov/.mkv/.avi/.webm/.m4v/.flv`）
- 标题：**始终由 LLM（DeepSeek）基于转录自动生成**。硬约束：≤ 6 个汉字。手动传入仅作兜底覆盖

## 输出（每条视频一个产物目录）
```
output/{stem}/
├── {stem}_sub.mp4       # 烧字幕后的视频
├── {stem}_cover.jpg     # 封面图：精彩帧 + 顶部大标题
├── {stem}.srt           # 字幕原文（便于调试）
├── {stem}.meta.json     # 标题、时长、挑帧依据、耗时等
└── debug/
    ├── candidates/       # 候选精彩帧（前 5-10 张，便于人工复核）
    ├── pick_reason.txt   # 为什么挑这一帧（清晰度/人脸/变化量分数）
    └── pipeline.log      # 本条视频的分步日志
```

## 流水线
```
视频 → ffprobe 获取时长/分辨率
     → faster-whisper 转录（zh）
     → 切句、烧录 ASS 字幕（样式见 validation.md）
     → 抽候选关键帧（scene detect + 人脸检测 + 清晰度评分）→ 选"精彩帧"
     → PIL 顶部合成大标题 → 封面图
     → 写 meta.json + debug 资料
```

## 字幕样式（对齐 samples/refs/subtitle_ref.jpg）
- 白色粗体中文 + 黑色圆角半透明底框
- 位置：画面下方 ~20%
- 字体：Source Han Sans SC Heavy

## 封面标题样式（对齐 samples/refs/title_ref.jpg）
- 白色超大粗体 + 黑色粗描边，无底框
- 位置：画面顶部 ~15%
- 字体：Source Han Sans SC Heavy

## 入口
- **CLI**：`python -m app.cli <video-or-dir>`（批量、脚本化场景）
- **Web UI**：FastAPI + Jinja2，`http://127.0.0.1:8000`
  - 上传/扫描 `samples/inbox/` → 看卡片进度 → 点开单条预览字幕视频和封面 → 不满意可重新生成标题 / 重新挑帧

## 非目标（本项目不做）
- 不做平台发布（已有 `自动发布的系统` 做这件事）
- 不做视频剪辑/换脸/特效

## 技术栈
- Python 3.10+
- faster-whisper（large-v3-turbo + int8）
- ffmpeg / ffprobe（已装）
- Pillow（封面合成）
- OpenCV（挑帧：清晰度 / 人脸）
- DeepSeek API（可选：生成标题）
- 字体：复用 `视频自动配字幕/fonts/SourceHanSansSC-Heavy.otf`

## 调试 & 可观测
- 每步打点写 `logs/run_{timestamp}.log`
- 异常时保留中间产物（帧、ass、候选封面）
- `--dry-run`：只跑转录和挑帧，不烧字幕、不出封面
- `--verbose`：把每段字幕的起止时间和候选帧分数打到 stdout
