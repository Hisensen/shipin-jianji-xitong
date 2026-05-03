/**
 * V6B 编辑部 / 报刊风
 * - 米黄底 + 深棕墨色 + 红色 accent
 * - 大字标题 + 编号期次 + 引号金句
 * - 字幕：经典印刷感（黑字 + 米色纸底 + 双横线分隔）
 * - 配图：相框感（白边 + 深色阴影 + 编号 caption）
 * 不影响 V1-V5 / V6A。
 */
import {
  AbsoluteFill,
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
import { subtitleSchema, type SubtitleProps, type Chapter, type Cue } from "./SubtitleWithImages";

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
  new FontFace(family, dataUrlToBuffer(dataUrl)).load()
    .then((loaded) => { (document.fonts as unknown as { add: (f: FontFace) => void }).add(loaded); continueRender(handle); })
    .catch((err) => cancelRender(err));
};
loadFont(SUB_FONT, FONT_SMILEY_SANS, "Editorial sub font");
loadFont(TITLE_FONT, FONT_PANGMEN, "Editorial title font");

export { subtitleSchema as editorialSchema };

const CREAM = "#F0E6D2";
const INK = "#2A1F18";
const PAPER = "#FAF1DD";
const ACCENT = "#B8302E";
const RULE = "#2A1F1840";

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

export const EditorialVideo: React.FC<SubtitleProps> = ({
  videoSrc, cues, title, hashtag, chapters,
  videoDurationInFrames, coverDurationInFrames, coverBgSrc,
  durationInFrames, disableImages,
}) => {
  const coverDur = coverDurationInFrames ?? 0;
  const videoDur = videoDurationInFrames ?? Math.max(1, durationInFrames - coverDur);
  return (
    <AbsoluteFill style={{ backgroundColor: CREAM }}>
      {coverDur > 0 ? (
        <Sequence from={0} durationInFrames={coverDur} layout="none">
          <EditorialCover title={title} coverBgSrc={coverBgSrc} hashtag={hashtag} />
        </Sequence>
      ) : null}
      <Sequence from={coverDur} durationInFrames={videoDur} layout="none">
        <EditorialScene
          videoSrc={videoSrc} cues={cues} chapters={chapters}
          hashtag={hashtag} title={title} disableImages={disableImages}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

const EditorialScene: React.FC<{
  videoSrc: string; cues: Cue[]; chapters?: Chapter[];
  hashtag?: string; title?: string; disableImages?: boolean;
}> = ({ videoSrc, cues, chapters, hashtag, title, disableImages }) => {
  const TITLE_BAND = 0.18;
  return (
    <AbsoluteFill style={{ backgroundColor: CREAM }}>
      {title ? <EditorialMasthead title={title} bandRatio={TITLE_BAND} hashtag={hashtag} /> : null}
      <AbsoluteFill style={{ top: `${TITLE_BAND * 100}%`, bottom: 0, height: "auto" }}>
        <OffthreadVideo
          src={resolveSrc(videoSrc)}
          style={{
            position: "absolute", inset: 0,
            width: "100%", height: "100%",
            objectFit: "cover", objectPosition: "center 35%",
            filter: "sepia(0.05) contrast(1.02)",
          }}
        />
        {/* 米色纸感叠加 + 暗角 */}
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(42,31,24,0.35) 100%)",
          pointerEvents: "none",
        }} />

        {chapters && chapters.length > 0 ? <EditorialChapter chapters={chapters} /> : null}

        {cues.map((cue, i) => {
          const dur = Math.max(1, cue.endFrame - cue.startFrame);
          return (
            <Sequence key={i} from={cue.startFrame} durationInFrames={dur}>
              {cue.isQuote ? (
                <EditorialQuote text={cue.text} durationInFrames={dur} />
              ) : (
                <EditorialCue
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

const EditorialMasthead: React.FC<{ title: string; bandRatio: number; hashtag?: string }> = ({
  title, bandRatio, hashtag,
}) => {
  const { width, height } = useVideoConfig();
  const bandH = Math.round(height * bandRatio);
  const n = Math.max(1, title.length);
  const charSlots = n + 0.04 * Math.max(0, n - 1) + 0.10;
  const widthBased = (width * 0.85) / charSlots;
  const heightBased = bandH * 0.50;
  const fontSize = Math.round(Math.min(widthBased, heightBased));
  return (
    <div style={{
      position: "absolute", top: 0, left: 0, width, height: bandH,
      backgroundColor: PAPER,
      borderBottom: `4px double ${INK}`,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: 6,
    }}>
      {/* 顶端期次 */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        width: width * 0.88,
        position: "absolute", top: 14,
        fontFamily: `'${SUB_FONT}', serif`,
        fontSize: Math.round(height * 0.018),
        color: INK, letterSpacing: 4, fontWeight: 700,
      }}>
        <span>VOL. 06 · 2026 春</span>
        <span>·</span>
        <span style={{ color: ACCENT }}>{hashtag ?? "EDITORIAL"}</span>
      </div>
      {/* 标题 */}
      <div style={{
        fontFamily: `'${TITLE_FONT}', serif`,
        fontSize, fontWeight: 900,
        color: INK,
        letterSpacing: Math.max(2, Math.round(fontSize * 0.02)),
        whiteSpace: "nowrap",
        marginTop: 12,
      }}>
        {title}
      </div>
      {/* 副线 */}
      <div style={{
        width: fontSize * 1.5,
        height: 2,
        backgroundColor: ACCENT,
        marginTop: 4,
      }} />
    </div>
  );
};

const EditorialChapter: React.FC<{ chapters: Chapter[] }> = ({ chapters }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const fontSize = Math.round(height * 0.020);
  const currentIdx = chapters.findIndex((c) => frame >= c.startFrame && frame < c.endFrame);
  const cur = currentIdx >= 0 ? currentIdx : 0;
  return (
    <div style={{
      position: "absolute",
      top: Math.round(height * 0.025),
      left: width * 0.05,
      fontFamily: `'${SUB_FONT}', serif`,
      fontSize, color: PAPER,
      letterSpacing: 4, fontWeight: 700,
      backgroundColor: "rgba(42,31,24,0.85)",
      padding: "8px 16px",
      borderLeft: `4px solid ${ACCENT}`,
    }}>
      <span style={{ color: ACCENT }}>NO.{String(cur + 1).padStart(2, "0")}</span>
      <span style={{ margin: "0 10px", opacity: 0.5 }}>—</span>
      <span>{chapters[cur]?.title ?? ""}</span>
    </div>
  );
};

const HIGHLIGHT_WORDS = ["贬低", "PUA", "自卑", "滚", "操控", "降低", "不配"];

const renderEditorialText = (
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
          color: ACCENT, fontWeight: 900,
          display: "inline-block",
          transform: `scale(${popScale})`,
          transformOrigin: "center bottom",
          textDecoration: `underline ${ACCENT}`,
          textUnderlineOffset: 4,
        }}>{part}</span>
      );
    }
    if (isHi) {
      return <span key={i} style={{ color: ACCENT, fontWeight: 800 }}>{part}</span>;
    }
    return <span key={i}>{part}</span>;
  });
};

