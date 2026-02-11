#!/usr/bin/env python3
"""
medley director
- builds a 60s intelligence brief from recent mega whales + top feed signals
- renders with ffmpeg h264_nvenc and writes a progress file for /hub polling
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
import models


def _timecode(seconds: float) -> str:
    millis = int(max(0, seconds) * 1000)
    h = millis // 3_600_000
    millis %= 3_600_000
    m = millis // 60_000
    millis %= 60_000
    s = millis // 1000
    ms = millis % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _escape_srt_text(line: str) -> str:
    return line.replace("\n", " ").strip()


def _ffmpeg_subtitles_path(path: Path) -> str:
    # ffmpeg subtitle filter escaping for linux paths.
    p = str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return p


def _build_brief_lines() -> List[str]:
    lines: List[str] = [
        "protocol pulse // commander brief",
        "signal room online | condition red tracking active",
    ]
    with app.app_context():
        whales = (
            models.WhaleTransaction.query.filter_by(is_mega=True)
            .order_by(models.WhaleTransaction.detected_at.desc())
            .limit(10)
            .all()
        )
        feed_items = (
            models.FeedItem.query.order_by(models.FeedItem.created_at.desc())
            .limit(5)
            .all()
        )

    if whales:
        lines.append("mega whale board // last 10:")
        for idx, w in enumerate(whales, start=1):
            usd = int(float(w.usd_value or 0))
            lines.append(
                f"{idx:02d}. {float(w.btc_amount or 0):.2f} btc | ${usd:,} | tx {str(w.txid or '')[:10]}..."
            )
    else:
        lines.append("mega whale board quiet | no qualifying transfers in cache.")

    if feed_items:
        lines.append("top news signals:")
        for idx, item in enumerate(feed_items, start=1):
            title = (item.title or "untitled signal").strip().lower()
            source = (item.source or "unknown").strip().lower()
            lines.append(f"{idx:02d}. {title[:80]} | src: {source}")
    else:
        lines.append("news queue sparse | no fresh feed items.")

    lines.append("action: monitor hashrate fluctuations | sentry queue standing by.")
    return [ln.lower() for ln in lines]


def _write_srt(lines: List[str], srt_path: Path, duration_sec: int = 60) -> None:
    usable = lines[:12] if lines else ["signal missing"]
    segment = max(3.5, duration_sec / max(1, len(usable)))
    cursor = 0.0
    chunks = []
    for idx, line in enumerate(usable, start=1):
        start = cursor
        end = min(duration_sec, cursor + segment)
        cursor = end
        chunks.append(
            f"{idx}\n{_timecode(start)} --> {_timecode(end)}\n{_escape_srt_text(line)}\n"
        )
        if end >= duration_sec:
            break
    srt_path.write_text("\n".join(chunks), encoding="utf-8")


def _render(output: Path, progress_file: Path, srt_file: Path, duration_sec: int = 60) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"subtitles='{_ffmpeg_subtitles_path(srt_file)}':"
        "force_style='FontName=JetBrains Mono,Fontsize=34,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H002626DC,"
        "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=90'"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x050508:s=1920x1080:d={int(duration_sec)}",
        "-vf",
        vf,
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-progress",
        str(progress_file),
        "-nostats",
        str(output),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="protocol pulse medley director")
    parser.add_argument("--output", required=True)
    parser.add_argument("--progress-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    progress_file = Path(args.progress_file).resolve()
    report_file = Path(args.report_file).resolve()
    report_file.parent.mkdir(parents=True, exist_ok=True)

    started = datetime.utcnow().isoformat()
    lines = _build_brief_lines()
    with tempfile.TemporaryDirectory(prefix="medley-director-") as td:
        srt_file = Path(td) / "brief.srt"
        duration_sec = max(4, int(args.duration or 60))
        _write_srt(lines, srt_file, duration_sec=duration_sec)
        _render(output, progress_file, srt_file, duration_sec=duration_sec)

    report = {
        "started_at": started,
        "finished_at": datetime.utcnow().isoformat(),
        "output": str(output),
        "line_count": len(lines),
        "gpu_hint": "cuda_visible_devices=1 expected",
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
