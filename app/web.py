"""FastAPI Web UI：上传/扫描/预览/重生成 + Remotion 多版本批量。"""
from __future__ import annotations

import asyncio
import io
import json
import shutil
import threading
import time
import uuid
import zipfile
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    INBOX_DIR,
    OUTPUT_DIR,
    ROOT,
    STATIC_DIR,
    TEMPLATES_DIR,
    VIDEO_EXTS,
)
from app.cover import compose_cover
from app.llm import generate_title
from app.pipeline import collect_videos, process_one
from app.subtitle import apply_cover_to_raw
from app import remotion_runner

app = FastAPI(title="视频字幕封面系统")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 运行中的任务：stem -> "processing" / "done" / "failed:<msg>"
_status: dict[str, str] = {}
_lock = asyncio.Lock()


def _list_inbox() -> list[dict]:
    rows: dict[str, dict] = {}
    # 1) 现存 inbox 视频
    for p in sorted(INBOX_DIR.glob("*")):
        if p.suffix.lower() not in VIDEO_EXTS:
            continue
        stem = p.stem
        out = OUTPUT_DIR / stem
        failed = OUTPUT_DIR / f"{stem}.FAILED"
        if out.exists():
            status = "done"
        elif failed.exists():
            status = "failed"
        else:
            status = _status.get(stem, "pending")
        rows[stem] = {
            "stem": stem,
            "name": p.name,
            "size_mb": round(p.stat().st_size / 1024 / 1024, 1),
            "status": status,
            "source_exists": True,
        }
    # 2) 已完成但 inbox 已删的：补上 output-only 行
    for out_dir in sorted(OUTPUT_DIR.glob("*")):
        if not out_dir.is_dir() or out_dir.name.endswith(".FAILED"):
            continue
        stem = out_dir.name
        if stem in rows:
            continue
        mp4 = out_dir / f"{stem}_sub.mp4"
        rows[stem] = {
            "stem": stem,
            "name": f"{stem} (源已删)",
            "size_mb": round(mp4.stat().st_size / 1024 / 1024, 1) if mp4.exists() else 0,
            "status": "done",
            "source_exists": False,
        }
    return list(rows.values())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"items": _list_inbox()},
    )


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    saved = []
    for f in files:
        name = Path(f.filename or "").name
        if not name or Path(name).suffix.lower() not in VIDEO_EXTS:
            continue
        dest = INBOX_DIR / name
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(name)
    return {"saved": saved}


@app.post("/api/scan")
async def scan():
    return {"items": _list_inbox()}


@app.get("/api/status")
async def status_api():
    return {"items": _list_inbox()}


async def _run_process(video: Path, override_title: Optional[str] = None):
    stem = video.stem
    async with _lock:
        _status[stem] = "processing"
    try:
        r = await asyncio.to_thread(process_one, video, override_title=override_title)
        _status[stem] = "done" if r.ok else f"failed: {r.error}"
    except Exception as e:
        _status[stem] = f"failed: {e}"


@app.post("/api/process/{stem}")
async def process_one_api(stem: str):
    video = _find_inbox(stem)
    if not video:
        raise HTTPException(404, "视频不存在")
    if _status.get(stem) == "processing":
        return {"ok": False, "msg": "已在处理中"}
    asyncio.create_task(_run_process(video))
    return {"ok": True}


@app.post("/api/process_all")
async def process_all_api():
    started = []
    for p in collect_videos(INBOX_DIR):
        stem = p.stem
        if (OUTPUT_DIR / stem).exists():
            continue
        if _status.get(stem) == "processing":
            continue
        asyncio.create_task(_run_process(p))
        started.append(stem)
    return {"started": started}


def _find_inbox(stem: str) -> Path | None:
    for ext in VIDEO_EXTS:
        p = INBOX_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