const EditorialCue: React.FC<{
  text: string; imageSrc?: string | null; imageMode?: "corner" | "fullscreen";
  calloutEmoji?: string | null; calloutText?: string | null;
  emoji?: string | null; emphasis?: string[];
  durationInFrames: number; cueIndex: number;
}> = ({ text, imageSrc, imageMode, calloutEmoji, calloutText, emoji, emphasis, durationInFrames, cueIndex }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const opacity = interpolate(frame, [0, 5], [0, 1], { extrapolateRight: "clamp" });
  const emphasisPop = interpolate(frame, safeRange(3, 8, 13), [1, 1.25, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const subFontSize = Math.round(height * 0.038);
  const subBottom = Math.round(height * 0.08);

  return (
    <AbsoluteFill>
      {imageSrc && imageMode === "fullscreen" ? (
        <EditorialFullscreenPhoto src={imageSrc} durationInFrames={durationInFrames} cueIndex={cueIndex} />
      ) : imageSrc ? (
        <EditorialFramedPhoto src={imageSrc} durationInFrames={durationInFrames} cueIndex={cueIndex} />
      ) : null}

      {(calloutText || calloutEmoji) ? (
        <EditorialPullQuote
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
          transform: `scale(${spring({ frame, fps, durationInFrames: 12 })}) rotate(-6deg)`,
          filter: "grayscale(0.2)",
        }}>{emoji}</div>
      ) : null}

      <div style={{
        position: "absolute", bottom: subBottom,
        left: 0, right: 0,
        display: "flex", justifyContent: "center",
        opacity, padding: "0 8%",
      }}>
        <span style={{
          color: INK,
          fontSize: subFontSize, fontWeight: 700,
          fontFamily: `'${SUB_FONT}', serif`,
          padding: `${subFontSize * 0.45}px ${subFontSize * 0.9}px`,
          backgroundColor: PAPER,
          borderTop: `2px solid ${INK}`,
          borderBottom: `2px solid ${INK}`,
          letterSpacing: 1, lineHeight: 1.35,
          textAlign: "center",
          maxWidth: "100%",
          boxShadow: "0 4px 12px rgba(42,31,24,0.18)",
        }}>
          {renderEditorialText(text, emphasis, emphasisPop)}
        </span>
      </div>
    </AbsoluteFill>
  );
};

