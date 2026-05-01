"""每行单独 TTS → ffprobe 测时长 → ffmpeg concat 成完整音频 + 切句 JSON。"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "script.txt"
AUDIO_OUT = ROOT / "voice.mp3"
CUES_OUT = ROOT / "voice_cues.json"
TMP = ROOT / "_tmp_lines"

VOICE = "zh-CN-YunjianNeural"  # 云健 — 运动播报员
RATE = "+12%"  # 紧致、有冲击力
VOLUME = "+0%"


def ffprobe_duration(p: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1", str(p),
        ],
        text=True,
    )
    return float(out.strip())


async def tts_line(text: str, out: Path) -> None:
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, volume=VOLUME)
    with out.open("wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])


async def main() -> None:
    text = SCRIPT.read_text(encoding="utf-8").strip()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    print(f"[1/3] 生成 {len(lines)} 行配音 (voice={VOICE}, rate={RATE})...")

    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir()

    cues: list[dict] = []
    cursor_ms = 0.0
    list_file = TMP / "concat.txt"
    list_lines: list[str] = []
    SILENCE_MS = 180  # 行间静音 — 紧致一点

    for i, line in enumerate(lines):
        line_path = TMP / f"line_{i:02d}.mp3"
        await tts_line(line, line_path)
        dur_s = ffprobe_duration(line_path)
        start_ms = cursor_ms
        end_ms = start_ms + dur_s * 1000
        cues.append({"text": line, "start_ms": start_ms, "end_ms": end_ms})
        cursor_ms = end_ms + SILENCE_MS
        list_lines.append(f"file '{line_path.resolve()}'")
        # 加一段静音过渡（最后一段不加）
        if i < len(lines) - 1:
            silence_path = TMP / f"sil_{i:02d}.mp3"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi", "-t", f"{SILENCE_MS/1000}",
                    "-i", "anullsrc=channel_layout=mono:sample_rate=24000",
                    "-q:a", "9", str(silence_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            list_lines.append(f"file '{silence_path.resolve()}'")
        print(f"      {start_ms/1000:5.2f}s-{end_ms/1000:5.2f}s  {line}")

    list_file.write_text("\n".join(list_lines), encoding="utf-8")

    print(f"[2/3] ffmpeg concat → {AUDIO_OUT.name}")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(AUDIO_OUT),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    total = ffprobe_duration(AUDIO_OUT)
    print(f"      总时长: {total:.2f}s")

    print(f"[3/3] 写 {CUES_OUT.name}")
    CUES_OUT.write_text(
        json.dumps({"cues": cues, "total_ms": total * 1000, "voice": VOICE}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    shutil.rmtree(TMP)
    print("完成。")


if __name__ == "__main__":
    asyncio.run(main())