@app.get("/detail/{stem}", response_class=HTMLResponse)
async def detail(request: Request, stem: str):
    out = OUTPUT_DIR / stem
    if not out.exists():
        raise HTTPException(404, "产物目录不存在")
    meta = json.loads((out / f"{stem}.meta.json").read_text(encoding="utf-8"))
    return templates.TemplateResponse(
        request,
        "detail.html",
        {"stem": stem, "meta": meta},
    )


def _reapply_cover_to_video(stem: str, meta: dict) -> None:
    """把当前 cover.jpg 重新贴到视频第一帧（concat stream-copy，秒级）。"""
    out = OUTPUT_DIR / stem
    raw = out / "debug" / f"{stem}_sub_raw.mp4"
    if not raw.exists():
        raise HTTPException(
            500,
            "这条视频是旧版处理的（没有 sub_raw.mp4），请删除产物后重新处理一次",
        )
    cover = out / f"{stem}_cover.jpg"
    video_sub = out / f"{stem}_sub.mp4"
    apply_cover_to_raw(
        cover=cover, raw=raw, video_out=video_sub,
        w=meta["width"], h=meta["height"],
        has_audio_flag=meta.get("has_audio", not meta.get("warning_no_audio", False)),
    )


@app.post("/api/regen_title/{stem}")
async def regen_title(stem: str):
    """重调 LLM 标题 → 重合成封面 → 封面回写到视频第一帧。"""
    out = OUTPUT_DIR / stem
    if not out.exists():
        raise HTTPException(404)
    meta = json.loads((out / f"{stem}.meta.json").read_text(encoding="utf-8"))
    srt_text = (out / f"{stem}.srt").read_text(encoding="utf-8")
    lines = [
        ln for ln in srt_text.splitlines()
        if ln and not ln[0].isdigit() and "-->" not in ln
    ]
    transcript = " ".join(lines)
    title, source = generate_title(transcript)
    cand = out / "debug" / "candidates"
    frames = sorted(cand.glob("cand_*.jpg"))
    best_time = meta.get("cover_frame_time", 0)
    best_frame = frames[0] if frames else None
    for f in frames:
        try:
            t = float(f.stem.split("_")[-1])
            if abs(t - best_time) < 0.1:
                best_frame = f
                break
        except Exception:
            pass
    if not best_frame:
        raise HTTPException(500, "找不到精彩帧")
    cover_path = out / f"{stem}_cover.jpg"
    cover_meta = compose_cover(best_frame, title, cover_path)
    meta["title"] = title
    meta["title_source"] = source
    meta["cover"] = cover_meta
    # 回写视频
    await asyncio.to_thread(_reapply_cover_to_video, stem, meta)
    (out / f"{stem}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"ok": True, "title": title, "source": source}


@app.post("/api/repick/{stem}")
async def repick_frame(stem: str, time: float):
    """换候选帧作封面 → 重合成 → 回写视频。"""
    out = OUTPUT_DIR / stem
    if not out.exists():
        raise HTTPException(404)
    cand = out / "debug" / "candidates"
    frames = sorted(cand.glob("cand_*.jpg"))
    best = None
    for f in frames:
        try:
            t = float(f.stem.split("_")[-1])
            if abs(t - time) < 0.05:
                best = f
                break
        except Exception:
            pass
    if not best:
        raise HTTPException(404, "候选帧不存在")
    meta = json.loads((out / f"{stem}.meta.json").read_text(encoding="utf-8"))
    title = meta.get("title") or "视频"
    cover_meta = compose_cover(best, title, out / f"{stem}_cover.jpg")
    meta["cover_frame_time"] = round(time, 3)
    meta["cover"] = cover_meta
    await asyncio.to_thread(_reapply_cover_to_video, stem, meta)
    (out / f"{stem}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"ok": True}


@app.get("/api/candidates/{stem}")
async def list_candidates(stem: str):
    cand = OUTPUT_DIR / stem / "debug" / "candidates"
    items = []
    for f in sorted(cand.glob("cand_*.jpg")):
        try:
            t = float(f.stem.split("_")[-1])
        except Exception:
            continue
        items.append({"time": t, "url": f"/output/{stem}/debug/candidates/{f.name}"})
    return {"items": items}


@app.get("/download/{stem}")
async def download_zip(stem: str):
    out = OUTPUT_DIR / stem
    if not out.exists():
        raise HTTPException(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in out.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(out))
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}.zip"'},
    )


