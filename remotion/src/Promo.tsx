import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
  spring,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { FONT_SMILEY_SANS, FONT_PANGMEN } from "./embeddedFonts";

const SUB_FONT = "Smiley Sans";
const TITLE_FONT = "PangMenZhengDao";

const dataUrlToBuffer = (dataUrl: string): ArrayBuffer => {
  const base64 = dataUrl.split(",")[1];
  const bin = atob(base64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
};

const loadFont = (family: string, dataUrl: string, label: string) => {
  const handle = delayRender(label, { timeoutInMilliseconds: 120000, retries: 3 });
  new FontFace(family, dataUrlToBuffer(dataUrl))
    .load()
    .then((loaded) => {
      (document.fonts as unknown as { add: (f: FontFace) => void }).add(loaded);
      continueRender(handle);
    })
    .catch((err) => cancelRender(err));
};

loadFont(SUB_FONT, FONT_SMILEY_SANS, "Loading sub font");
loadFont(TITLE_FONT, FONT_PANGMEN, "Loading title font");

const FPS = 30;
const ms = (x: number) => Math.round((x / 1000) * FPS);

// 音频时间戳 → 帧
const SEC = {
  hook: { from: ms(0), to: ms(3000) },
  stat3h: { from: ms(3000), to: ms(5800) },
  pain1: { from: ms(5800), to: ms(8500) },
  pain2: { from: ms(8500), to: ms(11200) },
  pain3: { from: ms(11200), to: ms(13800) },
  pain4: { from: ms(13800), to: ms(16500) },
  ask: { from: ms(16500), to: ms(18400) },
  pivot: { from: ms(18400), to: ms(21800) },
  before1: { from: ms(21800), to: ms(24800) },
  before2: { from: ms(24800), to: ms(27800) },
  ai1: { from: ms(27800), to: ms(30400) },
  ai2: { from: ms(30400), to: ms(35200) },
  std: { from: ms(35200), to: ms(38800) },
  templates: { from: ms(38800), to: ms(41200) },
  features: { from: ms(41200), to: ms(45600) },
  buy: { from: ms(45600), to: ms(50800) },
  cta: { from: ms(50800), to: ms(55100) },
};

const TOTAL_FRAMES = ms(55500);

export const Promo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a", overflow: "hidden" }}>
      <Audio src={staticFile("promo/voice.mp3")} />

      <BackgroundGrid />
      <ScanLines />

      {/* HOOK */}
      <Sequence from={SEC.hook.from} durationInFrames={SEC.hook.to - SEC.hook.from}>
        <HookScene />
      </Sequence>

      {/* "3 小时起" 大数字震动 */}
      <Sequence from={SEC.stat3h.from} durationInFrames={SEC.stat3h.to - SEC.stat3h.from}>
        <BigNumberScene number="3" unit="小时起" subtitle="做一条视频" />
      </Sequence>

      {/* 4 个痛点，每个伴随 ❌ */}
      <Sequence from={SEC.pain1.from} durationInFrames={SEC.pain1.to - SEC.pain1.from}>
        <PainItemScene label="卡字幕" cost="1 小时" idx={1} />
      </Sequence>
      <Sequence from={SEC.pain2.from} durationInFrames={SEC.pain2.to - SEC.pain2.from}>
        <PainItemScene label="调字体" cost="1 小时" idx={2} />
      </Sequence>
      <Sequence from={SEC.pain3.from} durationInFrames={SEC.pain3.to - SEC.pain3.from}>
        <PainItemScene label="找配图" cost="1 小时" idx={3} />
      </Sequence>
      <Sequence from={SEC.pain4.from} durationInFrames={SEC.pain4.to - SEC.pain4.from}>
        <PainItemScene label="做封面" cost="1 小时" idx={4} />
      </Sequence>

      {/* 反问 */}
      <Sequence from={SEC.ask.from} durationInFrames={SEC.ask.to - SEC.ask.from}>
        <BigQuestionScene text="你不累吗？" />
      </Sequence>

      {/* 转折：3 小时 → 1 分钟 */}
      <Sequence from={SEC.pivot.from} durationInFrames={SEC.pivot.to - SEC.pivot.from}>
        <PivotScene />
      </Sequence>

      {/* BEFORE */}
      <Sequence
        from={SEC.before1.from}
        durationInFrames={SEC.before2.to - SEC.before1.from}
      >
        <BeforeScene />
      </Sequence>

      {/* AI 流水线介绍 — 真 web app 截图 */}
      <Sequence from={SEC.ai1.from} durationInFrames={SEC.ai1.to - SEC.ai1.from}>
        <AppHeroScene />
      </Sequence>
      <Sequence from={SEC.ai2.from} durationInFrames={SEC.ai2.to - SEC.ai2.from}>
        <PipelineScene />
      </Sequence>

      {/* 标准 */}
      <Sequence from={SEC.std.from} durationInFrames={SEC.std.to - SEC.std.from}>
        <BigClaimScene
          a="头部账号的视觉水准"
          b="一键搞定"
          accent="#FFD93D"
        />
      </Sequence>

      {/* 5 套模板 — app busy 截图（多任务队列展示） */}
      <Sequence
        from={SEC.templates.from}
        durationInFrames={SEC.templates.to - SEC.templates.from}
      >
        <AppQueueScene />
      </Sequence>

      {/* AFTER V5 demo */}
      <Sequence
        from={SEC.features.from}
        durationInFrames={SEC.features.to - SEC.features.from}
      >
        <AfterScene />
      </Sequence>

      {/* 三连击 */}
      <Sequence from={SEC.buy.from} durationInFrames={SEC.buy.to - SEC.buy.from}>
        <ThreeStrikeScene />
      </Sequence>

      {/* CTA */}
      <Sequence from={SEC.cta.from} durationInFrames={TOTAL_FRAMES - SEC.cta.from}>
        <CTAScene />
      </Sequence>
    </AbsoluteFill>
  );
};

