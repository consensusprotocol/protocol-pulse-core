#!/usr/bin/env python3
"""
medley director
- builds a 60s intelligence brief from recent mega whales + top feed signals
- renders with ffmpeg h264_nvenc and writes a progress file for /hub polling
"""

from __future__ import annotations

import argparse
import json
import os
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


def _local_background_image() -> Path | None:
    candidates = [
        PROJECT_ROOT / "static" / "img" / "terminal_bg.png",
        PROJECT_ROOT / "static" / "img" / "starfield_deep.png",
        PROJECT_ROOT / "static" / "background.jpg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _validate_rendered_mp4(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "output missing"
    size = int(path.stat().st_size)
    if size < 10 * 1024:
        try:
            path.unlink()
        except Exception:
            pass
        return False, f"output too small ({size} bytes)"
    try:
        head = path.read_bytes()[:8192].lower()
        if b"<html" in head or b"<!doctype html" in head:
            try:
                path.unlink()
            except Exception:
                pass
            return False, "html payload detected in output"
    except Exception as e:
        return False, f"header read failed: {e}"

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name:format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        return False, "ffprobe failed"
    try:
        payload = json.loads(probe.stdout or "{}")
        streams = payload.get("streams") or []
        has_video = any((s or {}).get("codec_type") == "video" for s in streams)
        duration = float((payload.get("format") or {}).get("duration") or 0.0)
        if not has_video or duration <= 0:
            return False, "invalid ffprobe stream metadata"
        print(f"VIDEO VALIDATION OK | file={path} | size={size} | duration={duration:.2f}s")
        return True, "ok"
    except Exception as e:
        return False, f"ffprobe parse failed: {e}"


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


def _top_zapped_partner_urls(limit: int = 3) -> List[str]:
    urls: List[str] = []
    with app.app_context():
        posts = (
            models.CuratedPost.query.filter(
                models.CuratedPost.source_url.isnot(None),
                models.CuratedPost.source_url != "",
            )
            .order_by(models.CuratedPost.zaps_received.desc(), models.CuratedPost.signal_score.desc())
            .limit(max(10, limit * 3))
            .all()
        )
    for post in posts:
        u = str(post.source_url or "").strip()
        if not u:
            continue
        host = u.lower()
        if "youtube.com" in host or "youtu.be" in host:
            urls.append(u)
        if len(urls) >= limit:
            break
    return urls


def _download_partner_clips(urls: List[str], tmp: Path, clip_seconds: int = 20) -> List[Path]:
    clips: List[Path] = []
    for i, url in enumerate(urls, start=1):
        out = tmp / f"clip_{i:02d}.mp4"
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f",
            "bv*[height<=1080]+ba/b[height<=1080]/best",
            "--download-sections",
            f"*0-{clip_seconds}",
            "--merge-output-format",
            "mp4",
            "-o",
            str(out),
            url,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
            if out.exists() and out.stat().st_size > 0:
                clips.append(out)
        except Exception:
            continue
    return clips


def _build_elevenlabs_voiceover(lines: List[str], out_mp3: Path) -> bool:
    key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if not key:
        return False
    try:
        import requests
        voice_id = (os.environ.get("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL").strip()
        text = " ".join(lines[:8]).strip()[:1400]
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
                "voice_settings": {"stability": 0.35, "similarity_boost": 0.6},
            },
            timeout=45,
        )
        if not r.ok or not r.content:
            return False
        out_mp3.write_bytes(r.content)
        return out_mp3.exists() and out_mp3.stat().st_size > 0
    except Exception:
        return False


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


def _render(output: Path, progress_file: Path, text_file: Path, duration_sec: int = 60) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    bg = _local_background_image()
    if bg is None:
        raise RuntimeError("ERROR: MISSING ASSET (background image in static/img)")
    vf = (
        "scale=1920:1080,"
        "drawbox=x=80:y=120:w=1760:h=840:color=black@0.55:t=fill,"
        "drawbox=x=80:y=120:w=1760:h=4:color=#DC2626@0.95:t=fill,"
        "drawtext=font='JetBrains Mono':text='protocol pulse // commander brief':fontcolor=#DC2626:fontsize=34:x=(w-text_w)/2:y=170,"
        f"drawtext=font='JetBrains Mono':textfile='{_ffmpeg_subtitles_path(text_file)}':fontcolor=white:fontsize=30:line_spacing=12:x=140:y=260"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(bg),
        "-t",
        str(int(duration_sec)),
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
        text_file = Path(td) / "brief.txt"
        duration_sec = max(4, int(args.duration or 60))
        # Local-only rendering: no web screenshots/downloaded URL frames.
        _write_srt(lines, srt_file, duration_sec=duration_sec)
        text_file.write_text("\n".join(lines[:10]), encoding="utf-8")
        _render(output, progress_file, text_file, duration_sec=duration_sec)

    valid, validation_msg = _validate_rendered_mp4(output)
    if not valid:
        raise RuntimeError(f"media validation failed: {validation_msg}")

    report = {
        "started_at": started,
        "finished_at": datetime.utcnow().isoformat(),
        "output": str(output),
        "line_count": len(lines),
        "gpu_hint": "cuda_visible_devices=1 expected",
        "pipeline": "ffmpeg_local_background_drawtext",
        "validation": validation_msg,
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