@app.get("/download_mp4/{stem}")
async def download_mp4(stem: str):
    """单独下载带字幕的 mp4（带正确文件名）。"""
    mp4 = OUTPUT_DIR / stem / f"{stem}_sub.mp4"
    if not mp4.exists():
        raise HTTPException(404, "mp4 不存在")
    return FileResponse(
        mp4, media_type="video/mp4",
        filename=f"{stem}_sub.mp4",
    )


@app.get("/download_all_mp4")
async def download_all_mp4():
    """把所有已完成视频的 _sub.mp4 打包 zip 给用户一次下载。"""
    mp4s = sorted(OUTPUT_DIR.glob("*/*_sub.mp4"))
    if not mp4s:
        raise HTTPException(404, "还没有已完成的视频")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in mp4s:
            z.write(p, p.name)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="all_sub_mp4.zip"'},
    )


@app.post("/api/delete_source/{stem}")
async def delete_source(stem: str):
    """只删 inbox 里的源视频，保留 output 产物。"""
    src = _find_inbox(stem)
    if not src or not src.exists():
        raise HTTPException(404, "源视频不存在")
    try:
        src.unlink()
    except Exception as e:
        raise HTTPException(500, f"删除失败: {e}")
    return {"ok": True, "deleted": f"inbox/{src.name}"}


@app.post("/api/delete_output/{stem}")
async def delete_output(stem: str):
    """只删 output 产物目录（含 .FAILED），不动 inbox。"""
    deleted = []
    out = OUTPUT_DIR / stem
    if out.exists():
        shutil.rmtree(out)
        deleted.append(f"output/{stem}/")
    failed = OUTPUT_DIR / f"{stem}.FAILED"
    if failed.exists():
        shutil.rmtree(failed)
        deleted.append(f"output/{stem}.FAILED/")
    _status.pop(stem, None)
    if not deleted:
        raise HTTPException(404, "没有产物可删")
    return {"ok": True, "deleted": deleted}


@app.post("/api/delete_all_sources")
async def delete_all_sources():
    """一键删除 inbox 里的所有源视频，保留所有产物。"""
    deleted = []
    for p in INBOX_DIR.glob("*"):
        if p.suffix.lower() in VIDEO_EXTS:
            try:
                p.unlink()
                deleted.append(p.name)
            except Exception:
                pass
    return {"ok": True, "deleted": deleted, "count": len(deleted)}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# =====================================================================
# Remotion 多版本批量处理
# =====================================================================

REMOTION_OUTPUT_DIR = OUTPUT_DIR / "remotion"
REMOTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REMOTION_UPLOAD_DIR = ROOT / "uploads_remotion"
REMOTION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/remotion_output",
    StaticFiles(directory=REMOTION_OUTPUT_DIR),
    name="remotion_output",
)

VALID_VERSIONS = {"v1", "v2", "v3", "v4", "v5", "v6", "v7"}
VERSION_LABELS = {
    "v1": "V1 基础（封面+章节+字幕+Pexels 角落图）",
    "v2": "V2 极简（去掉所有图）",
    "v3": "V3 智能（自动选 callout/emoji/图）",
    "v4": "V4 爆款（金句卡+章节白闪+关键词弹跳）",
    "v5": "V5 顶配 · 黑白黄爆款（适合女性情感赛道）",
    "v6": "V6 报刊 · 米色衬线（适合知识深度赛道）",
    "v7": "V7 极简 AI · 黑底蓝光 + 进度条（适合 AI/科技赛道）",
}


