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
import { z } from "zod";
import { FONT_SMILEY_SANS, FONT_PANGMEN } from "./embeddedFonts";

const SUB_FONT = "Smiley Sans";
const TITLE_FONT = "PangMenZhengDao";

// data: URL → ArrayBuffer 直接喂给 FontFace，最快路径
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

loadFont(SUB_FONT, FONT_SMILEY_SANS, "Loading subtitle font");
loadFont(TITLE_FONT, FONT_PANGMEN, "Loading title font");

const cueSchema = z.object({
  startFrame: z.number(),
  endFrame: z.number(),
  text: z.string(),
  imageSrc: z.string().nullable().optional(),
  imageMode: z.enum(["corner", "fullscreen"]).optional(),
  calloutEmoji: z.string().nullable().optional(),
  calloutText: z.string().nullable().optional(),
  calloutBg: z.string().nullable().optional(),
  calloutFg: z.string().nullable().optional(),
  emoji: z.string().nullable().optional(),
  isQuote: z.boolean().optional(),
  emphasis: z.array(z.string()).optional(),
});

const chapterSchema = z.object({
  title: z.string(),
  startFrame: z.number(),
  endFrame: z.number(),
});

export const subtitleSchema = z.object({
  videoSrc: z.string(),
  cues: z.array(cueSchema),
  durationInFrames: z.number(),
  videoDurationInFrames: z.number().optional(),
  coverDurationInFrames: z.number().optional(),
  coverBgSrc: z.string().optional(),
  title: z.string().optional(),
  hashtag: z.string().optional(),
  chapters: z.array(chapterSchema).optional(),
  disableImages: z.boolean().optional(),
  zoomFrames: z.array(z.number()).optional(),
  beatFrames: z.array(z.number()).optional(),
  neonMode: z.boolean().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
});

export type SubtitleProps = z.infer<typeof subtitleSchema>;
export type Chapter = z.infer<typeof chapterSchema>;
export type Cue = z.infer<typeof cueSchema>;

export const defaultSubtitleProps: SubtitleProps = {
  videoSrc: staticFile("demo.mp4"),
  cues: [
    { startFrame: 0, endFrame: 60, text: "示例字幕一", imageSrc: undefined },
    { startFrame: 60, endFrame: 120, text: "示例字幕二", imageSrc: undefined },
  ],
  durationInFrames: 156,
  videoDurationInFrames: 120,
  coverDurationInFrames: 36,
  coverBgSrc: undefined,
  title: "示例标题",
  hashtag: "#示例",
  chapters: [
    { title: "开场", startFrame: 0, endFrame: 60 },
    { title: "结尾", startFrame: 60, endFrame: 120 },
  ],
};

const resolveSrc = (src: string): string => {
  if (/^(https?:|data:|blob:|\/)/i.test(src)) return src;
  return staticFile(src);
};

// 保证 interpolate 的 inputRange 严格递增，避免短 cue (< 12 帧) 时的崩溃
const safeRange = (...nums: number[]): number[] => {
  const out: number[] = [];
  for (let i = 0; i < nums.length; i++) {
    if (i === 0) out.push(nums[i]);
    else out.push(Math.max(out[i - 1] + 0.001, nums[i]));
  }
  return out;
};

export const SubtitleWithImages: React.FC<SubtitleProps> = ({
  videoSrc,
  cues,
  title,
  hashtag,
  chapters,
  videoDurationInFrames,
  coverDurationInFrames,
  coverBgSrc,
  durationInFrames,
  disableImages,
  neonMode,
}) => {
  const coverDur = coverDurationInFrames ?? 0;
  const videoDur = videoDurationInFrames ?? Math.max(1, durationInFrames - coverDur);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {coverDur > 0 ? (
        <Sequence from={0} durationInFrames={coverDur} layout="none">
          <CoverScene title={title} coverBgSrc={coverBgSrc} hashtag={hashtag} neonMode={neonMode} />
        </Sequence>
      ) : null}

      <Sequence from={coverDur} durationInFrames={videoDur} layout="none">
        <VideoScene
          videoSrc={videoSrc}
          cues={cues}
          chapters={chapters}
          hashtag={hashtag}
          disableImages={disableImages}
          neonMode={neonMode}
          title={title}
        />
      </Sequence>
    </AbsoluteFill>
  );
};

