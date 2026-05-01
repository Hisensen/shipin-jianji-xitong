# 视频字幕封面系统 — 验收标准

> 每条准则都可 **机器校验** 或 **肉眼对照参考图**。任何一条不达标 → 进修复循环直到满足。

参考图：
- 字幕样式：`samples/refs/subtitle_ref.jpg`
- 标题样式：`samples/refs/title_ref.jpg`

---

## 一、功能性（F）

| ID | 准则 | 校验方式 |
|----|------|----------|
| F1 | 支持处理单个视频文件 | `python -m app.cli samples/inbox/xxx.mp4` 成功生成产物目录 |
| F2 | 支持批量处理目录 | `python -m app.cli samples/inbox/` 按顺序处理目录里全部视频 |
| F3 | 每条视频产出 **5 个** 必需文件：`*_sub.mp4`、`*_cover.jpg`、`*.srt`、`*.meta.json`、`debug/pipeline.log` | 脚本 `ls` 检查文件都存在且非 0 字节 |
| F9 | Web UI 启动：`python run.py` → 打开 `http://127.0.0.1:8000` 能看到主页 | curl 200 + 渲染含关键字 |
| F10 | Web UI 每条视频可：预览带字幕视频、预览封面、重生成标题、重新挑帧、下载产物 zip | 点击可用 |
| F4 | `*_sub.mp4` 视频时长 = 原视频时长（±0.5 秒） | ffprobe 对比 |
| F5 | `*_cover.jpg` 分辨率 = 原视频分辨率 | ffprobe / PIL 读取 |
| F6 | `*.srt` 至少包含 1 条字幕 | 行数 > 0 |
| F7 | `meta.json` 含字段：`title / duration / subtitle_count / cover_frame_time / cover_pick_score / elapsed` | JSON schema 校验 |
| F8 | 失败不留残缺产物：中途报错时产物目录整个不生成（或标 `.FAILED`） | 注入异常后检查 |

## 二、字幕视觉（S） — 对齐 `subtitle_ref.jpg`

| ID | 准则 | 校验方式 |
|----|------|----------|
| S1 | 字体 = Source Han Sans SC Heavy | ass 文件 `Fontname` 字段 |
| S2 | 字色 = 纯白 `#FFFFFF` | ass `PrimaryColour=&H00FFFFFF` |
| S3 | 底框 = 黑色圆角半透明矩形（不是描边） | ass `BorderStyle=3`（opaque box）, `BackColour` alpha ≈ 40%-60% |
| S4 | 每行最多 12 个汉字，过长自动换行/切分 | 抽查 srt 每行长度 ≤ 12 |
| S5 | 字号 ≈ 视频高度的 3.8%-5% | 从 ass 读 Fontsize / 视频高度 |
| S6 | 纵向位置：文字中心在画面下方 70%-85% 区间 | MarginV 参数 |
| S7 | 字幕起止时间与语音对齐偏差 ≤ 0.5 秒 | 抽 3 段人工听 |
| S8 | 肉眼对照 `subtitle_ref.jpg`：底框形状/圆角/字重整体一致 | 截图 → `snapshots/subtitle_check.png` |

## 三、封面视觉（C） — 对齐 `title_ref.jpg`

| ID | 准则 | 校验方式 |
|----|------|----------|
| C1 | 封面底图 = 从视频里挑出的"精彩帧"，**不是 frame[0]** | `meta.json.cover_frame_time > 0.5s` 且 < 视频末尾 |
| C2 | 标题字体 = Source Han Sans SC Heavy | PIL 合成时记录到 meta |
| C3 | 标题字色 = 纯白，黑色描边宽度 ≥ 字号的 8% | PIL stroke_width |
| C4 | 标题字号按字数自适应：1-2 字用最大号，3-4 字中等，5-6 字基础号，始终保证横向不超出画面宽度 85% | PIL textbbox 测量 |
| C5 | 标题位置 **固定**：水平居中；竖直方向文字中心线在 **图高 15%** 处（顶部留白） | bbox 测量 |
| C6 | 无底框、无阴影（只有黑描边） | 合成代码不加 background 参数 |
| C7 | **硬约束：标题 ≤ 6 个汉字**。LLM 返回超长时自动截断并记 warning | meta.json 字段 + 单元测试 |
| C8 | 肉眼对照 `title_ref.jpg`：字重/描边粗细/上方留白整体一致 | 截图 → `snapshots/cover_check.png` |

## 四、挑帧质量（P）

| ID | 准则 | 校验方式 |
|----|------|----------|
| P1 | 精彩帧不能是全黑/全白/过曝帧 | 均值方差 > 阈值 |
| P2 | 精彩帧清晰度（Laplacian 方差）排名 ≥ 候选帧中位数 | 记录到 `pick_reason.txt` |
| P3 | 若视频主体是人：优先选含正脸的帧 | OpenCV haar/dnn 人脸检测命中 |
| P4 | `debug/candidates/` 至少保留 5 张候选，便于换 | 文件数 ≥ 5 |
| P5 | `pick_reason.txt` 记录挑中帧的分数明细（清晰度/人脸/时间位置） | 文本存在且非空 |

## 五、健壮性 & 性能（R）

| ID | 准则 | 校验方式 |
|----|------|----------|
| R1 | 10 分钟视频端到端 ≤ 5 分钟（CPU int8 whisper） | 记录 elapsed |
| R2 | 处理一条出错不影响后续视频（批量模式） | 注入一条坏视频测试 |
| R3 | 重入：同一视频再跑一次，输出可覆盖，不报错 | 连跑两次 |
| R4 | 日志里能还原完整命令、参数、ffmpeg 调用 | grep `pipeline.log` |

## 六、边界 & 异常（E）

| ID | 准则 | 校验方式 |
|----|------|----------|
| E1 | 无音频视频：跳过字幕，仍出封面，写一行警告到 log | 用静音视频测 |
| E2 | 非中文音频：按 whisper 自动语言，字幕仍烧录，warning 记录 | 用英文视频测 |
| E3 | 视频过短（<1s）：明确报错并退出，非 crash | 1 帧视频测 |
| E4 | 字体文件缺失：启动时前置检查，给出清晰报错 | 改路径测 |
| E5 | DeepSeek key 缺失：降级用视频首段字幕取前 6 字当标题，不阻断 | 清 env 测 |
| E6 | LLM 返回 >6 字或含标点/空格：自动清洗+截断至 6 字以内 | 注入长标题测 |

---

## 验证脚本（预留，实施后填充）

```
app/verify.py           # 把上面的准则跑成自动化断言
snapshots/              # 人眼复核用的快照
```

跑法：
```
python -m app.verify samples/inbox/demo.mp4
# 输出：PASS / FAIL + 每条准则的状态
```

## 循环修复约定

1. 跑 `verify`
2. 任一准则 FAIL → 列出 → 修代码 → 重跑
3. 最多 5 轮仍有 FAIL → 停下来跟用户同步当前卡点
