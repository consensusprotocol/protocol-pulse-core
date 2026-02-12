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


def _render_media_pipeline(output: Path, lines: List[str], duration_sec: int) -> bool:
    """Attempt yt-dlp + moviepy assembly first; return False to use fallback renderer."""
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips
    except Exception:
        return False

    with tempfile.TemporaryDirectory(prefix="medley-media-") as td:
        tmp = Path(td)
        urls = _top_zapped_partner_urls(limit=3)
        if not urls:
            return False
        clips = _download_partner_clips(urls, tmp, clip_seconds=max(12, duration_sec // 3))
        if not clips:
            return False

        video_clips = []
        for path in clips:
            try:
                c = VideoFileClip(str(path))
                if c.duration > 0:
                    video_clips.append(c)
            except Exception:
                continue
        if not video_clips:
            return False

        final = concatenate_videoclips(video_clips, method="compose")
        final = final.subclip(0, min(duration_sec, max(1, int(final.duration))))

        voice_mp3 = tmp / "voice.mp3"
        if _build_elevenlabs_voiceover(lines, voice_mp3):
            try:
                audio = AudioFileClip(str(voice_mp3))
                final = final.set_audio(audio.subclip(0, min(final.duration, audio.duration)))
            except Exception:
                pass

        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            final.write_videofile(
                str(output),
                codec="h264_nvenc",
                audio_codec="aac",
                fps=30,
                threads=4,
                ffmpeg_params=["-preset", "p4", "-pix_fmt", "yuv420p"],
                logger=None,
            )
        except Exception:
            final.write_videofile(
                str(output),
                codec="libx264",
                audio_codec="aac",
                fps=30,
                threads=4,
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                logger=None,
            )
        try:
            final.close()
            for c in video_clips:
                c.close()
        except Exception:
            pass
        return output.exists() and output.stat().st_size > 0


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
        used_media_pipeline = _render_media_pipeline(output, lines, duration_sec=duration_sec)
        if not used_media_pipeline:
            _write_srt(lines, srt_file, duration_sec=duration_sec)
            _render(output, progress_file, srt_file, duration_sec=duration_sec)

    report = {
        "started_at": started,
        "finished_at": datetime.utcnow().isoformat(),
        "output": str(output),
        "line_count": len(lines),
        "gpu_hint": "cuda_visible_devices=1 expected",
        "pipeline": "yt-dlp+moviepy+elevenlabs" if 'used_media_pipeline' in locals() and used_media_pipeline else "ffmpeg_nvenc_fallback",
    }
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