const VideoScene: React.FC<{
  videoSrc: string;
  cues: Cue[];
  chapters?: Chapter[];
  hashtag?: string;
  disableImages?: boolean;
  neonMode?: boolean;
  title?: string;
}> = ({ videoSrc, cues, chapters, hashtag, disableImages, neonMode, title }) => {
  // V5 4:5 布局：上 18% 持续标题条，下 82% 视频区
  const TITLE_BAND = 0.18;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {/* 上方持续标题条 */}
      {title ? <PersistentTitleBar title={title} bandRatio={TITLE_BAND} /> : null}

      {/* 视频区：top = TITLE_BAND，向下铺满 */}
      <AbsoluteFill style={{ top: `${TITLE_BAND * 100}%`, bottom: 0, height: "auto" }}>
        <OffthreadVideo
          src={resolveSrc(videoSrc)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center 35%",
          }}
        />

        {neonMode ? <NeonVignette /> : null}

        {chapters && chapters.length > 0 ? <ChapterBar chapters={chapters} neonMode={neonMode} /> : null}

        {hashtag ? <HashtagPill hashtag={hashtag} neonMode={neonMode} /> : null}

      {cues.map((cue, i) => {
        const dur = Math.max(1, cue.endFrame - cue.startFrame);
        return (
          <Sequence key={i} from={cue.startFrame} durationInFrames={dur}>
            {cue.isQuote ? (
              <QuoteCard text={cue.text} durationInFrames={dur} neonMode={neonMode} />
            ) : (
              <CueOverlay
                text={cue.text}
                imageSrc={disableImages ? undefined : cue.imageSrc}
                imageMode={cue.imageMode}
                calloutEmoji={cue.calloutEmoji}
                calloutText={cue.calloutText}
                calloutBg={cue.calloutBg}
                calloutFg={cue.calloutFg}
                emoji={cue.emoji}
                emphasis={cue.emphasis}
                durationInFrames={dur}
                neonMode={neonMode}
              />
            )}
          </Sequence>
        );
      })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const computeBeatZoom = (frame: number, beats: number[]): number => {
  let scale = 1;
  for (const bf of beats) {
    const delta = frame - bf;
    if (delta < -2 || delta > 14) continue;
    let s = 1;
    if (delta < 0) {
      s = 1 + ((delta + 2) / 2) * 0.08;
    } else {
      s = 1.08 - (delta / 14) * 0.08;
    }
    scale = Math.max(scale, s);
  }
  return scale;
};

const computeBeatShake = (frame: number, beats: number[]): { x: number; y: number } => {
  for (const bf of beats) {
    const delta = frame - bf;
    if (delta < 0 || delta > 5) continue;
    const decay = (5 - delta) / 5;
    const angle = (frame * 1.3) % (Math.PI * 2);
    return { x: Math.cos(angle) * 4 * decay, y: Math.sin(angle * 1.7) * 4 * decay };
  }
  return { x: 0, y: 0 };
};

const PersistentTitleBar: React.FC<{ title: string; bandRatio: number }> = ({
  title,
  bandRatio,
}) => {
  const { width, height } = useVideoConfig();
  const bandH = Math.round(height * bandRatio);
  // 标题字号：考虑 letterSpacing 5% + stroke 8% 的额外宽度占用
  const n = Math.max(1, title.length);
  const charSlots = n + 0.05 * Math.max(0, n - 1) + 0.16;
  const widthBased = (width * 0.85) / charSlots;
  const heightBased = bandH * 0.55;
  const fontSize = Math.round(Math.min(widthBased, heightBased));
  const strokeW = Math.max(2, Math.round(fontSize * 0.08));

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width,
        height: bandH,
        background:
          "linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 70%, #2a2a2a 100%)",
        borderBottom: "3px solid #FFD93D",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 4px 20px rgba(255,217,61,0.25)",
      }}
    >
      <div
        style={{
          fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', sans-serif`,
          fontSize,
          fontWeight: 900,
          color: "#FFD93D",
          WebkitTextStroke: `${strokeW}px black`,
          paintOrder: "stroke fill",
          letterSpacing: Math.max(2, Math.round(fontSize * 0.05)),
          textShadow: "0 4px 16px rgba(0,0,0,0.6)",
          whiteSpace: "nowrap",
        }}
      >
        {title}
      </div>
    </div>
  );
};