const EditorialFramedPhoto: React.FC<{ src: string; durationInFrames: number; cueIndex: number }> = ({
  src, durationInFrames, cueIndex,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 12, stiffness: 200 }, durationInFrames: 14 });
  const holdFrames = Math.min(durationInFrames, Math.round(fps * 1.6));
  const opacity = interpolate(frame, safeRange(0, 4, holdFrames - 8, holdFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const imgWidth = Math.round(width * 0.34);
  return (
    <div style={{
      position: "absolute",
      top: Math.round(height * 0.14),
      right: Math.round(width * 0.05),
      width: imgWidth,
      opacity,
      transform: `scale(${popIn})`,
      transformOrigin: "top right",
    }}>
      <Img src={resolveSrc(src)} style={{
        width: "100%",
        backgroundColor: PAPER,
        padding: 10,
        border: `2px solid ${INK}`,
        boxShadow: "6px 8px 20px rgba(42,31,24,0.32)",
        display: "block",
        filter: "sepia(0.1)",
      }} />
      <div style={{
        marginTop: 6,
        fontFamily: `'${SUB_FONT}', serif`,
        fontSize: Math.round(height * 0.018),
        color: INK,
        letterSpacing: 2,
        textAlign: "center",
        fontStyle: "italic",
      }}>
        FIG. {String(cueIndex + 1).padStart(2, "0")}
      </div>
    </div>
  );
};

const EditorialFullscreenPhoto: React.FC<{ src: string; durationInFrames: number; cueIndex: number }> = ({
  src, durationInFrames, cueIndex,
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
        filter: "sepia(0.15)",
      }} />
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to bottom, rgba(0,0,0,0.0) 50%, rgba(42,31,24,0.7) 100%)",
      }} />
    </AbsoluteFill>
  );
};

const EditorialPullQuote: React.FC<{
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
        backgroundColor: INK, color: PAPER,
        padding: `${fontSize * 0.4}px ${fontSize * 0.7}px`,
        fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', serif`,
        fontSize, fontWeight: 900,
        letterSpacing: 3,
        borderTop: `3px solid ${ACCENT}`,
        borderBottom: `3px solid ${ACCENT}`,
        display: "inline-flex", alignItems: "center", gap: fontSize * 0.3,
        maxWidth: width * 0.88, whiteSpace: "nowrap",
        boxShadow: "6px 8px 20px rgba(42,31,24,0.4)",
      }}>
        {emoji ? <span>{emoji}</span> : null}
        {text ? <span>{text}</span> : null}
      </div>
    </div>
  );
};