@dataclass
class RemotionJob:
    id: str
    video_name: str
    video_path: Path
    version: str
    status: str = "pending"  # pending / running / done / failed
    log: list[str] = field(default_factory=list)
    output_path: Optional[Path] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


_remotion_jobs: dict[str, RemotionJob] = {}
_remotion_queue: deque[str] = deque()
_remotion_lock = threading.Lock()
_remotion_worker: Optional[threading.Thread] = None


def _remotion_worker_loop():
    while True:
        with _remotion_lock:
            if not _remotion_queue:
                return
            job_id = _remotion_queue.popleft()
        job = _remotion_jobs.get(job_id)
        if not job:
            continue
        job.status = "running"
        try:
            stem = Path(job.video_name).stem
            out = REMOTION_OUTPUT_DIR / f"{stem}_{job.version}.mp4"
            remotion_runner.run(
                job.video_path,
                job.version,
                out,
                on_log=lambda s, j=job: j.log.append(s),
            )
            job.output_path = out
            job.status = "done"
        except Exception as e:
            job.error = str(e)
            job.status = "failed"


def _ensure_remotion_worker():
    global _remotion_worker
    with _remotion_lock:
        if _remotion_worker is None or not _remotion_worker.is_alive():
            _remotion_worker = threading.Thread(
                target=_remotion_worker_loop, daemon=True
            )
            _remotion_worker.start()


@app.get("/remotion", response_class=HTMLResponse)
async def remotion_page(request: Request):
    return templates.TemplateResponse(
        request,
        "remotion.html",
        {"version_labels": VERSION_LABELS},
    )


@app.post("/api/remotion/upload")
async def remotion_upload(
    version: str = Form(...),
    files: list[UploadFile] = File(...),
):
    if version not in VALID_VERSIONS:
        raise HTTPException(400, f"非法版本 {version}")
    job_ids: list[str] = []
    for f in files:
        name = Path(f.filename or "").name
        if not name or Path(name).suffix.lower() not in VIDEO_EXTS:
            continue
        # 不重名：加时间戳前缀
        unique_name = f"{int(time.time() * 1000)}_{name}"
        dest = REMOTION_UPLOAD_DIR / unique_name
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        job_id = uuid.uuid4().hex[:8]
        job = RemotionJob(
            id=job_id,
            video_name=name,
            video_path=dest,
            version=version,
        )
        _remotion_jobs[job_id] = job
        with _remotion_lock:
            _remotion_queue.append(job_id)
        job_ids.append(job_id)
    if not job_ids:
        raise HTTPException(400, "没有有效视频上传")
    _ensure_remotion_worker()
    return {"ok": True, "job_ids": job_ids, "queued": len(job_ids)}


@app.get("/api/remotion/jobs")
async def remotion_jobs():
    items = []
    for j in sorted(
        _remotion_jobs.values(), key=lambda x: x.created_at, reverse=True
    ):
        items.append(
            {
                "id": j.id,
                "name": j.video_name,
                "version": j.version,
                "status": j.status,
                "log": j.log[-3:],
                "output_url": (
                    f"/remotion_output/{j.output_path.name}"
                    if j.output_path and j.output_path.exists()
                    else None
                ),
                "output_filename": (
                    j.output_path.name if j.output_path else None
                ),
                "error": j.error,
                "created_at": j.created_at,
            }
        )
    return {"jobs": items}


@app.post("/api/remotion/delete/{job_id}")
async def remotion_delete(job_id: str):
    job = _remotion_jobs.pop(job_id, None)
    if not job:
        raise HTTPException(404, "任务不存在")
    # 清理上传文件 + 输出文件（如果存在）
    try:
        if job.video_path.exists():
            job.video_path.unlink()
    except Exception:
        pass
    try:
        if job.output_path and job.output_path.exists():
            job.output_path.unlink()
    except Exception:
        pass
    return {"ok": True}
