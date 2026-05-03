/**
 * V7C — 极简 AI 科技风
 * 适合：AI 教学、科技副业、苹果发布会风格
 *
 * 核心元素：
 * - 字体：阿里巴巴普惠体（现代干净）
 * - 配色：纯白 + 纯黑 + 电光蓝 + 一点科技绿
 * - 字幕：黑底白字大字号 + 圆角
 * - 标题：超粗黑体 + 渐变 underline
 * - 配图：纯白卡片 + 微阴影
 */
import {
  AbsoluteFill, Img, OffthreadVideo, Sequence,
  cancelRender, continueRender, delayRender, staticFile,
  spring, interpolate, useCurrentFrame, useVideoConfig,
} from "remotion";
import { FONT_GAODUANHEI, FONT_SHUHEITI, FONT_PANGMEN } from "./embeddedFonts";
import { subtitleSchema, type SubtitleProps, type Chapter, type Cue } from "./SubtitleWithImages";

// V7 精致版：站酷高端黑做正文，书黑做强调，庞门正道做大字封面
const PUHUITI = "ZcoolGaoduanhei";
const TITLE_FONT = "AlimamaShuHeiTi";
const COVER_FONT = "PangMenZhengDao";

const dataUrlToBuffer = (dataUrl: string): ArrayBuffer => {
  const base64 = dataUrl.split(",")[1];
  const bin = atob(base64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
};
const loadFont = (family: string, dataUrl: string, label: string) => {
  const handle = delayRender(label, { timeoutInMilliseconds: 120000, retries: 3 });
  new FontFace(family, dataUrlToBuffer(dataUrl)).load()
    .then((loaded) => { (document.fonts as unknown as { add: (f: FontFace) => void }).add(loaded); continueRender(handle); })
    .catch((err) => cancelRender(err));
};
loadFont(PUHUITI, FONT_GAODUANHEI, "MinimalAI body font");
loadFont(TITLE_FONT, FONT_SHUHEITI, "MinimalAI accent font");
loadFont(COVER_FONT, FONT_PANGMEN, "MinimalAI cover font");

export { subtitleSchema as minimalAISchema };

const WHITE = "#FFFFFF";
const BLACK = "#0A0A0A";
const ELECTRIC = "#0099FF";
const NEON = "#00E5A0";
const GRAY_DARK = "#1A1A1A";
const GRAY_LIGHT = "#E5E7EB";

const safeRange = (...nums: number[]): number[] => {
  const out: number[] = [];
  for (let i = 0; i < nums.length; i++) {
    if (i === 0) out.push(nums[i]);
    else out.push(Math.max(out[i - 1] + 0.001, nums[i]));
  }
  return out;
};

const resolveSrc = (src: string): string => {
  if (/^(https?:|data:|blob:|\/)/i.test(src)) return src;
  return staticFile(src);
};

export const MinimalAIVideo: React.FC<SubtitleProps> = ({
  videoSrc, cues, title, hashtag, chapters,
  videoDurationInFrames, coverDurationInFrames, coverBgSrc,
  durationInFrames, disableImages,
}) => {
  const coverDur = coverDurationInFrames ?? 0;
  const videoDur = videoDurationInFrames ?? Math.max(1, durationInFrames - coverDur);
  return (
    <AbsoluteFill style={{ backgroundColor: BLACK }}>
      {coverDur > 0 ? (
        <Sequence from={0} durationInFrames={coverDur} layout="none">
          <MinimalCover title={title} coverBgSrc={coverBgSrc} hashtag={hashtag} />
        </Sequence>
      ) : null}
      <Sequence from={coverDur} durationInFrames={videoDur} layout="none">
        <MinimalScene
          videoSrc={videoSrc} cues={cues} chapters={chapters}
          hashtag={hashtag} title={title} disableImages={disableImages}
          totalFrames={videoDur}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

const MinimalScene: React.FC<{
  videoSrc: string; cues: Cue[]; chapters?: Chapter[];
  hashtag?: string; title?: string; disableImages?: boolean;
  totalFrames: number;
}> = ({ videoSrc, cues, chapters, hashtag, title, disableImages, totalFrames }) => {
  const TITLE_BAND = 0.14;
  return (
    <AbsoluteFill style={{ backgroundColor: BLACK }}>
      {/* 顶部实时进度条 */}
      <ProgressBar totalFrames={totalFrames} />
      {title ? <MinimalTitleBar title={title} bandRatio={TITLE_BAND} hashtag={hashtag} /> : null}
      <AbsoluteFill style={{ top: `${TITLE_BAND * 100}%`, bottom: 0, height: "auto" }}>
        <OffthreadVideo
          src={resolveSrc(videoSrc)}
          style={{
            position: "absolute", inset: 0,
            width: "100%", height: "100%",
            objectFit: "cover", objectPosition: "center 35%",
            filter: "contrast(1.08) saturate(1.05)",
          }}
        />
        {/* 黑色 vignette */}
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,0.55) 100%)",
        }} />
        {/* 微妙的电光蓝光晕 */}
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: "30%",
          background: `linear-gradient(to bottom, rgba(0,153,255,0.10) 0%, transparent 100%)`,
          mixBlendMode: "screen",
        }} />

        {chapters && chapters.length > 0 ? <MinimalChapter chapters={chapters} /> : null}

        {cues.map((cue, i) => {
          const dur = Math.max(1, cue.endFrame - cue.startFrame);
          return (
            <Sequence key={i} from={cue.startFrame} durationInFrames={dur}>
              {cue.isQuote ? (
                <MinimalQuote text={cue.text} durationInFrames={dur} />
              ) : (
                <MinimalCue
                  text={cue.text}
                  imageSrc={disableImages ? undefined : cue.imageSrc}
                  imageMode={cue.imageMode}
                  calloutEmoji={cue.calloutEmoji}
                  calloutText={cue.calloutText}
                  emoji={cue.emoji}
                  emphasis={cue.emphasis}
                  durationInFrames={dur}
                  cueIndex={i}
                />
              )}
            </Sequence>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const MinimalTitleBar: React.FC<{ title: string; bandRatio: number; hashtag?: string }> = ({
  title, bandRatio, hashtag,
}) => {
  const { width, height } = useVideoConfig();
  const bandH = Math.round(height * bandRatio);
  const n = Math.max(1, title.length);
  const useTwoLines = n >= 5;
  const charsPerLine = useTwoLines ? Math.ceil(n / 2) : n;
  const lines = useTwoLines
    ? [title.slice(0, charsPerLine), title.slice(charsPerLine)]
    : [title];
  const charSlots = charsPerLine + 0.02 * Math.max(0, charsPerLine - 1);
  const widthBased = (width * 0.85) / charSlots;
  const heightBased = bandH * (useTwoLines ? 0.32 : 0.55);
  const fontSize = Math.round(Math.min(widthBased, heightBased));
  return (
    <div style={{
      position: "absolute", top: 0, left: 0, width, height: bandH,
      backgroundColor: BLACK,
      borderBottom: `1px solid ${ELECTRIC}33`,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
    }}>
      {/* 顶部 status */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        width: width * 0.92, position: "absolute", top: 14,
        fontFamily: `'${PUHUITI}', sans-serif`,
        fontSize: Math.round(height * 0.016),
        color: WHITE, letterSpacing: 4, fontWeight: 600,
      }}>
        <span>
          <span style={{ color: NEON, marginRight: 6 }}>●</span>
          AI · LIVE
        </span>
        <span style={{ color: ELECTRIC }}>{hashtag ?? ""}</span>
      </div>
      {/* 标题 */}
      <div style={{
        display: "flex", flexDirection: "column",
        alignItems: "center", gap: 0,
        marginTop: 12,
      }}>
        {lines.map((line, i) => (
          <div key={i} style={{
            fontFamily: `'${PUHUITI}', sans-serif`,
            fontSize, fontWeight: 700,
            color: WHITE,
            letterSpacing: Math.max(2, Math.round(fontSize * 0.02)),
            whiteSpace: "nowrap",
            lineHeight: 1.05,
          }}>{line}</div>
        ))}
      </div>
      {/* 渐变下划线 */}
      <div style={{
        position: "absolute", bottom: 0,
        left: width * 0.30, right: width * 0.30,
        height: 3,
        background: `linear-gradient(90deg, transparent 0%, ${ELECTRIC} 50%, transparent 100%)`,
      }} />
    </div>
  );
};

const MinimalChapter: React.FC<{ chapters: Chapter[] }> = ({ chapters }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const fontSize = Math.round(height * 0.018);
  const currentIdx = chapters.findIndex((c) => frame >= c.startFrame && frame < c.endFrame);
  const cur = currentIdx >= 0 ? currentIdx : 0;
  return (
    <div style={{
      position: "absolute",
      top: Math.round(height * 0.025),
      left: width * 0.04,
      backgroundColor: "rgba(10,10,10,0.85)",
      border: `1px solid ${ELECTRIC}66`,
      backdropFilter: "blur(10px)",
      padding: "8px 16px",
      fontFamily: `'${PUHUITI}', sans-serif`,
      fontSize, color: WHITE,
      letterSpacing: 4, fontWeight: 700,
      borderRadius: 4,
    }}>
      <span style={{ color: ELECTRIC, fontWeight: 700 }}>
        {String(cur + 1).padStart(2, "0")}/{String(chapters.length).padStart(2, "0")}
      </span>
      <span style={{ margin: "0 10px", color: `${WHITE}50` }}>—</span>
      <span>{chapters[cur]?.title ?? ""}</span>
    </div>
  );
};

const HIGHLIGHT_WORDS = ["AI", "GPT", "副业", "智能", "效率", "成长", "自由", "创造", "未来"];

const renderMinimalText = (
  text: string, emphasis: string[] | undefined, popScale: number,
): React.ReactNode => {
  const animWords = emphasis ?? [];
  const allWords = Array.from(new Set([...animWords, ...HIGHLIGHT_WORDS])).filter(Boolean);
  if (!allWords.length) return text;
  const pattern = new RegExp(`(${allWords.join("|")})`, "g");
  const parts = text.split(pattern);
  return parts.map((part, i) => {
    if (!part) return null;
    const isAnim = animWords.includes(part);
    const isHi = allWords.includes(part);
    if (isAnim) {
      return (
        <span key={i} style={{
          color: ELECTRIC, fontWeight: 700,
          display: "inline-block",
          transform: `scale(${popScale})`,
          transformOrigin: "center bottom",
          textShadow: `0 0 16px ${ELECTRIC}80`,
        }}>{part}</span>
      );
    }
    if (isHi) {
      return <span key={i} style={{ color: ELECTRIC, fontWeight: 800 }}>{part}</span>;
    }
    return <span key={i}>{part}</span>;
  });
};

const MinimalCue: React.FC<{
  text: string; imageSrc?: string | null; imageMode?: "corner" | "fullscreen";
  calloutEmoji?: string | null; calloutText?: string | null;
  emoji?: string | null; emphasis?: string[];
  durationInFrames: number; cueIndex: number;
}> = ({ text, imageSrc, imageMode, calloutEmoji, calloutText, emoji, emphasis, durationInFrames, cueIndex }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const opacity = interpolate(frame, [0, 5], [0, 1], { extrapolateRight: "clamp" });
  const emphasisPop = interpolate(frame, safeRange(3, 8, 13), [1, 1.3, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const subFontSize = Math.round(height * 0.040);
  const subBottom = Math.round(height * 0.07);

  return (
    <AbsoluteFill>
      {imageSrc && imageMode === "fullscreen" ? (
        <MinimalFullscreenPhoto src={imageSrc} durationInFrames={durationInFrames} />
      ) : imageSrc ? (
        <MinimalCornerCard src={imageSrc} durationInFrames={durationInFrames} cueIndex={cueIndex} />
      ) : null}

      {(calloutText || calloutEmoji) ? (
        <MinimalChip
          emoji={calloutEmoji ?? ""}
          text={calloutText ?? ""}
          durationInFrames={durationInFrames}
        />
      ) : null}

      {emoji ? (
        <div style={{
          position: "absolute",
          top: "30%", right: width * 0.08,
          fontSize: Math.round(height * 0.13),
          opacity: interpolate(frame, safeRange(0, 4, durationInFrames - 6, durationInFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" }),
          transform: `scale(${spring({ frame, fps, durationInFrames: 12 })})`,
          filter: "drop-shadow(0 0 16px rgba(0,153,255,0.5))",
        }}>{emoji}</div>
      ) : null}

      {/* 字幕：黑底白字 + 蓝色左竖线 */}
      <div style={{
        position: "absolute", bottom: subBottom,
        left: 0, right: 0,
        display: "flex", justifyContent: "center",
        opacity, padding: "0 5%",
      }}>
        <div style={{
          fontFamily: `'${PUHUITI}', 'PingFang SC', sans-serif`,
          fontSize: subFontSize, fontWeight: 700,
          color: WHITE,
          padding: `${subFontSize * 0.4}px ${subFontSize * 0.85}px`,
          backgroundColor: "rgba(10,10,10,0.92)",
          borderLeft: `4px solid ${ELECTRIC}`,
          backdropFilter: "blur(12px)",
          borderRadius: 6,
          letterSpacing: 1, lineHeight: 1.3,
          maxWidth: "100%", textAlign: "center",
          boxShadow: `0 8px 28px rgba(0,153,255,0.18)`,
        }}>
          {renderMinimalText(text, emphasis, emphasisPop)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const MinimalCornerCard: React.FC<{ src: string; durationInFrames: number; cueIndex: number }> = ({
  src, durationInFrames, cueIndex,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 12, stiffness: 200 }, durationInFrames: 14 });
  const holdFrames = Math.min(durationInFrames, Math.round(fps * 1.6));
  const opacity = interpolate(frame, safeRange(0, 4, holdFrames - 8, holdFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const imgWidth = Math.round(width * 0.32);
  return (
    <div style={{
      position: "absolute",
      top: Math.round(height * 0.13),
      right: Math.round(width * 0.05),
      width: imgWidth,
      opacity,
      transform: `scale(${popIn})`,
      transformOrigin: "top right",
    }}>
      <Img src={resolveSrc(src)} style={{
        width: "100%",
        backgroundColor: WHITE,
        padding: 6,
        borderRadius: 12,
        border: `1px solid ${ELECTRIC}66`,
        boxShadow: `0 8px 28px rgba(0,153,255,0.40), 0 0 60px rgba(0,153,255,0.15)`,
        display: "block",
      }} />
      <div style={{
        marginTop: 4,
        textAlign: "right", paddingRight: 4,
        fontFamily: `'${PUHUITI}', sans-serif`,
        fontSize: Math.round(height * 0.014),
        color: ELECTRIC, letterSpacing: 2, fontWeight: 700,
      }}>
        REF.{String(cueIndex + 1).padStart(3, "0")}
      </div>
    </div>
  );
};

const MinimalFullscreenPhoto: React.FC<{ src: string; durationInFrames: number }> = ({
  src, durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, safeRange(0, 4, durationInFrames - 8, durationInFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const kbScale = interpolate(frame, safeRange(0, durationInFrames), [1, 1.06], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity, pointerEvents: "none" }}>
      <Img src={resolveSrc(src)} style={{
        position: "absolute", inset: 0,
        width: "100%", height: "100%", objectFit: "cover",
        transform: `scale(${kbScale})`,
        filter: "saturate(1.1) contrast(1.05)",
      }} />
      {/* 蓝色光晕叠加 */}
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(135deg, rgba(0,153,255,0.18) 0%, rgba(0,0,0,0.0) 50%, rgba(0,0,0,0.6) 100%)`,
      }} />
    </AbsoluteFill>
  );
};

const MinimalChip: React.FC<{
  emoji: string; text: string; durationInFrames: number;
}> = ({ emoji, text, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 11, stiffness: 200 }, durationInFrames: 12 });
  const holdFrames = Math.min(durationInFrames, Math.round(fps * 1.6));
  const opacity = interpolate(frame, safeRange(0, 4, holdFrames - 8, holdFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const fontSize = Math.round(height * 0.075);
  return (
    <div style={{
      position: "absolute", top: "30%", left: 0, right: 0,
      display: "flex", justifyContent: "center", opacity,
      transform: `scale(${popIn})`,
    }}>
      <div style={{
        background: `linear-gradient(135deg, ${ELECTRIC} 0%, #00C8FF 100%)`,
        color: WHITE,
        padding: `${fontSize * 0.4}px ${fontSize * 0.7}px`,
        fontFamily: `'${PUHUITI}', '${TITLE_FONT}', sans-serif`,
        fontSize, fontWeight: 700, letterSpacing: 3,
        borderRadius: 12,
        display: "flex", alignItems: "center", gap: fontSize * 0.3,
        maxWidth: width * 0.85, whiteSpace: "nowrap",
        boxShadow: `0 12px 40px rgba(0,153,255,0.45), 0 0 80px rgba(0,153,255,0.25)`,
      }}>
        {emoji ? <span>{emoji}</span> : null}
        {text ? <span>{text}</span> : null}
      </div>
    </div>
  );
};

const MinimalQuote: React.FC<{ text: string; durationInFrames: number }> = ({
  text, durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps, height, width } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 11, stiffness: 200 }, durationInFrames: 14 });
  const opacity = interpolate(frame, safeRange(0, 4, durationInFrames - 8, durationInFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const bgOpacity = interpolate(frame, safeRange(0, 4, durationInFrames - 8, durationInFrames), [0, 0.95, 0.95, 0], { extrapolateRight: "clamp" });
  const n = text.length;
  const fontSize = Math.round(height * (n <= 6 ? 0.13 : 0.10));
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, backgroundColor: BLACK, opacity: bgOpacity }} />
      <AbsoluteFill style={{
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        opacity, padding: "0 8%",
      }}>
        <div style={{
          fontFamily: `'${PUHUITI}', sans-serif`,
          fontSize: fontSize * 0.32, color: ELECTRIC,
          letterSpacing: 8, marginBottom: fontSize * 0.4,
          fontWeight: 800,
        }}>INSIGHT.AI</div>
        <div style={{
          transform: `scale(${popIn})`,
          fontFamily: `'${PUHUITI}', '${TITLE_FONT}', sans-serif`,
          fontSize, fontWeight: 700,
          color: WHITE, letterSpacing: 4,
          textAlign: "center", lineHeight: 1.3,
          textShadow: `0 0 32px ${ELECTRIC}66`,
        }}>{text}</div>
        <div style={{
          marginTop: fontSize * 0.5,
          width: 60, height: 3,
          background: `linear-gradient(90deg, ${ELECTRIC}, ${NEON})`,
        }} />
        <div style={{
          marginTop: fontSize * 0.3,
          fontFamily: `'${PUHUITI}', sans-serif`,
          fontSize: fontSize * 0.28,
          color: `${WHITE}88`, letterSpacing: 4, fontWeight: 700,
        }}>— GENERATED BY 阿森.ai</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// 实时进度条：视频顶部 4px 细线，蓝→绿渐变填充
const ProgressBar: React.FC<{ totalFrames: number }> = ({ totalFrames }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const pct = Math.max(0, Math.min(1, frame / Math.max(1, totalFrames)));
  return (
    <div style={{
      position: "absolute",
      top: 0, left: 0,
      width, height: 4,
      backgroundColor: "rgba(255,255,255,0.08)",
      zIndex: 100,
      pointerEvents: "none",
    }}>
      <div style={{
        width: `${pct * 100}%`,
        height: "100%",
        background: `linear-gradient(90deg, ${ELECTRIC} 0%, ${NEON} 100%)`,
        boxShadow: `0 0 12px ${ELECTRIC}, 0 0 24px ${NEON}66`,
        transition: "none",
      }} />
      {/* 末尾光点 */}
      <div style={{
        position: "absolute",
        top: -2,
        left: `calc(${pct * 100}% - 6px)`,
        width: 12, height: 8,
        backgroundColor: NEON,
        borderRadius: 8,
        boxShadow: `0 0 16px ${NEON}, 0 0 32px ${ELECTRIC}`,
        opacity: pct > 0 ? 1 : 0,
      }} />
    </div>
  );
};

const MinimalCover: React.FC<{
  title?: string; coverBgSrc?: string; hashtag?: string;
}> = ({ title, coverBgSrc, hashtag }) => {
  const { width, height } = useVideoConfig();
  const titleLen = Math.max(1, (title ?? "").length);
  const useTwoLines = titleLen >= 4;
  const charsPerLine = useTwoLines ? Math.ceil(titleLen / 2) : titleLen;
  const lines = useTwoLines
    ? [(title ?? "").slice(0, charsPerLine), (title ?? "").slice(charsPerLine)]
    : [title ?? ""];
  const charSlots = charsPerLine + 0.02 * Math.max(0, charsPerLine - 1);
  const widthBased = (width * 0.78) / charSlots;
  const heightBased = (height * (useTwoLines ? 0.30 : 0.20)) / (useTwoLines ? 2 : 1);
  const fontSize = Math.round(Math.min(widthBased, heightBased));
  return (
    <AbsoluteFill style={{ backgroundColor: BLACK }}>
      {/* 背景图（蓝色滤镜暗化）*/}
      {coverBgSrc ? (
        <Img src={resolveSrc(coverBgSrc)} style={{
          position: "absolute", inset: 0,
          width: "100%", height: "100%",
          objectFit: "cover", objectPosition: "center 30%",
          filter: "brightness(0.32) saturate(1.1)",
        }} />
      ) : null}
      {/* 蓝色 vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(135deg, rgba(0,153,255,0.12) 0%, rgba(0,0,0,0.0) 50%, rgba(0,0,0,0.4) 100%)`,
      }} />

      {/* 顶部 status */}
      <div style={{
        position: "absolute",
        top: 32, left: 32, right: 32,
        display: "flex", justifyContent: "space-between",
        fontFamily: `'${PUHUITI}', sans-serif`,
        fontSize: Math.round(height * 0.018),
        color: WHITE, letterSpacing: 4, fontWeight: 600,
      }}>
        <span>
          <span style={{ color: NEON, marginRight: 6 }}>●</span>
          AI · 2026
        </span>
        <span style={{ color: ELECTRIC }}>{hashtag ?? ""}</span>
      </div>

      {/* 中央 title */}
      <AbsoluteFill style={{
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "0 6%",
      }}>
        <div style={{
          fontFamily: `'${PUHUITI}', sans-serif`,
          fontSize: Math.round(height * 0.020),
          color: ELECTRIC, letterSpacing: 8,
          marginBottom: 20, fontWeight: 700,
        }}>
          ✦ INSIGHT 2026 ✦
        </div>
        {lines.map((line, i) => (
          <div key={i} style={{
            fontFamily: `'${COVER_FONT}', '${PUHUITI}', sans-serif`,
            fontSize, fontWeight: 900,
            color: WHITE,
            letterSpacing: Math.max(2, Math.round(fontSize * 0.04)),
            whiteSpace: "nowrap",
            lineHeight: 1.05,
            textShadow: `0 0 60px ${ELECTRIC}50, 0 4px 20px rgba(0,0,0,0.7)`,
          }}>{line}</div>
        ))}
        {/* 渐变下划线 */}
        <div style={{
          marginTop: 24,
          width: 100, height: 4,
          background: `linear-gradient(90deg, ${ELECTRIC}, ${NEON})`,
          boxShadow: `0 0 16px ${ELECTRIC}`,
        }} />
      </AbsoluteFill>

      {/* 底部 */}
      <div style={{
        position: "absolute",
        bottom: 32, left: 32, right: 32,
        display: "flex", justifyContent: "space-between", alignItems: "center",
        fontFamily: `'${PUHUITI}', sans-serif`,
        fontSize: Math.round(height * 0.016),
        color: `${WHITE}88`, letterSpacing: 4, fontWeight: 600,
      }}>
        <span>powered by gpt-image-1</span>
        <span style={{ color: ELECTRIC }}>→ play</span>
      </div>
    </AbsoluteFill>
  );
};