const NeonVignette: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div
      style={{
        position: "absolute",
        inset: 0,
        background:
          "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.35) 100%)",
      }}
    />
  </AbsoluteFill>
);

const computeZoomScale = (frame: number, zoomFrames: number[]): number => {
  // 在每个 zoomFrame 附近（前 3 帧已经在 ramp up，后 9 帧 ramp down），最大 1.05
  let scale = 1;
  for (const zf of zoomFrames) {
    const delta = frame - zf;
    if (delta < -3 || delta > 9) continue;
    let s = 1;
    if (delta < 0) {
      // ramp up over 3 frames
      s = 1 + ((delta + 3) / 3) * 0.05;
    } else {
      // ramp down over 9 frames
      s = 1.05 - (delta / 9) * 0.05;
    }
    scale = Math.max(scale, s);
  }
  return scale;
};

const HIGHLIGHT_WORDS = ["贬低", "PUA", "自卑", "滚", "操控", "降低", "不配"];

const renderEmphasizedText = (
  text: string,
  emphasis: string[] | undefined,
  popScale: number,
  neonMode: boolean | undefined,
): React.ReactNode => {
  // BW + Yellow 配色：永远黄字，霓虹模式下加更厚黑描边 + drop shadow
  const hiColor = "#FFD93D";
  const hiGlow = neonMode
    ? "0 4px 12px rgba(0,0,0,0.85), 0 0 0 #000"
    : "none";
  const hiStroke = neonMode ? "2px black" : undefined;
  // 合并：来自 LLM 的 emphasis（动画放大） + 静态 HIGHLIGHT_WORDS
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
        <span
          key={i}
          style={{
            color: hiColor,
            textShadow: hiGlow,
            WebkitTextStroke: hiStroke,
            paintOrder: "stroke fill",
            display: "inline-block",
            transform: `scale(${popScale})`,
            transformOrigin: "center bottom",
          }}
        >
          {part}
        </span>
      );
    }
    if (isHi) {
      return (
        <span
          key={i}
          style={{
            color: hiColor,
            textShadow: hiGlow,
            WebkitTextStroke: hiStroke,
            paintOrder: "stroke fill",
          }}
        >
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
};

const CueOverlay: React.FC<{
  text: string;
  imageSrc?: string | null;
  imageMode?: "corner" | "fullscreen";
  calloutEmoji?: string | null;
  calloutText?: string | null;
  calloutBg?: string | null;
  calloutFg?: string | null;
  emoji?: string | null;
  emphasis?: string[];
  durationInFrames: number;
  neonMode?: boolean;
}> = ({
  text,
  imageSrc,
  imageMode,
  calloutEmoji,
  calloutText,
  calloutBg,
  calloutFg,
  emoji,
  emphasis,
  durationInFrames,
  neonMode,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const subOpacity = interpolate(frame, [0, 4], [0, 1], { extrapolateRight: "clamp" });

  // emphasis 词的弹跳放大：5 帧弹到 1.5x，5 帧回到 1
  const emphasisPop = interpolate(
    frame,
    [3, 8, 13],
    [1, 1.5, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const imgIn = spring({ frame, fps, config: { damping: 14, stiffness: 200, mass: 0.7 } });
  const imgHoldFrames = Math.min(durationInFrames, Math.round(fps * 1.6));
  const imgOutFrames = 8;
  const imgOpacity = interpolate(
    frame,
    safeRange(0, 4, imgHoldFrames - imgOutFrames, imgHoldFrames),
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  const imgScaleOut = interpolate(
    frame,
    safeRange(imgHoldFrames - imgOutFrames, imgHoldFrames),
    [1, 0.92],
    { extrapolateRight: "clamp" },
  );

  const subFontSize = Math.round(height * 0.042);
  const subBottom = Math.round(height * 0.06);
  const subSidePad = Math.round(subFontSize * 0.5);
  const subVertPad = Math.round(subFontSize * 0.25);

  const imgWidth = Math.round(width * 0.28);
  const imgTop = Math.round(height * 0.12);
  const imgRight = Math.round(width * 0.04);

  return (
    <AbsoluteFill>
      {imageSrc && imageMode === "fullscreen" ? (
        <FullscreenBroll
          src={imageSrc}
          durationInFrames={durationInFrames}
          neonMode={neonMode}
        />
      ) : imageSrc ? (
        <div
          style={{
            position: "absolute",
            top: imgTop,
            right: imgRight,
            width: imgWidth,
            opacity: imgOpacity,
            transform: `scale(${imgIn * imgScaleOut})`,
            transformOrigin: "top right",
          }}
        >
          <Img
            src={resolveSrc(imageSrc)}
            style={{
              width: "100%",
              borderRadius: 16,
              border: neonMode ? "3px solid #FFD93D" : "3px solid white",
              boxShadow: neonMode
                ? "0 0 16px rgba(255,217,61,0.5), 0 8px 32px rgba(0,0,0,0.6)"
                : "0 8px 32px rgba(0,0,0,0.6)",
              display: "block",
            }}
          />
        </div>
      ) : null}

      {calloutText || calloutEmoji ? (
        <CalloutCard
          emoji={calloutEmoji ?? ""}
          text={calloutText ?? ""}
          bg={calloutBg ?? "#FACC15"}
          fg={calloutFg ?? "#1F2937"}
          durationInFrames={durationInFrames}
        />
      ) : null}

      {emoji ? <EmojiSticker emoji={emoji} durationInFrames={durationInFrames} /> : null}

      <div
        style={{
          position: "absolute",
          bottom: subBottom,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: subOpacity,
        }}
      >
        <span
          style={{
            color: "white",
            fontSize: subFontSize,
            fontWeight: 700,
            fontFamily: `'${SUB_FONT}', 'PingFang SC', sans-serif`,
            padding: `${subVertPad}px ${subSidePad}px`,
            backgroundColor: "rgba(0,0,0,0.75)",
            letterSpacing: 1,
            lineHeight: 1.2,
          }}
        >
          {renderEmphasizedText(text, emphasis, emphasisPop, neonMode)}
        </span>
      </div>
    </AbsoluteFill>
  );
};

const ChapterBar: React.FC<{ chapters: Chapter[]; neonMode?: boolean }> = ({ chapters, neonMode }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const barH = Math.round(height * 0.055);
  const fontSize = Math.round(barH * 0.55);

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width,
        height: barH,
        display: "flex",
        backgroundColor: "#3A3A3A",
        boxShadow: "0 2px 4px rgba(0,0,0,0.5)",
      }}
    >
      {chapters.map((c, i) => {
        const span = Math.max(1, c.endFrame - c.startFrame);
        const isActive = frame >= c.startFrame && frame < c.endFrame;
        return (
          <div
            key={i}
            style={{
              flex: span,
              backgroundColor: isActive
                ? neonMode
                  ? "#FFD93D"
                  : "#E5DDC8"
                : "transparent",
              borderRight:
                i < chapters.length - 1 ? "2px solid rgba(255,255,255,0.55)" : "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: isActive ? "#000" : "white",
              fontSize,
              fontWeight: 900,
              fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', sans-serif`,
              letterSpacing: 1,
              textShadow: isActive ? "none" : "0 1px 3px rgba(0,0,0,0.9)",
            }}
          >
            {c.title}
          </div>
        );
      })}
    </div>
  );
};

const HashtagPill: React.FC<{ hashtag: string; neonMode?: boolean }> = ({ hashtag, neonMode }) => {
  const { width, height } = useVideoConfig();
  const top = Math.round(height * 0.085);
  const left = Math.round(width * 0.04);
  const fontSize = Math.round(height * 0.024);
  const padX = Math.round(fontSize * 0.7);
  const padY = Math.round(fontSize * 0.3);

  return (
    <div
      style={{
        position: "absolute",
        top,
        left,
        padding: `${padY}px ${padX}px`,
        backgroundColor: neonMode ? "rgba(0,0,0,0.85)" : "rgba(0,0,0,0.65)",
        borderRadius: 999,
        color: "#FFD93D",
        fontSize,
        fontWeight: 800,
        fontFamily: `'${SUB_FONT}', sans-serif`,
        letterSpacing: 1,
        boxShadow: "0 2px 8px rgba(0,0,0,0.5)",
        border: neonMode ? "2px solid #FFD93D" : "none",
      }}
    >
      {hashtag}
    </div>
  );
};

const FullscreenBroll: React.FC<{
  src: string;
  durationInFrames: number;
  neonMode?: boolean;
}> = ({ src, durationInFrames, neonMode }) => {
  const frame = useCurrentFrame();
  const outFrames = 8;
  const opacity = interpolate(
    frame,
    safeRange(0, 4, durationInFrames - outFrames, durationInFrames),
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  // Ken Burns 缓慢放大
  const kbScale = interpolate(frame, safeRange(0, durationInFrames), [1, 1.08], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity, pointerEvents: "none" }}>
      <Img
        src={resolveSrc(src)}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${kbScale})`,
        }}
      />
      {/* 暗化底部，给字幕留呼吸 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.0) 40%, rgba(0,0,0,0.6) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

const QuoteCard: React.FC<{
  text: string;
  durationInFrames: number;
  neonMode?: boolean;
}> = ({ text, durationInFrames, neonMode }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 整屏黑底，金句大字弹入
  const popIn = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 200, mass: 0.5 },
    durationInFrames: 14,
  });
  const outFrames = 8;
  const opacity = interpolate(
    frame,
    safeRange(0, 3, durationInFrames - outFrames, durationInFrames),
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  const bgOpacity = interpolate(
    frame,
    safeRange(0, 4, durationInFrames - outFrames, durationInFrames),
    [0, 0.85, 0.85, 0],
    { extrapolateRight: "clamp" },
  );

  // 字号根据字数
  const n = text.length;
  const fontRatio = n <= 4 ? 0.18 : n <= 8 ? 0.13 : 0.1;
  const fontSize = Math.round(height * fontRatio);
  const strokeW = Math.round(fontSize * 0.06);

  const quoteColor = "#FFD93D";
  const quoteGlow = "0 8px 32px rgba(0,0,0,0.85)";

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `rgba(0,0,0,${bgOpacity})`,
        }}
      />
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity,
        }}
      >
        <div
          style={{
            transform: `scale(${popIn})`,
            fontSize,
            fontWeight: 900,
            fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', sans-serif`,
            color: quoteColor,
            WebkitTextStroke: `${strokeW}px black`,
            paintOrder: "stroke fill",
            letterSpacing: 4,
            textAlign: "center",
            maxWidth: width * 0.85,
            lineHeight: 1.15,
            textShadow: quoteGlow,
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const ChapterTransition: React.FC<{
  title: string;
  index: number;
  neonMode?: boolean;
}> = ({ title, index, neonMode }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 0~3 帧：白闪
  // 3~18 帧：标题弹入 + 居中显示
  // 18~20 帧：淡出
  const flashOpacity = interpolate(frame, [0, 1, 3], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const titleVisible = frame >= 3;
  const localFrame = Math.max(0, frame - 3);
  const popIn = spring({
    frame: localFrame,
    fps,
    config: { damping: 12, stiffness: 200, mass: 0.5 },
    durationInFrames: 10,
  });
  const titleOpacity = interpolate(
    localFrame,
    [0, 3, 12, 17],
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  const fontSize = Math.round(height * 0.085);
  const strokeW = Math.round(fontSize * 0.08);
  const indexFontSize = Math.round(fontSize * 0.55);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundColor: "white",
          opacity: flashOpacity,
        }}
      />
      {titleVisible ? (
        <AbsoluteFill
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: titleOpacity,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: Math.round(fontSize * 0.4),
              transform: `scale(${popIn})`,
              padding: `${Math.round(fontSize * 0.4)}px ${Math.round(fontSize * 0.7)}px`,
              backgroundColor: "rgba(0,0,0,0.92)",
              borderRadius: 24,
              border: "4px solid #FFD93D",
              boxShadow: "0 12px 36px rgba(0,0,0,0.75)",
            }}
          >
            <div
              style={{
                fontSize: indexFontSize,
                fontWeight: 900,
                color: "#FFD93D",
                fontFamily: `'${TITLE_FONT}', sans-serif`,
                lineHeight: 1,
              }}
            >
              0{index + 1}
            </div>
            <div
              style={{
                fontSize,
                fontWeight: 900,
                color: "white",
                fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', sans-serif`,
                WebkitTextStroke: `${strokeW}px black`,
                paintOrder: "stroke fill",
                letterSpacing: 3,
                lineHeight: 1,
                whiteSpace: "nowrap",
              }}
            >
              {title}
            </div>
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

const CalloutCard: React.FC<{
  emoji: string;
  text: string;
  bg: string;
  fg: string;
  durationInFrames: number;
}> = ({ emoji, text, bg, fg, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 弹入：spring 缩放 + 旋转一点点；末尾淡出
  const popIn = spring({
    frame,
    fps,
    config: { damping: 9, stiffness: 220, mass: 0.6 },
    durationInFrames: 14,
  });
  const holdFrames = Math.min(durationInFrames, Math.round(fps * 1.6));
  const outFrames = 7;
  const opacity = interpolate(
    frame,
    safeRange(0, 3, holdFrames - outFrames, holdFrames),
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  const scaleOut = interpolate(
    frame,
    safeRange(holdFrames - outFrames, holdFrames),
    [1, 0.85],
    { extrapolateRight: "clamp" },
  );
  const rotate = interpolate(popIn, [0, 1], [-6, 0], { extrapolateRight: "clamp" });

  const fontSize = Math.round(height * 0.085);
  const padX = Math.round(fontSize * 0.6);
  const padY = Math.round(fontSize * 0.32);

  return (
    <div
      style={{
        position: "absolute",
        top: "32%",
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        opacity,
        transform: `scale(${popIn * scaleOut}) rotate(${rotate}deg)`,
      }}
    >
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: Math.round(fontSize * 0.25),
          padding: `${padY}px ${padX}px`,
          backgroundColor: bg,
          color: fg,
          fontSize,
          fontWeight: 900,
          fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', sans-serif`,
          letterSpacing: 2,
          borderRadius: 20,
          border: `5px solid ${fg === "#FFFFFF" ? "#000000" : "#FFFFFF"}`,
          boxShadow: "0 12px 36px rgba(0,0,0,0.55)",
          maxWidth: width * 0.85,
          whiteSpace: "nowrap",
        }}
      >
        {emoji ? <span style={{ fontSize: fontSize * 1.05 }}>{emoji}</span> : null}
        {text ? <span>{text}</span> : null}
      </div>
    </div>
  );
};

const EmojiSticker: React.FC<{
  emoji: string;
  durationInFrames: number;
}> = ({ emoji, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const popIn = spring({
    frame,
    fps,
    config: { damping: 8, stiffness: 180, mass: 0.5 },
    durationInFrames: 12,
  });
  const holdFrames = Math.min(durationInFrames, Math.round(fps * 1.5));
  const opacity = interpolate(
    frame,
    safeRange(0, 3, holdFrames - 6, holdFrames),
    [0, 1, 1, 0],
    { extrapolateRight: "clamp" },
  );
  // 轻微浮动
  const float = Math.sin((frame / fps) * 4) * 6;

  const fontSize = Math.round(height * 0.13);

  return (
    <div
      style={{
        position: "absolute",
        top: "30%",
        right: width * 0.08,
        opacity,
        transform: `scale(${popIn}) translateY(${float}px) rotate(${interpolate(
          popIn,
          [0, 1],
          [-15, 0],
        )}deg)`,
        fontSize,
        textShadow: "0 8px 24px rgba(0,0,0,0.45)",
        pointerEvents: "none",
      }}
    >
      {emoji}
    </div>
  );
};

const CoverScene: React.FC<{
  title?: string;
  coverBgSrc?: string;
  hashtag?: string;
  neonMode?: boolean;
}> = ({ title, coverBgSrc, hashtag, neonMode }) => {
  const { width, height } = useVideoConfig();

  // 标题样式跟 Python pipeline 完全对齐：
  // - PangMen 字体
  // - 白色 + 12% 字号厚黑外描边（paint-order:stroke 让描边在白字底下）
  // - 顶部 15% 中心位置
  // - 字号根据字数：1-2 字 17%，3-4 字 15%，5-6 字 13%
  const titleLen = Math.max(1, (title ?? "").length);
  // 4 字以上换两行，让字号大幅放大
  const useTwoLines = titleLen >= 4;
  const totalLines = useTwoLines ? 2 : 1;
  const charsPerLine = useTwoLines ? Math.ceil(titleLen / 2) : titleLen;
  const lines = useTwoLines
    ? [
        (title ?? "").slice(0, charsPerLine),
        (title ?? "").slice(charsPerLine),
      ]
    : [title ?? ""];
  // 实际宽度 ≈ charsPerLine × fontSize + letterSpacing + stroke
  const charSlots = charsPerLine + 0.04 * Math.max(0, charsPerLine - 1) + 0.24;
  const widthBased = (width * 0.85) / charSlots;
  // 总高度 ≤ 32% 画面（双行）/ 20%（单行）
  const heightBased = (height * (useTwoLines ? 0.36 : 0.22)) / totalLines;
  const fontSize = Math.round(Math.min(widthBased, heightBased));
  const strokeW = Math.round(fontSize * 0.10);
  // 标题块中心位置：双行时下移到 18% 让两行都在上半部
  const titleCenterY = Math.round(height * (useTwoLines ? 0.20 : 0.15));

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {coverBgSrc ? (
        <Img
          src={resolveSrc(coverBgSrc)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      ) : null}

      {hashtag ? <HashtagPill hashtag={hashtag} neonMode={neonMode} /> : null}

      {title ? (
        <div
          style={{
            position: "absolute",
            top: titleCenterY,
            left: 0,
            right: 0,
            transform: "translateY(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 0,
          }}
        >
          {lines.map((line, i) => (
            <div
              key={i}
              style={{
                fontSize,
                fontWeight: 900,
                fontFamily: `'${TITLE_FONT}', '${SUB_FONT}', sans-serif`,
                color: "white",
                WebkitTextStroke: `${strokeW}px black`,
                paintOrder: "stroke fill",
                letterSpacing: Math.max(2, Math.round(fontSize * 0.04)),
                lineHeight: 1.0,
                whiteSpace: "nowrap",
                textShadow: neonMode ? "0 8px 24px rgba(0,0,0,0.8)" : "none",
              }}
            >
              {line}
            </div>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