// ===== 通用背景 =====

const BackgroundGrid: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = (frame * 0.4) % 80;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.18 }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,217,61,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,217,61,0.4) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
          backgroundPosition: `${drift}px ${drift}px`,
        }}
      />
    </AbsoluteFill>
  );
};

const ScanLines: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.08 }}>
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage:
          "repeating-linear-gradient(0deg, rgba(255,255,255,0.6) 0px, rgba(255,255,255,0.6) 1px, transparent 1px, transparent 4px)",
      }}
    />
  </AbsoluteFill>
);

// ===== Scenes =====

const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 12, stiffness: 200 }, durationInFrames: 12 });
  const opacity = interpolate(frame, [0, 4], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", opacity }}>
        <div
          style={{
            color: "#FFD93D",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.025),
            letterSpacing: 6,
            marginBottom: 18,
            textTransform: "uppercase",
          }}
        >
          ▌ AI VIDEO PIPELINE
        </div>
        <div
          style={{
            color: "white",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.085),
            fontWeight: 900,
            transform: `scale(${popIn})`,
            WebkitTextStroke: "3px black",
            paintOrder: "stroke fill",
            textShadow: "0 0 40px rgba(255,217,61,0.4)",
          }}
        >
          做内容的兄弟
        </div>
        <div
          style={{
            color: "#FFD93D",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.065),
            fontWeight: 900,
            marginTop: 16,
            transform: `scale(${popIn})`,
            WebkitTextStroke: "2px black",
            paintOrder: "stroke fill",
          }}
        >
          听好了
        </div>
      </div>
    </AbsoluteFill>
  );
};

