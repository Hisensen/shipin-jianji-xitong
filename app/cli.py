"""CLI 入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.pipeline import collect_videos, process_many


def main() -> None:
    ap = argparse.ArgumentParser(description="视频字幕封面系统 — CLI")
    ap.add_argument("input", help="视频文件或目录")
    ap.add_argument("--title", help="手动指定标题，覆盖 LLM", default=None)
    args = ap.parse_args()
    p = Path(args.input).expanduser().resolve()
    if not p.exists():
        sys.exit(f"错误: {p} 不存在")
    videos = collect_videos(p)
    if not videos:
        sys.exit(f"无视频: {p}")
    if args.title and len(videos) > 1:
        sys.exit("错误：--title 只能配合单个视频使用")
    if args.title:
        from app.pipeline import process_one
        r = process_one(videos[0], override_title=args.title)
        print(f"{'✅' if r.ok else '❌'} {r.out_dir}")
        sys.exit(0 if r.ok else 1)
    results = process_many(videos)
    ok = sum(1 for r in results if r.ok)
    print(f"\n总计 {len(results)}: {ok} 成功 / {len(results)-ok} 失败")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
