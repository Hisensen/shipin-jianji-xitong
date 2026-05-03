"""跑单条 Remotion 任务：调对应的 make_cues 脚本 + 调 npx remotion render。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTION_DIR = ROOT / "remotion"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
REMOTION_BIN = REMOTION_DIR / "node_modules" / ".bin" / "remotion"

# version → (make_cues 脚本, Composition id)
VERSION_TO_SCRIPT = {
    "v1": "make_cues.py",
    "v2": "make_cues.py",  # V1/V2 共用数据
    "v3": "make_cues_v3.py",
    "v4": "make_cues_v4.py",
    "v5": "make_cues_v5.py",
    "v6": "make_cues_v6.py",
    "v7": "make_cues_v7.py",
}

VERSION_TO_COMPOSITION = {
    "v1": "PublishVideo14",
    "v2": "PublishVideo14NoImages",
    "v3": "PublishVideo14V3",
    "v4": "PublishVideo14V4",
    "v5": "PublishVideo14V5",
    "v6": "PublishVideo14V6",
    "v7": "PublishVideo14V7",
}


def run(
    video_path: Path,
    version: str,
    output_path: Path,
    on_log=lambda s: None,
) -> Path:
    """跑完一个版本，返回输出 mp4 路径。失败抛 RuntimeError。"""
    if version not in VERSION_TO_COMPOSITION:
        raise ValueError(f"未知版本: {version}")
    script = VERSION_TO_SCRIPT[version]
    composition = VERSION_TO_COMPOSITION[version]

    # 确保是绝对路径 — Remotion 渲染时 cwd=remotion/，相对路径会解析错位置
    output_path = output_path.expanduser().resolve()
    video_path = video_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) make_cues
    on_log(f"[1/2] {script} ...")
    py = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    proc = subprocess.run(
        [py, str(REMOTION_DIR / script), str(video_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    for line in out.strip().splitlines()[-15:]:
        on_log(line)
    if proc.returncode != 0:
        raise RuntimeError(f"make_cues 失败 (exit {proc.returncode})")

    # 2) remotion render
    on_log(f"[2/2] render {composition} ...")
    bin_path = REMOTION_BIN if REMOTION_BIN.exists() else "npx"
    if bin_path == "npx":
        cmd = [
            "npx", "remotion", "render", composition,
            str(output_path), "--timeout=60000",
        ]
    else:
        cmd = [
            str(bin_path), "render", composition,
            str(output_path), "--timeout=60000",
        ]
    proc = subprocess.run(
        cmd,
        cwd=str(REMOTION_DIR),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    for line in out.strip().splitlines()[-10:]:
        on_log(line)
    if proc.returncode != 0:
        raise RuntimeError(f"render 失败 (exit {proc.returncode})")

    if not output_path.exists():
        raise RuntimeError(f"render 完成但找不到输出文件: {output_path}")
    on_log(f"完成 → {output_path.name}")
    return output_path