const EditorialQuote: React.FC<{ text: string; durationInFrames: number }> = ({
  text, durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const popIn = spring({ frame, fps, config: { damping: 11, stiffness: 200 }, durationInFrames: 14 });
  const opacity = interpolate(frame, safeRange(0, 4, durationInFrames - 8, durationInFrames), [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const bgOpacity = interpolate(frame, safeRange(0, 4, durationInFrames - 8, durationInFrames), [0, 0.96, 0.96, 0], { extrapolateRight: "clamp" });
  const n = text.length;
  const fontRatio = n <= 4 ? 0.13 : n <= 8 ? 0.10 : 0.08;
  const fontSize = Math.round(height * fontRatio);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: 0, backgroundColor: PAPER, opacity: bgOpacity }} />
      <AbsoluteFill style={{
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        opacity, padding: "0 10%",
      }}>
        <div style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: fontSize * 2.5, color: ACCENT,
          opacity: 0.7, lineHeight: 0.6, marginBottom: 0,
        }}>"</div>
        <div style={{
          transform: `scale(${popIn})`,
          fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', serif`,
          fontSize, fontWeight: 900,
          color: INK, letterSpacing: 4,
          textAlign: "center", lineHeight: 1.35,
        }}>{text}</div>
        <div style={{ width: 120, height: 2, backgroundColor: INK, marginTop: fontSize * 0.5 }} />
        <div style={{
          marginTop: fontSize * 0.25,
          fontFamily: `'${SUB_FONT}', serif`,
          fontSize: Math.round(fontSize * 0.32),
          color: `${INK}99`, letterSpacing: 6, fontStyle: "italic",
        }}>EDITOR'S PICK</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const EditorialCover: React.FC<{
  title?: string; coverBgSrc?: string; hashtag?: string;
}> = ({ title, coverBgSrc, hashtag }) => {
  const { width, height } = useVideoConfig();
  const titleLen = Math.max(1, (title ?? "").length);
  const useTwoLines = titleLen >= 4;
  const charsPerLine = useTwoLines ? Math.ceil(titleLen / 2) : titleLen;
  const lines = useTwoLines
    ? [(title ?? "").slice(0, charsPerLine), (title ?? "").slice(charsPerLine)]
    : [title ?? ""];
  const charSlots = charsPerLine + 0.04 * Math.max(0, charsPerLine - 1);
  const widthBased = (width * 0.78) / charSlots;
  const heightBased = (height * (useTwoLines ? 0.30 : 0.20)) / (useTwoLines ? 2 : 1);
  const fontSize = Math.round(Math.min(widthBased, heightBased));
  return (
    <AbsoluteFill style={{ backgroundColor: PAPER }}>
      {/* 顶部期次 */}
      <div style={{
        position: "absolute",
        top: height * 0.05,
        left: width * 0.06, right: width * 0.06,
        display: "flex", justifyContent: "space-between",
        fontFamily: `'${SUB_FONT}', serif`,
        fontSize: Math.round(height * 0.022),
        color: INK, letterSpacing: 4, fontWeight: 700,
        borderBottom: `2px solid ${INK}`,
        paddingBottom: 8,
      }}>
        <span>VOL. 06</span>
        <span style={{ color: ACCENT }}>2026 春刊</span>
        <span>{hashtag ?? "EDITORIAL"}</span>
      </div>

      {/* 双横线 */}
      <div style={{
        position: "absolute",
        top: height * 0.13,
        left: width * 0.06, right: width * 0.06,
        height: 1, backgroundColor: INK, opacity: 0.5,
      }} />

      {/* 标题块 */}
      <div style={{
        position: "absolute",
        top: height * 0.17,
        left: 0, right: 0,
        display: "flex", flexDirection: "column",
        alignItems: "center", gap: 0,
      }}>
        {lines.map((line, i) => (
          <div key={i} style={{
            fontFamily: `'${TITLE_FONT}', serif`,
            fontSize, fontWeight: 900,
            color: INK,
            letterSpacing: Math.max(2, Math.round(fontSize * 0.02)),
            whiteSpace: "nowrap",
            lineHeight: 1.05,
          }}>{line}</div>
        ))}
        <div style={{
          width: fontSize * 1.5, height: 3,
          backgroundColor: ACCENT, marginTop: 18,
        }} />
      </div>

      {/* 配图（裱框）*/}
      {coverBgSrc ? (
        <div style={{
          position: "absolute",
          top: "68%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: width * 0.74,
          height: height * 0.32,
          backgroundColor: PAPER,
          padding: 14,
          border: `2px solid ${INK}`,
          boxShadow: "8px 12px 30px rgba(42,31,24,0.35)",
        }}>
          <Img src={resolveSrc(coverBgSrc)} style={{
            width: "100%", height: "100%",
            objectFit: "cover", objectPosition: "center 30%",
            filter: "sepia(0.12) contrast(1.05)",
          }} />
        </div>
      ) : null}

      {/* 底部 ISBN-style 编号 */}
      <div style={{
        position: "absolute",
        bottom: height * 0.05,
        left: 0, right: 0,
        textAlign: "center",
        fontFamily: `'${SUB_FONT}', serif`,
        fontSize: Math.round(height * 0.018),
        color: INK, letterSpacing: 8, opacity: 0.7,
      }}>
        — A LIFE IN EDITORIAL · 2026 —
      </div>
    </AbsoluteFill>
  );
};
