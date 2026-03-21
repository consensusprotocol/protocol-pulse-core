#!/usr/bin/env python3
"""Protocol Pulse Daily Montage Producer.

Assembles top-scored clips into a branded 45-90s highlights montage.
Pure FFmpeg — no external APIs, no re-downloads.

Usage:
    python3 services/montage_producer.py              # today
    python3 services/montage_producer.py 2026-03-21   # specific date
"""

import json
import logging
import os
import random
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MONTAGE] %(levelname)s %(message)s",
)
log = logging.getLogger("montage")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_OUTPUT = PROJECT_ROOT / "video_pipeline_v3" / "output"
MUSIC_DIR = PROJECT_ROOT / "video_pipeline_v3" / "assets" / "music"
STATIC_DIR = PROJECT_ROOT / "static"

SCORE_THRESHOLD = 60.0
SCORE_THRESHOLD_LOW = 40.0
MAX_CLIPS = 4
MIN_CLIPS = 2
MAX_DURATION = 90.0
MIN_DURATION = 45.0
MIN_CLIP_DURATION = 5.0


# ── Helpers ──────────────────────────────────────────────────────────

def run_cmd(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a shell command, raise on failure."""
    log.debug("CMD: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)


def ffprobe_info(path: str) -> dict | None:
    """Return dict with duration, width, height, has_audio for a video file."""
    try:
        r = run_cmd([
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,width,height,duration",
            "-of", "json", str(path),
        ])
        data = json.loads(r.stdout)
        info = {"duration": 0.0, "width": 0, "height": 0, "has_audio": False}
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["width"] = int(stream.get("width", 0))
                info["height"] = int(stream.get("height", 0))
                if stream.get("duration"):
                    info["duration"] = float(stream["duration"])
            elif stream.get("codec_type") == "audio":
                info["has_audio"] = True
                if not info["duration"] and stream.get("duration"):
                    info["duration"] = float(stream["duration"])
        return info
    except Exception as e:
        log.warning("ffprobe failed for %s: %s", path, e)
        return None


def score_dots(score: float) -> str:
    """Convert score to signal dots string like ●●●●○."""
    filled = min(5, max(1, int(score / 20)))
    return "●" * filled + "○" * (5 - filled)


# ── Pipeline Steps ───────────────────────────────────────────────────

def load_clips(date_str: str) -> list[dict]:
    """Load and filter clips from selections.json."""
    output_dir = PIPELINE_OUTPUT / date_str
    sel_path = output_dir / "selections.json"
    clips_dir = output_dir / "clips"

    if not sel_path.exists():
        log.error("No selections.json at %s", sel_path)
        return []

    with open(sel_path) as f:
        data = json.load(f)

    selections = data.get("clips", [])

    # Map each selection to its clip file
    clip_list = []
    for sel in selections:
        rank = sel["rank"]
        channel = sel["channel"].replace(" ", "_")
        vid = sel["video_id"]
        pattern = f"clip_{rank}_{channel}_{vid}.mp4"
        clip_path = clips_dir / pattern

        if not clip_path.exists():
            log.warning("Clip file not found: %s", clip_path)
            continue

        sel["file"] = str(clip_path)
        clip_list.append(sel)

    # Filter by score threshold
    filtered = [c for c in clip_list if c["score"] >= SCORE_THRESHOLD]
    filtered.sort(key=lambda c: c["score"], reverse=True)

    # If not enough clips or total too short, lower threshold
    if len(filtered) < MIN_CLIPS:
        log.info("Only %d clips >= %.0f, lowering to %.0f", len(filtered), SCORE_THRESHOLD, SCORE_THRESHOLD_LOW)
        filtered = [c for c in clip_list if c["score"] >= SCORE_THRESHOLD_LOW]
        filtered.sort(key=lambda c: c["score"], reverse=True)

    return filtered[:MAX_CLIPS + 1]  # take up to 5 for duration fitting


def validate_clips(clips: list[dict]) -> list[dict]:
    """Probe each clip, skip corrupt or too-short ones."""
    valid = []
    for clip in clips:
        info = ffprobe_info(clip["file"])
        if not info:
            log.warning("Skipping corrupt clip: %s", clip["file"])
            continue
        if info["duration"] < MIN_CLIP_DURATION:
            log.warning("Skipping short clip (%.1fs): %s", info["duration"], clip["file"])
            continue
        clip["probe"] = info
        valid.append(clip)

    if len(valid) < MIN_CLIPS:
        log.error("Only %d valid clips — need at least %d", len(valid), MIN_CLIPS)
        return []

    return valid


def fit_duration(clips: list[dict]) -> list[dict]:
    """Trim clip list to fit within MAX_DURATION. Trim lowest-scoring clip if needed."""
    total = sum(c["probe"]["duration"] for c in clips)

    # Take top 4 first
    result = clips[:MAX_CLIPS]
    total = sum(c["probe"]["duration"] for c in result)

    # If still over 90s, drop the lowest-scoring clip
    while total > MAX_DURATION and len(result) > MIN_CLIPS:
        dropped = result.pop()
        total = sum(c["probe"]["duration"] for c in result)
        log.info("Dropped clip %s (score %.0f) to fit duration — total now %.1fs",
                 dropped["channel"], dropped["score"], total)

    # If under 45s and we had more clips, try adding one back with lower threshold
    if total < MIN_DURATION and len(clips) > len(result):
        for extra in clips[len(result):]:
            if extra not in result:
                result.append(extra)
                total = sum(c["probe"]["duration"] for c in result)
                if total >= MIN_DURATION:
                    break

    log.info("Final clip count: %d, total duration: %.1fs", len(result), total)
    return result


def normalize_audio(clip_path: str, work_dir: Path) -> str:
    """LUFS normalize a clip to -16."""
    out = work_dir / f"norm_{Path(clip_path).name}"
    run_cmd([
        "ffmpeg", "-y", "-i", clip_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "copy", "-ar", "48000",
        str(out),
    ])
    return str(out)


def scale_video(clip_path: str, work_dir: Path) -> str:
    """Scale to 1920x1080 if needed."""
    info = ffprobe_info(clip_path)
    if info and info["width"] == 1920 and info["height"] == 1080:
        return clip_path

    out = work_dir / f"scaled_{Path(clip_path).name}"
    run_cmd([
        "ffmpeg", "-y", "-i", clip_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "copy",
        str(out),
    ])
    return str(out)


def build_intro_slate(work_dir: Path, date_str: str) -> str:
    """Build 3s intro slate with FFmpeg lavfi."""
    out = work_dir / "intro.mp4"
    display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y").upper()
    run_cmd([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0A0A0F:s=1920x1080:d=3:r=30",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", (
            f"drawtext=fontcolor=white:fontsize=80:text='PROTOCOL PULSE'"
            f":x=(w-tw)/2:y=(h-th)/2-60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            f"drawtext=fontcolor=0xFF3333:fontsize=40:text='DAILY HIGHLIGHTS'"
            f":x=(w-tw)/2:y=(h-th)/2+20:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            f"drawtext=fontcolor=white:fontsize=30:text='{display_date}'"
            f":x=(w-tw)/2:y=(h-th)/2+80:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-t", "3", "-shortest",
        str(out),
    ])
    return str(out)


def build_lower_third(clip_path: str, channel: str, score: float, work_dir: Path, idx: int) -> str:
    """Burn lower-third overlay onto clip."""
    out = work_dir / f"lt_{idx}_{Path(clip_path).name}"
    dots = score_dots(score)
    label = f"{channel}  {dots}"
    # Escape special chars for drawtext
    label_escaped = label.replace(":", "\\:").replace("'", "\\'")
    run_cmd([
        "ffmpeg", "-y", "-i", clip_path,
        "-vf", (
            "drawbox=x=0:y=1000:w=650:h=55:color=0xFF3333@0.85:t=fill,"
            f"drawtext=fontcolor=white:fontsize=26:text='{label_escaped}'"
            f":x=15:y=1013:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(out),
    ])
    return str(out)


def build_outro_slate(work_dir: Path) -> str:
    """Build 2s outro slate."""
    out = work_dir / "outro.mp4"
    run_cmd([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0A0A0F:s=1920x1080:d=2:r=30",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", (
            "drawtext=fontcolor=0xFF3333:fontsize=90:text='STAY SOVEREIGN.'"
            ":x=(w-tw)/2:y=(h-th)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=fontcolor=white:fontsize=35:text='protocolpulse.io'"
            ":x=(w-tw)/2:y=(h-th)/2+60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-t", "2", "-shortest",
        str(out),
    ])
    return str(out)


def concat_with_xfade(parts: list[str], work_dir: Path) -> str:
    """Concat video parts with 0.3s xfade dissolve between each."""
    if len(parts) == 1:
        return parts[0]

    out = work_dir / "montage_nomusic.mp4"
    xfade_dur = 0.3

    # Get durations for offset calculation
    durations = []
    for p in parts:
        info = ffprobe_info(p)
        durations.append(info["duration"] if info else 10.0)

    # Build xfade filter chain
    n = len(parts)
    inputs = " ".join(f"-i {p}" for p in parts)
    vfilters = []
    afilters = []
    offset = 0.0

    # Video xfade chain
    for i in range(n - 1):
        if i == 0:
            vin = "[0:v]"
        else:
            vin = f"[xv{i}]"

        offset = sum(durations[:i + 1]) - xfade_dur * (i + 1)
        vout = f"[xv{i + 1}]" if i < n - 2 else "[vout]"
        vfilters.append(f"{vin}[{i + 1}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.3f}{vout}")

    # Audio crossfade chain
    for i in range(n - 1):
        if i == 0:
            ain = "[0:a]"
        else:
            ain = f"[xa{i}]"

        offset = sum(durations[:i + 1]) - xfade_dur * (i + 1)
        aout = f"[xa{i + 1}]" if i < n - 2 else "[aout]"
        afilters.append(f"{ain}[{i + 1}:a]acrossfade=d={xfade_dur}:c1=tri:c2=tri{aout}")

    fc = ";".join(vfilters + afilters)

    cmd = ["ffmpeg", "-y"]
    for p in parts:
        cmd.extend(["-i", p])
    cmd.extend([
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000",
        "-movflags", "+faststart",
        str(out),
    ])
    run_cmd(cmd, timeout=600)
    return str(out)


def add_music_bed(video_path: str, work_dir: Path, date_str: str) -> str:
    """Mix background music at 0.15 volume."""
    out = work_dir / f"montage_{date_str}.mp4"

    # Pick a music track — prefer tense/edge for market content
    candidates = list(MUSIC_DIR.glob("tense_*.mp3")) + list(MUSIC_DIR.glob("edge_*.mp3"))
    if not candidates:
        candidates = list(MUSIC_DIR.glob("*.mp3"))
    if not candidates:
        log.warning("No music files found, skipping music bed")
        shutil.copy2(video_path, str(out))
        return str(out)

    track = str(random.choice(candidates))
    log.info("Music bed: %s", track)

    run_cmd([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", track,
        "-filter_complex",
        "[1:a]aloop=loop=-1:size=48000*300,atrim=duration=300[bgm];"
        "[0:a][bgm]amix=inputs=2:weights=1 0.15:duration=first[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000",
        "-movflags", "+faststart",
        str(out),
    ])
    return str(out)


def generate_shorts(montage_path: str, work_dir: Path, date_str: str) -> str:
    """Crop center 1080x1920 for Shorts format."""
    out = work_dir / f"montage_{date_str}_shorts.mp4"
    run_cmd([
        "ffmpeg", "-y", "-i", montage_path,
        "-vf", "crop=607:1080:656:0,scale=1080:1920",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out),
    ])
    return str(out)


def generate_thumbnail(top_clip_path: str, work_dir: Path, date_str: str) -> str:
    """Extract frame from midpoint of highest-scoring clip."""
    out = work_dir / f"montage_thumb_{date_str}.jpg"
    info = ffprobe_info(top_clip_path)
    midpoint = (info["duration"] / 2) if info else 10.0
    run_cmd([
        "ffmpeg", "-y",
        "-ss", f"{midpoint:.1f}",
        "-i", top_clip_path,
        "-vframes", "1", "-q:v", "2",
        str(out),
    ])
    return str(out)


def copy_outputs(work_dir: Path, date_str: str, output_dir: Path):
    """Copy final files to output dir and update symlink."""
    montage = work_dir / f"montage_{date_str}.mp4"
    shorts = work_dir / f"montage_{date_str}_shorts.mp4"
    thumb = work_dir / f"montage_thumb_{date_str}.jpg"

    for src in [montage, shorts, thumb]:
        if src.exists():
            dst = output_dir / src.name
            shutil.copy2(str(src), str(dst))
            log.info("Copied %s → %s", src.name, dst)

    # Symlink for latest
    symlink = STATIC_DIR / "montage_latest.mp4"
    target = output_dir / f"montage_{date_str}.mp4"
    if target.exists():
        symlink.unlink(missing_ok=True)
        symlink.symlink_to(target)
        log.info("Symlink: %s → %s", symlink, target)

    shorts_symlink = STATIC_DIR / "montage_latest_shorts.mp4"
    shorts_target = output_dir / f"montage_{date_str}_shorts.mp4"
    if shorts_target.exists():
        shorts_symlink.unlink(missing_ok=True)
        shorts_symlink.symlink_to(shorts_target)


# ── Main ─────────────────────────────────────────────────────────────

def produce_montage(date_str: str | None = None) -> dict:
    """Run the full montage pipeline. Returns metadata dict."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    output_dir = PIPELINE_OUTPUT / date_str
    work_dir = output_dir / "montage_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== MONTAGE PRODUCER START — %s ===", date_str)

    # A) Load clips
    clips = load_clips(date_str)
    if not clips:
        log.error("No clips found for %s", date_str)
        return {"error": "no_clips"}

    # B) Validate
    clips = validate_clips(clips)
    if not clips:
        return {"error": "insufficient_valid_clips"}

    # Fit to duration
    clips = fit_duration(clips)
    if not clips:
        return {"error": "cannot_fit_duration"}

    log.info("Selected %d clips: %s", len(clips),
             ", ".join(f"{c['channel']}({c['score']:.0f})" for c in clips))

    # C) Normalize audio + D) Scale video
    processed = []
    for i, clip in enumerate(clips):
        path = clip["file"]
        path = normalize_audio(path, work_dir)
        path = scale_video(path, work_dir)
        processed.append({"path": path, "clip": clip, "idx": i})
        log.info("Processed clip %d/%d: %s", i + 1, len(clips), clip["channel"])

    # F) Add lower thirds
    lt_parts = []
    for item in processed:
        path = build_lower_third(
            item["path"], item["clip"]["channel"],
            item["clip"]["score"], work_dir, item["idx"],
        )
        lt_parts.append(path)

    # E) Build intro slate
    intro = build_intro_slate(work_dir, date_str)

    # G) Build outro slate
    outro = build_outro_slate(work_dir)

    # H) Concat with xfade
    all_parts = [intro] + lt_parts + [outro]
    montage_nomusic = concat_with_xfade(all_parts, work_dir)

    # I) Add music bed
    montage_final = add_music_bed(montage_nomusic, work_dir, date_str)

    # Verify duration
    final_info = ffprobe_info(montage_final)
    if not final_info:
        return {"error": "final_probe_failed"}

    log.info("Montage duration: %.1fs", final_info["duration"])

    # J) Generate shorts
    shorts_path = generate_shorts(montage_final, work_dir, date_str)

    # K) Generate thumbnail
    thumb_path = generate_thumbnail(clips[0]["file"], work_dir, date_str)

    # L) Copy to output + symlink
    copy_outputs(work_dir, date_str, output_dir)

    # Build metadata
    metadata = {
        "date": date_str,
        "title": f"Protocol Pulse Daily Highlights — {date_str}",
        "duration": round(final_info["duration"], 1),
        "clips_used": [
            {
                "channel": c["channel"],
                "video_title": c.get("video_title", ""),
                "score": c["score"],
                "quote": c.get("quote", ""),
            }
            for c in clips
        ],
        "montage_file": f"montage_{date_str}.mp4",
        "shorts_file": f"montage_{date_str}_shorts.mp4",
        "thumbnail_file": f"montage_thumb_{date_str}.jpg",
        "produced_at": datetime.now().isoformat(),
    }

    # Save metadata
    meta_path = output_dir / f"montage_{date_str}_meta.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    log.info("Metadata saved: %s", meta_path)

    log.info("=== MONTAGE COMPLETE — %s ===", date_str)
    return metadata


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = produce_montage(date_arg)
    if "error" in result:
        log.error("Montage failed: %s", result["error"])
        sys.exit(1)
    print(json.dumps(result, indent=2))