const BigNumberScene: React.FC<{ number: string; unit: string; subtitle: string }> = ({
  number,
  unit,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const numScale = spring({ frame, fps, config: { damping: 7, stiffness: 240 }, durationInFrames: 14 });
  const shake = (Math.sin(frame * 1.5) * Math.exp(-frame / 10)) * 8;
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", transform: `translate(${shake}px, ${shake}px)` }}>
        <div
          style={{
            color: "white",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.04),
            opacity: 0.85,
            marginBottom: 10,
          }}
        >
          {subtitle}
        </div>
        <div
          style={{
            color: "#FF3838",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.32),
            fontWeight: 900,
            transform: `scale(${numScale})`,
            WebkitTextStroke: "6px black",
            paintOrder: "stroke fill",
            lineHeight: 1,
            textShadow: "0 0 60px rgba(255,56,56,0.5)",
          }}
        >
          {number}
        </div>
        <div
          style={{
            color: "#FFD93D",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.07),
            fontWeight: 900,
            marginTop: -10,
            WebkitTextStroke: "2px black",
            paintOrder: "stroke fill",
          }}
        >
          {unit}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const PainItemScene: React.FC<{ label: string; cost: string; idx: number }> = ({
  label,
  cost,
  idx,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 220 }, durationInFrames: 10 });
  const xPop = spring({
    frame: frame - 5,
    fps,
    config: { damping: 8, stiffness: 240 },
    durationInFrames: 10,
  });
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            color: "#888",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.03),
            marginBottom: 14,
          }}
        >
          0{idx} / 04
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 28,
            transform: `scale(${pop})`,
          }}
        >
          <div
            style={{
              fontSize: Math.round(height * 0.13),
              transform: `scale(${xPop}) rotate(${interpolate(xPop, [0, 1], [-30, 0])}deg)`,
              color: "#FF3838",
              fontWeight: 900,
              filter: "drop-shadow(0 0 16px rgba(255,56,56,0.7))",
              fontFamily: `'${TITLE_FONT}', sans-serif`,
              WebkitTextStroke: "3px black",
              paintOrder: "stroke fill",
            }}
          >
            ✕
          </div>
          <div
            style={{
              color: "white",
              fontFamily: `'${TITLE_FONT}', sans-serif`,
              fontSize: Math.round(height * 0.1),
              fontWeight: 900,
              WebkitTextStroke: "3px black",
              paintOrder: "stroke fill",
            }}
          >
            {label}
          </div>
        </div>
        <div
          style={{
            color: "#FFD93D",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.045),
            marginTop: 24,
            opacity: interpolate(frame, [10, 16], [0, 1], { extrapolateRight: "clamp" }),
            letterSpacing: 2,
          }}
        >
          → 耗你 {cost}
        </div>
        {/* 进度条 */}
        <div
          style={{
            width: width * 0.6,
            margin: "32px auto 0",
            height: 6,
            backgroundColor: "rgba(255,255,255,0.15)",
            borderRadius: 999,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${(idx / 4) * 100}%`,
              height: "100%",
              backgroundColor: "#FFD93D",
              transition: "none",
            }}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const BigQuestionScene: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const breathe = 1 + Math.sin(frame * 0.3) * 0.04;
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          color: "white",
          fontFamily: `'${TITLE_FONT}', sans-serif`,
          fontSize: Math.round(height * 0.14),
          fontWeight: 900,
          transform: `scale(${breathe})`,
          textAlign: "center",
          WebkitTextStroke: "5px black",
          paintOrder: "stroke fill",
          textShadow: "0 0 60px rgba(255,217,61,0.5)",
          letterSpacing: 6,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const PivotScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  // 第一阶段：显示"3 小时" + 划掉
  const phase1End = ms(2000); // 在场景内本地帧
  const phase2 = frame >= phase1End;
  const lineThrough = interpolate(frame, [ms(800), ms(1500)], [0, 1], {
    extrapolateRight: "clamp",
  });
  const oneMinPop = phase2
    ? spring({ frame: frame - phase1End, fps, config: { damping: 8, stiffness: 240 }, durationInFrames: 12 })
    : 0;
  const oneMinShake = phase2 ? Math.sin((frame - phase1End) * 1.2) * 6 * Math.exp(-(frame - phase1End) / 12) : 0;

  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            position: "relative",
            display: "inline-block",
            color: phase2 ? "#666" : "#FF3838",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * (phase2 ? 0.085 : 0.18)),
            fontWeight: 900,
            WebkitTextStroke: "3px black",
            paintOrder: "stroke fill",
            transition: "all 0.3s",
          }}
        >
          3 小时
          {/* 划掉线 */}
          <div
            style={{
              position: "absolute",
              left: -10,
              right: -10,
              top: "50%",
              height: 8,
              background: "#FF3838",
              transform: `scaleX(${lineThrough})`,
              transformOrigin: "left center",
            }}
          />
        </div>
        {phase2 ? (
          <>
            <div
              style={{
                color: "#FFD93D",
                fontFamily: `'${SUB_FONT}', sans-serif`,
                fontSize: Math.round(height * 0.04),
                margin: "28px 0 8px",
              }}
            >
              ↓ 压缩到 ↓
            </div>
            <div
              style={{
                color: "#FFD93D",
                fontFamily: `'${TITLE_FONT}', sans-serif`,
                fontSize: Math.round(height * 0.22),
                fontWeight: 900,
                transform: `scale(${oneMinPop}) translate(${oneMinShake}px, 0)`,
                WebkitTextStroke: "5px black",
                paintOrder: "stroke fill",
                textShadow: "0 0 50px rgba(255,217,61,0.6)",
                lineHeight: 1,
              }}
            >
              1 分钟
            </div>
          </>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const BeforeScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const opacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity }}>
      <OffthreadVideo
        src={staticFile("promo/before.mp4")}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
      />
      {/* 顶部红色"原片"标签 */}
      <div
        style={{
          position: "absolute",
          top: Math.round(height * 0.06),
          left: "50%",
          transform: "translateX(-50%)",
          backgroundColor: "#FF3838",
          color: "white",
          fontFamily: `'${TITLE_FONT}', sans-serif`,
          fontSize: Math.round(height * 0.045),
          fontWeight: 900,
          padding: "12px 32px",
          letterSpacing: 4,
          border: "3px solid black",
          boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
        }}
      >
        ⊘ 原片（BEFORE）
      </div>
      {/* 底部黑色字幕 */}
      <div
        style={{
          position: "absolute",
          bottom: Math.round(height * 0.12),
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <span
          style={{
            backgroundColor: "rgba(0,0,0,0.85)",
            color: "white",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.04),
            fontWeight: 700,
            padding: "10px 20px",
          }}
        >
          朴素 · 平淡 · 没记忆点
        </span>
      </div>
    </AbsoluteFill>
  );
};

const BrowserChrome: React.FC<{
  url: string;
  imageSrc: string;
  caption: string;
  imageRatio: number;  // height / width 比例
  popIn: number;
  pulse?: number;
}> = ({ url, imageSrc, caption, imageRatio, popIn, pulse = 1 }) => {
  const { width, height } = useVideoConfig();
  const winW = width * 0.92;
  const winH = winW * imageRatio;
  const chromeH = 56;
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          width: winW,
          transform: `scale(${popIn * pulse})`,
        }}
      >
        {/* 顶部浏览器 chrome */}
        <div
          style={{
            background: "linear-gradient(180deg, #2a2a2a 0%, #1c1c1c 100%)",
            borderTopLeftRadius: 14,
            borderTopRightRadius: 14,
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            padding: "0 20px",
            height: chromeH,
            display: "flex",
            alignItems: "center",
            gap: 14,
          }}
        >
          {/* 红黄绿圆点 */}
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c, i) => (
            <div
              key={i}
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                backgroundColor: c,
              }}
            />
          ))}
          {/* 地址栏 */}
          <div
            style={{
              marginLeft: 18,
              flex: 1,
              backgroundColor: "rgba(0,0,0,0.5)",
              borderRadius: 8,
              padding: "6px 14px",
              fontFamily: "ui-monospace, Menlo, monospace",
              fontSize: 18,
              color: "#bbb",
              border: "1px solid rgba(255,217,61,0.3)",
            }}
          >
            <span style={{ color: "#FFD93D" }}>●</span>&nbsp;&nbsp;{url}
          </div>
        </div>
        {/* 内容（截图） */}
        <div
          style={{
            position: "relative",
            width: winW,
            height: winH,
            overflow: "hidden",
            borderBottomLeftRadius: 14,
            borderBottomRightRadius: 14,
            border: "2px solid #FFD93D",
            borderTop: "none",
            boxShadow: "0 0 64px rgba(255,217,61,0.35), 0 24px 80px rgba(0,0,0,0.7)",
            backgroundColor: "#0a0a0a",
          }}
        >
          <Img
            src={resolveSrc(imageSrc)}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
              objectPosition: "top center",
            }}
          />
          {/* 顶部到底部的 vignette 加深 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(ellipse at center, rgba(0,0,0,0) 60%, rgba(0,0,0,0.5) 100%)",
              pointerEvents: "none",
            }}
          />
        </div>
        {/* 底部 caption */}
        {caption ? (
          <div
            style={{
              marginTop: 22,
              textAlign: "center",
              color: "#FFD93D",
              fontFamily: `'${TITLE_FONT}', sans-serif`,
              fontSize: Math.round(height * 0.033),
              fontWeight: 900,
              letterSpacing: 2,
              WebkitTextStroke: "1.5px black",
              paintOrder: "stroke fill",
            }}
          >
            {caption}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const resolveSrc = (src: string): string => {
  if (/^(https?:|data:|blob:|\/)/i.test(src)) return src;
  return staticFile(src);
};

const AppHeroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const popIn = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 180, mass: 0.7 },
    durationInFrames: 16,
  });
  return (
    <BrowserChrome
      url="http://localhost:8800/remotion"
      imageSrc="promo/app_empty.png"
      caption="◆ 上传 · 选模板 · 一键开跑"
      imageRatio={600 / 1080}
      popIn={popIn}
    />
  );
};

const AppQueueScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const popIn = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 180, mass: 0.7 },
    durationInFrames: 14,
  });
  return (
    <BrowserChrome
      url="http://localhost:8800/remotion"
      imageSrc="promo/app_busy.png"
      caption="◆ 多视频并行 · 5 套模板任你选"
      imageRatio={740 / 1080}
      popIn={popIn}
    />
  );
};

const PipelineScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height, width } = useVideoConfig();
  const items = ["加字幕", "出封面", "智能配图", "金句卡", "切章节"];
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 18, width: width * 0.8 }}>
        {items.map((item, i) => {
          const start = i * 14;
          const visible = frame >= start;
          if (!visible) return <div key={i} style={{ height: Math.round(height * 0.06) }} />;
          const localFrame = frame - start;
          const slide = spring({
            frame: localFrame,
            fps,
            config: { damping: 12, stiffness: 200 },
            durationInFrames: 12,
          });
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                padding: "18px 28px",
                backgroundColor: "rgba(255,217,61,0.12)",
                border: "2px solid #FFD93D",
                borderRadius: 12,
                transform: `translateX(${interpolate(slide, [0, 1], [-100, 0])}px)`,
                opacity: slide,
                boxShadow: "0 0 16px rgba(255,217,61,0.25)",
              }}
            >
              <div
                style={{
                  fontFamily: "ui-monospace, Menlo, monospace",
                  color: "#FFD93D",
                  fontSize: Math.round(height * 0.03),
                  minWidth: 50,
                }}
              >
                ✓ {String(i + 1).padStart(2, "0")}
              </div>
              <div
                style={{
                  color: "white",
                  fontFamily: `'${TITLE_FONT}', sans-serif`,
                  fontSize: Math.round(height * 0.052),
                  fontWeight: 900,
                  WebkitTextStroke: "1.5px black",
                  paintOrder: "stroke fill",
                }}
              >
                {item}
              </div>
              <div
                style={{
                  marginLeft: "auto",
                  color: "#FFD93D",
                  fontSize: Math.round(height * 0.025),
                  fontFamily: "ui-monospace, Menlo, monospace",
                }}
              >
                AUTO
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const BigClaimScene: React.FC<{ a: string; b: string; accent: string }> = ({ a, b, accent }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const popA = spring({ frame, fps, config: { damping: 10, stiffness: 220 }, durationInFrames: 12 });
  const popB = spring({ frame: frame - 14, fps, config: { damping: 10, stiffness: 220 }, durationInFrames: 12 });
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            color: "white",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.07),
            fontWeight: 900,
            transform: `scale(${popA})`,
            WebkitTextStroke: "3px black",
            paintOrder: "stroke fill",
          }}
        >
          {a}
        </div>
        <div
          style={{
            marginTop: 24,
            display: "inline-block",
            backgroundColor: accent,
            color: "black",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.075),
            fontWeight: 900,
            padding: "16px 40px",
            transform: `scale(${popB})`,
            border: "4px solid black",
            letterSpacing: 4,
            boxShadow: "0 12px 40px rgba(255,217,61,0.4)",
          }}
        >
          {b}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const AfterScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  // 5 套模板小卡片 + V5 视频在中间播放
  const templates = ["V1 基础", "V2 极简", "V3 智能", "V4 爆款", "V5 顶配"];
  const opacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity }}>
      <OffthreadVideo
        src={staticFile("promo/after.mp4")}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
      />
      {/* 顶部黄色"AI 处理后"标签 */}
      <div
        style={{
          position: "absolute",
          top: Math.round(height * 0.06),
          left: "50%",
          transform: "translateX(-50%)",
          backgroundColor: "#FFD93D",
          color: "black",
          fontFamily: `'${TITLE_FONT}', sans-serif`,
          fontSize: Math.round(height * 0.04),
          fontWeight: 900,
          padding: "12px 32px",
          letterSpacing: 4,
          border: "3px solid black",
          boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
        }}
      >
        ✦ AI 处理后（AFTER）
      </div>

      {/* 5 套模板浮动 chips */}
      <div
        style={{
          position: "absolute",
          bottom: Math.round(height * 0.06),
          left: 0,
          right: 0,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 8,
          padding: "0 20px",
        }}
      >
        {templates.map((t, i) => {
          const start = i * 7;
          const local = frame - start;
          const slide = spring({
            frame: local,
            fps,
            config: { damping: 12, stiffness: 220 },
            durationInFrames: 10,
          });
          return (
            <div
              key={i}
              style={{
                padding: "8px 16px",
                backgroundColor: "rgba(0,0,0,0.85)",
                color: "#FFD93D",
                border: "2px solid #FFD93D",
                borderRadius: 999,
                fontFamily: `'${SUB_FONT}', sans-serif`,
                fontSize: Math.round(height * 0.022),
                fontWeight: 800,
                transform: `translateY(${interpolate(slide, [0, 1], [40, 0])}px) scale(${slide})`,
                opacity: slide,
                boxShadow: "0 4px 12px rgba(255,217,61,0.3)",
              }}
            >
              {t}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const ThreeStrikeScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const items = [
    { text: "想用？", offset: 0 },
    { text: "想买？", offset: 28 },
    { text: "想升级？", offset: 56 },
  ];
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {items.map((it, i) => {
          const local = frame - it.offset;
          const pop = spring({
            frame: local,
            fps,
            config: { damping: 8, stiffness: 240 },
            durationInFrames: 10,
          });
          return (
            <div
              key={i}
              style={{
                color: i === 2 ? "#FFD93D" : "white",
                fontFamily: `'${TITLE_FONT}', sans-serif`,
                fontSize: Math.round(height * (i === 2 ? 0.12 : 0.1)),
                fontWeight: 900,
                transform: `scale(${pop}) translateX(${interpolate(pop, [0, 1], [-80, 0])}px)`,
                opacity: pop,
                WebkitTextStroke: "3px black",
                paintOrder: "stroke fill",
                textShadow: i === 2 ? "0 0 40px rgba(255,217,61,0.5)" : "none",
                textAlign: "center",
              }}
            >
              {it.text}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, height, width } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 10, stiffness: 200 }, durationInFrames: 14 });
  const pulse = 1 + Math.sin(frame * 0.25) * 0.04;
  return (
    <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", transform: `scale(${popIn})` }}>
        <div
          style={{
            color: "#FFD93D",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.025),
            letterSpacing: 6,
            marginBottom: 14,
          }}
        >
          ▌ FOLLOW × DM
        </div>
        <div
          style={{
            display: "inline-block",
            backgroundColor: "#FFD93D",
            color: "black",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.12),
            fontWeight: 900,
            padding: "20px 50px",
            border: "5px solid black",
            transform: `scale(${pulse})`,
            boxShadow: "0 16px 48px rgba(255,217,61,0.6), 0 0 80px rgba(255,217,61,0.3)",
            letterSpacing: 6,
          }}
        >
          私信阿森
        </div>
        <div
          style={{
            color: "white",
            fontFamily: `'${TITLE_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.052),
            fontWeight: 900,
            marginTop: 28,
            WebkitTextStroke: "2px black",
            paintOrder: "stroke fill",
          }}
        >
          让 AI 帮你卷起来
        </div>
        <div
          style={{
            color: "#888",
            fontFamily: `'${SUB_FONT}', sans-serif`,
            fontSize: Math.round(height * 0.022),
            marginTop: 24,
            letterSpacing: 4,
          }}
        >
          ARSEN · AI VIDEO PIPELINE
        </div>
      </div>
    </AbsoluteFill>
  );
};
